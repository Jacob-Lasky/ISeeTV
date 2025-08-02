"""Plugin Registry for Built-in Rules System.

This module provides a centralized registry for managing built-in rule plugins,
including loading, validation, and execution of plugins.

Architecture:
- Atomic Design: Each function has single responsibility
- Singleton Pattern: Global plugin registry for consistent state
- Modular: Clear separation between registration and execution
- Extensible: Easy to add new plugins without modifying registry
"""

import importlib
import inspect
import os
from typing import Any, Dict, List, Optional, Type, Union

from common.log_utils import get_logger
from models.models import EpgChannel, M3uChannel, Program
from rules.plugins import BasePlugin, PluginConfig, PluginResult

logger = get_logger(__name__)


class PluginRegistry:
    """Registry for managing built-in rule plugins."""
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self._plugin_instances: Dict[str, BasePlugin] = {}
        self._loaded = False
        logger.debug("PluginRegistry initialized")
    
    def load_plugins(self, plugins_dir: Optional[str] = None) -> None:
        """Load all plugins from the plugins directory.
        
        Args:
            plugins_dir: Directory to load plugins from (defaults to current directory)
        """
        if self._loaded:
            logger.debug("Plugins already loaded, skipping reload")
            return
        
        if plugins_dir is None:
            plugins_dir = os.path.dirname(__file__)
        
        logger.info(f"Loading plugins from {plugins_dir}")
        
        # Get all Python files in the plugins directory
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                self._load_plugin_module(module_name, plugins_dir)
        
        self._loaded = True
        logger.info(f"Loaded {len(self._plugins)} plugins: {list(self._plugins.keys())}")
    
    def _load_plugin_module(self, module_name: str, plugins_dir: str) -> None:
        """Load a single plugin module and register its plugins.
        
        Args:
            module_name: Name of the module to load
            plugins_dir: Directory containing the module
        """
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                f"rules.plugins.{module_name}",
                os.path.join(plugins_dir, f"{module_name}.py")
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Could not load spec for plugin module {module_name}")
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find all plugin classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BasePlugin) and 
                    obj != BasePlugin and 
                    not inspect.isabstract(obj)):
                    self.register_plugin(obj)
                    logger.debug(f"Registered plugin class {name} from module {module_name}")
        
        except Exception as e:
            logger.error(f"Error loading plugin module {module_name}: {e}")
    
    def register_plugin(self, plugin_class: Type[BasePlugin]) -> None:
        """Register a plugin class.
        
        Args:
            plugin_class: The plugin class to register
        """
        # Create a temporary instance to get the plugin name
        temp_config = PluginConfig()
        temp_instance = plugin_class(temp_config)
        plugin_name = temp_instance.name
        
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} already registered, overwriting")
        
        self._plugins[plugin_name] = plugin_class
        logger.debug(f"Registered plugin: {plugin_name}")
    
    def get_plugin(self, plugin_name: str, config: PluginConfig) -> Optional[BasePlugin]:
        """Get a plugin instance with the given configuration.
        
        Args:
            plugin_name: Name of the plugin to get
            config: Configuration for the plugin
            
        Returns:
            Plugin instance or None if not found
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin {plugin_name} not found in registry")
            return None
        
        # Create new instance with the provided config
        plugin_class = self._plugins[plugin_name]
        try:
            plugin_instance = plugin_class(config)
            
            # Validate configuration
            is_valid, errors = plugin_instance.validate_config()
            if not is_valid:
                logger.error(f"Invalid configuration for plugin {plugin_name}: {errors}")
                return None
            
            return plugin_instance
        
        except Exception as e:
            logger.error(f"Error creating plugin instance {plugin_name}: {e}")
            return None
    
    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available plugins.
        
        Returns:
            Dictionary mapping plugin names to their metadata
        """
        if not self._loaded:
            self.load_plugins()
        
        plugins_info = {}
        for plugin_name, plugin_class in self._plugins.items():
            # Create temporary instance to get metadata
            temp_config = PluginConfig()
            temp_instance = plugin_class(temp_config)
            
            plugins_info[plugin_name] = {
                "name": temp_instance.name,
                "description": temp_instance.description,
                "version": temp_instance.version,
                "supported_tables": temp_instance.supported_tables,
                "default_parameters": temp_instance.get_default_parameters(),
                "parameter_schema": temp_instance.get_parameter_schema()
            }
        
        return plugins_info
    
    def list_plugins(self) -> List[str]:
        """Get a list of all available plugin names.
        
        Returns:
            List of plugin names
        """
        if not self._loaded:
            self.load_plugins()
        
        return list(self._plugins.keys())
    
    def get_plugin_class(self, plugin_name: str) -> Optional[Type[BasePlugin]]:
        """Get a plugin class by name.
        
        Args:
            plugin_name: Name of the plugin to get
            
        Returns:
            Plugin class or None if not found
        """
        if not self._loaded:
            self.load_plugins()
        
        return self._plugins.get(plugin_name)
    
    def apply_plugin(
        self,
        plugin_name: str,
        config: PluginConfig,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
        context: Dict[str, Any] = None
    ) -> Optional[PluginResult]:
        """Apply a plugin to a record.
        
        Args:
            plugin_name: Name of the plugin to apply
            config: Configuration for the plugin
            record: Record to process
            table_name: Name of the table being processed
            source_name: Name of the source being processed
            context: Additional context data
            
        Returns:
            PluginResult or None if plugin not found or error occurred
        """
        plugin = self.get_plugin(plugin_name, config)
        if plugin is None:
            return None
        
        if not plugin.enabled:
            logger.debug(f"Plugin {plugin_name} is disabled, skipping")
            return PluginResult(passed=True, reason="Plugin disabled")
        
        if table_name not in plugin.supported_tables:
            logger.debug(f"Plugin {plugin_name} does not support table {table_name}")
            return PluginResult(passed=True, reason=f"Table {table_name} not supported")
        
        try:
            return plugin.apply(record, table_name, source_name, context or {})
        except Exception as e:
            logger.error(f"Error applying plugin {plugin_name}: {e}")
            return PluginResult(passed=True, reason=f"Plugin error: {str(e)}")


# Global plugin registry instance
plugin_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    return plugin_registry


def load_all_plugins() -> None:
    """Load all available plugins into the registry."""
    plugin_registry.load_plugins()


def get_available_plugins() -> Dict[str, Dict[str, Any]]:
    """Get information about all available plugins."""
    return plugin_registry.get_available_plugins()


def apply_plugin(
    plugin_name: str,
    config: PluginConfig,
    record: Union[M3uChannel, EpgChannel, Program],
    table_name: str,
    source_name: str,
    context: Dict[str, Any] = None
) -> Optional[PluginResult]:
    """Apply a plugin to a record using the global registry."""
    return plugin_registry.apply_plugin(
        plugin_name, config, record, table_name, source_name, context
    )
