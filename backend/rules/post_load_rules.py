"""Post-Load Rules System - Apply rules after data is loaded into database

This module provides a post-load rule system that applies user-defined filters
to data after it has been loaded into the database. Records are marked with
filter_reason field for traceability instead of being removed.

Architecture:
- Atomic Design: Each function has single responsibility
- Post-Load Processing: Rules applied after database insertion
- Traceability: Records marked with filter reason instead of deletion
- Vectorized: Uses pandas for performance on large datasets
"""

from typing import Any, Dict, List
import logging

import pandas as pd

from sqlalchemy import text
from common.db import SessionLocal
from rules.ingestion_rules import (
    IngestionRule,
    SourceRuleAssignment,
    IngestionRulesEngine,
)
from common.utils import log_function

logger = logging.getLogger(__name__)


class PostLoadRulesEngine:
    """Engine for applying rules to database records after loading"""

    def __init__(self):
        """Initialize the post-load rules engine"""
        log_function("PostLoadRulesEngine initialized", level="debug")
        self.ingestion_engine = IngestionRulesEngine()

    def apply_rules_to_table(self, table_name: str, source_name: str) -> Dict[str, Any]:
        """Apply rules to all records in a specific table for a source"""
        log_function(
            f"Applying post-load rules to {table_name} for source {source_name}"
        )

        # Get source assignment and applicable rules
        source_assignment = self.ingestion_engine.get_source_assignment(source_name)
        if not source_assignment:
            log_function(
                f"No source assignment found for {source_name}, skipping rule application"
            )
            return {"processed": 0, "filtered": 0, "passed": 0}

        applicable_rules = self.ingestion_engine.get_applicable_rules(
            table_name, source_name
        )
        if not applicable_rules:
            log_function(
                f"No applicable rules for {table_name}/{source_name}, skipping rule application"
            )
            return {"processed": 0, "filtered": 0, "passed": 0}

        # Load records from database
        records = self._load_records_from_db(table_name, source_name)
        if not records:
            log_function(f"No records found in {table_name} for source {source_name}")
            return {"processed": 0, "filtered": 0, "passed": 0}

        log_function(
            f"Loaded {len(records)} records from {table_name} for {source_name}"
        )

        # Apply rules using vectorized processing
        results = self._apply_rules_vectorized(
            records, applicable_rules, source_assignment, table_name
        )

        # Update database with filter reasons
        self._update_records_in_db(table_name, results["updated_records"])

        log_function(
            f"Post-load rules applied to {table_name}/{source_name}: {results['processed']} processed, {results['filtered']} filtered, {results['passed']} passed"
        )

        return results

    def _load_records_from_db(
        self, table_name: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Load records from database for rule processing"""
        log_function(
            f"Loading records from {table_name} for source {source_name}", level="debug"
        )
        try:
            with SessionLocal() as session:
                # Use raw SQL for direct database access
                result = session.execute(
                    text(f"SELECT * FROM {table_name} WHERE source = :source_name"),
                    {"source_name": source_name},
                )

                # Get column names
                columns = result.keys()

                # Fetch all records
                rows = result.fetchall()

                # Convert to list of dictionaries
                records = []
                for row in rows:
                    record_dict = dict(zip(columns, row))
                    records.append(record_dict)

                return records

        except Exception as e:
            logger.error(f"Error loading records from {table_name}: {e}")
            return []

    def _apply_rules_vectorized(
        self,
        records: List[Dict[str, Any]],
        rules: List[IngestionRule],
        source_assignment: SourceRuleAssignment,
        table_name: str,
    ) -> Dict[str, Any]:
        """Apply rules to records using vectorized operations"""
        try:
            # Create DataFrame for vectorized processing
            df = pd.DataFrame(records)
            log_function(
                f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns",
                level="debug",
            )

            # Initialize filter reason column
            df["filter_reason"] = None

            # Track filtering results
            passed_mask = pd.Series([True] * len(df), index=df.index)
            filtered_count = 0

            for rule in rules:
                if rule.field not in df.columns:
                    logger.warning(
                        f"Field '{rule.field}' not found in records, skipping rule '{rule.name}'"
                    )
                    continue

                try:
                    # Vectorized regex matching
                    field_series = df[rule.field].astype(str)
                    matches = field_series.str.match(rule.regex, na=False)

                    if source_assignment.rule_mode == "blacklist":
                        # Blacklist: matching records are filtered
                        filtered_mask = matches & passed_mask
                        passed_mask = passed_mask & ~matches

                        # Set filter reason for blacklisted records
                        df.loc[filtered_mask, "filter_reason"] = (
                            f"Blacklisted by rule '{rule.name}': matched pattern '{rule.regex}' in field '{rule.field}'"
                        )

                    else:
                        # Whitelist: only matching records pass
                        filtered_mask = ~matches & passed_mask
                        passed_mask = passed_mask & matches

                        # Set filter reason for non-whitelisted records
                        df.loc[filtered_mask, "filter_reason"] = (
                            f"Not whitelisted by rule '{rule.name}': did not match pattern '{rule.regex}' in field '{rule.field}'"
                        )

                    filtered_count += filtered_mask.sum()

                except Exception as e:
                    logger.error(
                        f"Error applying rule '{rule.name}' with regex '{rule.regex}': {e}"
                    )
                    continue

            # Convert back to list of dictionaries
            updated_records = df.to_dict("records")

            results = {
                "processed": len(records),
                "filtered": filtered_count,
                "passed": passed_mask.sum(),
                "updated_records": updated_records,
            }

            return results

        except Exception as e:
            logger.error(f"Error in vectorized rule application: {e}")
            return {
                "processed": len(records),
                "filtered": 0,
                "passed": len(records),
                "updated_records": records,
            }

    def _update_records_in_db(
        self, table_name: str, records: List[Dict[str, Any]]
    ) -> None:
        """Update records in database with filter reasons"""
        log_function(
            f"Updating records in {table_name} with filter reasons", level="debug"
        )
        try:
            with SessionLocal() as session:
                # Update each record with its filter reason
                for record in records:
                    # Get the primary key (assuming 'id' exists)
                    if "id" not in record:
                        logger.warning(
                            f"No 'id' field found in record, skipping update"
                        )
                        continue

                    # Use SQLAlchemy text for raw SQL execution
                    session.execute(
                        text(
                            "UPDATE {} SET filter_reason = :filter_reason WHERE id = :record_id".format(
                                table_name
                            )
                        ),
                        {
                            "filter_reason": record.get("filter_reason"),
                            "record_id": record["id"],
                        },
                    )

                session.commit()
                log_function(
                    f"Updated {len(records)} records in {table_name} with filter reasons"
                )

        except Exception as e:
            logger.error(f"Error updating records in {table_name}: {e}")

    def apply_rules_to_all_sources(self, table_name: str) -> Dict[str, Any]:
        """Apply rules to all sources in a table"""
        log_function(f"Applying post-load rules to all sources in {table_name}")

        # Get all unique sources from the table
        sources = self._get_sources_from_table(table_name)

        total_results = {"processed": 0, "filtered": 0, "passed": 0}

        for source in sources:
            results = self.apply_rules_to_table(table_name, source)
            total_results["processed"] += results["processed"]
            total_results["filtered"] += results["filtered"]
            total_results["passed"] += results["passed"]

        log_function(
            f"Post-load rules applied to all sources in {table_name}: {total_results}"
        )
        return total_results

    def _get_sources_from_table(self, table_name: str) -> List[str]:
        """Get all unique sources from a table"""
        log_function(f"Getting sources from {table_name}", level="debug")
        try:
            with SessionLocal() as session:
                result = session.execute(
                    text(f"SELECT DISTINCT source FROM {table_name}")
                )
                sources = [row[0] for row in result.fetchall()]
                return sources

        except Exception as e:
            logger.error(f"Error getting sources from {table_name}: {e}")
            return []


# Global post-load rules engine instance
post_load_engine = PostLoadRulesEngine()


def apply_post_load_rules(table_name: str, source_name: str = None) -> Dict[str, Any]:
    """Apply post-load rules to a table (atomic operation)"""
    log_function(f"Applying post-load rules to {table_name}")
    if source_name:
        return post_load_engine.apply_rules_to_table(table_name, source_name)
    else:
        return post_load_engine.apply_rules_to_all_sources(table_name)
