"""Ingestion Rules System - Prefilter for parsed data before database loading

This module provides a plugin-based rule system that applies user-defined filters
to parsed data after parsing (epg_parser.py, m3u_parser.py) but before database
loading. Filtered-out rows are saved to JSON files with rejection reasons.

Architecture:
- Atomic Design: Each function has single responsibility
- Plugin System: Rules loaded from JSON configuration
- Modular: Clear separation between rule loading, application, and logging
- Scalable: Handles large datasets efficiently with streaming processing
"""

from typing import List, Dict, Any, Optional, Tuple, Union, Literal
from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import re
import time
from datetime import datetime
import logging
import pandas as pd
import numpy as np

from models.models import EpgChannel, M3uChannel, Program
from common.utils import log_function
from common.constants import DATA_PATH

logger = logging.getLogger(__name__)

# Directory for storing filtered-out records
INGESTION_RULES_LOGS = os.path.join(DATA_PATH, "ingestion_rules_logs")
if not os.path.exists(INGESTION_RULES_LOGS):
    os.makedirs(INGESTION_RULES_LOGS, exist_ok=True)

# Rules configuration file
RULES_CONFIG_FILE = os.path.join(DATA_PATH, "rules.json")


@dataclass
class IngestionRule:
    """Atomic representation of a single ingestion rule pattern"""

    log_function("Creating ingestion rule")

    name: str
    tables: List[
        str
    ]  # Tables this rule applies to (e.g., ["m3u_channels", "epg_channels"])
    field: str  # Field name to apply regex to
    regex: str  # Regular expression pattern
    enabled: bool = True
    not_: bool = False  # If True, inverts the regex match (NOT matching the pattern)

    def __post_init__(self):
        """Validate rule configuration"""
        if not self.name or not self.name.strip():
            raise ValueError("Rule name cannot be empty")
        if not self.tables:
            raise ValueError("Rule must specify at least one table")
        if not self.field or not self.field.strip():
            raise ValueError("Rule field cannot be empty")
        if not self.regex or not self.regex.strip():
            raise ValueError("Rule regex cannot be empty")

        # Validate regex pattern
        try:
            re.compile(self.regex)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.regex}': {e}")


@dataclass
class SourceRuleAssignment:
    """Named assignment of rules to a source with unique identifier"""

    log_function("Creating source rule assignment")

    id: str
    assignment_name: str
    source_name: str
    rule_mode: Literal[
        "whitelist", "blacklist"
    ]  # whitelist = start with 0, blacklist = start with all
    assigned_rules: List[str] = field(default_factory=list)  # List of rule names
    enabled: bool = True

    def __post_init__(self):
        """Validate source rule assignment"""
        if not self.id or not self.id.strip():
            raise ValueError("Assignment ID cannot be empty")
        if not self.assignment_name or not self.assignment_name.strip():
            raise ValueError("Assignment name cannot be empty")
        if not self.source_name or not self.source_name.strip():
            raise ValueError("Source name cannot be empty")
        if self.rule_mode not in ["whitelist", "blacklist"]:
            raise ValueError("Rule mode must be 'whitelist' or 'blacklist'")


@dataclass
class FilterResult:
    """Result of applying ingestion rules to a record"""

    log_function("Creating filter result")

    passed: bool  # True if record passes all rules
    rejected_by: Optional[str] = None  # Name of rule that rejected the record
    reason: Optional[str] = None  # Detailed rejection reason


