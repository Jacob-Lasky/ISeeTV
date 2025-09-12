"""Generic table querying and pagination utilities.

Follows the same design principles used by streams utilities but works on any
single table (e.g., m3u_channels, epg_channels, programs).
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from common.db import engine
from common.filter_utils import get_all_filter_values
from common.log_utils import get_logger
from common.utils import validate_table_name
from models.models import TablePaginatedResponse, TableQueryParams

logger = get_logger(__name__)

# Targeted, well-known text-search fields per table for global filtering
TABLE_GLOBAL_FILTER_FIELDS: dict[str, list[str]] = {
    "m3u_channels": ["name", "tvg_id", "group", "source"],
    "epg_channels": ["channel_id", "display_name", "source"],
    "programs": ["title", "description", "channel_id", "source"],
}


def _quote_col(col: str) -> str:
    """Backtick-quote a column to avoid reserved word conflicts (e.g. `group`)."""
    return f"`{col}`"


def _get_columns(session: Session, table: str) -> list[str]:
    """Return list of actual columns for a table using SQLAlchemy inspection."""
    try:
        inspector = inspect(session.bind or engine)
        return [c["name"] for c in inspector.get_columns(table)]
    except Exception:
        logger.exception("Failed to inspect columns for table %s", table)
        return []


def _get_default_sort_field(columns: list[str]) -> str:
    for candidate in ("id", "created_at", "updated_at", "name"):
        if candidate in columns:
            return candidate
    return columns[0] if columns else "id"


def _rules_filter_condition(table_alias: str, filter_view: str) -> str | None:
    """Return a WHERE condition for rules-based filtering based on filter_reasons.

    - normal: rows that "passed" (filter_reasons == '[]')
    - inverse: rows that were filtered (filter_reasons != '[]')
    - all: no additional condition
    """
    if filter_view == "all":
        return None
    if filter_view == "normal":
        return f"({table_alias}.filter_reasons = '[]')"
    if filter_view == "inverse":
        return f"({table_alias}.filter_reasons != '[]')"
    # Unknown -> no extra filtering
    logger.info("Unknown filter_view: %s, defaulting to all", filter_view)
    return None


def _parse_column_filters(column_filters: str | None) -> dict[str, Any]:
    if not column_filters:
        return {}
    try:
        parsed = json.loads(column_filters)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Invalid column_filters JSON: %s", column_filters)
        return {}


def get_table_filter_view_counts(
    session: Session,
    table: str,
    source: str | None = None,
    global_filter: str | None = None,
    column_filters: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Get counts for normal/inverse/all views for a given table using a single query."""
    validate_table_name(table, include_streams=False)

    try:
        columns = _get_columns(session, table)
        table_alias = "t"

        base_query = f"""
            SELECT
                COUNT(CASE WHEN {table_alias}.filter_reasons = '[]' THEN 1 END) as normal_count,
                COUNT(CASE WHEN {table_alias}.filter_reasons != '[]' THEN 1 END) as inverse_count,
                COUNT(*) as all_count
            FROM {table} {table_alias}
        """

        where_clauses: list[str] = []
        params: dict[str, Any] = {}

        if source and "source" in columns:
            where_clauses.append(f"{table_alias}.source = :source")
            params["source"] = source

        # Global filter: targeted across pre-defined fields for this table
        if global_filter:
            candidates = [f for f in TABLE_GLOBAL_FILTER_FIELDS.get(table, []) if f in columns]
            if candidates:
                like_param = f"%{global_filter}%"
                ors = [f"COALESCE({table_alias}.{_quote_col(c)}, '') LIKE :global_filter" for c in candidates]
                where_clauses.append("(" + " OR ".join(ors) + ")")
                params["global_filter"] = like_param

        # Column filters
        if column_filters:
            for column, value in column_filters.items():
                if not value or column not in columns:
                    continue
                pname = f"cf_{column}"
                # Equality for some fields, LIKE for text-ish
                if column in {"source", "group", "stream_mode"}:
                    where_clauses.append(f"{table_alias}.{_quote_col(column)} = :{pname}")
                    params[pname] = value
                else:
                    where_clauses.append(f"{table_alias}.{_quote_col(column)} LIKE :{pname}")
                    params[pname] = f"%{value}%"

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        row = session.execute(text(base_query), params).fetchone()
        return {
            "normal": (row.normal_count or 0) if row else 0,
            "inverse": (row.inverse_count or 0) if row else 0,
            "all": (row.all_count or 0) if row else 0,
        }
    except Exception:
        logger.exception("Error computing filter view counts for %s", table)
        return {"normal": 0, "inverse": 0, "all": 0}


