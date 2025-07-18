"""Utility functions for streams view with atomic join logic."""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from models.db_models import M3uChannelTable, EpgChannelTable, ProgramTable
from models.stream_models import StreamChannel, StreamProgram
from utils.filter_utils import precompute_filter_values, get_all_filter_values
import logging
from common.utils import log_function
from datetime import datetime
from rules.ingestion_rules import IngestionRulesEngine

logger = logging.getLogger(__name__)


def _get_rules_filter_condition(source: Optional[str], filter_view: str = "normal") -> Optional[str]:
    """
    Atomic function to generate SQL WHERE condition for rules-based filtering.
    
    Uses the filter_reasons field populated by the post-load rules system to
    determine which records should be included based on filter view mode.
    
    For Normal/Inverse logic:
    - Normal: Shows intended result (excludes blacklisted for blacklist mode, shows only whitelisted for whitelist mode)
    - Inverse: Shows opposite (shows blacklisted for blacklist mode, excludes whitelisted for whitelist mode)
    - All: Shows everything regardless of rules
    
    Args:
        source: Source name to filter by (if None, applies to all sources)
        filter_view: Filter view mode ("normal", "inverse", "all")
        
    Returns:
        SQL WHERE condition string or None if no filtering needed
    """
    if filter_view == "all":
        # Show all rows, ignoring filter status
        return None
    
    log_function(f"Applying rules filtering for filter_view: {filter_view}")
    
    if filter_view == "normal":
        # Normal: Shows intended result based on rule mode
        # For blacklist mode: show records that passed (filter_reasons is null)
        # For whitelist mode: show records that matched rules (filter_reasons is not null)
        # Since most current assignments are blacklist, default to blacklist behavior
        # TODO: This could be enhanced to check actual rule_mode per source
        return "(m.filter_reasons IS NULL)"
    
    elif filter_view == "inverse":
        # Inverse: Shows opposite of intended result
        # For blacklist mode: show records that were filtered out (filter_reasons is not null)
        # For whitelist mode: show records that didn't match rules (filter_reasons is null)
        # Since most current assignments are blacklist, default to blacklist inverse behavior
        return "(m.filter_reasons IS NOT NULL)"
    else:
        # Default to showing all if unknown filter_view
        log_function(f"Unknown filter_view: {filter_view}, showing all records")
        return None