class IngestionRulesEngine:
    """Engine for loading and applying source-based ingestion rules with caching"""

    log_function("Creating ingestion rules engine")

    def __init__(self, rules_file: str = None):
        """Initialize the rules engine with optional rules file path"""
        self.rules_file = rules_file or os.path.join(DATA_PATH, "rules.json")
        self.assignments_file = os.path.join(DATA_PATH, "assignments.json")
        self._rules_cache: List[IngestionRule] = []
        self._assignments_cache: List[SourceRuleAssignment] = []
        self._cache_timestamp: Optional[float] = None
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    def _should_reload_rules(self) -> bool:
        """Check if rules file has been modified since last load"""
        log_function(
            "Checking if rules file has been modified since last load", level="debug"
        )
        try:
            file_mtime = os.path.getmtime(self.rules_file)
            return self._cache_timestamp is None or file_mtime > self._cache_timestamp
        except (OSError, FileNotFoundError):
            return True

    def load_rules(self) -> Tuple[List[IngestionRule], List[SourceRuleAssignment]]:
        """Load rules and source assignments from separate configuration files with caching"""
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
            log_function(
                f"Loading ingestion rules from {self.rules_file} and {assignments_file}"
            )
            rules = []
            assignments = []

            try:
                # Load rules from rules.json
                if os.path.exists(self.rules_file):
                    with open(self.rules_file, "r", encoding="utf-8") as f:
                        rules_data = json.load(f)

                    # Handle both array format and object format
                    if isinstance(rules_data, list):
                        rules_list = rules_data
                    else:
                        rules_list = rules_data.get("rules", [])

                    log_function(f"Found {len(rules_list)} rules in configuration")
                    for rule_data in rules_list:
                        try:
                            rule = IngestionRule(**rule_data)
                            rules.append(rule)
                            log_function(f"Loaded rule: {rule.name}")
                        except Exception as e:
                            logger.error(f"Failed to parse rule {rule_data}: {e}")
                            continue
                else:
                    logger.warning(f"Rules file not found: {self.rules_file}")

                # Load assignments from assignments.json
                if os.path.exists(assignments_file):
                    with open(assignments_file, "r", encoding="utf-8") as f:
                        assignments_data = json.load(f)

                    # Handle both array format and object format
                    if isinstance(assignments_data, list):
                        assignments_list = assignments_data
                    else:
                        assignments_list = assignments_data.get(
                            "source_assignments", []
                        )

                    log_function(
                        f"Found {len(assignments_list)} source assignments in configuration"
                    )
                    for assignment_data in assignments_list:
                        try:
                            assignment = SourceRuleAssignment(**assignment_data)
                            assignments.append(assignment)
                            logger.debug(
                                f"Loaded assignment for source: {assignment.source_name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to parse assignment {assignment_data}: {e}"
                            )
                            continue
                else:
                    logger.warning(f"Assignments file not found: {assignments_file}")

                # Update cache
                self._rules_cache = rules
                self._assignments_cache = assignments
                self._cache_timestamp = time.time()
                log_function(
                    f"Successfully loaded {len(rules)} rules and {len(assignments)} assignments"
                )

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in configuration files: {e}")
                self._rules_cache = []
                self._assignments_cache = []
                self._cache_timestamp = time.time()
            except Exception as e:
                logger.error(f"Unexpected error loading rules: {e}")
                self._rules_cache = []
                self._assignments_cache = []
                self._cache_timestamp = time.time()

        return self._rules_cache, self._assignments_cache

    def get_applicable_rules(
        self, table_name: str, source_name: str
    ) -> List[IngestionRule]:
        """Get rules that apply to a specific table and source (atomic operation)"""
        log_function("Getting applicable rules for table and source", level="debug")
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
        applicable_rules = []
        for rule in rules:
            if (
                rule.enabled
                and table_name in rule.tables
                and rule.name in all_assigned_rule_names
            ):
                applicable_rules.append(rule)

        log_function(
            f"Found {len(applicable_rules)} applicable rules for {table_name}/{source_name}: {[r.name for r in applicable_rules]}",
            level="debug"
        )
        return applicable_rules

    def get_source_assignments(self, source_name: str) -> List[SourceRuleAssignment]:
        """Get all assignments for a specific source (supports multi-assignment architecture)"""
        log_function(f"Getting all assignments for source: {source_name}", level="debug")
        _, assignments = self.load_rules()

        # Find all enabled assignments for this source
        source_assignments = [
            assignment for assignment in assignments 
            if assignment.source_name == source_name and assignment.enabled
        ]
        
        log_function(
            f"Found {len(source_assignments)} assignments for {source_name}: {[a.id for a in source_assignments]}",
            level="debug"
        )
        
        return source_assignments
    
    def get_assignment_by_id(self, assignment_id: str) -> Optional[SourceRuleAssignment]:
        """Get a specific assignment by its ID"""
        log_function(f"Getting assignment by ID: {assignment_id}", level="debug")
        _, assignments = self.load_rules()
        
        for assignment in assignments:
            if assignment.id == assignment_id and assignment.enabled:
                return assignment
                
        return None
        
    def get_source_assignment(self, source_name: str) -> Optional[SourceRuleAssignment]:
        """Legacy method for backwards compatibility - returns first assignment for source"""
        assignments = self.get_source_assignments(source_name)
        return assignments[0] if assignments else None
    
    def get_all_source_assignments(self) -> List[SourceRuleAssignment]:
        """Get all enabled source assignments across all sources"""
        log_function("Getting all source assignments", level="debug")
        _, assignments = self.load_rules()
        
        # Return all enabled assignments
        enabled_assignments = [assignment for assignment in assignments if assignment.enabled]
        
        log_function(
            f"Found {len(enabled_assignments)} enabled assignments: {[a.id for a in enabled_assignments]}",
            level="debug"
        )
        
        return enabled_assignments

    def apply_rules_to_records_batch(
        self,
        records: List[Union[M3uChannel, EpgChannel, Program]],
        table_name: str,
        source_name: str,
    ) -> Tuple[List[Union[M3uChannel, EpgChannel, Program]], List[Dict[str, Any]]]:
        """Apply rules to a batch of records using vectorized operations for performance"""
        if not records:
            return [], []

        log_function(f"Applying batch rules to {len(records)} records")

        # Get source assignment and applicable rules
        source_assignment = self.get_source_assignment(source_name)
        if not source_assignment:
            log_function(
                f"No source assignment found for {source_name}, allowing all records"
            )
            return records, []

        applicable_rules = self.get_applicable_rules(table_name, source_name)
        if not applicable_rules:
            log_function(
                f"No applicable rules for {table_name}/{source_name}, allowing all records"
            )
            return records, []

        # Convert records to DataFrame for vectorized operations
        try:
            records_data = [record.model_dump() for record in records]
            df = pd.DataFrame(records_data)
            log_function(
                f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns"
            )
        except Exception as e:
            logger.error(f"Failed to create DataFrame from records: {e}")
            # Fall back to single record processing
            return self._apply_rules_fallback(records, table_name, source_name)

        # Apply rules vectorized
        passed_mask = pd.Series([True] * len(df), index=df.index)
        rejected_records = []

        for rule in applicable_rules:
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
                    # Blacklist: matching records are rejected
                    rejected_mask = matches & passed_mask
                    passed_mask = passed_mask & ~matches
                else:
                    # Whitelist: only matching records are allowed
                    passed_mask = passed_mask & matches
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

            except Exception as e:
                logger.error(
                    f"Error applying rule '{rule.name}' with regex '{rule.regex}': {e}"
                )
                continue

        # Filter records based on results
        passed_indices = df[passed_mask].index.tolist()
        filtered_records = [records[i] for i in passed_indices]

        log_function(
            f"Batch processing complete: {len(filtered_records)} passed, {len(rejected_records)} rejected"
        )
        return filtered_records, rejected_records

    def _apply_rules_fallback(
        self,
        records: List[Union[M3uChannel, EpgChannel, Program]],
        table_name: str,
        source_name: str,
    ) -> Tuple[List[Union[M3uChannel, EpgChannel, Program]], List[Dict[str, Any]]]:
        """Fallback to single record processing if batch processing fails"""
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
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
    ) -> FilterResult:
        """Apply source-based rules to a single record (atomic operation)"""
        log_function("Applying rules to record", level="debug")

        # Type safety checks
        if not isinstance(record, (M3uChannel, EpgChannel, Program)):
            logger.error(
                f"Expected M3uChannel/EpgChannel/Program, got {type(record)}: {record}"
            )
            return FilterResult(passed=True)  # Default to pass for unexpected types

        # Get source assignment to determine mode
        source_assignment = self.get_source_assignment(source_name)
        log_function(
            f"Source assignment for {source_name}: {source_assignment}", level="debug"
        )

        if not source_assignment:
            # No assignment for this source, default to pass (blacklist mode behavior)
            log_function(
                f"No source assignment found for {source_name}, defaulting to pass",
                level="debug",
            )
            return FilterResult(passed=True)

        # Get applicable rules for this source and table
        applicable_rules = self.get_applicable_rules(table_name, source_name)
        log_function(
            f"Found {len(applicable_rules)} applicable rules for {table_name}/{source_name}",
            level="debug",
        )

        # Log rule details
        for rule in applicable_rules:
            log_function(
                f"Applicable rule: {rule.name}, field: {rule.field}, regex: {rule.regex}",
                level="debug",
            )

        # Convert record to dict for field access
        # Handle Pydantic models properly
        # Pydantic v2 models
        try:
            record_dict = record.model_dump()
            log_function(
                f"Converted record using model_dump(): {record_dict}", level="debug"
            )
        except Exception as e:
            logger.error(f"Failed to convert record using model_dump(): {e}")
            return FilterResult(passed=True)

        # Validate record_dict is actually a dict
        if not isinstance(record_dict, dict):
            logger.error(
                f"Record conversion failed - expected dict, got {type(record_dict)}: {record_dict}"
            )
            return FilterResult(passed=True)

        # Apply rules based on source mode
        if source_assignment.rule_mode == "whitelist":
            # Whitelist mode: start with rejected, rules can allow
            log_function(f"Applying whitelist rules to record", level="debug")
            return self._apply_whitelist_rules(record_dict, applicable_rules)
        else:
            # Blacklist mode: start with allowed, rules can reject
            log_function(f"Applying blacklist rules to record", level="debug")
            return self._apply_blacklist_rules(record_dict, applicable_rules)

    def _apply_whitelist_rules(
        self, record_dict: dict, rules: List[IngestionRule]
    ) -> FilterResult:
        """Apply rules in whitelist mode (start rejected, rules allow)"""
        log_function("Applying whitelist rules")
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
                logger.error(f"Regex error in rule '{rule.name}': {e}")
                continue

        # No rules matched in whitelist mode
        return FilterResult(
            passed=False,
            rejected_by="whitelist_mode",
            reason="No whitelist rules matched",
        )

    def _apply_blacklist_rules(
        self, record_dict: dict, rules: List[IngestionRule]
    ) -> FilterResult:
        """Apply rules in blacklist mode (start allowed, rules reject)"""
        log_function("Applying blacklist rules", level="debug")
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
                logger.error(f"Regex error in rule '{rule.name}': {e}")
                continue

        # No blacklist rules matched, allow record
        return FilterResult(passed=True)

    def save_rejected_records(
        self, rejected_records: List[Dict[str, Any]], table_name: str, source_name: str
    ) -> None:
        """Save rejected records to JSON file (atomic operation)"""
        if not rejected_records:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{table_name}_rejected_{timestamp}.json"
        filepath = os.path.join(INGESTION_RULES_LOGS, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rejected_records, f, indent=2, default=str)

            log_function(
                f"Saved {len(rejected_records)} rejected records to {filepath}"
            )

        except Exception as e:
            logger.error(f"Error saving rejected records to {filepath}: {e}")