def get_table_query(
    session: Session,
    table: str,
    source: str | None,
    page: int,
    page_size: int,
    sort_field: str,
    sort_order: str,
    global_filter: str | None,
    column_filters: dict[str, Any] | None,
    apply_rules: bool,
    filter_view: str,
) -> tuple[list[dict[str, Any]], int]:
    """Generic query for any table with filtering, sorting, and pagination."""
    validate_table_name(table, include_streams=False)

    try:
        table_alias = "t"
        columns = _get_columns(session, table)
        if not columns:
            return [], 0

        # Validate sort field/order
        if sort_field not in columns:
            sort_field = _get_default_sort_field(columns)
        if sort_order.lower() not in {"asc", "desc"}:
            sort_order = "asc"

        base_query = f"SELECT * FROM {table} {table_alias}"

        where_clauses: list[str] = []
        params: dict[str, Any] = {}

        if source and "source" in columns:
            where_clauses.append(f"{table_alias}.source = :source")
            params["source"] = source

        # Global filter (targeted fields per table)
        if global_filter:
            candidates = [f for f in TABLE_GLOBAL_FILTER_FIELDS.get(table, []) if f in columns]
            if candidates:
                ors = [f"COALESCE({table_alias}.{_quote_col(c)}, '') LIKE :global_filter" for c in candidates]
                params["global_filter"] = f"%{global_filter}%"
                where_clauses.append("(" + " OR ".join(ors) + ")")

        # Column filters
        if column_filters:
            for column, value in column_filters.items():
                if not value or column not in columns:
                    continue
                pname = f"cf_{column}"
                if column in {"source", "group", "stream_mode"}:
                    where_clauses.append(f"{table_alias}.{_quote_col(column)} = :{pname}")
                    params[pname] = value
                else:
                    where_clauses.append(f"{table_alias}.{_quote_col(column)} LIKE :{pname}")
                    params[pname] = f"%{value}%"

        # Rules-based filter on filter_reasons when requested and column exists
        if apply_rules and "filter_reasons" in columns:
            condition = _rules_filter_condition(table_alias, filter_view)
            if condition:
                where_clauses.append(condition)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Sorting
        base_query += f" ORDER BY {table_alias}.{_quote_col(sort_field)} {sort_order.upper()}"

        # Count
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) sub"
        total_count = session.execute(text(count_query), params).scalar() or 0

        # Pagination
        offset = (page - 1) * page_size
        base_query += " LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset

        # Data
        result = session.execute(text(base_query), params)
        records = [dict(row._mapping) for row in result.fetchall()]
        return records, total_count
    except Exception:
        logger.exception("Error executing table query for %s", table)
        raise


def get_table_internal(
    session: Session,
    table: str,
    source: str,
    params: TableQueryParams,
) -> TablePaginatedResponse:
    """Shared internal logic for paginated table endpoints."""
    logger.info(
        "Getting table: table=%s, page=%s, size=%s, source=%s",
        table,
        params.page,
        params.page_size,
        source,
    )

    # Validate page_size
    page_size = min(params.page_size, 500)
    if page_size < 1:
        page_size = 100

    # Parse column filters
    parsed_column_filters = _parse_column_filters(params.column_filters)

    # Data
    records, total_count = get_table_query(
        session=session,
        table=table,
        source=source,
        page=params.page,
        page_size=page_size,
        sort_field=params.sort_field,
        sort_order=params.sort_order,
        global_filter=params.global_filter,
        column_filters=parsed_column_filters,
        apply_rules=params.apply_rules,
        filter_view=params.filter_view,
    )

    # Filters
    filters = get_all_filter_values(session, table)

    # Filter view counts (when applicable)
    filter_view_counts = (
        get_table_filter_view_counts(
            session=session,
            table=table,
            source=source,
            global_filter=params.global_filter,
            column_filters=parsed_column_filters,
        )
        if "filter_reasons" in _get_columns(session, table)
        else {"normal": total_count, "inverse": 0, "all": total_count}
    )

    total_pages = (total_count + page_size - 1) // page_size
    has_next = params.page < total_pages
    has_prev = params.page > 1

    return TablePaginatedResponse(
        success=True,
        data=records,
        total=total_count,
        page=params.page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        filters=filters,
        filter_view_counts=filter_view_counts,
    )