def get_filter_view_counts(
    session: Session,
    source: Optional[str] = None,
    group: Optional[str] = None,
    global_filter: Optional[str] = None,
    column_filters: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    """
    Atomic function to get counts for each filter view mode using a single optimized query.
    
    Args:
        session: SQLAlchemy session
        source: Filter by source name
        group: Filter by channel group
        global_filter: Global search term
        column_filters: Column-specific filters
        
    Returns:
        Dictionary with counts for normal, inverse, and all views
    """
    try:
        # Single query with conditional counting for all filter views
        base_query = """
            SELECT 
                COUNT(CASE WHEN m.filter_reasons IS NULL THEN 1 END) as normal_count,
                COUNT(CASE WHEN m.filter_reasons IS NOT NULL THEN 1 END) as inverse_count,
                COUNT(*) as all_count
            FROM m3u_channels m
            LEFT JOIN epg_channels e ON m.source = e.source AND m.tvg_id = e.channel_id
            LEFT JOIN (
                SELECT 
                    source,
                    channel_id,
                    COUNT(*) as program_count,
                    MIN(CASE WHEN start_time > datetime('now') THEN start_time END) as next_program_start,
                    MIN(CASE WHEN start_time > datetime('now') THEN title END) as next_program_title
                FROM programs 
                GROUP BY source, channel_id
            ) p ON m.source = p.source AND m.tvg_id = p.channel_id
        """
        
        where_conditions = []
        params = {}
        
        # Apply basic filters (same as main query)
        if source:
            where_conditions.append("m.source = :source")
            params["source"] = source
        if group:
            where_conditions.append("m.`group` = :group")
            params["group"] = group
        if global_filter:
            where_conditions.append(
                "(m.name LIKE :global_filter OR m.tvg_id LIKE :global_filter OR "
                "COALESCE(e.display_name, '') LIKE :global_filter OR "
                "COALESCE(m.`group`, '') LIKE :global_filter)"
            )
            params["global_filter"] = f"%{global_filter}%"
        
        # Apply column filters
        if column_filters:
            for column, value in column_filters.items():
                if value and column in ["name", "tvg_id", "group", "source"]:
                    if column == "name":
                        where_conditions.append("m.name LIKE :name_filter")
                        params["name_filter"] = f"%{value}%"
                    elif column == "tvg_id":
                        where_conditions.append("m.tvg_id LIKE :tvg_id_filter")
                        params["tvg_id_filter"] = f"%{value}%"
                    elif column == "group":
                        where_conditions.append("m.`group` = :group_filter")
                        params["group_filter"] = value
                    elif column == "source":
                        where_conditions.append("m.source = :source_filter")
                        params["source_filter"] = value
        
        # Add WHERE clause if conditions exist
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        # Execute single count query
        result = session.execute(text(base_query), params)
        row = result.fetchone()
        
        counts = {
            "normal": row.normal_count or 0,
            "inverse": row.inverse_count or 0,
            "all": row.all_count or 0
        }
        
        log_function(f"Filter view counts: {counts}")
        return counts
        
    except Exception as e:
        logger.error(f"Error getting filter view counts: {e}")
        return {"normal": 0, "inverse": 0, "all": 0}


def get_streams_query(
    session: Session,
    source: Optional[str] = None,
    group: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    sort_field: str = "name",
    sort_order: str = "asc",
    global_filter: Optional[str] = None,
    column_filters: Optional[Dict[str, str]] = None,
    apply_rules: bool = True,
    filter_view: str = "normal",
) -> Tuple[List[StreamChannel], int]:
    """
    Atomic function to get streams with joined M3U, EPG, and program data.
    
    Performs a complex LEFT JOIN query to combine:
    - m3u_channels (primary table with stream URLs)
    - epg_channels (display names and icons)
    - programs (aggregated counts and next program info)
    
    Optionally applies rules-based filtering using the filter_reasons field
    populated by the post-load rules system.
    
    Args:
        session: SQLAlchemy session
        source: Filter by source name
        group: Filter by channel group
        page: Page number (1-based)
        page_size: Number of records per page
        sort_field: Field to sort by
        sort_order: Sort order (asc/desc)
        global_filter: Global search term
        column_filters: Column-specific filters
        apply_rules: Whether to apply ingestion rules filtering
        filter_view: Filter view mode ("normal", "inverse", "all")

    Returns:
        Tuple of (stream_channels, total_count)
    """
    log_function(
        f"Executing streams query: page={page}, size={page_size}, source={source}, group={group}"
    )

    try:
        # Build the base query with LEFT JOINs
        # M3U channels as primary table, EPG channels and programs as supplementary
        base_query = """
        SELECT 
            m.id as m3u_id,
            m.source,
            m.tvg_id,
            m.name,
            m.stream_url,
            m.logo_url,
            m.`group`,
            m.stream_mode,
            e.id as epg_id,
            e.display_name,
            e.icon_url,
            m.created_at,
            m.updated_at,
            m.filter_reasons,
            COALESCE(p.program_count, 0) as program_count,
            p.next_program_title,
            p.next_program_start
        FROM m3u_channels m
        LEFT JOIN epg_channels e ON m.source = e.source AND m.tvg_id = e.channel_id
        LEFT JOIN (
            SELECT 
                source,
                channel_id,
                COUNT(*) as program_count,
                MIN(CASE WHEN start_time > datetime('now') THEN title END) as next_program_title,
                MIN(CASE WHEN start_time > datetime('now') THEN start_time END) as next_program_start
            FROM programs
            GROUP BY source, channel_id
        ) p ON m.source = p.source AND m.tvg_id = p.channel_id
        """

        # Build WHERE conditions
        where_conditions = []
        params = {}

        if source:
            where_conditions.append("m.source = :source")
            params["source"] = source

        if group:
            where_conditions.append("m.`group` = :group")
            params["group"] = group

        if global_filter:
            where_conditions.append(
                """
                (m.name LIKE :global_filter 
                OR m.tvg_id LIKE :global_filter 
                OR e.display_name LIKE :global_filter 
                OR m.`group` LIKE :global_filter)
            """
            )
            params["global_filter"] = f"%{global_filter}%"

        if column_filters:
            for column, value in column_filters.items():
                if value:
                    if column == "name":
                        where_conditions.append("m.name LIKE :name_filter")
                        params["name_filter"] = f"%{value}%"
                    elif column == "tvg_id":
                        where_conditions.append("m.tvg_id LIKE :tvg_id_filter")
                        params["tvg_id_filter"] = f"%{value}%"
                    elif column == "display_name":
                        where_conditions.append(
                            "e.display_name LIKE :display_name_filter"
                        )
                        params["display_name_filter"] = f"%{value}%"
                    elif column == "group":
                        where_conditions.append("m.`group` = :group_filter")
                        params["group_filter"] = value
                    elif column == "source":
                        where_conditions.append("m.source = :source_filter")
                        params["source_filter"] = value

        # Apply rules-based filtering if enabled
        if apply_rules:
            rules_condition = _get_rules_filter_condition(source, filter_view)
            if rules_condition:
                where_conditions.append(rules_condition)

        # Add WHERE clause if conditions exist
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Add ORDER BY
        valid_sort_fields = [
            "name",
            "tvg_id",
            "display_name",
            "group",
            "source",
            "program_count",
            "created_at",
            "updated_at",
        ]
        if sort_field not in valid_sort_fields:
            sort_field = "name"
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"

        # Map sort fields to actual column names
        sort_mapping = {
            "name": "m.name",
            "tvg_id": "m.tvg_id",
            "display_name": "e.display_name",
            "group": "m.`group`",
            "source": "m.source",
            "program_count": "program_count",
            "created_at": "m.created_at",
            "updated_at": "m.updated_at",
        }

        base_query += f" ORDER BY {sort_mapping[sort_field]} {sort_order.upper()}"

        # Get total count first
        count_query = f"""
        SELECT COUNT(*) as total
        FROM ({base_query}) as subquery
        """

        count_result = session.execute(text(count_query), params).fetchone()
        total_count = count_result.total if count_result else 0

        # Add pagination
        offset = (page - 1) * page_size
        base_query += f" LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset

        # Execute main query
        result = session.execute(text(base_query), params)

        # Convert to StreamChannel objects
        streams = []
        for row in result:
            stream = StreamChannel(
                m3u_id=row.m3u_id,
                source=row.source,
                tvg_id=row.tvg_id,
                name=row.name,
                stream_url=row.stream_url,
                logo_url=row.logo_url,
                group=row.group,
                stream_mode=row.stream_mode,
                epg_id=row.epg_id,
                display_name=row.display_name,
                icon_url=row.icon_url,
                created_at=(
                    datetime.fromisoformat(row.created_at.replace("Z", "+00:00"))
                    if isinstance(row.created_at, str)
                    else row.created_at
                ),
                updated_at=(
                    datetime.fromisoformat(row.updated_at.replace("Z", "+00:00"))
                    if isinstance(row.updated_at, str)
                    else row.updated_at
                ),
                program_count=row.program_count or 0,
                next_program_title=row.next_program_title,
                next_program_start=(
                    datetime.fromisoformat(
                        row.next_program_start.replace("Z", "+00:00")
                    )
                    if row.next_program_start
                    and isinstance(row.next_program_start, str)
                    else row.next_program_start
                ),
            )
            streams.append(stream)

        log_function(f"Retrieved {len(streams)} streams out of {total_count} total")
        return streams, total_count

    except Exception as e:
        logger.error(f"Error executing streams query: {e}")
        raise


def get_stream_programs_query(
    session: Session,
    channel_id: str,
    source: str,
    page: int = 1,
    page_size: int = 100,
    sort_field: str = "start_time",
    sort_order: str = "asc",
    global_filter: Optional[str] = None,
    column_filters: Optional[Dict[str, str]] = None,
) -> Tuple[List[StreamProgram], int]:
    """
    Atomic function to get programs for a specific channel with context.

    Args:
        session: SQLAlchemy session
        channel_id: Channel ID (tvg_id)
        source: Source name
        page: Page number (1-based)
        page_size: Number of records per page
        sort_field: Field to sort by
        sort_order: Sort order (asc/desc)
        global_filter: Global search term
        column_filters: Column-specific filters

    Returns:
        Tuple of (stream_programs, total_count)
    """
    log_function(
        f"Executing stream programs query: channel_id={channel_id}, source={source}"
    )

    try:
        # Build the base query with JOINs to get channel context
        base_query = """
        SELECT 
            p.id as program_id,
            p.source,
            p.program_id as program_uid,
            p.channel_id,
            p.start_time,
            p.end_time,
            p.title,
            p.description,
            p.created_at,
            p.updated_at,
            m.name as channel_name,
            e.display_name as channel_display_name,
            m.`group` as channel_group,
            m.stream_url,
            m.logo_url,
            e.icon_url
        FROM programs p
        LEFT JOIN m3u_channels m ON p.source = m.source AND p.channel_id = m.tvg_id
        LEFT JOIN epg_channels e ON p.source = e.source AND p.channel_id = e.channel_id
        WHERE p.channel_id = :channel_id AND p.source = :source
        """

        params = {"channel_id": channel_id, "source": source}

        # Add additional filters
        where_conditions = []

        if global_filter:
            where_conditions.append(
                """
                (p.title LIKE :global_filter 
                OR p.description LIKE :global_filter 
                OR m.name LIKE :global_filter 
                OR e.display_name LIKE :global_filter)
            """
            )
            params["global_filter"] = f"%{global_filter}%"

        if column_filters:
            for column, value in column_filters.items():
                if value:
                    if column == "title":
                        where_conditions.append("p.title LIKE :title_filter")
                        params["title_filter"] = f"%{value}%"
                    elif column == "description":
                        where_conditions.append(
                            "p.description LIKE :description_filter"
                        )
                        params["description_filter"] = f"%{value}%"

        # Add additional WHERE conditions
        if where_conditions:
            base_query += " AND " + " AND ".join(where_conditions)

        # Add ORDER BY
        valid_sort_fields = [
            "start_time",
            "end_time",
            "title",
            "created_at",
            "updated_at",
        ]
        if sort_field not in valid_sort_fields:
            sort_field = "start_time"
        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "asc"

        base_query += f" ORDER BY p.{sort_field} {sort_order.upper()}"

        # Get total count
        count_query = f"""
        SELECT COUNT(*) as total
        FROM ({base_query}) as subquery
        """

        count_result = session.execute(text(count_query), params).fetchone()
        total_count = count_result.total if count_result else 0

        # Add pagination
        offset = (page - 1) * page_size
        base_query += f" LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset

        # Execute main query
        result = session.execute(text(base_query), params)

        # Convert to StreamProgram objects
        programs = []
        for row in result:
            program = StreamProgram(
                program_id=row.program_id,
                source=row.source,
                program_uid=row.program_uid,
                channel_id=row.channel_id,
                start_time=(
                    datetime.fromisoformat(row.start_time.replace("Z", "+00:00"))
                    if isinstance(row.start_time, str)
                    else row.start_time
                ),
                end_time=(
                    datetime.fromisoformat(row.end_time.replace("Z", "+00:00"))
                    if isinstance(row.end_time, str)
                    else row.end_time
                ),
                title=row.title,
                description=row.description,
                created_at=(
                    datetime.fromisoformat(row.created_at.replace("Z", "+00:00"))
                    if isinstance(row.created_at, str)
                    else row.created_at
                ),
                updated_at=(
                    datetime.fromisoformat(row.updated_at.replace("Z", "+00:00"))
                    if isinstance(row.updated_at, str)
                    else row.updated_at
                ),
                channel_name=row.channel_name,
                channel_display_name=row.channel_display_name,
                channel_group=row.channel_group,
                stream_url=row.stream_url,
                logo_url=row.logo_url,
                icon_url=row.icon_url,
            )
            programs.append(program)

        log_function(
            f"Retrieved {len(programs)} programs out of {total_count} total for channel {channel_id}"
        )
        return programs, total_count

    except Exception as e:
        logger.error(f"Error executing stream programs query: {e}")
        raise


def precompute_streams_filter_values(session: Session) -> None:
    """
    Precompute filter values for the streams view.

    Args:
        session: SQLAlchemy session
    """
    log_function("Precomputing filter values for streams view")

    try:
        # Define filterable columns for streams view
        streams_filterable_columns = ["source", "group"]

        # Clear existing filter values for streams
        from models.db_models import FilterValueTable

        session.query(FilterValueTable).filter(
            FilterValueTable.table_name == "streams"
        ).delete()

        # Precompute source values from M3U channels
        source_query = text(
            """
            SELECT source as value, COUNT(*) as count
            FROM m3u_channels
            WHERE source IS NOT NULL AND source != ''
            GROUP BY source
            ORDER BY source
        """
        )

        source_result = session.execute(source_query)
        source_values = []
        for row in source_result:
            source_values.append(
                FilterValueTable(
                    table_name="streams",
                    column_name="source",
                    value=row.value,
                    count=row.count,
                )
            )

        # Precompute group values from M3U channels
        group_query = text(
            """
            SELECT `group` as value, COUNT(*) as count
            FROM m3u_channels
            WHERE `group` IS NOT NULL AND `group` != ''
            GROUP BY `group`
            ORDER BY `group`
        """
        )

        group_result = session.execute(group_query)
        group_values = []
        for row in group_result:
            group_values.append(
                FilterValueTable(
                    table_name="streams",
                    column_name="group",
                    value=row.value,
                    count=row.count,
                )
            )

        # Add all filter values
        all_values = source_values + group_values
        if all_values:
            session.add_all(all_values)
            session.commit()
            log_function(f"Added {len(all_values)} filter values for streams view")
        else:
            logger.warning("No filter values found for streams view")

    except Exception as e:
        logger.error(f"Error precomputing streams filter values: {e}")
        session.rollback()
        raise


def get_streams_filter_values(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get precomputed filter values for streams view.

    Args:
        session: SQLAlchemy session

    Returns:
        Dictionary mapping column names to filter values
    """
    try:
        return get_all_filter_values(session, "streams")
    except Exception as e:
        logger.error(f"Error getting streams filter values: {e}")
        return {}
