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
            logger.warning(
                f"Error checking source {source_name} modification times: {e}"
            )
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
            logger.error(
                f"Error reloading flow configuration for source {source_name}: {e}"
            )

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
        """Path-based flow processing with detailed tracing.

        Only records that flow through connected paths continue to next nodes.
        Provides detailed tracing of each record's journey through the flow.
        """
        total_records = len(records)
        logger.info(
            f"Starting path-based flow processing for {total_records} records from {source_name} on table {table_name}"
        )

        if not records:
            logger.info("No records to process, returning empty results")
            return [], []

        # Convert records to list of dictionaries
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

        # Load flow configuration
        logger.debug(f"Loading flow configuration for source: {source_name}")
        flow_config = self.load_flow_configuration(source_name)
        if not flow_config:
            logger.warning(
                f"No flow configuration found for {source_name}, accepting all records"
            )
            # Add required columns for no flow config
            for record in records_data:
                record["_trace"] = [
                    {
                        "node_id": f"source:{source_name.lower()}",
                        "type": "source",
                        "input_table": table_name,
                        "output": table_name,
                    },
                    {"node_id": "stream:accepted", "type": "sink", "accepted": True},
                ]
                record["filter_reasons"] = {}
                record["accepted"] = True

            logger.info(f"Completed with {len(records_data)} accepted (no flow config)")
            return records_data, []

        # Load the flow JSON to get edge information
        flow_file_path = os.path.join(self.flows_dir, f"{source_name}_flow.json")
        if not os.path.exists(flow_file_path):
            logger.error(f"Flow file not found: {flow_file_path}")
            return records_data, []  # Fallback to accepting all

        with open(flow_file_path, "r") as f:
            flow_data = json.load(f)

        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])

        # Build node lookup
        node_lookup = {node["id"]: node for node in nodes}

        # Build edge lookup for path routing
        edge_lookup = {}
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]
            source_handle = edge.get("sourceHandle", "default")
            target_handle = edge.get("targetHandle", "default")

            if source_id not in edge_lookup:
                edge_lookup[source_id] = {}
            if source_handle not in edge_lookup[source_id]:
                edge_lookup[source_id][source_handle] = []
            edge_lookup[source_id][source_handle].append(
                {
                    "target_id": target_id,
                    "target_handle": target_handle,
                    "edge_id": edge["id"],
                }
            )

        # Find source node for this table
        source_node = None
        for node in nodes:
            if node["type"] == "source" and node["data"]["sourceName"] == source_name:
                source_node = node
                break

        if not source_node:
            logger.error(f"Source node not found for {source_name}")
            return records_data, []  # Fallback

        # Process each record through the flow
        accepted_records = []
        rejected_records = []

        for i, record in enumerate(records_data):
            if i % 1000 == 0:  # Log progress every 1k records
                logger.debug(f"Processing record {i}/{total_records}")

            # Initialize record tracing
            record["_trace"] = []
            record["filter_reasons"] = {}
            record["accepted"] = False

            # Start at source node
            record["_trace"].append(
                {
                    "node_id": source_node["id"],
                    "type": "source",
                    "input_table": table_name,
                    "output": table_name,
                }
            )

            # Find the path from source to first rule for this table
            table_handle = f"table-{table_name}"
            if (
                source_node["id"] not in edge_lookup
                or table_handle not in edge_lookup[source_node["id"]]
            ):
                # No path from this table, reject record
                record["accepted"] = False
                rejected_records.append(record)
                continue

            # Follow the flow path
            current_connections = edge_lookup[source_node["id"]][table_handle]
            record_accepted = False

            for connection in current_connections:
                target_node_id = connection["target_id"]
                target_node = node_lookup.get(target_node_id)

                if not target_node:
                    continue

                # Process through the flow starting from this target
                if self._process_record_through_flow(
                    record,
                    target_node,
                    edge_lookup,
                    node_lookup,
                    flow_config,
                    table_name,
                ):
                    record_accepted = True
                    break

            record["accepted"] = record_accepted
            if record_accepted:
                accepted_records.append(record)
                if len(accepted_records) < 2:  # Debug first few records
                    logger.info(f"Record {i} added to accepted_records with trace: {record.get('_trace', [])}")
            else:
                rejected_records.append(record)
                if len(rejected_records) < 2:  # Debug first few records
                    logger.info(f"Record {i} added to rejected_records with trace: {record.get('_trace', [])}")

        accepted_count = len(accepted_records)
        rejected_count = len(rejected_records)
        # Report progress
        if progress_callback:
            logger.info(
                f"Calling progress callback: {accepted_count} accepted, {rejected_count} rejected"
            )
            try:
                progress_callback(
                    processed=total_records,
                    total=total_records,
                    current_item=f"Path-based flow processing completed",
                    accepted=accepted_count,
                    rejected=rejected_count,
                )
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

        logger.info(
            f"Processing completed: {accepted_count} accepted, {rejected_count} rejected"
        )

        return accepted_records, rejected_records

    def _process_record_through_flow(
        self,
        record: Dict[str, Any],
        current_node: Dict[str, Any],
        edge_lookup: Dict[str, Any],
        node_lookup: Dict[str, Any],
        flow_config: FlowConfiguration,
        table_name: str,
    ) -> bool:
        """Process a single record through the flow starting from current_node.

        Returns True if record reaches an accepted sink, False otherwise.
        """
        # Handle different node types
        if current_node["type"] == "rule":
            return self._process_rule_node(
                record, current_node, edge_lookup, node_lookup, flow_config, table_name
            )
        elif current_node["type"] == "stream":
            return self._process_stream_node(record, current_node)
        else:
            logger.warning(f"Unknown node type: {current_node['type']}")
            return False

    def _process_rule_node(
        self,
        record: Dict[str, Any],
        rule_node: Dict[str, Any],
        edge_lookup: Dict[str, Any],
        node_lookup: Dict[str, Any],
        flow_config: FlowConfiguration,
        table_name: str,
    ) -> bool:
        """Process a record through a rule node."""
        rule_name = rule_node["data"]["ruleName"]
        rule = flow_config.get_rule_by_name(rule_name)

        if not rule or table_name not in rule.tables:
            logger.debug(f"Rule {rule_name} not applicable to table {table_name}")
            return False

        # Evaluate the rule
        field_value = record.get(rule.field, "")
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
                return False

        pattern = self._compiled_patterns[pattern_key]
        match = bool(pattern.search(str(field_value)))

        # Apply NOT logic if specified
        if rule.not_:
            match = not match

        # Record the rule result
        record["filter_reasons"][f"rule:{rule_name.lower().replace(' ', '_')}"] = match

        # Determine which path to take
        path = "passed" if match else "caught"

        # Add trace entry
        record["_trace"].append(
            {
                "node_id": f"rule:{rule_name.lower().replace(' ', '_')}",
                "type": "rule",
                "field": rule.field,
                "result": match,
                "path": path,
                "continued": True,  # Rules don't continue to next nodes for record processing
            }
        )        
        # Find outgoing connections for this path
        rule_node_id = rule_node["id"]
        if rule_node_id not in edge_lookup:
            # No outgoing connections, record stops here
            record["_trace"][-1]["continued"] = False
            
        return match

    def _process_stream_node(
        self, record: Dict[str, Any], stream_node: Dict[str, Any]
    ) -> bool:
        """Process a record through a stream (sink) node."""
        stream_name = stream_node["data"].get("streamName", "unknown")

        # Determine if this is an accepting stream
        is_accepting = stream_name.lower() in ["accepted", "accept", "pass"]

        # Add trace entry
        record["_trace"].append(
            {
                "node_id": f"stream:{stream_name.lower()}",
                "type": "sink",
                "accepted": is_accepting,
            }
        )

        return is_accepting


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
