"""Enhanced Rules Engine with Sequential Flow and Tracing.

This module implements a visual flow-based rules engine that applies rules sequentially
as a logical mask. Rules can terminate processing (terminal nodes) or pass records
to subsequent rules. Each record gets detailed tracing of its journey through the rules.

Architecture:
- Atomic Design: Each function has single responsibility
- Sequential Processing: Rules applied in visual flow order
- Terminal Nodes: Rules can stop further processing
- Detailed Tracing: Complete audit trail of rule evaluation
- Flow-based Logic: Supports complex rule routing and branching
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from common.constants import DATA_PATH
from common.log_utils import get_logger
from common.trace_utils import (
    RuleTrace,
    create_trace,
    trace_table_entry,
    trace_rule_evaluation,
    trace_termination,
    trace_final_decision,
    merge_trace_into_record,
)
from models.models import EpgChannel, M3uChannel, Program

logger = get_logger(__name__)

# Configuration files
RULES_CONFIG_FILE = os.path.join(DATA_PATH, "rules.json")
ASSIGNMENTS_CONFIG_FILE = os.path.join(DATA_PATH, "assignments.json")
FLOWS_CONFIG_FILE = os.path.join(DATA_PATH, "flows")


@dataclass
class FlowRule:
    """Enhanced rule with flow control capabilities."""

    name: str
    tables: List[str]
    field: str
    regex: str
    enabled: bool = True
    not_: bool = False
    is_terminal: bool = False  # If True, stops processing when rule is triggered
    next_rules: List[str] = None  # Rules to apply next (for non-terminal rules)

    def __post_init__(self):
        """Initialize next_rules as empty list if None."""
        if self.next_rules is None:
            self.next_rules = []

        # Validate regex pattern
        try:
            re.compile(self.regex)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{self.regex}': {e}")


@dataclass
class FlowConfiguration:
    """Configuration for a complete rule flow."""

    source_name: str
    entry_point: str  # Name of the first rule to apply
    rules: List[FlowRule]
    mode: str = "sequential"  # "sequential" or "parallel"

    def get_rule_by_name(self, rule_name: str) -> Optional[FlowRule]:
        """Get a rule by its name (atomic lookup)."""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None


class EnhancedRulesEngine:
    """Enhanced rules engine with sequential flow processing and detailed tracing."""

    def __init__(
        self, rules_file: Optional[str] = None, assignments_file: Optional[str] = None
    ):
        """Initialize the enhanced rules engine."""
        self.rules_file = rules_file or RULES_CONFIG_FILE
        self.assignments_file = assignments_file or ASSIGNMENTS_CONFIG_FILE
        self.flows_dir = FLOWS_CONFIG_FILE

        self._flow_cache: Dict[str, FlowConfiguration] = {}
        self._cache_timestamp: Optional[float] = None
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    def _should_reload_cache(self) -> bool:
        """Check if cache should be reloaded based on file modification times."""
        try:
            # Check rules file
            if os.path.exists(self.rules_file):
                rules_mtime = os.path.getmtime(self.rules_file)
                if self._cache_timestamp is None or rules_mtime > self._cache_timestamp:
                    return True

            # Check assignments file
            if os.path.exists(self.assignments_file):
                assignments_mtime = os.path.getmtime(self.assignments_file)
                if (
                    self._cache_timestamp is None
                    or assignments_mtime > self._cache_timestamp
                ):
                    return True

            # Check flows directory
            if os.path.exists(self.flows_dir):
                for filename in os.listdir(self.flows_dir):
                    if filename.endswith("_flow.json"):
                        flow_file = os.path.join(self.flows_dir, filename)
                        flow_mtime = os.path.getmtime(flow_file)
                        if (
                            self._cache_timestamp is None
                            or flow_mtime > self._cache_timestamp
                        ):
                            return True

            return False
        except Exception as e:
            logger.warning(f"Error checking file modification times: {e}")
            return True

    def load_flow_configuration(self, source_name: str) -> Optional[FlowConfiguration]:
        """Load flow configuration for a specific source."""
        # Check if we need to reload this specific source's configuration
        if self._should_reload_source_cache(source_name):
            self._reload_source_cache(source_name)

        return self._flow_cache.get(source_name)

    def _should_reload_source_cache(self, source_name: str) -> bool:
        """Check if a specific source's cache needs reloading."""
        try:
            # If source not in cache, need to load it
            if source_name not in self._flow_cache:
                return True

            # Check if rules file has been modified
            if os.path.exists(self.rules_file):
                rules_mtime = os.path.getmtime(self.rules_file)
                if self._cache_timestamp is None or rules_mtime > self._cache_timestamp:
                    return True

            # Check if this specific source's flow file has been modified
            flow_file = os.path.join(self.flows_dir, f"{source_name}_flow.json")
            if os.path.exists(flow_file):
                flow_mtime = os.path.getmtime(flow_file)
                if self._cache_timestamp is None or flow_mtime > self._cache_timestamp:
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error checking source {source_name} modification times: {e}")
            return True

    def _reload_source_cache(self, source_name: str) -> None:
        """Reload flow configuration for a specific source only."""
        logger.info(f"Reloading flow configuration for source: {source_name}")
        
        try:
            # Load flow configuration for this specific source
            flow_config = self._load_flow_from_file(source_name)
            if flow_config:
                self._flow_cache[source_name] = flow_config
                logger.info(f"Loaded flow configuration for source: {source_name}")
            else:
                # Remove from cache if flow file doesn't exist or failed to load
                if source_name in self._flow_cache:
                    del self._flow_cache[source_name]
                logger.debug(f"No flow configuration found for source: {source_name}")

            self._cache_timestamp = datetime.now().timestamp()

        except Exception as e:
            logger.error(f"Error reloading flow configuration for source {source_name}: {e}")

    def _reload_cache(self) -> None:
        """Reload all flow configurations from files (for bulk operations)."""
        logger.info("Reloading enhanced rules engine cache")
        self._flow_cache.clear()
        self._compiled_patterns.clear()

        try:
            # Load flow configurations from flows directory
            if os.path.exists(self.flows_dir):
                for filename in os.listdir(self.flows_dir):
                    if filename.endswith("_flow.json"):
                        source_name = filename.replace("_flow.json", "")
                        flow_config = self._load_flow_from_file(source_name)
                        if flow_config:
                            self._flow_cache[source_name] = flow_config

            self._cache_timestamp = datetime.now().timestamp()
            logger.info(f"Loaded {len(self._flow_cache)} flow configurations")

        except Exception as e:
            logger.error(f"Error reloading enhanced rules cache: {e}")

    def _load_rule_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load rule definitions from rules.json file."""
        try:
            if not os.path.exists(self.rules_file):
                logger.warning(f"Rules file not found: {self.rules_file}")
                return {}

            with open(self.rules_file, "r") as f:
                rules_data = json.load(f)

            # Convert list of rules to dictionary keyed by rule name
            rule_definitions = {}
            for rule in rules_data:
                if isinstance(rule, dict) and "name" in rule:
                    rule_definitions[rule["name"]] = rule

            logger.debug(
                f"Loaded {len(rule_definitions)} rule definitions from {self.rules_file}"
            )
            return rule_definitions

        except Exception as e:
            logger.error(f"Error loading rule definitions from {self.rules_file}: {e}")
            return {}

    def _load_flow_from_file(self, source_name: str) -> Optional[FlowConfiguration]:
        """Load a flow configuration from a JSON file."""
        flow_file = os.path.join(self.flows_dir, f"{source_name}_flow.json")

        if not os.path.exists(flow_file):
            logger.debug(f"No flow file found for source: {source_name}")
            return None

        try:
            with open(flow_file, "r") as f:
                flow_data = json.load(f)

            # Load rule definitions from rules.json
            rule_definitions = self._load_rule_definitions()

            # Extract rules from flow nodes
            rules = []
            entry_point = None

            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])

            # Build rule objects from nodes
            for node in nodes:
                if node.get("type") == "rule":
                    node_data = node.get("data", {})
                    rule_name = node_data.get("label", f"rule_{node['id']}")

                    # Look up rule definition from rules.json
                    rule_def = rule_definitions.get(rule_name)
                    if rule_def:
                        rule = FlowRule(
                            name=rule_name,
                            tables=rule_def["tables"],
                            field=rule_def["field"],
                            regex=rule_def["regex"],
                            enabled=rule_def.get("enabled", True),
                            not_=rule_def.get("not_", False),
                            is_terminal=self._is_terminal_node(node["id"], edges),
                        )
                        rules.append(rule)
                        logger.debug(
                            f"Loaded rule '{rule_name}' with regex: {rule_def['regex']}"
                        )
                    else:
                        logger.warning(
                            f"Rule definition not found for '{rule_name}' in rules.json"
                        )
                        # Fallback to node data if rule definition not found
                        rule = FlowRule(
                            name=rule_name,
                            tables=[node_data.get("table", "unknown")],
                            field=node_data.get("field", "name"),
                            regex=".*",  # Safe fallback
                            enabled=True,
                            not_=node_data.get("not_", False),
                            is_terminal=self._is_terminal_node(node["id"], edges),
                        )
                        rules.append(rule)

                elif node.get("type") == "source":
                    # Source node is the entry point
                    entry_point = self._find_first_rule_from_source(
                        node["id"], edges, nodes
                    )

            # Build next_rules relationships from edges
            self._build_rule_relationships(rules, edges, nodes)

            if not entry_point:
                logger.warning(f"No entry point found for flow: {source_name}")
                return None

            return FlowConfiguration(
                source_name=source_name,
                entry_point=entry_point,
                rules=rules,
                mode="sequential",
            )

        except Exception as e:
            logger.error(f"Error loading flow configuration for {source_name}: {e}")
            return None

    def _is_terminal_node(self, node_id: str, edges: List[Dict]) -> bool:
        """Check if a node is terminal (has no outgoing edges to other rules)."""
        for edge in edges:
            if edge.get("source") == node_id:
                return False
        return True

    def _find_first_rule_from_source(
        self, source_node_id: str, edges: List[Dict], nodes: List[Dict]
    ) -> Optional[str]:
        """Find the first rule node connected to the source node."""
        for edge in edges:
            if edge.get("source") == source_node_id:
                target_node_id = edge.get("target")
                # Find the target node and check if it's a rule
                for node in nodes:
                    if node["id"] == target_node_id and node.get("type") == "rule":
                        return node.get("data", {}).get("label", f"rule_{node['id']}")
        return None

    def _build_rule_relationships(
        self, rules: List[FlowRule], edges: List[Dict], nodes: List[Dict]
    ) -> None:
        """Build next_rules relationships from flow edges."""
        # Create node_id to rule_name mapping
        node_to_rule = {}
        for node in nodes:
            if node.get("type") == "rule":
                rule_name = node.get("data", {}).get("label", f"rule_{node['id']}")
                node_to_rule[node["id"]] = rule_name

        # Build relationships
        for rule in rules:
            rule_node_id = None
            # Find the node ID for this rule
            for node in nodes:
                if (
                    node.get("type") == "rule"
                    and node.get("data", {}).get("label", f"rule_{node['id']}")
                    == rule.name
                ):
                    rule_node_id = node["id"]
                    break

            if rule_node_id:
                # Find outgoing edges from this rule
                for edge in edges:
                    if edge.get("source") == rule_node_id:
                        target_node_id = edge.get("target")
                        if target_node_id in node_to_rule:
                            rule.next_rules.append(node_to_rule[target_node_id])

    def apply_flow_to_record(
        self,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
    ) -> Tuple[bool, RuleTrace]:
        """Apply flow-based rules to a single record with detailed tracing."""
        trace = create_trace()
        trace_table_entry(trace, table_name)

        # Load flow configuration
        flow_config = self.load_flow_configuration(source_name)
        if not flow_config:
            logger.debug(f"No flow configuration found for source: {source_name}")
            trace_final_decision(trace, True, "no_flow_configuration")
            return True, trace

        # Convert record to dictionary for processing
        if hasattr(record, "__dict__"):
            record_dict = {
                k: v for k, v in record.__dict__.items() if not k.startswith("_")
            }
        else:
            record_dict = record

        # Start processing from entry point
        current_rule_name = flow_config.entry_point
        processed_rules = set()  # Prevent infinite loops

        while current_rule_name and current_rule_name not in processed_rules:
            processed_rules.add(current_rule_name)

            # Get the rule
            rule = flow_config.get_rule_by_name(current_rule_name)
            if not rule:
                logger.warning(f"Rule not found: {current_rule_name}")
                break

            # Check if rule applies to this table
            if table_name not in rule.tables:
                logger.debug(f"Rule {rule.name} does not apply to table {table_name}")
                # Move to next rule in sequence
                if rule.next_rules:
                    current_rule_name = rule.next_rules[0]
                else:
                    break
                continue

            # Apply the rule
            rule_result = self._evaluate_rule(rule, record_dict)
            trace_rule_evaluation(trace, rule.name, rule_result, caught=not rule_result)

            # Handle rule result
            if not rule_result:  # Rule caught the record
                if rule.is_terminal:
                    # Terminal rule - stop processing
                    trace_termination(trace, rule.name, "REJECTED")
                    trace_final_decision(trace, False, f"terminated_at_{rule.name}")
                    return False, trace
                else:
                    # Non-terminal rule - continue to next rules
                    if rule.next_rules:
                        current_rule_name = rule.next_rules[0]
                    else:
                        break
            else:  # Rule passed the record
                # Continue to next rules
                if rule.next_rules:
                    current_rule_name = rule.next_rules[0]
                else:
                    break

        # If we get here, record passed all applicable rules
        trace_final_decision(trace, True, "passed_all_rules")
        return True, trace

    def _evaluate_rule(self, rule: FlowRule, record_dict: Dict[str, Any]) -> bool:
        """Evaluate a single rule against a record (atomic operation)."""
        if not rule.enabled:
            return True  # Disabled rules always pass

        field_value = record_dict.get(rule.field, "")
        if field_value is None:
            field_value = ""

        # Get or compile regex pattern
        pattern_key = f"{rule.name}:{rule.regex}"
        if pattern_key not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern_key] = re.compile(
                    rule.regex, re.IGNORECASE
                )
            except re.error as e:
                logger.error(f"Invalid regex in rule {rule.name}: {e}")
                return True  # Invalid regex passes by default

        pattern = self._compiled_patterns[pattern_key]
        match = bool(pattern.search(str(field_value)))

        # Apply NOT logic if specified
        if rule.not_:
            match = not match

        return match

    def apply_flow_to_records_vectorized(
        self,
        records: List[Union[M3uChannel, EpgChannel, Program]],
        table_name: str,
        source_name: str,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fast vectorized processing optimized for large datasets.

        Prioritizes speed over detailed tracing for massive performance gains.
        """
        total_records = len(records)
        logger.info(
            f"Starting processing for {total_records} records from {source_name}"
        )

        if not records:
            logger.info("No records to process, returning empty results")
            return [], []

        # Convert to DataFrame quickly
        records_data = []
        for i, record in enumerate(records):
            if i % 10000 == 0:  # Log progress every 10k records
                logger.debug(f"Converting record {i}/{total_records}")
            if hasattr(record, "__dict__"):
                record_dict = {
                    k: v for k, v in record.__dict__.items() if not k.startswith("_")
                }
            else:
                record_dict = dict(record)
            records_data.append(record_dict)

        logger.debug(f"Creating pandas DataFrame from {len(records_data)} records")
        df = pd.DataFrame(records_data)
        logger.debug(f"DataFrame created successfully with shape: {df.shape}")

        # Load flow configuration
        logger.info(f"Loading flow configuration for source: {source_name}")
        flow_config = self.load_flow_configuration(source_name)
        if not flow_config:
            logger.warning(
                f"No flow configuration found for {source_name}, accepting all records"
            )
            # Add required columns
            df["_trace"] = [
                [f"table_entry:{table_name}", "final_decision:accepted:no_flow_config"]
            ] * len(df)
            df["filter_reasons"] = [""] * len(
                df
            )  # String format for Pydantic compatibility
            df["accepted"] = True

            accepted_records = df.to_dict("records")
            logger.info(
                f"Completed with {len(accepted_records)} accepted (no flow config)"
            )
            return accepted_records, []

        # Get entry rule
        logger.info(
            f"Getting entry rule for flow config entry point: {flow_config.entry_point}"
        )
        entry_rule = flow_config.get_rule_by_name(flow_config.entry_point)
        if not entry_rule or table_name not in entry_rule.tables:
            logger.warning(
                f"No applicable entry rule for table {table_name}, accepting all records"
            )
            df["accepted"] = True
        else:
            logger.info(
                f"Applying rule {entry_rule.name} to field '{entry_rule.field}' with regex: {entry_rule.regex}"
            )

            try:
                logger.debug(
                    f"Starting vectorized regex matching on field: {entry_rule.field}"
                )
                # Fast vectorized regex matching
                field_values = df[entry_rule.field].fillna("").astype(str)
                logger.debug(f"Field values extracted, applying regex pattern")
                # Use regex string directly with pandas (don't pre-compile)
                matches = field_values.str.contains(
                    entry_rule.regex, case=False, na=False, regex=True
                )
                logger.info(
                    f"Vectorized matching completed, {matches.sum()} matches found"
                )

                if entry_rule.not_:
                    matches = ~matches
                    logger.debug(
                        f"Applied NOT logic, {matches.sum()} matches after negation"
                    )

                if entry_rule.is_terminal:
                    logger.debug(f"Terminal rule, setting accepted column")
                    df["accepted"] = matches
                else:
                    logger.info(f"Non-terminal rule, continuing to next rules in flow")
                    # For non-terminal rules, we need to continue processing
                    # Start with records that matched this rule
                    df["accepted"] = False  # Initialize all as rejected
                    df.loc[matches, "accepted"] = True  # Accept matches from this rule
                    
                    # Process subsequent rules for matched records
                    current_rule = entry_rule
                    processed_mask = matches.copy()  # Track which records have been processed
                    
                    while current_rule and not current_rule.is_terminal and current_rule.next_rules:
                        logger.info(f"Processing next rules from {current_rule.name}: {current_rule.next_rules}")
                        
                        for next_rule_name in current_rule.next_rules:
                            next_rule = flow_config.get_rule_by_name(next_rule_name)
                            if not next_rule or table_name not in next_rule.tables:
                                logger.warning(f"Skipping invalid next rule: {next_rule_name}")
                                continue
                                
                            logger.info(f"Applying next rule {next_rule.name} to field '{next_rule.field}' with regex: {next_rule.regex}")
                            
                            # Apply rule only to records that haven't been processed yet
                            unprocessed_mask = processed_mask & ~df["accepted"]
                            if not unprocessed_mask.any():
                                logger.info(f"No unprocessed records for rule {next_rule.name}")
                                continue
                                
                            # Get field values for unprocessed records
                            field_values = df.loc[unprocessed_mask, next_rule.field].fillna("").astype(str)
                            
                            # Apply regex matching
                            rule_matches = field_values.str.contains(
                                next_rule.regex, case=False, na=False, regex=True
                            )
                            
                            if next_rule.not_:
                                rule_matches = ~rule_matches
                                
                            # Update acceptance status
                            matched_indices = field_values.index[rule_matches]
                            df.loc[matched_indices, "accepted"] = True
                            
                            # Mark these records as processed
                            processed_mask.loc[matched_indices] = True
                            
                            logger.info(f"Rule {next_rule.name} matched {rule_matches.sum()} additional records")
                            
                            # If this is a terminal rule, stop processing
                            if next_rule.is_terminal:
                                logger.info(f"Reached terminal rule {next_rule.name}, stopping flow")
                                current_rule = None
                                break
                            else:
                                current_rule = next_rule
                                break  # Process one rule at a time for now
                        else:
                            # No valid next rules found
                            logger.info(f"No more valid rules to process from {current_rule.name}")
                            break

                logger.info(f"Rule matched {matches.sum()} out of {len(df)} records")

            except Exception as e:
                logger.error(f"Error applying rule {entry_rule.name}: {e}")
                df["accepted"] = True

        # Add minimal tracing
        logger.info(f"Adding tracing columns")
        df["_trace"] = [
            [f"table_entry:{table_name}", "vectorized_fast_processing"]
        ] * len(df)
        df["filter_reasons"] = [""] * len(
            df
        )  # String format for Pydantic compatibility

        # Report progress
        if progress_callback:
            accepted_count = int(df["accepted"].sum())
            rejected_count = len(df) - accepted_count
            logger.info(
                f"Calling progress callback: {accepted_count} accepted, {rejected_count} rejected"
            )
            try:
                progress_callback(
                    processed=total_records,
                    total=total_records,
                    current_item=f"Fast vectorized processing completed",
                    accepted=accepted_count,
                    rejected=rejected_count,
                )
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

        # Convert to results
        logger.debug(f"Converting results to dictionaries")
        accepted_records = df[df["accepted"]].to_dict("records")
        rejected_records = df[~df["accepted"]].to_dict("records")

        logger.info(
            f"Processing completed: {len(accepted_records)} accepted, {len(rejected_records)} rejected"
        )
        return accepted_records, rejected_records


