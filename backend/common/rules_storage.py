"""Atomic rules and assignments storage utilities following atomic design principles.

This module provides atomic functions for saving and loading ingestion rules
and source rule assignments to separate JSON files.
"""

import os
from typing import Any

from common.constants import DATA_PATH
from common.file_utils import atomic_read_json, atomic_write_json, ensure_file_exists
from common.log_utils import get_logger
from rules.ingestion_rules import IngestionRule, SourceRuleAssignment

logger = get_logger(__name__)

# File paths for rules and assignments
RULES_FILE = os.path.join(DATA_PATH, "rules.json")
ASSIGNMENTS_FILE = os.path.join(DATA_PATH, "assignments.json")


def save_rules(rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Atomically save ingestion rules to rules.json file.

    Args:
        rules: List of rule dictionaries to save

    Returns:
        Dict with success status and message

    Raises:
        Exception: If file operations fail

    """
    logger.info("Saving %s rules to %s", len(rules), RULES_FILE)

    # Debug: Log incoming rules data
    for i, rule_data in enumerate(rules):
        logger.debug("Rule %d incoming data: %s", i, rule_data)

    try:
        # Validate rules structure
        validated_rules = []
        for i, rule_data in enumerate(rules):
            logger.debug("Validating rule %d: %s", i, rule_data)

            # Create IngestionRule object for validation
            ingestion_rule = IngestionRule(**rule_data)
            logger.debug(
                "Rule %d validation passed, IngestionRule object: %s", i, ingestion_rule
            )

            # Convert back to dict to preserve all fields
            rule_dict = {
                "name": ingestion_rule.name,
                "tables": ingestion_rule.tables,
                "field": ingestion_rule.field,
                "regex": ingestion_rule.regex,
                "enabled": ingestion_rule.enabled,
                "not_": ingestion_rule.not_,
            }
            
            # Preserve labels if present in original data
            if 'labels' in rule_data:
                rule_dict['labels'] = rule_data['labels']

            validated_rules.append(rule_dict)
            logger.debug("Rule %d final dict: %s", i, rule_dict)

        # Debug: Log what we're about to save
        logger.debug("About to save %d rules to file:", len(validated_rules))
        for i, rule in enumerate(validated_rules):
            logger.debug("Final rule %d: %s", i, rule)

        # Atomically write rules to file
        atomic_write_json(RULES_FILE, validated_rules)

        logger.info("Successfully saved %s rules", len(validated_rules))
        return {
            "success": True,
            "message": f"Successfully saved {len(validated_rules)} rules",
        }

    except Exception as e:
        logger.exception("Error saving rules: %s", e)
        raise


def save_assignments(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Atomically save source rule assignments to assignments.json file.

    Args:
        assignments: List of assignment dictionaries to save

    Returns:
        Dict with success status and message

    Raises:
        Exception: If file operations fail

    """
    logger.info("Saving %s assignments to %s", len(assignments), ASSIGNMENTS_FILE)

    try:
        # Filter out unknown fields before validation and saving
        valid_fields = {
            "id",
            "assignment_name",
            "source_name",
            "rule_mode",
            "assigned_rules",
            "enabled",
        }
        cleaned_assignments = []

        for assignment_data in assignments:
            # Filter out unknown fields (like filter_stats)
            cleaned_data = {
                k: v for k, v in assignment_data.items() if k in valid_fields
            }

            # Normalize assigned_rules to always be an array (atomic design)
            if "assigned_rules" in cleaned_data:
                if isinstance(cleaned_data["assigned_rules"], str):
                    cleaned_data["assigned_rules"] = [cleaned_data["assigned_rules"]]
                elif not isinstance(cleaned_data["assigned_rules"], list):
                    cleaned_data["assigned_rules"] = []
            else:
                cleaned_data["assigned_rules"] = []

            # Validate the cleaned data
            SourceRuleAssignment(**cleaned_data)  # This will raise if invalid
            cleaned_assignments.append(cleaned_data)

        # Atomically write assignments to file
        atomic_write_json(ASSIGNMENTS_FILE, cleaned_assignments)

        logger.info("Successfully saved %s assignments", len(assignments))
        return {
            "success": True,
            "message": f"Successfully saved {len(assignments)} assignments",
        }

    except Exception as e:
        logger.exception("Error saving assignments: %s", e)
        raise


def load_rules() -> list[dict[str, Any]]:
    """Load ingestion rules from rules.json file.

    Returns:
        List of rule dictionaries, empty list if file doesn't exist

    """
    logger.info("Loading rules from %s", RULES_FILE)

    # Ensure file exists with empty array default
    ensure_file_exists(RULES_FILE, [])

    rules = atomic_read_json(RULES_FILE, [])
    logger.info("Loaded %s rules", len(rules))
    return rules


def load_assignments() -> list[dict[str, Any]]:
    """Load source rule assignments from assignments.json file.

    Returns:
        List of assignment dictionaries, empty list if file doesn't exist

    """
    logger.info("Loading assignments from %s", ASSIGNMENTS_FILE)

    # Ensure file exists with empty array default
    ensure_file_exists(ASSIGNMENTS_FILE, [])

    assignments = atomic_read_json(ASSIGNMENTS_FILE, [])
    logger.info("Loaded %s assignments", len(assignments))
    return assignments
