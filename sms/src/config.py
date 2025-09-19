"""
Dynamic Configuration System for SMS Transaction Analysis
Replaces all hardcoded values with configurable, scalable parameters.
"""

import os
from typing import Dict, List, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class SystemConfig:
    """Centralized configuration system for all system parameters."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize configuration system.
        
        Args:
            config_file: Optional path to custom config file
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config = self._load_config()
        self._validate_config()
        logger.info("System configuration loaded successfully")
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        return str(Path(__file__).parent.parent / "resources" / "system_config.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_file}")
                return self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration with all necessary parameters."""
        default_config = {
            "transaction_classification": {
                "salary_confidence_threshold": 15.0,
                "large_transaction_amount": 20000,
                "similarity_threshold": 0.6,
                "recurring_merchant_ratio": 0.5,
                "pattern_matching": {
                    "exact_match_weight": 1.0,
                    "partial_match_weight": 0.7,
                    "fuzzy_match_weight": 0.5
                }
            },
            "time_configurations": {
                "weekend_days": [5, 6],  # Saturday, Sunday
                "time_bins": [0, 6, 12, 18, 24],
                "day_categories": {
                    "weekday": [0, 1, 2, 3, 4],
                    "weekend": [5, 6]
                },
                "monthly_analysis_periods": [3, 6, 12, 24]
            },
            "performance_limits": {
                "max_transactions_per_user": 5000,
                "batch_size": 1000,
                "cache_timeout": 300,
                "max_concurrent_users": 100,
                "memory_limit_mb": 2048
            },
            "anomaly_detection": {
                "pattern_break_threshold": 1.5,
                "spending_spike_threshold": 2.0,
                "panic_spending_threshold": 5,
                "relationship_change_threshold": 0.3
            },
            "merchant_categorization": {
                "fuzzy_threshold": 85,
                "similarity_threshold": 0.7,
                "category_confidence_threshold": 0.6,
                "auto_learning_enabled": True
            },
            "database": {
                "connection_pool_size": 10,
                "max_connection_lifetime": 3600,
                "index_creation_enabled": True,
                "batch_write_size": 1000
            },
            "caching": {
                "enabled": True,
                "redis_host": "localhost",
                "redis_port": 6379,
                "redis_db": 0,
                "default_ttl": 3600
            },
            "ml_models": {
                "classification_model_path": "models/transaction_classifier.pkl",
                "merchant_categorizer_path": "models/merchant_categorizer.pkl",
                "anomaly_detector_path": "models/anomaly_detector.pkl",
                "auto_retrain_enabled": True,
                "retrain_threshold": 1000
            },
            "scalability": {
                "user_batch_size": 100,
                "transaction_batch_size": 1000,
                "parallel_processing": True,
                "max_workers": 4,
                "load_balancing_enabled": True
            }
        }
        
        # Save default config
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Default configuration created at {self.config_file}")
        return default_config
    
    def _validate_config(self):
        """Validate configuration parameters."""
        required_sections = [
            "transaction_classification", "time_configurations", 
            "performance_limits", "anomaly_detection", 
            "merchant_categorization", "database", "caching", 
            "ml_models", "scalability"
        ]
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        logger.info("Configuration validation passed")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., 'transaction_classification.salary_confidence_threshold')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            logger.warning(f"Configuration key not found: {key_path}, using default: {default}")
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Configuration key path
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
        logger.info(f"Configuration updated: {key_path} = {value}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def reload_config(self):
        """Reload configuration from file."""
        self.config = self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary."""
        return self.config.copy()

# Global configuration instance
system_config = SystemConfig()

# Convenience functions for backward compatibility
def get_config(key_path: str, default: Any = None) -> Any:
    """Get configuration value."""
    return system_config.get(key_path, default)

def set_config(key_path: str, value: Any):
    """Set configuration value."""
    system_config.set(key_path, value)

def save_config():
    """Save configuration."""
    system_config.save_config()
