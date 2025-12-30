"""Configuration loader for algorithm and environment configs."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_algorithm_config(config_path: str) -> Dict[str, Any]:
    """Load algorithm configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    logger.info(f"Loading configuration from: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    if config is None:
        logger.warning(f"Configuration file is empty: {config_path}")
        return {}

    logger.info(f"Loaded configuration with {len(config)} top-level keys")

    return config


def merge_configs(
    base_config: Dict[str, Any],
    override_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Merge two configuration dictionaries.

    The override_config takes precedence over base_config for any overlapping keys.
    Nested dictionaries are merged recursively.

    Args:
        base_config: Base configuration
        override_config: Configuration to override base (optional)

    Returns:
        Merged configuration dictionary
    """
    if override_config is None:
        return base_config.copy()

    merged = base_config.copy()

    for key, value in override_config.items():
        if (
            key in merged and
            isinstance(merged[key], dict) and
            isinstance(value, dict)
        ):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Override value
            merged[key] = value

    return merged


def extract_env_config(full_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract environment configuration from full algorithm config.

    Args:
        full_config: Full configuration dictionary

    Returns:
        Environment configuration with 'fully_obs', 'max_params', etc.
    """
    env_config = {}

    # Extract environment-specific keys
    env_keys = ['fully_obs', 'randomize_env', 'max_params']
    for key in env_keys:
        if key in full_config:
            env_config[key] = full_config[key]

    logger.info(f"Extracted environment config with keys: {list(env_config.keys())}")

    return env_config


def extract_hyperparameters(
    full_config: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Extract hyperparameters from configuration.

    Args:
        full_config: Full configuration dictionary
        defaults: Default hyperparameters (optional)

    Returns:
        Hyperparameters dictionary
    """
    # Start with defaults if provided
    hyperparams = defaults.copy() if defaults else {}

    # Override with config values
    if 'hyperparameters' in full_config:
        hyperparams.update(full_config['hyperparameters'])

    logger.info(f"Extracted {len(hyperparams)} hyperparameters")

    return hyperparams


def validate_env_config(env_config: Dict[str, Any]) -> bool:
    """Validate environment configuration.

    Args:
        env_config: Environment configuration to validate

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ['max_params']

    for key in required_keys:
        if key not in env_config:
            raise ValueError(f"Missing required key in env_config: {key}")

    # Validate max_params
    max_params = env_config['max_params']
    required_max_params = [
        'MAX_HOSTS', 'MAX_PROCESSES', 'MAX_CONNECTIONS',
        'MAX_VULNERABILITIES', 'MAX_INTERFACES', 'MAX_SESSIONS',
        'MAX_USERS'
    ]

    for key in required_max_params:
        if key not in max_params:
            raise ValueError(f"Missing required key in max_params: {key}")
        if not isinstance(max_params[key], int) or max_params[key] < 0:
            raise ValueError(f"Invalid value for {key}: {max_params[key]} (must be non-negative integer)")

    logger.info("Environment configuration validated successfully")
    return True


def get_config_value(
    config: Dict[str, Any],
    key_path: str,
    default: Any = None
) -> Any:
    """Get a configuration value using dot-notation path.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated path to value (e.g., 'hyperparameters.learning_rate')
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example:
        >>> config = {'hyperparameters': {'learning_rate': 0.001}}
        >>> get_config_value(config, 'hyperparameters.learning_rate')
        0.001
        >>> get_config_value(config, 'hyperparameters.gamma', 0.99)
        0.99
    """
    keys = key_path.split('.')
    value = config

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value
