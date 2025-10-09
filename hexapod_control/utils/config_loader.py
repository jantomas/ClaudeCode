"""Configuration loader for YAML configuration files."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigLoader:
    """Load and manage YAML configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Directory containing configuration files.
                       Defaults to 'config' in project root.
        """
        if config_dir is None:
            # Get project root (parent of utils directory)
            project_root = Path(__file__).parent.parent
            self.config_dir = project_root / "config"
        else:
            self.config_dir = Path(config_dir)

        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")

        self._configs: Dict[str, Any] = {}
        logger.info(f"ConfigLoader initialized with directory: {self.config_dir}")

    def load(self, config_name: str, required: bool = True) -> Optional[Dict[str, Any]]:
        """
        Load a YAML configuration file.

        Args:
            config_name: Name of config file (without .yaml extension)
            required: If True, raise error if file not found

        Returns:
            Dictionary containing configuration data, or None if not found and not required

        Raises:
            FileNotFoundError: If required config file not found
            yaml.YAMLError: If YAML parsing fails
        """
        # Check if already loaded
        if config_name in self._configs:
            logger.debug(f"Returning cached config: {config_name}")
            return self._configs[config_name]

        # Build file path
        config_file = self.config_dir / f"{config_name}.yaml"

        if not config_file.exists():
            if required:
                raise FileNotFoundError(f"Required configuration file not found: {config_file}")
            else:
                logger.warning(f"Optional configuration file not found: {config_file}")
                return None

        # Load YAML file
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            self._configs[config_name] = config_data
            logger.info(f"Loaded configuration: {config_name}")
            return config_data

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {config_file}: {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to load configuration {config_file}: {e}")
            raise

    def load_all(self) -> Dict[str, Any]:
        """
        Load all standard configuration files.

        Returns:
            Dictionary with all configurations
        """
        configs = {}

        # Load hardware configuration
        configs['hardware'] = self.load('hardware', required=True)

        # Load behavior configuration
        configs['behavior'] = self.load('behavior', required=True)

        # Load Azure configuration (optional, may not exist in development)
        azure_config = self.load('azure_config', required=False)
        if azure_config:
            configs['azure'] = azure_config
        else:
            logger.warning("Azure configuration not loaded. Using template or mock mode.")
            configs['azure'] = self._load_azure_template()

        return configs

    def _load_azure_template(self) -> Dict[str, Any]:
        """
        Load Azure configuration template as fallback.

        Returns:
            Azure config template with placeholder values
        """
        template_file = self.config_dir / "azure_config.yaml.template"

        if template_file.exists():
            with open(template_file, 'r') as f:
                template = yaml.safe_load(f)
            logger.info("Loaded Azure configuration template (mock mode)")
            return template
        else:
            logger.warning("Azure template not found, using minimal default config")
            return {
                'azure_iot': {
                    'connection_string': '',
                    'protocol': 'MQTT',
                },
                'development': {
                    'mock_connection': True
                }
            }

    def get(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value using dot notation.

        Args:
            config_name: Name of configuration file
            key_path: Dot-separated path to configuration key (e.g., 'hexapod.dimensions.coxa_length')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> loader = ConfigLoader()
            >>> coxa_length = loader.get('hardware', 'hexapod.dimensions.coxa_length')
        """
        config = self.load(config_name)
        if config is None:
            return default

        # Navigate through nested dictionary
        keys = key_path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.debug(f"Key path not found: {key_path}, returning default")
                return default

        return value

    def reload(self, config_name: Optional[str] = None):
        """
        Reload configuration file(s).

        Args:
            config_name: Specific config to reload, or None to reload all
        """
        if config_name:
            # Remove from cache and reload
            if config_name in self._configs:
                del self._configs[config_name]
            self.load(config_name)
            logger.info(f"Reloaded configuration: {config_name}")
        else:
            # Reload all
            self._configs.clear()
            self.load_all()
            logger.info("Reloaded all configurations")

    def get_hardware_config(self) -> Dict[str, Any]:
        """Get hardware configuration."""
        return self.load('hardware')

    def get_behavior_config(self) -> Dict[str, Any]:
        """Get behavior configuration."""
        return self.load('behavior')

    def get_azure_config(self) -> Dict[str, Any]:
        """Get Azure IoT configuration."""
        return self.load('azure_config', required=False) or self._load_azure_template()

    def validate_hardware_config(self) -> bool:
        """
        Validate hardware configuration has all required fields.

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'hexapod.leg_count',
            'hexapod.dimensions.coxa_length',
            'hexapod.dimensions.femur_length',
            'hexapod.dimensions.tibia_length',
            'servos.driver.type',
            'imu.type',
        ]

        hardware = self.get_hardware_config()

        for field in required_fields:
            if self.get('hardware', field) is None:
                logger.error(f"Missing required hardware configuration field: {field}")
                return False

        logger.info("Hardware configuration validated successfully")
        return True

    def validate_behavior_config(self) -> bool:
        """
        Validate behavior configuration has all required fields.

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'gaits.tripod',
            'navigation.path_planning.algorithm',
            'autonomy.default_mode',
        ]

        behavior = self.get_behavior_config()

        for field in required_fields:
            if self.get('behavior', field) is None:
                logger.error(f"Missing required behavior configuration field: {field}")
                return False

        logger.info("Behavior configuration validated successfully")
        return True


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Get singleton ConfigLoader instance.

    Args:
        config_dir: Configuration directory (only used on first call)

    Returns:
        ConfigLoader instance
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)

    return _config_loader
