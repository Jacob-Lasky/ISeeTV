"""
Node Executor for Modular Flow Execution.

This module implements atomic, modular node execution for flow-based rule processing.
Supports executing single nodes, partial flows (up-to-node, from-node), and maintains
detailed tracing and execution context.

Architecture:
- Atomic Design: Each function has single responsibility
- Modular Execution: Individual nodes can be run independently
- Flow Traversal: Supports partial flow execution with proper node ordering
- Context Preservation: Maintains execution state and tracing
- Rule Integration: Leverages existing enhanced_rules_engine for rule processing
"""

import json
import tempfile
import os
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime
from sqlalchemy import text
from itertools import islice

from common.db import SessionLocal
from common.log_utils import get_logger
from models.db_models import get_table_model
from .enhanced_rules_engine import EnhancedRulesEngine
from common.flow_storage import update_flow_stats

logger = get_logger(__name__)


def _chunks(iterable, size):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            return
        yield batch

class NodeExecutor:
    """Handles modular execution of individual nodes and partial flows."""
    
    def __init__(self):
        self.rules_engine = EnhancedRulesEngine()
    
    async def execute_single_node(
        self,
        source: str,
        node: Dict[str, Any],
        flow_data: Dict[str, Any],
        table_name: str,
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """
        Execute a single node independently using filtered input rows.
        
        Args:
            source: Source identifier
            node: Node configuration to execute
            flow_data: Complete flow data for context
            table_name: Database table to process
            limit: Limit the number of input rows to process
            
        Returns:
            Execution results with statistics and processed records
        """
        node_id = node.get('id')
        logger.info(f"Executing single node {node_id} of type {node.get('type')}")
        
        # Get filtered input rows that would actually reach this node
        filtered_input_rows = await self.get_filtered_rows_for_node(
            source=source,
            target_node_id=node_id,
            flow_data=flow_data,
            table_name=table_name,
            limit=limit
        )
        
        if not filtered_input_rows:
            return self._create_empty_result(f"No filtered input rows found for node '{node_id}'")
        
        # Convert dict records back to ORM objects for the rules engine
        # This is needed because _execute_flow_with_records expects ORM objects
        table_model = get_table_model(table_name)
        if not table_model:
            raise ValueError(f"Invalid table name: {table_name}")
        
        # Convert filtered rows back to ORM-like objects
        orm_records = []
        for row_dict in filtered_input_rows:
            # Create a mock ORM object with the row data
            mock_record = type('MockRecord', (), {})()
            mock_record.__table__ = table_model.__table__
            for key, value in row_dict.items():
                setattr(mock_record, key, value)
            orm_records.append(mock_record)
        
        # Create a minimal flow with just this node
        minimal_flow = self._create_single_node_flow(node, flow_data)
        
        # Execute the node on the filtered input data
        accepted_records, rejected_records = await self._execute_flow_with_records(
            orm_records, minimal_flow, table_name
        )
        update_flow_stats(source, node_id, len(accepted_records), len(rejected_records))
        await self._persist_trace_data(accepted_records + rejected_records, table_name, source)
        
        return self._create_execution_result(
            orm_records, accepted_records, rejected_records,
            execution_context={
                "node_id": node_id,
                "node_type": node.get("type"),
                "execution_mode": "single_node_with_filtered_input",
                "input_rows_count": len(filtered_input_rows)
            }
        )
    
    async def execute_flow_to_node(
        self,
        source: str,
        target_node_id: str,
        flow_data: Dict[str, Any],
        table_name: str,
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """
        Execute flow from start up to (and including) the specified node.
        
        Args:
            source: Source identifier
            target_node_id: ID of the target node to stop at
            flow_data: Complete flow data
            table_name: Database table to process
            limit: Limit the number of records to process
            
        Returns:
            Execution results with statistics and processed records
        """
        logger.info(f"Executing flow up to node {target_node_id}")
        
        # Get input data from database
        records = await self._get_input_records(source, table_name, limit)
        if not records:
            return self._create_empty_result(f"No records found for source '{source}' in table '{table_name}'")
        
        # Create partial flow up to target node
        partial_flow = self._create_flow_to_node(target_node_id, flow_data)
        if not partial_flow:
            raise ValueError(f"Could not create flow path to node {target_node_id}")
        
        # Execute the partial flow
        accepted_records, rejected_records = await self._execute_flow_with_records(
            records, partial_flow, table_name
        )
        
        return self._create_execution_result(
            records, accepted_records, rejected_records,
            execution_context={
                "target_node_id": target_node_id,
                "execution_mode": "flow_to_node",
                "nodes_executed": len(partial_flow.get("nodes", []))
            }
        )
    
    async def execute_flow_from_node(
        self,
        source: str,
        start_node_id: str,
        flow_data: Dict[str, Any],
        table_name: str,
        limit: int | None = None
    ) -> Dict[str, Any]:
        """
        Execute flow from the specified node to the end.
        
        Args:
            source: Source identifier
            start_node_id: ID of the node to start from
            flow_data: Complete flow data
            table_name: Database table to process
            limit: Maximum records to process
            
        Returns:
            Execution results with statistics and processed records
        """
        logger.info(f"Executing flow from node {start_node_id}")
        
        # Get input data from database
        records = await self._get_input_records(source, table_name, limit)
        if not records:
            return self._create_empty_result(f"No records found for source '{source}' in table '{table_name}'")
        
        # Create partial flow from start node
        partial_flow = self._create_flow_from_node(start_node_id, flow_data)
        if not partial_flow:
            raise ValueError(f"Could not create flow path from node {start_node_id}")
        
        # Execute the partial flow
        accepted_records, rejected_records = await self._execute_flow_with_records(
            records, partial_flow, table_name
        )
        
        return self._create_execution_result(
            records, accepted_records, rejected_records,
            execution_context={
                "start_node_id": start_node_id,
                "execution_mode": "flow_from_node",
                "nodes_executed": len(partial_flow.get("nodes", []))
            }
        )
    
    async def _get_input_records(self, source: str, table_name: str, limit: int | None = None) -> List[Any]:
        """Get input records from the specified database table."""
        table_model = get_table_model(table_name)
        if not table_model:
            raise ValueError(f"Invalid table name: {table_name}")
        
        with SessionLocal() as session:
            query = session.query(table_model)
            
            # Filter by source if the table has a source column
            if hasattr(table_model, "source"):
                query = query.filter(table_model.source == source)
            
            # Limit the number of records
            if limit:
                records = query.limit(limit).all()
            else:
                records = query.all()
            
            # Return the actual ORM objects for the rules engine
            return records
    
    def _create_single_node_flow(self, node: Dict[str, Any], flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a minimal flow containing only the specified node."""
        # Create a source node for input
        source_node = self._find_source_node(flow_data)
        if not source_node:
            raise ValueError("No source node found in flow data")
        
        # Create minimal flow with source and target node
        minimal_flow = {
            "nodes": [source_node, node],
            "edges": [
                {
                    "id": f"edge-{source_node['id']}-{node['id']}",
                    "source": source_node["id"],
                    "target": node["id"],
                    "sourceHandle": self._get_appropriate_source_handle(source_node, node),
                    "targetHandle": "input"
                }
            ],
            "source": flow_data.get("source"),
            "version": "1.0"
        }
        
        return minimal_flow
    
    def _create_flow_to_node(self, target_node_id: str, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a partial flow from start up to the target node."""
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        # Find all nodes that need to be included (from source to target)
        included_nodes = self._find_nodes_to_target(target_node_id, nodes, edges)
        if not included_nodes:
            return None
        
        # Filter nodes and edges
        filtered_nodes = [node for node in nodes if node["id"] in included_nodes]
        filtered_edges = [
            edge for edge in edges 
            if edge["source"] in included_nodes and edge["target"] in included_nodes
        ]
        
        return {
            "nodes": filtered_nodes,
            "edges": filtered_edges,
            "source": flow_data.get("source"),
            "version": "1.0"
        }
    
    def _create_flow_from_node(self, start_node_id: str, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a partial flow from the start node to the end."""
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        # Find all nodes that need to be included (from start to end)
        included_nodes = self._find_nodes_from_start(start_node_id, nodes, edges)
        if not included_nodes:
            return None
        
        # Add source node for data input
        source_node = self._find_source_node(flow_data)
        if source_node and source_node["id"] not in included_nodes:
            included_nodes.add(source_node["id"])
        
        # Filter nodes and edges
        filtered_nodes = [node for node in nodes if node["id"] in included_nodes]
        filtered_edges = [
            edge for edge in edges 
            if edge["source"] in included_nodes and edge["target"] in included_nodes
        ]
        
        return {
            "nodes": filtered_nodes,
            "edges": filtered_edges,
            "source": flow_data.get("source"),
            "version": "1.0"
        }
    
    def _find_nodes_to_target(self, target_node_id: str, nodes: List[Dict], edges: List[Dict]) -> Set[str]:
        """Find all nodes from source to target using BFS traversal."""
        # Find source nodes
        source_nodes = {node["id"] for node in nodes if node.get("type") == "source"}
        if not source_nodes:
            return set()
        
        # Build adjacency list
        adjacency = {}
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]
            if source_id not in adjacency:
                adjacency[source_id] = []
            adjacency[source_id].append(target_id)
        
        # BFS to find path to target
        visited = set()
        queue = list(source_nodes)
        path_nodes = set(source_nodes)
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            if current == target_node_id:
                return path_nodes
            
            # Add connected nodes
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
                    path_nodes.add(neighbor)
        
        return set()
    
    def _find_nodes_from_start(self, start_node_id: str, nodes: List[Dict], edges: List[Dict]) -> Set[str]:
        """Find all nodes from start to end using DFS traversal."""
        # Build adjacency list
        adjacency = {}
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]
            if source_id not in adjacency:
                adjacency[source_id] = []
            adjacency[source_id].append(target_id)
        
        # DFS to find all reachable nodes from start
        visited = set()
        stack = [start_node_id]
        reachable_nodes = {start_node_id}
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            
            # Add connected nodes
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    stack.append(neighbor)
                    reachable_nodes.add(neighbor)
        
        return reachable_nodes
    
    def _find_source_node(self, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the source node in the flow data."""
        for node in flow_data.get("nodes", []):
            if node.get("type") == "source":
                return node
        return None
    
    def _get_appropriate_source_handle(self, source_node: Dict[str, Any], target_node: Dict[str, Any]) -> str:
        """Get the appropriate source handle based on the target node's table requirement."""
        target_table = target_node.get("data", {}).get("table")
        if target_table:
            return f"table-{target_table}"
        # Default to first available handle
        handles = source_node.get("handleBounds", {}).get("source", [])
        if handles:
            return handles[0].get("id", "table-m3u_channels")
        return "table-m3u_channels"
    
    async def _execute_flow_with_records(
        self, 
        records: List[Any], 
        flow_data: Dict[str, Any], 
        table_name: str = "m3u_channels"
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Execute flow configuration on the provided records."""
        # Create temporary flow file for the rules engine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(flow_data, temp_file, indent=2)
            temp_flow_path = temp_file.name
        
        try:
            # Execute the flow using the enhanced rules engine with custom flow
            # Override the flow configuration to use our minimal flow
            source_name = flow_data.get("source", "unknown")
            
            # Temporarily override the flow configuration
            original_config = self.rules_engine._flow_cache.get(source_name)
            self.rules_engine._flow_cache[source_name] = flow_data
            
            try:
                accepted_records, rejected_records = self.rules_engine.apply_flow_to_records_vectorized(
                    records, table_name, source_name
                )
                return accepted_records, rejected_records
            finally:
                # Restore original configuration
                if original_config is not None:
                    self.rules_engine._flow_cache[source_name] = original_config
                else:
                    self.rules_engine._flow_cache.pop(source_name, None)
        finally:
            # Clean up temporary file
            if os.path.exists(temp_flow_path):
                os.unlink(temp_flow_path)
    
    def _create_execution_result(
        self,
        original_records: List[Dict[str, Any]],
        accepted_records: List[Dict[str, Any]],
        rejected_records: List[Dict[str, Any]],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create standardized execution result."""
        total_records = len(original_records)
        accepted_count = len(accepted_records)
        rejected_count = len(rejected_records)
        
        # Calculate tracing statistics
        records_with_trace = len([
            r for r in accepted_records + rejected_records
            if r.get("_trace") and len(r.get("_trace", [])) > 0
        ])
        
        records_with_filter_reasons = len([
            r for r in rejected_records
            if r.get("_filter_reasons") and len(r.get("_filter_reasons", [])) > 0
        ])
        
        return {
            "source": execution_context.get("source", "unknown"),
            "total_records": total_records,
            "execution_results": {
                "accepted": accepted_records[:10],  # Limit for response size
                "rejected": rejected_records[:10],   # Limit for response size
                "stats": {
                    "total": total_records,
                    "accepted": accepted_count,
                    "rejected": rejected_count,
                    "with_trace": records_with_trace,
                    "with_filter_reasons": records_with_filter_reasons,
                },
            },
            "execution_context": execution_context,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_filtered_rows_for_node(
        self,
        source: str,
        target_node_id: str,
        flow_data: Dict[str, Any],
        table_name: str,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Get the filtered rows that will be input to the specified node.
        
        This function traces the flow execution up to (but not including) the target node
        to determine what data the target node will receive as input.
        
        Args:
            source: Source identifier
            target_node_id: ID of the node to get input data for
            flow_data: Complete flow data
            table_name: Database table to process
            limit: Limit the number of rows returned
            
        Returns:
            List of records that will be input to the target node
        """
        logger.info(f"Getting filtered rows for node {target_node_id}")
        if limit:
            logger.info(f"Limiting output rows to {limit}")
        
        # Get all records from the source
        all_records = await self._get_input_records(source, table_name)
        if not all_records:
            logger.warning(f"No records found for source '{source}' in table '{table_name}'")
            return []
        
        # Find the path to the target node (excluding the target itself)
        path_to_target = self._get_path_to_node(target_node_id, flow_data)
        logger.info(f"Path to target node {target_node_id}: {path_to_target}")
        
        if not path_to_target:
            # If no path found or target is a source node, return all records
            logger.info(f"No path to target node {target_node_id}, returning all source records")
            result_records = [self._record_to_dict(record) for record in all_records]
            if limit:
                result_records = result_records[:limit]
            return result_records
        
        # Execute flow up to (but not including) the target node
        if len(path_to_target) <= 2:
            # Target node is directly connected to source (path: [source, target])
            logger.info(f"Target node {target_node_id} is directly connected to source, returning raw source data")
            result_records = [self._record_to_dict(record) for record in all_records]
            if limit:
                result_records = result_records[:limit]
            return result_records
        
        # Create flow that stops at the node before target
        previous_node_id = path_to_target[-2]  # Node before target
        partial_flow = self._create_flow_to_node(previous_node_id, flow_data)
        
        if not partial_flow:
            logger.warning(f"Could not create partial flow to node {previous_node_id}")
            result_records = [self._record_to_dict(record) for record in all_records]
            if limit:
                result_records = result_records[:limit]
            return result_records
        
        # Execute the partial flow to get filtered records
        accepted_records, rejected_records = await self._execute_flow_with_records(
            all_records, partial_flow, table_name
        )
        
        # Determine which records should go to the target node based on edge configuration
        target_records = self._get_records_for_target_node(
            target_node_id, previous_node_id, accepted_records, rejected_records, flow_data
        )

        if limit:
            target_records = target_records[:limit]
        
        logger.info(f"Found {len(target_records)} records for node {target_node_id}")
        return target_records
    
    async def process_rows_through_node(
        self,
        source: str,
        target_node_id: str,
        flow_data: Dict[str, Any],
        table_name: str,
        input_rows: Optional[List[Dict[str, Any]]] = None,
        limit: int | None = None,
    ) -> Dict[str, Any]:
        """
        Process specific input rows through a target node to see filtering results.
        
        Args:
            source: Source identifier
            target_node_id: ID of the node to process through
            flow_data: Complete flow data
            table_name: Database table name
            input_rows: Specific rows to process (if None, gets filtered rows for node)
            limit: Limit the number of input rows to process
            
        Returns:
            Dict with input rows, passed rows, caught rows, and statistics
        """
        logger.info(f"Processing rows through node {target_node_id}")
        
        # Get input rows if not provided
        if input_rows is None:
            input_rows = await self.get_filtered_rows_for_node(
                source, target_node_id, flow_data, table_name, limit
            )
        elif limit:
            input_rows = input_rows[:limit]
        
        if not input_rows:
            return {
                "node_id": target_node_id,
                "input_rows": [],
                "passed_rows": [],
                "caught_rows": [],
                "stats": {"input": 0, "passed": 0, "caught": 0}
            }
        
        # Find the target node configuration
        target_node = None
        for node in flow_data.get("nodes", []):
            if node.get("id") == target_node_id:
                target_node = node
                break
        
        if not target_node:
            raise ValueError(f"Node {target_node_id} not found in flow")
        
        if target_node.get("type") != "rule":
            raise ValueError(f"Node {target_node_id} is not a rule node (type: {target_node.get('type')})")
        
        # Process rows through the rule
        passed_rows = []
        caught_rows = []
        
        rule_config = target_node.get("data", {})
        pattern = rule_config.get("pattern", "")
        field = rule_config.get("field", "")
        
        if not pattern or not field:
            raise ValueError(f"Rule node {target_node_id} missing pattern or field configuration")
        
        import re
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern in node {target_node_id}: {e}")
        
        for row in input_rows:
            field_value = str(row.get(field, ""))
            
            if compiled_pattern.match(field_value):
                # Rule matched - add to passed
                passed_rows.append({**row, "_rule_result": "passed", "_matched_value": field_value})
            else:
                # Rule didn't match - add to caught
                caught_rows.append({**row, "_rule_result": "caught", "_matched_value": field_value})
        
        logger.info(f"Processed {len(input_rows)} rows through {target_node_id}: {len(passed_rows)} passed, {len(caught_rows)} caught")
        
        return {
            "node_id": target_node_id,
            "rule_name": rule_config.get("ruleName", target_node_id),
            "pattern": pattern,
            "field": field,
            "input_rows": input_rows,
            "passed_rows": passed_rows,
            "caught_rows": caught_rows,
            "stats": {
                "input": len(input_rows),
                "passed": len(passed_rows),
                "caught": len(caught_rows),
                "pass_rate": len(passed_rows) / len(input_rows) if input_rows else 0
            }
        }
    
    def _get_path_to_node(self, target_node_id: str, flow_data: Dict[str, Any]) -> List[str]:
        """
        Get the execution path from source to target node.
        
        Returns:
            List of node IDs in execution order from source to target
        """
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        # Find source node
        source_node = self._find_source_node(flow_data)
        if not source_node:
            return []
        
        # Build adjacency list
        adjacency = {}
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]
            if source_id not in adjacency:
                adjacency[source_id] = []
            adjacency[source_id].append(target_id)
        
        # BFS to find path to target
        queue = [(source_node["id"], [source_node["id"]])]
        visited = set()
        
        while queue:
            current_node, path = queue.pop(0)
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            if current_node == target_node_id:
                return path
            
            # Add neighbors to queue
            for neighbor in adjacency.get(current_node, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        
        return []
    
    def _get_records_for_target_node(
        self,
        target_node_id: str,
        previous_node_id: str,
        accepted_records: List[Dict[str, Any]],
        rejected_records: List[Dict[str, Any]],
        flow_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Determine which records (accepted or rejected) should go to the target node
        based on the edge configuration between previous and target nodes.
        """
        # Find the edge from previous node to target node
        edges = flow_data.get("edges", [])
        connecting_edge = None
        
        for edge in edges:
            if edge["source"] == previous_node_id and edge["target"] == target_node_id:
                connecting_edge = edge
                break
        
        if not connecting_edge:
            logger.warning(f"No edge found from {previous_node_id} to {target_node_id}")
            return accepted_records  # Default to accepted records
        
        # Determine which path the edge represents
        source_handle = connecting_edge.get("sourceHandle", "")
        
        # Rule nodes typically have "passed" and "caught" handles
        # "passed" handle connects to accepted records
        # "caught" handle connects to rejected records
        if "caught" in source_handle.lower() or "rejected" in source_handle.lower():
            return rejected_records
        else:
            # Default to accepted records for "passed" or unspecified handles
            return accepted_records
    
    def _record_to_dict(self, record: Any) -> Dict[str, Any]:
        """Convert ORM record to dictionary format, including runtime fields."""
        if hasattr(record, '__dict__'):
            # ORM object - convert to dict
            result = {}
            for column in record.__table__.columns:
                result[column.name] = getattr(record, column.name)
            
            # Include runtime fields that might not be in the table schema
            runtime_fields = ['_trace', 'filter_reasons', 'accepted']
            for field in runtime_fields:
                if hasattr(record, field):
                    result[field] = getattr(record, field)
            
            return result
        elif isinstance(record, dict):
            # Already a dictionary
            return record
        else:
            # Fallback - try to convert to dict
            return dict(record) if hasattr(record, 'keys') else {}

    async def _persist_trace_data(self, processed_records, table_name: str, source: str, batch_size: int = 5_000) -> None:
        logger.info("Persisting trace data for %s records in %s", len(processed_records), table_name)
        if not processed_records:
            return

        session = SessionLocal()
        try:
            # If a transaction already exists, reuse it; otherwise start one
            ctx = nullcontext() if session.in_transaction() else session.begin()
            with ctx:
                # One temp table for all batches
                session.execute(text("""
                    CREATE TEMP TABLE IF NOT EXISTS _stage_updates (
                        id INTEGER PRIMARY KEY,
                        _trace TEXT,              -- may be NULL
                        _trace_set INTEGER,       -- 1=set, 0=leave as-is
                        filter_reasons TEXT,
                        filter_set INTEGER,
                        accepted INTEGER,
                        accepted_set INTEGER
                    )
                """))

                for batch in _chunks(processed_records, batch_size):
                    rows = []
                    for r in batch:
                        rid = r.get("id")
                        if rid is None:
                            continue
                        # encode the 3-state intent: set to value / set to NULL / leave alone
                        trc_present = "_trace" in r
                        flt_present = "filter_reasons" in r
                        acc_present = "accepted" in r
                        if not (trc_present or flt_present or acc_present):
                            continue

                        rows.append({
                            "id": rid,
                            "_trace": None if (trc_present and r["_trace"] is None) else (
                                json.dumps(r["_trace"]) if trc_present else None),
                            "_trace_set": 1 if trc_present else 0,
                            "filter_reasons": None if (flt_present and r["filter_reasons"] is None) else (
                                json.dumps(r["filter_reasons"]) if flt_present else None),
                            "filter_set": 1 if flt_present else 0,
                            "accepted": None if (acc_present and r["accepted"] is None) else (
                                1 if (acc_present and r["accepted"]) else 0 if acc_present else None),
                            "accepted_set": 1 if acc_present else 0,
                        })
                    if not rows:
                        continue

                    # clear stage & insert executemany
                    session.execute(text("DELETE FROM _stage_updates"))
                    session.execute(
                        text("""
                            INSERT INTO _stage_updates
                            (id,_trace,_trace_set,filter_reasons,filter_set,accepted,accepted_set)
                            VALUES (:id,:_trace,:_trace_set,:filter_reasons,:filter_set,:accepted,:accepted_set)
                        """),
                        rows
                    )

                    # update only where the *_set flags say "apply"
                    session.execute(text(f"""
                        UPDATE {table_name} AS t
                        SET
                        _trace = CASE
                            WHEN (SELECT s._trace_set FROM _stage_updates s WHERE s.id=t.id)=1
                            THEN (SELECT s._trace FROM _stage_updates s WHERE s.id=t.id)
                            ELSE _trace END,
                        filter_reasons = CASE
                            WHEN (SELECT s.filter_set FROM _stage_updates s WHERE s.id=t.id)=1
                            THEN (SELECT s.filter_reasons FROM _stage_updates s WHERE s.id=t.id)
                            ELSE filter_reasons END,
                        accepted = CASE
                            WHEN (SELECT s.accepted_set FROM _stage_updates s WHERE s.id=t.id)=1
                            THEN (SELECT s.accepted FROM _stage_updates s WHERE s.id=t.id)
                            ELSE accepted END
                        WHERE EXISTS (SELECT 1 FROM _stage_updates s WHERE s.id=t.id)
                    """))

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _create_empty_result(self, message: str) -> Dict[str, Any]:
        """Create empty result for cases with no input data."""
        return {
            "message": message,
            "total_records": 0,
            "execution_results": {
                "accepted": [],
                "rejected": [],
                "stats": {
                    "total": 0,
                    "accepted": 0,
                    "rejected": 0,
                    "with_trace": 0,
                    "with_filter_reasons": 0,
                },
            },
            "timestamp": datetime.now().isoformat()
        }
