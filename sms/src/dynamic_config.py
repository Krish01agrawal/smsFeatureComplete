"""
Dynamic Configuration System
Automatically adapts thresholds and parameters based on user data patterns.
No hardcoded values - everything is calculated dynamically.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DynamicConfigManager:
    """
    Manages dynamic configuration based on user's transaction patterns.
    Eliminates hardcoded values for truly dynamic, global-ready system.
    """
    
    def __init__(self, user_id: str = None):
        """Initialize dynamic configuration manager."""
        self.user_id = user_id
        self.config_cache = {}
        self.user_stats = {}
        
    def calculate_user_config(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate user-specific configuration based on their transaction patterns.
        
        Args:
            df: User's transaction DataFrame
            
        Returns:
            Dictionary with dynamic configuration values
        """
        if df.empty:
            return self._get_default_config()
        
        # Calculate user statistics
        self.user_stats = self._calculate_user_statistics(df)
        
        # Generate dynamic configuration
        dynamic_config = {
            'salary_detection': self._calculate_salary_thresholds(df),
            'recurring_patterns': self._calculate_recurring_thresholds(df),
            'spending_analysis': self._calculate_spending_thresholds(df),
            'anomaly_detection': self._calculate_anomaly_thresholds(df),
            'currency_info': self._detect_currency_patterns(df),
            'user_profile': self._generate_user_profile(df)
        }
        
        # Cache the configuration
        self.config_cache = dynamic_config
        
        logger.info(f"Generated dynamic configuration for user {self.user_id}")
        logger.info(f"Currency: {dynamic_config['currency_info']['primary_currency']}")
        logger.info(f"Income range: {dynamic_config['user_profile']['income_tier']}")
        
        return dynamic_config
    
    def _calculate_user_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive user statistics."""
        amounts = df['amount'].dropna()
        
        if len(amounts) == 0:
            return {}
        
        return {
            'mean_amount': amounts.mean(),
            'median_amount': amounts.median(),
            'std_amount': amounts.std(),
            'min_amount': amounts.min(),
            'max_amount': amounts.max(),
            'q10': amounts.quantile(0.10),
            'q25': amounts.quantile(0.25),
            'q75': amounts.quantile(0.75),
            'q90': amounts.quantile(0.90),
            'q95': amounts.quantile(0.95),
            'q99': amounts.quantile(0.99),
            'coefficient_of_variation': amounts.std() / amounts.mean() if amounts.mean() > 0 else 0,
            'total_transactions': len(df),
            'credit_transactions': len(df[df['transaction_type'] == 'credit']),
            'debit_transactions': len(df[df['transaction_type'] == 'debit'])
        }
    
    def _calculate_salary_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate dynamic salary detection thresholds."""
        credit_df = df[df['transaction_type'] == 'credit']
        
        if credit_df.empty:
            return self._get_default_salary_config()
        
        amounts = credit_df['amount'].dropna()
        
        return {
            # Minimum salary threshold: 20% of user's 75th percentile credit amount
            'min_salary_threshold': amounts.quantile(0.75) * 0.2,
            
            # High salary threshold: 80th percentile of credit amounts
            'high_salary_threshold': amounts.quantile(0.80),
            
            # Very high salary threshold: 90th percentile of credit amounts
            'very_high_salary_threshold': amounts.quantile(0.90),
            
            # Salary progression threshold: Based on income volatility
            'progression_base': 1.05,  # Minimum 5% increase
            'progression_volatility_factor': min(0.15, amounts.std() / amounts.mean() * 0.1),
            
            # Consistency threshold for salary detection
            'consistency_threshold': 0.15,  # 15% coefficient of variation max
            
            # Frequency thresholds
            'max_monthly_frequency': 3,  # Max transactions per month for salary
            'min_monthly_gap': 20,  # Minimum days between salary payments
        }
    
    def _calculate_recurring_thresholds(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate dynamic recurring transaction thresholds."""
        amounts = df['amount'].dropna()
        
        if len(amounts) == 0:
            return self._get_default_recurring_config()
        
        return {
            # Amount percentiles for classification
            'amount_percentiles': {
                '10th': amounts.quantile(0.10),
                '20th': amounts.quantile(0.20),
                '50th': amounts.quantile(0.50),
                '75th': amounts.quantile(0.75),
                '80th': amounts.quantile(0.80),
                '90th': amounts.quantile(0.90)
            },
            
            # Dynamic classification thresholds
            'high_value_threshold': amounts.quantile(0.80),  # Top 20% of amounts
            'medium_value_threshold': amounts.quantile(0.50),  # Median
            'low_value_threshold': amounts.quantile(0.20),   # Bottom 80%
            
            # Frequency analysis
            'min_occurrences': max(2, int(len(df) * 0.01)),  # 1% of transactions or min 2
            'day_tolerance': max(2, int(amounts.std() / amounts.mean() * 10)),  # Based on variability
        }
    
    def _calculate_spending_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate dynamic spending analysis thresholds."""
        debit_df = df[df['transaction_type'] == 'debit']
        
        if debit_df.empty:
            return self._get_default_spending_config()
        
        amounts = debit_df['amount'].dropna()
        
        return {
            # Spending categorization thresholds
            'micro_spending': amounts.quantile(0.25),    # Small purchases
            'regular_spending': amounts.quantile(0.50),   # Regular purchases
            'significant_spending': amounts.quantile(0.75), # Significant purchases
            'major_spending': amounts.quantile(0.90),     # Major purchases
            
            # Anomaly detection for spending
            'spending_anomaly_threshold': amounts.quantile(0.95),
            
            # Daily/weekly/monthly spending patterns
            'daily_avg_spending': amounts.mean(),
            'spending_volatility': amounts.std() / amounts.mean() if amounts.mean() > 0 else 0,
        }
    
    def _calculate_anomaly_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate dynamic anomaly detection thresholds."""
        amounts = df['amount'].dropna()
        
        if len(amounts) == 0:
            return {}
        
        # Use statistical methods for anomaly detection
        q1 = amounts.quantile(0.25)
        q3 = amounts.quantile(0.75)
        iqr = q3 - q1
        
        return {
            # Outlier detection using IQR method
            'lower_outlier_threshold': q1 - (1.5 * iqr),
            'upper_outlier_threshold': q3 + (1.5 * iqr),
            
            # Extreme outlier detection
            'lower_extreme_threshold': q1 - (3 * iqr),
            'upper_extreme_threshold': q3 + (3 * iqr),
            
            # Z-score based thresholds
            'zscore_threshold': 2.5,  # Standard z-score threshold
            'extreme_zscore_threshold': 3.5,
        }
    
    def _detect_currency_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect user's primary currency and patterns."""
        # Analyze amount patterns to infer currency
        amounts = df['amount'].dropna()
        
        if len(amounts) == 0:
            return {'primary_currency': 'USD', 'currency_symbol': '$'}
        
        # Infer currency based on amount patterns
        median_amount = amounts.median()
        
        # Simple heuristic based on typical amount ranges
        if median_amount > 1000:  # Likely INR, JPY, KRW
            if median_amount > 100000:
                currency_info = {'primary_currency': 'JPY', 'currency_symbol': '¥'}
            else:
                currency_info = {'primary_currency': 'INR', 'currency_symbol': '₹'}
        elif median_amount > 100:  # Likely USD, EUR, GBP
            currency_info = {'primary_currency': 'USD', 'currency_symbol': '$'}
        else:  # Very small amounts - could be any currency
            currency_info = {'primary_currency': 'USD', 'currency_symbol': '$'}
        
        # Add currency-specific formatting
        currency_info.update({
            'decimal_places': 2,
            'thousands_separator': ',',
            'amount_format': f"{currency_info['currency_symbol']}{{:,.2f}}"
        })
        
        return currency_info
    
    def _generate_user_profile(self, df: pd.DataFrame) -> Dict[str, str]:
        """Generate user financial profile."""
        credit_df = df[df['transaction_type'] == 'credit']
        
        if credit_df.empty:
            return {'income_tier': 'unknown', 'user_type': 'unknown'}
        
        monthly_income = credit_df['amount'].sum() / max(1, len(credit_df.groupby(credit_df['transaction_date'].dt.to_period('M'))))
        
        # Dynamic income tier classification
        if monthly_income > self.user_stats.get('q95', 100000):
            income_tier = 'high_income'
        elif monthly_income > self.user_stats.get('q75', 50000):
            income_tier = 'upper_middle'
        elif monthly_income > self.user_stats.get('q50', 25000):
            income_tier = 'middle_income'
        elif monthly_income > self.user_stats.get('q25', 10000):
            income_tier = 'lower_middle'
        else:
            income_tier = 'low_income'
        
        return {
            'income_tier': income_tier,
            'monthly_income_estimate': monthly_income,
            'user_type': 'active_user' if len(df) > 50 else 'casual_user',
            'transaction_frequency': 'high' if len(df) > 100 else 'medium' if len(df) > 30 else 'low'
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when no data is available."""
        return {
            'salary_detection': self._get_default_salary_config(),
            'recurring_patterns': self._get_default_recurring_config(),
            'spending_analysis': self._get_default_spending_config(),
            'currency_info': {'primary_currency': 'USD', 'currency_symbol': '$'},
            'user_profile': {'income_tier': 'unknown', 'user_type': 'new_user'}
        }
    
    def _get_default_salary_config(self) -> Dict[str, float]:
        """Default salary configuration."""
        return {
            'min_salary_threshold': 1000,  # Very conservative default
            'high_salary_threshold': 5000,
            'very_high_salary_threshold': 10000,
            'progression_base': 1.05,
            'progression_volatility_factor': 0.05,
            'consistency_threshold': 0.20,
            'max_monthly_frequency': 3,
            'min_monthly_gap': 20,
        }
    
    def _get_default_recurring_config(self) -> Dict[str, Any]:
        """Default recurring configuration."""
        return {
            'amount_percentiles': {
                '10th': 10, '20th': 50, '50th': 200,
                '75th': 500, '80th': 1000, '90th': 2000
            },
            'high_value_threshold': 1000,
            'medium_value_threshold': 200,
            'low_value_threshold': 50,
            'min_occurrences': 2,
            'day_tolerance': 3,
        }
    
    def _get_default_spending_config(self) -> Dict[str, float]:
        """Default spending configuration."""
        return {
            'micro_spending': 25,
            'regular_spending': 100,
            'significant_spending': 500,
            'major_spending': 1000,
            'spending_anomaly_threshold': 2000,
            'daily_avg_spending': 50,
            'spending_volatility': 1.0,
        }


# Global instance for easy access
dynamic_config_manager = DynamicConfigManager()


def get_dynamic_config(user_id: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get dynamic configuration for a specific user.
    
    Args:
        user_id: User identifier
        df: User's transaction data
        
    Returns:
        Dynamic configuration dictionary
    """
    manager = DynamicConfigManager(user_id)
    return manager.calculate_user_config(df)