# Global rules engine instance
rules_engine = IngestionRulesEngine()


def apply_ingestion_rules(
    records: List[Union[M3uChannel, EpgChannel, Program]],
    table_name: str,
    source_name: str,
) -> Tuple[List[Union[M3uChannel, EpgChannel, Program]], List[Dict[str, Any]]]:
    """Apply ingestion rules to a list of records and return filtered and rejected records"""
    log_function(
        f"Applying ingestion rules to {len(records)} {table_name} records from {source_name}"
    )

    # Type safety checks
    if not records:
        log_function("No records to process")
        return [], []

    # Log first record for debugging
    first_record = records[0]
    log_function(
        f"First record type: {type(first_record)}, hasattr __dict__: {hasattr(first_record, '__dict__')}, hasattr model_dump: {hasattr(first_record, 'model_dump')}, hasattr dict: {hasattr(first_record, 'dict')}"
    )

    if hasattr(first_record, "model_dump"):
        log_function(f"First record model_dump: {first_record.model_dump()}")

    # Initialize rules engine
    rules_engine = IngestionRulesEngine()

    # Use batch processing for better performance on large datasets
    try:
        filtered_records, rejected_records = rules_engine.apply_rules_to_records_batch(
            records, table_name, source_name
        )

        log_function(
            f"Batch ingestion rules applied: {len(filtered_records)} records passed, {len(rejected_records)} records rejected"
        )

        # Save rejected records if any
        if rejected_records:
            rules_engine.save_rejected_records(
                rejected_records, table_name, source_name
            )

        return filtered_records, rejected_records

    except Exception as e:
        logger.error(
            f"Batch processing failed, falling back to single record processing: {e}"
        )

        # Fallback to single record processing
        filtered_records = []
        rejected_records = []

        for i, record in enumerate(records):
            if not isinstance(record, (M3uChannel, EpgChannel, Program)):
                logger.error(f"Record {i} has unexpected type {type(record)}: {record}")
                continue

            # Apply rules to individual record
            result = rules_engine.apply_rules_to_record(record, table_name, source_name)

            if result.passed:
                filtered_records.append(record)
            else:
                # Convert record to dict for rejected records log
                try:
                    record_dict = record.model_dump()
                except Exception as e:
                    logger.error(f"Failed to convert rejected record to dict: {e}")
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

        log_function(
            f"Fallback ingestion rules applied: {len(filtered_records)} records passed, {len(rejected_records)} records rejected"
        )

        # Save rejected records if any
        if rejected_records:
            rules_engine.save_rejected_records(
                rejected_records, table_name, source_name
            )

        return filtered_records, rejected_records


