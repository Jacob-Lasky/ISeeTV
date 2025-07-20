"""Ingestion Rules System - Prefilter for parsed data before database loading.

This module provides a plugin-based rule system that applies user-defined filters
to parsed data after parsing (epg_parser.py, m3u_parser.py) but before database
loading. Filtered-out rows are saved to JSON files with rejection reasons.

Architecture:
- Atomic Design: Each function has single responsibility
- Plugin System: Rules loaded from JSON configuration
- Modular: Clear separation between rule loading, application, and logging
- Scalable: Handles large datasets efficiently with streaming processing
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import pandas as pd

from common.constants import DATA_PATH
from common.log_utils import get_logger
from models.models import EpgChannel, M3uChannel, Program

logger = get_logger(__name__)

# Directory for storing filtered-out records
INGESTION_RULES_LOGS = os.path.join(DATA_PATH, "ingestion_rules_logs")
if not os.path.exists(INGESTION_RULES_LOGS):
    os.makedirs(INGESTION_RULES_LOGS, exist_ok=True)

# Rules configuration file
RULES_CONFIG_FILE = os.path.join(DATA_PATH, "rules.json")


@dataclass
class IngestionRule:
    """Atomic representation of a single ingestion rule pattern."""

    logger.debug("Creating ingestion rule")

    name: str
    tables: list[
        str
    ]  # Tables this rule applies to (e.g., ["m3u_channels", "epg_channels"])
    field: str  # Field name to apply regex to
    regex: str  # Regular expression pattern
    enabled: bool = True
    not_: bool = False  # If True, inverts the regex match (NOT matching the pattern)

    def __post_init__(self):
        """Validate rule configuration."""
        if not self.name or not self.name.strip():
            msg = "Rule name cannot be empty"
            raise ValueError(msg)
        if not self.tables:
            msg = "Rule must specify at least one table"
            raise ValueError(msg)
        if not self.field or not self.field.strip():
            msg = "Rule field cannot be empty"
            raise ValueError(msg)
        if not self.regex or not self.regex.strip():
            msg = "Rule regex cannot be empty"
            raise ValueError(msg)

        # Validate regex pattern
        try:
            re.compile(self.regex)
        except re.error as e:
            msg = f"Invalid regex pattern '{self.regex}': {e}"
            raise ValueError(msg)


@dataclass
class SourceRuleAssignment:
    """Named assignment of rules to a source with unique identifier."""

    logger.debug("Creating source rule assignment")

    id: str
    assignment_name: str
    source_name: str
    rule_mode: Literal[
        "whitelist", "blacklist"
    ]  # whitelist = start with 0, blacklist = start with all
    assigned_rules: list[str] = field(default_factory=list)  # List of rule names
    enabled: bool = True

    def __post_init__(self):
        """Validate source rule assignment."""
        if not self.id or not self.id.strip():
            msg = "Assignment ID cannot be empty"
            raise ValueError(msg)
        if not self.assignment_name or not self.assignment_name.strip():
            msg = "Assignment name cannot be empty"
            raise ValueError(msg)
        if not self.source_name or not self.source_name.strip():
            msg = "Source name cannot be empty"
            raise ValueError(msg)
        if self.rule_mode not in {"whitelist", "blacklist"}:
            msg = "Rule mode must be 'whitelist' or 'blacklist'"
            raise ValueError(msg)


@dataclass
class FilterResult:
    """Result of applying ingestion rules to a record."""

    logger.debug("Creating filter result")

    passed: bool  # True if record passes all rules
    rejected_by: str | None = None  # Name of rule that rejected the record
    reason: str | None = None  # Detailed rejection reason


class IngestionRulesEngine:
    """Engine for loading and applying source-based ingestion rules with caching."""

    logger.debug("Creating ingestion rules engine")

    def __init__(self, rules_file: str | None = None) -> None:
        """Initialize the rules engine with optional rules file path."""
        self.rules_file = rules_file or os.path.join(DATA_PATH, "rules.json")
        self.assignments_file = os.path.join(DATA_PATH, "assignments.json")
        self._rules_cache: list[IngestionRule] = []
        self._assignments_cache: list[SourceRuleAssignment] = []
        self._cache_timestamp: float | None = None
        self._compiled_patterns: dict[str, re.Pattern] = {}

    def _should_reload_rules(self) -> bool:
        """Check if rules file has been modified since last load."""
        logger.debug("Checking if rules file has been modified since last load")
        try:
            file_mtime = os.path.getmtime(self.rules_file)
            return self._cache_timestamp is None or file_mtime > self._cache_timestamp
        except (OSError, FileNotFoundError):
            return True

    def load_rules(self) -> tuple[list[IngestionRule], list[SourceRuleAssignment]]:
        """Load rules and source assignments from separate configuration files with caching."""
        # Define paths for separate files
        assignments_file = self.assignments_file

        # Check if we need to reload from files
        rules_mtime = (
            os.path.getmtime(self.rules_file) if os.path.exists(self.rules_file) else 0
        )
        assignments_mtime = (
            os.path.getmtime(assignments_file)
            if os.path.exists(assignments_file)
            else 0
        )
        latest_mtime = max(rules_mtime, assignments_mtime)

        if self._cache_timestamp is None or latest_mtime > self._cache_timestamp:
            logger.info(
                "Loading ingestion rules from %s and %s",
                self.rules_file,
                assignments_file,
            )
            rules = []
            assignments = []

            try:
                # Load rules from rules.json
                if os.path.exists(self.rules_file):
                    with open(self.rules_file, encoding="utf-8") as f:
                        rules_data = json.load(f)

                    # Handle both array format and object format
                    if isinstance(rules_data, list):
                        rules_list = rules_data
                    else:
                        rules_list = rules_data.get("rules", [])

                    logger.debug("Found %s rules in configuration", len(rules_list))
                    for rule_data in rules_list:
                        try:
                            rule = IngestionRule(**rule_data)
                            rules.append(rule)
                            logger.debug("Loaded rule: %s", rule.name)
                        except Exception:
                            logger.exception("Failed to parse rule %s", rule_data)
                            continue
                else:
                    logger.warning("Rules file not found: %s", self.rules_file)

                # Load assignments from assignments.json
                if os.path.exists(assignments_file):
                    with open(assignments_file, encoding="utf-8") as f:
                        assignments_data = json.load(f)

                    # Handle both array format and object format
                    if isinstance(assignments_data, list):
                        assignments_list = assignments_data
                    else:
                        assignments_list = assignments_data.get(
                            "source_assignments", []
                        )

                    logger.debug(
                        "Found %s source assignments in configuration",
                        len(assignments_list),
                    )
                    for assignment_data in assignments_list:
                        try:
                            assignment = SourceRuleAssignment(**assignment_data)
                            assignments.append(assignment)
                            logger.debug(
                                "Loaded assignment for source: %s",
                                assignment.source_name,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to parse assignment %s", assignment_data
                            )
                            continue
                else:
                    logger.warning("Assignments file not found: %s", assignments_file)

                # Update cache
                self._rules_cache = rules
                self._assignments_cache = assignments
                self._cache_timestamp = time.time()
                logger.info(
                    "Successfully loaded %s rules and %s assignments",
                    len(rules),
                    len(assignments),
                )

            except json.JSONDecodeError as e:
                logger.exception("Invalid JSON in configuration files: %s", e)
                self._rules_cache = []
                self._assignments_cache = []
                self._cache_timestamp = time.time()
            except Exception:
                logger.exception("Unexpected error loading rules")
                self._rules_cache = []
                self._assignments_cache = []
                self._cache_timestamp = time.time()

        return self._rules_cache, self._assignments_cache

    def get_applicable_rules(
        self, table_name: str, source_name: str
    ) -> list[IngestionRule]:
        """Get rules that apply to a specific table and source (atomic operation)."""
        logger.debug("Getting applicable rules for table and source")
        rules, _ = self.load_rules()

        # Get ALL assignments for this source (supports multi-assignment architecture)
        source_assignments = self.get_source_assignments(source_name)
        if not source_assignments:
            return []  # No rules assigned to this source

        # Collect all assigned rule names from all assignments for this source
        all_assigned_rule_names = set()
        for assignment in source_assignments:
            all_assigned_rule_names.update(assignment.assigned_rules)

        # Get applicable rules for this source and table
        applicable_rules = [rule for rule in rules if rule.enabled
                and table_name in rule.tables
                and rule.name in all_assigned_rule_names]

        logger.debug(
            "Found %s applicable rules for %s/%s: %s",
            len(applicable_rules),
            table_name,
            source_name,
            [r.name for r in applicable_rules],
        )
        return applicable_rules

    def get_source_assignments(self, source_name: str) -> list[SourceRuleAssignment]:
        """Get all assignments for a specific source (supports multi-assignment architecture)."""
        logger.debug("Getting all assignments for source: %s", source_name)
        _, assignments = self.load_rules()

        # Find all enabled assignments for this source
        source_assignments = [
            assignment
            for assignment in assignments
            if assignment.source_name == source_name and assignment.enabled
        ]

        logger.debug(
            "Found %s assignments for %s: %s",
            len(source_assignments),
            source_name,
            [a.id for a in source_assignments],
        )

        return source_assignments

    def get_assignment_by_id(self, assignment_id: str) -> SourceRuleAssignment | None:
        """Get a specific assignment by its ID."""
        logger.debug("Getting assignment by ID: %s", assignment_id)
        _, assignments = self.load_rules()

        for assignment in assignments:
            if assignment.id == assignment_id and assignment.enabled:
                return assignment

        return None

    def get_source_assignment(self, source_name: str) -> SourceRuleAssignment | None:
        """Legacy method for backwards compatibility - returns first assignment for source."""
        logger.debug("Getting source assignment for source: %s", source_name)
        assignments = self.get_source_assignments(source_name)
        return assignments[0] if assignments else None

    def get_all_source_assignments(self) -> list[SourceRuleAssignment]:
        """Get all enabled source assignments across all sources."""
        logger.debug("Getting all source assignments")
        _, assignments = self.load_rules()

        # Return all enabled assignments
        enabled_assignments = [
            assignment for assignment in assignments if assignment.enabled
        ]

        logger.debug(
            "Found %s enabled assignments: %s",
            len(enabled_assignments),
            [a.id for a in enabled_assignments],
        )

        return enabled_assignments

    def apply_rules_to_records_batch(
        self,
        records: list[M3uChannel | EpgChannel | Program],
        table_name: str,
        source_name: str,
    ) -> tuple[list[M3uChannel | EpgChannel | Program], list[dict[str, Any]]]:
        """Apply rules to a batch of records using vectorized operations for performance."""
        if not records:
            return [], []

        logger.info("Applying batch rules to %s records", len(records))

        # Get source assignment and applicable rules
        source_assignment = self.get_source_assignment(source_name)
        if not source_assignment:
            logger.info(
                "No source assignment found for %s, allowing all records", source_name
            )
            return records, []

        applicable_rules = self.get_applicable_rules(table_name, source_name)
        if not applicable_rules:
            logger.info(
                "No applicable rules for %s/%s, allowing all records",
                table_name,
                source_name,
            )
            return records, []

        # Convert records to DataFrame for vectorized operations
        try:
            records_data = [record.model_dump() for record in records]
            df = pd.DataFrame(records_data)
            logger.info(
                "Created DataFrame with %s rows and %s columns",
                len(df),
                len(df.columns),
            )
        except Exception:
            logger.exception("Failed to create DataFrame from records")
            # Fall back to single record processing
            return self._apply_rules_fallback(records, table_name, source_name)

        # Apply rules vectorized
        passed_mask = pd.Series([True] * len(df), index=df.index)
        rejected_records = []

        for rule in applicable_rules:
            if rule.field not in df.columns:
                logger.warning(
                    "Field '%s' not found in records, skipping rule '%s'",
                    rule.field,
                    rule.name,
                )
                continue

            try:
                # Vectorized regex matching
                field_series = df[rule.field].astype(str)
                matches = field_series.str.match(rule.regex, na=False)

                if source_assignment.rule_mode == "blacklist":
                    # Blacklist: matching records are rejected
                    rejected_mask = matches & passed_mask
                    passed_mask &= ~matches
                else:
                    # Whitelist: only matching records are allowed
                    passed_mask &= matches
                    rejected_mask = ~matches & passed_mask

                # Collect rejected records
                if rejected_mask.any():
                    rejected_indices = df[rejected_mask].index
                    for idx in rejected_indices:
                        record_dict = df.loc[idx].to_dict()
                        rejected_record = {
                            **record_dict,
                            "reason": f"{'Blacklist' if source_assignment.rule_mode == 'blacklist' else 'Whitelist'} rule '{rule.name}' {'matched' if source_assignment.rule_mode == 'blacklist' else 'did not match'} field '{rule.field}': {record_dict[rule.field]}",
                            "rejected_by": rule.name,
                            "rejected_at": datetime.now().isoformat(),
                            "source_name": source_name,
                            "table_name": table_name,
                        }
                        rejected_records.append(rejected_record)

            except Exception:
                logger.exception(
                    "Error applying rule '%s' with regex '%s'",
                    rule.name,
                    rule.regex,
                )
                continue

        # Filter records based on results
        passed_indices = df[passed_mask].index.tolist()
        filtered_records = [records[i] for i in passed_indices]

        logger.info(
            "Batch rule application complete: %s passed, %s rejected",
            len(filtered_records),
            len(rejected_records),
        )
        return filtered_records, rejected_records

    def _apply_rules_fallback(
        self,
        records: list[M3uChannel | EpgChannel | Program],
        table_name: str,
        source_name: str,
    ) -> tuple[list[M3uChannel | EpgChannel | Program], list[dict[str, Any]]]:
        """Fallback to single record processing if batch processing fails."""
        logger.warning("Falling back to single record processing")
        filtered_records = []
        rejected_records = []

        for record in records:
            result = self.apply_rules_to_record(record, table_name, source_name)
            if result.passed:
                filtered_records.append(record)
            else:
                record_dict = record.model_dump()
                rejected_record = {
                    **record_dict,
                    "reason": result.reason,
                    "rejected_by": result.rejected_by,
                    "rejected_at": datetime.now().isoformat(),
                    "source_name": source_name,
                    "table_name": table_name,
                }
                rejected_records.append(rejected_record)

        return filtered_records, rejected_records

    def apply_rules_to_record(
        self,
        record: M3uChannel | EpgChannel | Program,
        table_name: str,
        source_name: str,
    ) -> FilterResult:
        """Apply source-based rules to a single record (atomic operation)."""
        logger.debug("Applying rules to record")

        # Type safety checks
        if not isinstance(record, (M3uChannel, EpgChannel, Program)):
            logger.error(
                "Expected M3uChannel/EpgChannel/Program, got %s: %s",
                type(record),
                record,
            )
            return FilterResult(passed=True)  # Default to pass for unexpected types

        # Get source assignment to determine mode
        source_assignment = self.get_source_assignment(source_name)
        logger.debug("Source assignment for %s: %s", source_name, source_assignment)

        if not source_assignment:
            # No assignment for this source, default to pass (blacklist mode behavior)
            logger.debug(
                "No source assignment found for %s, defaulting to pass", source_name
            )
            return FilterResult(passed=True)

        # Get applicable rules for this source and table
        applicable_rules = self.get_applicable_rules(table_name, source_name)
        logger.debug(
            "Found %s applicable rules for %s/%s",
            len(applicable_rules),
            table_name,
            source_name,
        )

        # Log rule details
        for rule in applicable_rules:
            logger.debug(
                "Applicable rule: %s, field: %s, regex: %s",
                rule.name,
                rule.field,
                rule.regex,
            )

        # Convert record to dict for field access
        # Handle Pydantic models properly
        # Pydantic v2 models
        try:
            record_dict = record.model_dump()
            logger.debug("Converted record using model_dump(): %s", record_dict)
        except Exception:
            logger.exception("Failed to convert record using model_dump()")
            return FilterResult(passed=True)

        # Validate record_dict is actually a dict
        if not isinstance(record_dict, dict):
            logger.error(
                "Record conversion failed - expected dict, got %s: %s",
                type(record_dict),
                record_dict,
            )
            return FilterResult(passed=True)

        # Apply rules based on source mode
        if source_assignment.rule_mode == "whitelist":
            # Whitelist mode: start with rejected, rules can allow
            logger.debug("Applying whitelist rules to record")
            return self._apply_whitelist_rules(record_dict, applicable_rules)
        # Blacklist mode: start with allowed, rules can reject
        logger.debug("Applying blacklist rules to record")
        return self._apply_blacklist_rules(record_dict, applicable_rules)

    def _apply_whitelist_rules(
        self, record_dict: dict, rules: list[IngestionRule]
    ) -> FilterResult:
        """Apply rules in whitelist mode (start rejected, rules allow)."""
        logger.info("Applying whitelist rules")
        if not rules:
            # No rules in whitelist mode means reject everything
            return FilterResult(
                passed=False,
                rejected_by="whitelist_mode",
                reason="No whitelist rules matched",
            )

        # Check if any rule matches (allows the record)
        for rule in rules:
            field_value = record_dict.get(rule.field)
            if field_value is None:
                continue  # Skip rules for missing fields

            field_str = str(field_value)
            try:
                if re.search(rule.regex, field_str):
                    return FilterResult(passed=True)  # Rule matched, allow record
            except re.error as e:
                logger.exception("Regex error in rule '%s': %s", rule.name, e)
                continue

        # No rules matched in whitelist mode
        return FilterResult(
            passed=False,
            rejected_by="whitelist_mode",
            reason="No whitelist rules matched",
        )

    def _apply_blacklist_rules(
        self, record_dict: dict, rules: list[IngestionRule]
    ) -> FilterResult:
        """Apply rules in blacklist mode (start allowed, rules reject)."""
        logger.debug("Applying blacklist rules")
        if not rules:
            # No rules in blacklist mode means allow everything
            return FilterResult(passed=True)

        # Check if any rule matches (rejects the record)
        for rule in rules:
            field_value = record_dict.get(rule.field)
            if field_value is None:
                continue  # Skip rules for missing fields

            field_str = str(field_value)
            try:
                if re.search(rule.regex, field_str):
                    return FilterResult(
                        passed=False,
                        rejected_by=rule.name,
                        reason=f"Blacklist rule '{rule.name}' matched field '{rule.field}': {field_str}",
                    )
            except re.error as e:
                logger.exception("Regex error in rule '%s': %s", rule.name, e)
                continue

        # No blacklist rules matched, allow record
        return FilterResult(passed=True)

    def save_rejected_records(
        self, rejected_records: list[dict[str, Any]], table_name: str, source_name: str
    ) -> None:
        """Save rejected records to JSON file (atomic operation)."""
        logger.debug(
            "Saving %s rejected records to %s", len(rejected_records), table_name
        )
        if not rejected_records:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{table_name}_rejected_{timestamp}.json"
        filepath = os.path.join(INGESTION_RULES_LOGS, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rejected_records, f, indent=2, default=str)

            logger.info(
                "Saved %s rejected records to %s", len(rejected_records), filepath
            )

        except Exception:
            logger.exception("Error saving rejected records to %s", filepath)


# Global rules engine instance
rules_engine = IngestionRulesEngine()


def apply_ingestion_rules(
    records: list[M3uChannel | EpgChannel | Program],
    table_name: str,
    source_name: str,
) -> tuple[list[M3uChannel | EpgChannel | Program], list[dict[str, Any]]]:
    """Apply ingestion rules to a list of records and return filtered and rejected records."""
    logger.info(
        "Applying ingestion rules to %s %s records from %s",
        len(records),
        table_name,
        source_name,
    )

    # Type safety checks
    if not records:
        logger.info("No records to process")
        return [], []

    # Log first record for debugging
    first_record = records[0]
    logger.info(
        "First record type: %s, hasattr __dict__: %s, hasattr model_dump: %s, hasattr dict: %s",
        type(first_record),
        hasattr(first_record, "__dict__"),
        hasattr(first_record, "model_dump"),
        hasattr(first_record, "dict"),
    )

    if hasattr(first_record, "model_dump"):
        logger.info("First record model_dump: %s", first_record.model_dump())

    # Initialize rules engine
    rules_engine = IngestionRulesEngine()

    # Use batch processing for better performance on large datasets
    try:
        filtered_records, rejected_records = rules_engine.apply_rules_to_records_batch(
            records, table_name, source_name
        )

        logger.info(
            "Batch ingestion rules applied: %s records passed, %s records rejected",
            len(filtered_records),
            len(rejected_records),
        )

        # Save rejected records if any
        if rejected_records:
            rules_engine.save_rejected_records(
                rejected_records, table_name, source_name
            )

        return filtered_records, rejected_records

    except Exception:
        logger.exception(
            "Batch processing failed, falling back to single record processing"
        )

        # Fallback to single record processing
        filtered_records = []
        rejected_records = []

        for i, record in enumerate(records):
            if not isinstance(record, (M3uChannel, EpgChannel, Program)):
                logger.exception(
                    "Record %s has unexpected type %s: %s", i, type(record), record
                )
                continue

            # Apply rules to individual record
            result = rules_engine.apply_rules_to_record(record, table_name, source_name)

            if result.passed:
                filtered_records.append(record)
            else:
                # Convert record to dict for rejected records log
                try:
                    record_dict = record.model_dump()
                except Exception:
                    logger.exception("Failed to convert rejected record to dict")
                    continue

                rejected_record = {
                    **record_dict,
                    "reason": result.reason,
                    "rejected_by": result.rejected_by,
                    "rejected_at": datetime.now().isoformat(),
                    "source_name": source_name,
                    "table_name": table_name,
                }
                rejected_records.append(rejected_record)

        logger.info(
            "Fallback ingestion rules applied: %s records passed, %s records rejected",
            len(filtered_records),
            len(rejected_records),
        )

        # Save rejected records if any
        if rejected_records:
            rules_engine.save_rejected_records(
                rejected_records, table_name, source_name
            )

        return filtered_records, rejected_records


def save_rejected_records(
    rejected_records: list[dict[str, Any]], table_name: str, source_name: str
) -> None:
    """Save rejected records to JSON file (atomic operation)."""
    logger.info(
        "Saving %s rejected records to JSON file for %s (%s)",
        len(rejected_records),
        table_name,
        source_name,
    )
    if not rejected_records:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name}_{table_name}_rejected_{timestamp}.json"
    filepath = os.path.join(INGESTION_RULES_LOGS, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rejected_records, f, indent=2, default=str)

        logger.info("Saved %s rejected records to %s", len(rejected_records), filepath)

    except Exception:
        logger.exception("Error saving rejected records to %s", filepath)


def validate_rules_config(rules_data: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Validate rules configuration data (atomic operation).

    Args:
        rules_data: List of rule dictionaries to validate

    Returns:
        Tuple of (is_valid, error_messages)

    """
    logger.info("Validating rules configuration")
    errors = []

    if not isinstance(rules_data, list):
        return False, ["Rules configuration must be a list"]

    valid_tables = {"m3u_channels", "epg_channels", "programs"}

    for i, rule_data in enumerate(rules_data):
        if not isinstance(rule_data, dict):
            errors.append(f"Rule {i}: Must be an object")
            continue

        # Required fields
        required_fields = ["name", "tables", "field", "regex"]
        errors.extend(f"Rule {i}: Missing required field '{field}'" for field in required_fields if field not in rule_data)

        # Validate tables
        if "tables" in rule_data:
            if not isinstance(rule_data["tables"], list):
                errors.append(f"Rule {i}: 'tables' must be a list")
            else:
                errors.extend(f"Rule {i}: Invalid table '{table}'. Valid tables: {valid_tables}" for table in rule_data["tables"] if table not in valid_tables)

        # Validate regex
        if "regex" in rule_data:
            try:
                re.compile(rule_data["regex"])
            except re.error as e:
                errors.append(
                    f"Rule {i}: Invalid regex pattern '{rule_data['regex']}': {e}"
                )

        # Validate boolean fields
        errors.extend(f"Rule {i}: '{bool_field}' must be a boolean" for bool_field in ["is_whitelist", "enabled"] if bool_field in rule_data and not isinstance(rule_data[bool_field], bool))

    return len(errors) == 0, errors


def get_ingestion_rules_status() -> dict[str, Any]:
    """Get current status of ingestion rules system (atomic operation)."""
    logger.info("Getting rules status")
    rules_engine.load_rules()

    status = {
        "rules_loaded": len(rules_engine.rules),
        "rules_file_exists": os.path.exists(RULES_CONFIG_FILE),
        "logs_directory": INGESTION_RULES_LOGS,
        "rules_by_table": {},
    }

    # Group rules by table
    for rule in rules_engine.rules:
        for table in rule.tables:
            if table not in status["rules_by_table"]:
                status["rules_by_table"][table] = []
            status["rules_by_table"][table].append(
                {
                    "name": rule.name,
                    "field": rule.field,
                    "is_whitelist": rule.is_whitelist,
                    "enabled": rule.enabled,
                }
            )

    return status
