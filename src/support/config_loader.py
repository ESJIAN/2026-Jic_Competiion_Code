"""
Load configuration from yaml files.

This module provides functions to load configuration from yaml files.
The configuration files are expected to be in the 'config' directory
relative to the project root.

"""

import yaml
from pathlib import Path

from program.src.support.logger import get_logger
PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = get_logger(__name__)


def load_config(config_file_name: str) -> dict:
    """
    Load configuration from a yaml file in the config directory.
    
    Args:
        config_file_name (str): The name of the config file (e.g., 'chasis_params.yaml').
        
    Returns:
        dict: Configuration dictionary.
    """
    config_path = PROJECT_ROOT / 'config' / config_file_name
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            return {}
    else:
        logger.warning(f"Configuration file not found: {config_path}")
        return {}

def load_chassis_config() -> dict:
    """
    Load chassis configuration from chasis_params.yaml.
    
    Returns:
        dict: Configuration dictionary.
    
    """
    return load_config('chasis_params.yaml')

def load_imu_config() -> dict:
    """
    Load imu configuration from imu_params.yaml.
    
    Returns:
        dict: Configuration dictionary.
    
    """
    return load_config('imu_params.yaml')



