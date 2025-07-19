"""Utility functions for precomputing and managing filter values."""

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.utils import log_function
from models.db_models import FilterValueTable

logger = logging.getLogger(__name__)


def precompute_filter_values(session: Session, table_name: str) -> None:
    """Precompute unique values for filterable columns in a table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table to process

    """
    log_function(f"Precomputing filter values for table: {table_name}")
    # Define filterable columns for each table
    filterable_columns = {
        "epg_channels": ["source", "filter_reasons"],
        "m3u_channels": ["source", "group", "stream_mode", "filter_reasons"],
        "programs": ["source", "filter_reasons"],
    }

    if table_name not in filterable_columns:
        logger.warning(f"No filterable columns defined for table: {table_name}")
        return

    log_function(f"Precomputing filter values for table: {table_name}")

    # Clear existing filter values for this table
    session.query(FilterValueTable).filter(
        FilterValueTable.table_name == table_name
    ).delete()

    # Process each filterable column
    for column_name in filterable_columns[table_name]:
        try:
            # Handle filter_reasons as a special case (JSON array)
            if column_name == "filter_reasons":
                # Query to extract individual filter reasons from JSON array
                # Use json_each with proper table aliases to avoid ambiguous column names
                query = text(
                    f"""
                    WITH expanded_reasons AS (
                        SELECT 
                            t.id as table_id,
                            j.value as filter_reasons
                        FROM {table_name} t, json_each(t.filter_reasons) j
                        WHERE t.filter_reasons != '[]'
                    )
                    SELECT 
                        filter_reasons as value,
                        COUNT(*) as count
                    FROM expanded_reasons
                    WHERE filter_reasons IS NOT NULL
                    GROUP BY filter_reasons
                    
                    UNION ALL
                    
                    SELECT 'Passed' as value, COUNT(*) as count
                    FROM {table_name}
                    WHERE filter_reasons = '[]'
                    
                    ORDER BY value
                """
                )
            else:
                # Regular column handling
                # Escape column names with backticks to handle reserved keywords like 'group'
                query = text(
                    f"""
                    SELECT `{column_name}` as value, COUNT(*) as count
                    FROM {table_name}
                    WHERE `{column_name}` IS NOT NULL AND `{column_name}` != ''
                    GROUP BY `{column_name}`
                    ORDER BY `{column_name}`
                """
                )

            result = session.execute(query)

            # Insert filter values
            filter_values = []
            for row in result:
                if (
                    row.value and row.count > 0
                ):  # Only add non-empty values with positive counts
                    filter_values.append(
                        FilterValueTable(
                            table_name=table_name,
                            column_name=column_name,
                            value=row.value,
                            count=row.count,
                        )
                    )

            if filter_values:
                session.add_all(filter_values)
                log_function(
                    f"Added {len(filter_values)} unique values for {table_name}.{column_name}"
                )
            else:
                logger.warning(f"No unique values found for {table_name}.{column_name}")

        except Exception as e:
            logger.error(
                f"Error precomputing filter values for {table_name}.{column_name}: {e}"
            )
            raise

    # Commit the changes
    session.commit()
    log_function(f"Successfully precomputed filter values for table: {table_name}")


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
    except Exception as e:
        logger.error(f"Error getting filter values for {table_name}.{column_name}: {e}")
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
    except Exception as e:
        logger.error(f"Error getting all filter values for {table_name}: {e}")
        return {}


def get_table_filter_statistics(session: Session, table_name: str) -> dict[str, int]:
    """Get filter statistics for an entire table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table to get statistics for

    Returns:
        Dictionary mapping filter reason to count

    """
    try:
        log_function(f"Getting filter statistics for table: {table_name}")

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

        log_function(f"Filter statistics for {table_name}: {dict(filter_stats)}")

        return filter_stats

    except Exception as e:
        logger.error(f"Error getting filter statistics for table {table_name}: {e}")
        return {}


def get_table_filter_statistics_by_source(
    session: Session, table_name: str, source: str
) -> dict[str, int]:
    try:
        log_function(
            f"Getting filter statistics for table: {table_name} and source: {source}"
        )

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

        log_function(f"Filter statistics for {table_name}: {dict(filter_stats)}")

        return {
            "filter_stats": filter_stats,
            "passed": passed,
            "all_not_passed": all_not_passed,
            "total": total,
        }

    except Exception as e:
        logger.error(
            f"Error getting filter statistics for table {table_name} and source {source}: {e}"
        )
        return {}
