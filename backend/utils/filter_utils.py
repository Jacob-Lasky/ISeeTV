"""Utility functions for precomputing and managing filter values."""

from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.log_utils import get_logger
from models.db_models import FilterValueTable

logger = get_logger(__name__)

FILTERABLE_COLUMNS_CONFIG = {
    "epg_channels": ["source", "filter_reasons"],
    "m3u_channels": ["source", "group", "stream_mode", "filter_reasons"],
    "programs": ["source", "filter_reasons"],
    "streams": ["source", "group", "stream_mode", "filter_reasons"],
}

# Special query configurations for complex filter types
SPECIAL_FILTER_QUERIES = {
    "streams": {
        "source": """
            SELECT source as value, COUNT(*) as count
            FROM m3u_channels
            WHERE source IS NOT NULL AND source != ''
            GROUP BY source
            ORDER BY source
        """,
        "group": """
            SELECT `group` as value, COUNT(*) as count
            FROM m3u_channels
            WHERE `group` IS NOT NULL AND `group` != ''
            GROUP BY `group`
            ORDER BY `group`
        """,
        "stream_mode": """
            SELECT stream_mode as value, COUNT(*) as count
            FROM m3u_channels
            WHERE stream_mode IS NOT NULL AND stream_mode != ''
            GROUP BY stream_mode
            ORDER BY stream_mode
        """,
        "filter_reasons": """
            WITH filter_values AS (
                SELECT 
                    CASE 
                        WHEN filter_reasons IS NULL OR filter_reasons = '' OR filter_reasons = '[]' THEN 'Passed'
                        ELSE TRIM(REPLACE(REPLACE(filter_reasons, '["', ''), '"]', ''))
                    END as value
                FROM m3u_channels
            )
            SELECT 
                value,
                COUNT(*) as count
            FROM filter_values
            WHERE value IS NOT NULL
            GROUP BY value
            ORDER BY value
        """,
    }
}


def _get_filter_query(table_name: str, column_name: str) -> str:
    """Get the appropriate SQL query for a specific table/column combination.

    Args:
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        SQL query string
    """
    # Check if there's a special query for this table/column combination
    if (
        table_name in SPECIAL_FILTER_QUERIES
        and column_name in SPECIAL_FILTER_QUERIES[table_name]
    ):
        return SPECIAL_FILTER_QUERIES[table_name][column_name]

    # Handle filter_reasons as a special case for regular tables
    if column_name == "filter_reasons":
        return f"""
            WITH filter_values AS (
                SELECT 
                    CASE 
                        WHEN filter_reasons IS NULL OR filter_reasons = '' OR filter_reasons = '[]' THEN 'Passed'
                        ELSE TRIM(REPLACE(REPLACE(filter_reasons, '["', ''), '"]', ''))
                    END as value
                FROM {table_name}
            )
            SELECT 
                value,
                COUNT(*) as count
            FROM filter_values
            WHERE value IS NOT NULL
            GROUP BY value
            ORDER BY value
        """

    # Standard column query
    safe_col = f"`{column_name}`"
    return f"""
        SELECT {safe_col} as value, COUNT(*) as count
        FROM {table_name}
        WHERE {safe_col} IS NOT NULL AND {safe_col} != ''
        GROUP BY {safe_col}
        ORDER BY {safe_col}
    """


def _precompute_column_values(
    session: Session, table_name: str, column_name: str
) -> List[FilterValueTable]:
    """Precompute filter values for a specific column.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        List of FilterValueTable objects
    """
    try:
        query = _get_filter_query(table_name, column_name)
        result = session.execute(text(query))

        filter_values = [
            FilterValueTable(
                table_name=table_name,
                column_name=column_name,
                value=row.value,
                count=row.count,
            )
            for row in result
            if row.value  # Skip empty values
        ]

        logger.debug(
            "Computed %s filter values for %s.%s",
            len(filter_values),
            table_name,
            column_name,
        )
        return filter_values

    except Exception:
        logger.exception(
            "Error computing filter values for %s.%s", table_name, column_name
        )
        raise


def precompute_filter_values(session: Session, table_name: str) -> None:
    """Precompute unique values for filterable columns in a table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table to process

    """
    if table_name not in FILTERABLE_COLUMNS_CONFIG:
        logger.warning("No filterable columns defined for table: %s", table_name)
        return

    logger.debug("Precomputing filter values for table: %s", table_name)

    try:
        # Clear existing filter values for this table
        session.query(FilterValueTable).filter(
            FilterValueTable.table_name == table_name
        ).delete()

        # Process each filterable column
        all_filter_values = []
        for column_name in FILTERABLE_COLUMNS_CONFIG[table_name]:
            column_values = _precompute_column_values(session, table_name, column_name)
            all_filter_values.extend(column_values)

        # Add all filter values in batch
        if all_filter_values:
            session.add_all(all_filter_values)
            session.commit()
            logger.info(
                "Successfully precomputed %s filter values for table: %s",
                len(all_filter_values),
                table_name,
            )
        else:
            logger.warning("No filter values found for table: %s", table_name)

    except Exception:
        logger.exception("Error precomputing filter values for table: %s", table_name)
        session.rollback()
        raise


