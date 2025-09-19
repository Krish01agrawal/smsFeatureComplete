"""
Enhanced Configuration for Smart Financial Insights
Enables the new intelligent insights system by default.
"""

import os
from typing import Dict, Any

class EnhancedConfig:
    """Configuration for enhanced insights system"""
    
    # Enable enhanced insights system by default
    USE_ENHANCED_INSIGHTS = True
    
    # Data quality settings
    ENABLE_DATA_QUALITY_CHECKS = True
    DUPLICATE_REMOVAL = True
    CURRENCY_STANDARDIZATION = True
    
    # Pattern recognition settings
    SALARY_DETECTION_THRESHOLD = 15000  # Minimum amount to consider for salary
    PATTERN_CONFIDENCE_THRESHOLD = 0.7
    
    # Performance settings
    ENABLE_PATTERN_CACHING = True
    MAX_TRANSACTIONS_FOR_ANALYSIS = 10000
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration settings"""
        return {
            'use_enhanced_insights': cls.USE_ENHANCED_INSIGHTS,
            'enable_data_quality_checks': cls.ENABLE_DATA_QUALITY_CHECKS,
            'duplicate_removal': cls.DUPLICATE_REMOVAL,
            'currency_standardization': cls.CURRENCY_STANDARDIZATION,
            'salary_detection_threshold': cls.SALARY_DETECTION_THRESHOLD,
            'pattern_confidence_threshold': cls.PATTERN_CONFIDENCE_THRESHOLD,
            'enable_pattern_caching': cls.ENABLE_PATTERN_CACHING,
            'max_transactions_for_analysis': cls.MAX_TRANSACTIONS_FOR_ANALYSIS
        }
    
    @classmethod
    def enable_enhanced_system(cls):
        """Enable the enhanced insights system"""
        cls.USE_ENHANCED_INSIGHTS = True
    
    @classmethod
    def disable_enhanced_system(cls):
        """Disable enhanced system (use legacy)"""
        cls.USE_ENHANCED_INSIGHTS = False
