"""
Utility functions for precomputing and managing filter values.
"""

from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.db_models import FilterValueTable
import logging
from common.utils import log_function

logger = logging.getLogger(__name__)


def precompute_filter_values(session: Session, table_name: str) -> None:
    """
    Precompute unique values for filterable columns in a table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table to process
    """
    log_function(f"Precomputing filter values for table: {table_name}")
    # Define filterable columns for each table
    filterable_columns = {
        "epg_channels": ["source"],
        "m3u_channels": ["source", "group"],
        "programs": ["source"],
    }

    if table_name not in filterable_columns:
        logger.warning(f"No filterable columns defined for table: {table_name}")
        return

    logger.info(f"Precomputing filter values for table: {table_name}")

    # Clear existing filter values for this table
    session.query(FilterValueTable).filter(
        FilterValueTable.table_name == table_name
    ).delete()

    # Process each filterable column
    for column_name in filterable_columns[table_name]:
        try:
            # Query unique values and their counts
            query = text(
                f"""
                SELECT {column_name} as value, COUNT(*) as count
                FROM {table_name}
                WHERE {column_name} IS NOT NULL AND {column_name} != ''
                GROUP BY {column_name}
                ORDER BY {column_name}
            """
            )

            result = session.execute(query)

            # Insert filter values
            filter_values = []
            for row in result:
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
                logger.info(
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
    logger.info(f"Successfully precomputed filter values for table: {table_name}")


def get_filter_values(
    session: Session, table_name: str, column_name: str
) -> List[Dict[str, Any]]:
    """
    Get precomputed filter values for a specific table and column.

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
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all precomputed filter values for a table.

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