def precompute_all_filter_values(session: Session) -> None:
    """Precompute filter values for all configured tables and views.

    Args:
        session: SQLAlchemy session
    """
    logger.info("Precomputing filter values for all tables")

    for table_name in FILTERABLE_COLUMNS_CONFIG.keys():
        try:
            precompute_filter_values(session, table_name)
        except Exception:
            logger.exception(
                "Failed to precompute filter values for table: %s", table_name
            )
            # Continue with other tables even if one fails

    logger.info("Completed precomputing filter values for all tables")


def get_filter_values(
    session: Session, table_name: str, column_name: str
) -> list[dict[str, Any]]:
    """Get precomputed filter values for a specific table and column.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        List of dictionaries with 'value' and 'count' keys

    """
    logger.info("Getting filter values for %s.%s", table_name, column_name)
    try:
        filter_values = (
            session.query(FilterValueTable)
            .filter(
                FilterValueTable.table_name == table_name,
                FilterValueTable.column_name == column_name,
            )
            .order_by(FilterValueTable.value)
            .all()
        )

        return [{"value": fv.value, "count": fv.count} for fv in filter_values]
    except Exception:
        logger.exception(
            "Error getting filter values for %s.%s", table_name, column_name
        )
        return []


def get_all_filter_values(
    session: Session, table_name: str
) -> dict[str, list[dict[str, Any]]]:
    """Get all precomputed filter values for a table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table

    Returns:
        Dictionary mapping column names to lists of filter values

    """
    logger.debug("Getting all filter values for %s", table_name)
    try:
        filter_values = (
            session.query(FilterValueTable)
            .filter(FilterValueTable.table_name == table_name)
            .order_by(FilterValueTable.column_name, FilterValueTable.value)
            .all()
        )

        result = {}
        for fv in filter_values:
            if fv.column_name not in result:
                result[fv.column_name] = []
            result[fv.column_name].append({"value": fv.value, "count": fv.count})

        return result
    except Exception:
        logger.exception("Error getting all filter values for %s", table_name)
        return {}


def get_table_filter_statistics(session: Session, table_name: str) -> dict[str, int]:
    """Get filter statistics for an entire table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table to get statistics for

    Returns:
        Dictionary mapping filter reason to count

    """
    logger.info("Getting filter statistics for table: %s", table_name)
    try:
        query = text(
            f"""
            SELECT 
                source,
                CASE 
                    WHEN filter_reasons = '[]' THEN 'Passed'
                    ELSE json_extract(filter_reasons, '$[0]') 
                END as reason,
                COUNT(*) as count
            FROM {table_name}
            GROUP BY source, filter_reasons
            ORDER BY source, count DESC
        """
        )

        result = session.execute(query)
        filter_stats = defaultdict(dict)
        for row in result:
            source = row.source
            reason = row.reason
            count = row.count
            filter_stats[source][reason] = count

        logger.info("Filter statistics for %s: %s", table_name, dict(filter_stats))

        return filter_stats

    except Exception:
        logger.exception("Error getting filter statistics for table %s", table_name)
        return {}


def get_table_filter_statistics_by_source(
    session: Session, table_name: str, source: str
) -> dict[str, int]:
    logger.debug(
        "Getting filter statistics for table: %s and source: %s", table_name, source
    )
    try:
        # Query using filter_reasons field - handle JSON arrays of assignment IDs
        # The filter_reasons column now contains JSON arrays like ["alice_sports_content"]
        query = text(
            f"""
            WITH expanded_reasons AS (
                SELECT 
                    t.id as table_id,
                    j.value as assignment_id
                FROM {table_name} t, json_each(t.filter_reasons) j
                WHERE t.source = :source
                    AND t.filter_reasons != '[]'
            )
            SELECT 
                assignment_id as reason,
                COUNT(*) as count
            FROM expanded_reasons
            WHERE assignment_id IS NOT NULL AND assignment_id != ''
            GROUP BY assignment_id
            
            UNION ALL
            
            SELECT 'Passed' as reason, COUNT(*) as count
            FROM {table_name}
            WHERE source = :source
                AND filter_reasons = '[]'
            
            ORDER BY count DESC
        """
        )

        result = session.execute(query, {"source": source})
        filter_stats = defaultdict(dict)
        all_not_passed = 0
        passed = 0
        total = 0

        for row in result:
            reason = row.reason
            count = row.count
            if reason != "Passed":
                all_not_passed += count
            else:
                passed += count
            total += count
            filter_stats[reason] = count

        logger.info("Filter statistics for %s: %s", table_name, dict(filter_stats))

        return {
            "filter_stats": filter_stats,
            "passed": passed,
            "all_not_passed": all_not_passed,
            "total": total,
        }

    except Exception:
        logger.exception(
            "Error getting filter statistics for table %s and source %s",
            table_name,
            source,
        )
        return {}