# Global enhanced rules engine instance
enhanced_rules_engine = EnhancedRulesEngine()


def apply_enhanced_rules(
    records: List[Union[M3uChannel, EpgChannel, Program]],
    table_name: str,
    source_name: str,
    progress_callback: Optional[callable] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Apply enhanced flow-based rules to records using fast vectorized processing.

    Args:
        records: List of records to process
        table_name: Name of the table being processed
        source_name: Name of the source
        progress_callback: Optional callback function for progress updates
    """
    record_count = len(records)
    logger.info(
        f"Applying enhanced rules to {record_count} {table_name} records for source {source_name}"
    )

    try:
        # Always use vectorized processing for optimal performance
        logger.info(f"Using fast vectorized processing for {record_count} records")
        accepted, rejected = enhanced_rules_engine.apply_flow_to_records_vectorized(
            records, table_name, source_name, progress_callback
        )

        logger.info(
            f"Enhanced rules processing complete: {len(accepted)} accepted, {len(rejected)} rejected"
        )
        return accepted, rejected

    except Exception as e:
        logger.error(f"Error in enhanced rules processing: {e}")
        # Fallback: accept all records with error trace
        fallback_records = []
        for record in records:
            if hasattr(record, "__dict__"):
                record_dict = {
                    k: v for k, v in record.__dict__.items() if not k.startswith("_")
                }
            else:
                record_dict = dict(record)

            error_trace = create_trace()
            trace_table_entry(error_trace, table_name)
            trace_final_decision(error_trace, True, f"fallback_due_to_error: {str(e)}")
            record_dict = merge_trace_into_record(record_dict, error_trace)
            fallback_records.append(record_dict)

        return fallback_records, []
