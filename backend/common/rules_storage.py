"""Atomic rules and assignments storage utilities following atomic design principles

This module provides atomic functions for saving and loading ingestion rules
and source rule assignments to separate JSON files.
"""

import os
from typing import List, Dict, Any
import logging

from common.constants import DATA_PATH
from common.file_utils import atomic_write_json, atomic_read_json, ensure_file_exists
from common.utils import log_function

logger = logging.getLogger(__name__)

# File paths for rules and assignments
RULES_FILE = os.path.join(DATA_PATH, "rules.json")
ASSIGNMENTS_FILE = os.path.join(DATA_PATH, "assignments.json")


def save_rules(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Atomically save ingestion rules to rules.json file.
    
    Args:
        rules: List of rule dictionaries to save
        
    Returns:
        Dict with success status and message
        
    Raises:
        Exception: If file operations fail
    """
    log_function(f"Saving {len(rules)} rules to {RULES_FILE}")
    
    try:
        # Validate rules structure
        from rules.ingestion_rules import IngestionRule
        
        for rule_data in rules:
            IngestionRule(**rule_data)  # This will raise if invalid
        
        # Atomically write rules to file
        atomic_write_json(RULES_FILE, rules)
        
        log_function(f"Successfully saved {len(rules)} rules")
        return {
            "success": True,
            "message": f"Successfully saved {len(rules)} rules"
        }
        
    except Exception as e:
        logger.error(f"Error saving rules: {e}")
        raise e


def save_assignments(assignments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Atomically save source rule assignments to assignments.json file.
    
    Args:
        assignments: List of assignment dictionaries to save
        
    Returns:
        Dict with success status and message
        
    Raises:
        Exception: If file operations fail
    """
    log_function(f"Saving {len(assignments)} assignments to {ASSIGNMENTS_FILE}")
    
    try:
        # Validate assignments structure
        from rules.ingestion_rules import SourceRuleAssignment
        
        # Filter out unknown fields before validation and saving
        valid_fields = {'id', 'assignment_name', 'source_name', 'rule_mode', 'assigned_rules', 'enabled'}
        cleaned_assignments = []
        
        for assignment_data in assignments:
            # Filter out unknown fields (like filter_stats)
            cleaned_data = {k: v for k, v in assignment_data.items() if k in valid_fields}
            
            # Normalize assigned_rules to always be an array (atomic design)
            if 'assigned_rules' in cleaned_data:
                if isinstance(cleaned_data['assigned_rules'], str):
                    cleaned_data['assigned_rules'] = [cleaned_data['assigned_rules']]
                elif not isinstance(cleaned_data['assigned_rules'], list):
                    cleaned_data['assigned_rules'] = []
            else:
                cleaned_data['assigned_rules'] = []
            
            # Validate the cleaned data
            SourceRuleAssignment(**cleaned_data)  # This will raise if invalid
            cleaned_assignments.append(cleaned_data)
        
        # Atomically write assignments to file
        atomic_write_json(ASSIGNMENTS_FILE, cleaned_assignments)
        
        log_function(f"Successfully saved {len(assignments)} assignments")
        return {
            "success": True,
            "message": f"Successfully saved {len(assignments)} assignments"
        }
        
    except Exception as e:
        logger.error(f"Error saving assignments: {e}")
        raise e


def load_rules() -> List[Dict[str, Any]]:
    """Load ingestion rules from rules.json file.
    
    Returns:
        List of rule dictionaries, empty list if file doesn't exist
    """
    log_function(f"Loading rules from {RULES_FILE}")
    
    # Ensure file exists with empty array default
    ensure_file_exists(RULES_FILE, [])
    
    rules = atomic_read_json(RULES_FILE, [])
    log_function(f"Loaded {len(rules)} rules")
    return rules


def load_assignments() -> List[Dict[str, Any]]:
    """Load source rule assignments from assignments.json file.
    
    Returns:
        List of assignment dictionaries, empty list if file doesn't exist
    """
    log_function(f"Loading assignments from {ASSIGNMENTS_FILE}")
    
    # Ensure file exists with empty array default
    ensure_file_exists(ASSIGNMENTS_FILE, [])
    
    assignments = atomic_read_json(ASSIGNMENTS_FILE, [])
    log_function(f"Loaded {len(assignments)} assignments")
    return assignments



