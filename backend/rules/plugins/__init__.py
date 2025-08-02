"""Built-in Rules Plugin System for ISeeTV.

This module provides a plugin system for built-in rules that extend the existing
ingestion and post-load rules systems with intelligent filtering capabilities.

Architecture:
- Atomic Design: Each plugin has single responsibility
- Plugin Interface: Standardized contract for all built-in rules
- Modular: Clear separation between plugin types and implementations
- Extensible: Easy to add new plugins without modifying core system
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from models.models import EpgChannel, M3uChannel, Program


@dataclass
class PluginConfig:
    """Configuration for a built-in rule plugin."""
    
    enabled: bool = True
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class PluginResult:
    """Result of applying a built-in rule plugin."""
    
    passed: bool
    reason: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BasePlugin(ABC):
    """Abstract base class for all built-in rule plugins."""
    
    def __init__(self, config: PluginConfig):
        """Initialize plugin with configuration."""
        self.config = config
        self.enabled = config.enabled
        self.parameters = config.parameters
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this plugin."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this plugin does."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Version of this plugin."""
        pass
    
    @property
    @abstractmethod
    def supported_tables(self) -> List[str]:
        """List of table names this plugin can process."""
        pass
    
    @abstractmethod
    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate plugin configuration.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass
    
    @abstractmethod
    def apply(
        self,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
        context: Dict[str, Any] = None
    ) -> PluginResult:
        """Apply plugin logic to a single record.
        
        Args:
            record: The record to evaluate
            table_name: Name of the table being processed
            source_name: Name of the source being processed
            context: Additional context data (e.g., database session, related records)
            
        Returns:
            PluginResult indicating whether record should pass or be filtered
        """
        pass
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for this plugin."""
        return {}
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get JSON schema for plugin parameters."""
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }


class ChannelPlugin(BasePlugin):
    """Base class for plugins that operate on channel records."""
    
    @property
    def supported_tables(self) -> List[str]:
        return ["m3u_channels", "epg_channels"]


class ProgramPlugin(BasePlugin):
    """Base class for plugins that operate on program records."""
    
    @property
    def supported_tables(self) -> List[str]:
        return ["programs"]


class CrossTablePlugin(BasePlugin):
    """Base class for plugins that operate across multiple tables."""
    
    @property
    def supported_tables(self) -> List[str]:
        return ["m3u_channels", "epg_channels", "programs"]
