"""Plugin Integration for Built-in Rules System.

This module integrates the plugin system with the existing ingestion and post-load
rules engines, providing seamless execution of built-in rules alongside user-defined rules.

Architecture:
- Atomic Design: Each function has single responsibility
- Integration Layer: Bridges plugins with existing rules system
- Modular: Clear separation between plugin execution and rules engine
- Backward Compatible: Doesn't modify existing rules functionality
"""

import json
import os
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from common.constants import DATA_PATH
from common.log_utils import get_logger
from models.models import EpgChannel, M3uChannel, Program
from rules.plugins import PluginConfig, PluginResult
from rules.plugins.registry import get_plugin_registry, load_all_plugins

logger = get_logger(__name__)

# Configuration file for built-in plugins
PLUGINS_CONFIG_FILE = os.path.join(DATA_PATH, "plugins.json")


class PluginIntegration:
    """Integration layer for built-in rule plugins with source-based configuration."""
    
    def __init__(self):
        """Initialize the plugin integration system."""
        # Source-based plugin configuration: {source_name: {plugin_name: config}}
        self._plugins_config: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._config_loaded = False
        logger.debug("PluginIntegration initialized with source-based architecture")
    
    def load_plugins_config(self) -> None:
        """Load plugins configuration from file."""
        if self._config_loaded and os.path.exists(PLUGINS_CONFIG_FILE):
            # Check if file has been modified
            config_mtime = os.path.getmtime(PLUGINS_CONFIG_FILE)
            if hasattr(self, '_config_mtime') and config_mtime <= self._config_mtime:
                return
            self._config_mtime = config_mtime
        
        try:
            if os.path.exists(PLUGINS_CONFIG_FILE):
                with open(PLUGINS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._plugins_config = json.load(f)
                logger.info(f"Loaded plugins configuration with {len(self._plugins_config)} plugins")
            else:
                # Create default configuration
                self._plugins_config = self._create_default_config()
                self.save_plugins_config()
                logger.info("Created default plugins configuration")
            
            self._config_loaded = True
        
        except Exception as e:
            logger.error(f"Error loading plugins configuration: {e}")
            self._plugins_config = {}
    
    def _create_default_config(self) -> Dict[str, Dict[str, Any]]:
        """Create default plugins configuration."""
        # Load available plugins to get their default parameters
        load_all_plugins()
        registry = get_plugin_registry()
        available_plugins = registry.get_available_plugins()
        
        default_config = {}
        for plugin_name, plugin_info in available_plugins.items():
            default_config[plugin_name] = {
                "enabled": False,  # Plugins disabled by default
                "parameters": plugin_info["default_parameters"]
            }
        
        return default_config
    
    def save_plugins_config(self) -> None:
        """Save plugins configuration to file."""
        try:
            os.makedirs(os.path.dirname(PLUGINS_CONFIG_FILE), exist_ok=True)
            with open(PLUGINS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._plugins_config, f, indent=2, ensure_ascii=False)
            logger.info("Saved plugins configuration")
        except Exception as e:
            logger.error(f"Error saving plugins configuration: {e}")
    
    def get_plugins_config(self, source_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get current plugins configuration.
        
        Args:
            source_name: If provided, returns config for specific source.
                        If None, returns all available plugins with default config.
        
        Returns:
            Plugin configuration dictionary
        """
        if not self._config_loaded:
            self.load_plugins_config()
        
        if source_name:
            # Return source-specific configuration
            return self._plugins_config.get(source_name, {}).copy()
        else:
            # Return all available plugins with their default configurations
            load_all_plugins()
            registry = get_plugin_registry()
            available_plugins = {}
            
            for plugin_name in registry.list_plugins():
                plugin_class = registry.get_plugin_class(plugin_name)
                if plugin_class:
                    # Create temporary instance to get default config
                    temp_config = PluginConfig()
                    temp_instance = plugin_class(temp_config)
                    available_plugins[plugin_name] = {
                        "enabled": False,
                        "parameters": temp_instance.get_default_parameters()
                    }
            
            return available_plugins
    
    def update_plugin_config(self, source_name: str, plugin_name: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a specific plugin on a specific source.
        
        Args:
            source_name: Name of the source
            plugin_name: Name of the plugin
            config: Plugin configuration
            
        Returns:
            True if successful, False otherwise
        """
        if not self._config_loaded:
            self.load_plugins_config()
        
        try:
            if source_name not in self._plugins_config:
                self._plugins_config[source_name] = {}
            
            self._plugins_config[source_name][plugin_name] = config
            self.save_plugins_config()
            logger.info(f"Updated configuration for plugin {plugin_name} on source {source_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating plugin configuration: {e}")
            return False
    
    def update_plugins_config_for_source(self, source_name: str, plugins_config: Dict[str, Dict[str, Any]]) -> bool:
        """Update configuration for all plugins on a specific source.
        
        Args:
            source_name: Name of the source
            plugins_config: Dictionary of plugin configurations
            
        Returns:
            True if successful, False otherwise
        """
        if not self._config_loaded:
            self.load_plugins_config()
        
        try:
            self._plugins_config[source_name] = plugins_config
            self.save_plugins_config()
            logger.info(f"Updated all plugin configurations for source {source_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating plugins configuration for source {source_name}: {e}")
            return False
    
    def apply_plugins_to_record(
        self,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
        db_session: Optional[Session] = None
    ) -> List[PluginResult]:
        """Apply all enabled plugins to a record for the specified source.
        
        Args:
            record: Record to process
            table_name: Name of the table being processed
            source_name: Name of the source being processed
            db_session: Database session for plugins that need database access
            
        Returns:
            List of PluginResult objects from all applied plugins
        """
        if not self._config_loaded:
            self.load_plugins_config()
        
        # Get source-specific plugin configuration
        source_plugins_config = self._plugins_config.get(source_name, {})
        if not source_plugins_config:
            logger.debug(f"No plugin configuration found for source {source_name}")
            return []
        
        # Load plugins if not already loaded
        load_all_plugins()
        registry = get_plugin_registry()
        
        results = []
        context = {"db_session": db_session} if db_session else {}
        
        for plugin_name, plugin_config in source_plugins_config.items():
            if not plugin_config.get("enabled", False):
                continue
            
            try:
                config = PluginConfig(
                    enabled=plugin_config.get("enabled", False),
                    parameters=plugin_config.get("parameters", {})
                )
                
                result = registry.apply_plugin(
                    plugin_name, config, record, table_name, source_name, context
                )
                
                if result:
                    results.append(result)
                    logger.debug(f"Applied plugin {plugin_name} to {table_name} record: {result.passed}")
            
            except Exception as e:
                logger.error(f"Error applying plugin {plugin_name}: {e}")
                results.append(PluginResult(
                    passed=True,
                    reason=f"Plugin error: {str(e)}",
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_plugin_filter_result(
        self,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
        db_session: Optional[Session] = None
    ) -> tuple[bool, Optional[str]]:
        """Get combined filter result from all plugins.
        
        Args:
            record: Record to process
            table_name: Name of the table being processed
            source_name: Name of the source being processed
            db_session: Database session for plugins that need database access
            
        Returns:
            Tuple of (passed, rejection_reason)
        """
        plugin_results = self.apply_plugins_to_record(
            record, table_name, source_name, db_session
        )
        
        # If any plugin rejects the record, it's rejected
        for result in plugin_results:
            if not result.passed:
                return False, f"Built-in plugin '{result.reason}'"
        
        # All plugins passed or no plugins applied
        return True, None
    
    def validate_plugins_config(self, config: Dict[str, Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Validate plugins configuration.
        
        Args:
            config: Plugins configuration to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Load available plugins
        load_all_plugins()
        registry = get_plugin_registry()
        available_plugins = registry.get_available_plugins()
        
        for plugin_name, plugin_config in config.items():
            if plugin_name not in available_plugins:
                errors.append(f"Unknown plugin: {plugin_name}")
                continue
            
            # Validate plugin configuration
            try:
                config_obj = PluginConfig(
                    enabled=plugin_config.get("enabled", False),
                    parameters=plugin_config.get("parameters", {})
                )
                
                plugin = registry.get_plugin(plugin_name, config_obj)
                if plugin is None:
                    errors.append(f"Failed to create plugin instance: {plugin_name}")
                    continue
                
                is_valid, plugin_errors = plugin.validate_config()
                if not is_valid:
                    for error in plugin_errors:
                        errors.append(f"Plugin {plugin_name}: {error}")
            
            except Exception as e:
                errors.append(f"Plugin {plugin_name}: {str(e)}")
        
        return len(errors) == 0, errors


# Global plugin integration instance
plugin_integration = PluginIntegration()


def get_plugin_integration() -> PluginIntegration:
    """Get the global plugin integration instance."""
    return plugin_integration


def apply_plugins_to_record(
    record: Union[M3uChannel, EpgChannel, Program],
    table_name: str,
    source_name: str,
    db_session: Optional[Session] = None
) -> List[PluginResult]:
    """Apply all enabled plugins to a record using the global integration."""
    return plugin_integration.apply_plugins_to_record(
        record, table_name, source_name, db_session
    )


def get_plugin_filter_result(
    record: Union[M3uChannel, EpgChannel, Program],
    table_name: str,
    source_name: str,
    db_session: Optional[Session] = None
) -> tuple[bool, Optional[str]]:
    """Get combined filter result from all plugins using the global integration."""
    return plugin_integration.get_plugin_filter_result(
        record, table_name, source_name, db_session
    )