def save_rejected_records(
    rejected_records: List[Dict[str, Any]], table_name: str, source_name: str
) -> None:
    """Save rejected records to JSON file (atomic operation)"""
    log_function(
        f"Saving rejected records to JSON file for {table_name} ({source_name})"
    )
    if not rejected_records:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{source_name}_{table_name}_rejected_{timestamp}.json"
    filepath = os.path.join(INGESTION_RULES_LOGS, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rejected_records, f, indent=2, default=str)

        log_function(f"Saved {len(rejected_records)} rejected records to {filepath}")

    except Exception as e:
        logger.error(f"Error saving rejected records to {filepath}: {e}")


def validate_rules_config(rules_data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate rules configuration data (atomic operation)

    Args:
        rules_data: List of rule dictionaries to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    log_function("Validating rules configuration")
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
        for field in required_fields:
            if field not in rule_data:
                errors.append(f"Rule {i}: Missing required field '{field}'")

        # Validate tables
        if "tables" in rule_data:
            if not isinstance(rule_data["tables"], list):
                errors.append(f"Rule {i}: 'tables' must be a list")
            else:
                for table in rule_data["tables"]:
                    if table not in valid_tables:
                        errors.append(
                            f"Rule {i}: Invalid table '{table}'. Valid tables: {valid_tables}"
                        )

        # Validate regex
        if "regex" in rule_data:
            try:
                re.compile(rule_data["regex"])
            except re.error as e:
                errors.append(
                    f"Rule {i}: Invalid regex pattern '{rule_data['regex']}': {e}"
                )

        # Validate boolean fields
        for bool_field in ["is_whitelist", "enabled"]:
            if bool_field in rule_data and not isinstance(rule_data[bool_field], bool):
                errors.append(f"Rule {i}: '{bool_field}' must be a boolean")

    return len(errors) == 0, errors


def get_ingestion_rules_status() -> Dict[str, Any]:
    """Get current status of ingestion rules system (atomic operation)"""
    log_function("Getting rules status")
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
