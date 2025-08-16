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

from common.db import SessionLocal
from common.log_utils import get_logger
from models.db_models import get_table_model
from .enhanced_rules_engine import EnhancedRulesEngine

logger = get_logger(__name__)


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
        limit: int
    ) -> Dict[str, Any]:
        """
        Execute a single node independently.
        
        Args:
            source: Source identifier
            node: Node configuration to execute
            flow_data: Complete flow data for context
            table_name: Database table to process
            limit: Maximum records to process
            
        Returns:
            Execution results with statistics and processed records
        """
        logger.info(f"Executing single node {node.get('id')} of type {node.get('type')}")
        
        # Get input data from database
        records = await self._get_input_records(source, table_name, limit)
        if not records:
            return self._create_empty_result(f"No records found for source '{source}' in table '{table_name}'")
        
        # Create a minimal flow with just this node
        minimal_flow = self._create_single_node_flow(node, flow_data)
        
        # Execute the node
        accepted_records, rejected_records = await self._execute_flow_with_records(
            records, minimal_flow, table_name
        )
        
        return self._create_execution_result(
            records, accepted_records, rejected_records,
            execution_context={
                "node_id": node.get("id"),
                "node_type": node.get("type"),
                "execution_mode": "single_node"
            }
        )
    
    async def execute_flow_to_node(
        self,
        source: str,
        target_node_id: str,
        flow_data: Dict[str, Any],
        table_name: str,
        limit: int
    ) -> Dict[str, Any]:
        """
        Execute flow from start up to (and including) the specified node.
        
        Args:
            source: Source identifier
            target_node_id: ID of the target node to stop at
            flow_data: Complete flow data
            table_name: Database table to process
            limit: Maximum records to process
            
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
        limit: int
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
    
    async def _get_input_records(self, source: str, table_name: str, limit: int) -> List[Any]:
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
            records = query.limit(limit).all()
            
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
            # Execute the flow using the enhanced rules engine
            # The method expects ORM objects, table name, and source name
            source_name = flow_data.get("source", "unknown")
            accepted_records, rejected_records = self.rules_engine.apply_flow_to_records_vectorized(
                records, table_name, source_name
            )
            return accepted_records, rejected_records
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
