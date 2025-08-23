"""
Flow storage utilities for managing per-source flow configurations.
Follows atomic design principles with single-responsibility functions.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .constants import DATA_PATH
from .file_utils import atomic_write_json, atomic_read_json, ensure_file_exists
import logging

logger = logging.getLogger(__name__)


def get_flows_directory() -> Path:
    """Get the flows directory path, creating it if it doesn't exist."""
    flows_dir = Path(DATA_PATH) / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    return flows_dir


def get_flow_file_path(source_name: str) -> Path:
    """Get the file path for a specific source's flow configuration."""
    flows_dir = get_flows_directory()
    # Sanitize source name for filename
    safe_name = "".join(c for c in source_name if c.isalnum() or c in ('-', '_', '.'))
    return flows_dir / f"{safe_name}_flow.json"


def save_flow(source_name: str, flow_data: Dict[str, Any]) -> bool:
    """
    Save flow configuration for a specific source.
    
    Args:
        source_name: Name of the source
        flow_data: Flow configuration data including nodes, edges, layout
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        flow_file = get_flow_file_path(source_name)
        
        # Add metadata
        flow_data_with_meta = {
            **flow_data,
            "source": source_name,
            "saved_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        atomic_write_json(flow_file, flow_data_with_meta)
        return True
        
    except Exception as e:
        print(f"Error saving flow for source '{source_name}': {e}")
        return False


def load_flow(source_name: str) -> Optional[Dict[str, Any]]:
    """
    Load flow configuration for a specific source.
    
    Args:
        source_name: Name of the source
        
    Returns:
        Dict containing flow data or None if not found
    """
    try:
        flow_file = get_flow_file_path(source_name)
        
        if not flow_file.exists():
            return None
            
        flow_data = atomic_read_json(flow_file, default={})
        
        # Return None if file exists but is empty
        if not flow_data:
            return None
            
        return flow_data
        
    except Exception as e:
        print(f"Error loading flow for source '{source_name}': {e}")
        return None


def delete_flow(source_name: str) -> bool:
    """
    Delete flow configuration for a specific source.
    
    Args:
        source_name: Name of the source
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        flow_file = get_flow_file_path(source_name)
        
        if flow_file.exists():
            flow_file.unlink()
            return True
        else:
            # File doesn't exist, consider it successfully "deleted"
            return True
            
    except Exception as e:
        print(f"Error deleting flow for source '{source_name}': {e}")
        return False


def list_saved_flows() -> Dict[str, Dict[str, Any]]:
    """
    List all saved flow configurations.
    
    Returns:
        Dict mapping source names to their flow metadata
    """
    try:
        flows_dir = get_flows_directory()
        flows = {}
        
        for flow_file in flows_dir.glob("*_flow.json"):
            try:
                flow_data = atomic_read_json(flow_file, default_content={})
                if flow_data and "source" in flow_data:
                    source_name = flow_data["source"]
                    flows[source_name] = {
                        "source": source_name,
                        "saved_at": flow_data.get("saved_at"),
                        "version": flow_data.get("version", "1.0"),
                        "node_count": len(flow_data.get("nodes", [])),
                        "edge_count": len(flow_data.get("edges", [])),
                        "layout": flow_data.get("layout", "TB")
                    }
            except Exception as e:
                print(f"Error reading flow file {flow_file}: {e}")
                continue
                
        return flows
        
    except Exception as e:
        print(f"Error listing flows: {e}")
        return {}


def validate_flow_data(flow_data: Dict[str, Any]) -> bool:
    """
    Validate flow data structure.
    
    Args:
        flow_data: Flow data to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check for frontend format (sources, rules, streams, connections)
        frontend_fields = ["sources", "rules", "streams", "connections"]
        has_frontend_format = all(field in flow_data for field in frontend_fields)
        
        # Check for backend format (nodes, edges)
        backend_fields = ["nodes", "edges"]
        has_backend_format = all(field in flow_data for field in backend_fields)
        
        if has_frontend_format:
            # Validate frontend format
            for field in frontend_fields:
                if not isinstance(flow_data[field], list):
                    return False
            
            # Basic validation for sources, rules, streams
            for item in flow_data["sources"] + flow_data["rules"] + flow_data["streams"]:
                if not isinstance(item, dict) or "id" not in item:
                    return False
            
            # Basic validation for connections
            for connection in flow_data["connections"]:
                if not isinstance(connection, dict) or "from" not in connection or "to" not in connection:
                    return False
                    
        elif has_backend_format:
            # Validate backend format
            for field in backend_fields:
                if not isinstance(flow_data[field], list):
                    return False
                    
            # Basic node validation
            for node in flow_data["nodes"]:
                if not isinstance(node, dict) or "id" not in node:
                    return False
                    
            # Basic edge validation
            for edge in flow_data["edges"]:
                if not isinstance(edge, dict) or "source" not in edge or "target" not in edge:
                    return False
        else:
            # Neither format is valid
            return False
                
        return True
        
    except Exception:
        return False


def update_flow_stats(source: str, node_id: str, accepted_count: int, rejected_count: int) -> bool:
    """Update flow statistics in the flow data."""
    logger.info(f"Updating flow statistics for source '{source}' and node '{node_id}'")
    flow_data = load_flow(source)
    processed_count = accepted_count + rejected_count

    for node in flow_data["nodes"]:
        if node["id"] == node_id:
            logger.debug(f"Updating flow statistics for node '{node_id}'")
            node["data"]["stats"]["processed"] = processed_count
            node["data"]["stats"]["passed"] = accepted_count
            node["data"]["stats"]["caught"] = rejected_count
    
            save_flow(source, flow_data)
    
            logger.info(f"Flow execution results saved for source '{source}'")
            return True

    logger.warning(f"Node '{node_id}' not found in flow data for source '{source}'")
    return False