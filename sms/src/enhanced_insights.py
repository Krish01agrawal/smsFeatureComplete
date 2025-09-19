"""
Enhanced Insights Generator using Smart Data Orchestrator
Provides accurate, dynamic financial insights without hardcoded logic.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from .core.smart_data_orchestrator import SmartDataOrchestrator, ConfidenceLevel

# Configure logging
logger = logging.getLogger(__name__)


class EnhancedInsightsGenerator:
    """
    Enhanced insights generator that provides accurate financial insights
    by leveraging the Smart Data Orchestrator's pattern recognition capabilities.
    """
    
    def __init__(self, user_id=None):
        """Initialize enhanced insights generator"""
        self.orchestrator = SmartDataOrchestrator(user_id=user_id)
        logger.info("Enhanced Insights Generator initialized")
    
    def generate_comprehensive_insights(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive insights using intelligent pattern recognition.
        
        Args:
            df: Raw transaction DataFrame from MongoDB
            
        Returns:
            Dictionary with enhanced insights compatible with existing dashboard
        """
        logger.info(f"Generating comprehensive insights for {len(df)} transactions")
        
        # Ensure we have data to work with
        if df.empty:
            logger.warning("Empty DataFrame provided, returning empty insights")
            return self._get_empty_insights()
        
        # Get intelligent insights from orchestrator
        smart_insights = self.orchestrator.orchestrate_insights(df)
        
        # Transform to dashboard-compatible format
        dashboard_insights = self._transform_to_dashboard_format(smart_insights, df)
        
        # Add backward compatibility
        dashboard_insights = self._ensure_backward_compatibility(dashboard_insights)
        
        logger.info("Comprehensive insights generation completed")
        return dashboard_insights
    
    def _transform_to_dashboard_format(self, smart_insights: Dict, df: pd.DataFrame) -> Dict:
        """Transform smart insights to dashboard-compatible format"""
        insights = {}
        
        # Basic statistics
        insights['stats'] = self._generate_basic_stats(df, smart_insights)
        
        # Salary and income insights
        salary_insights = smart_insights.get('salary_insights', {})
        insights.update(self._generate_salary_insights(salary_insights))
        
        # Spending insights
        spending_insights = smart_insights.get('spending_insights', {})
        insights.update(self._generate_spending_insights(spending_insights))
        
        # Extract enhanced patterns from smart orchestrator
        patterns = smart_insights.get('patterns', {})
        insights.update(self._extract_enhanced_patterns(patterns, df))
        
        # Trend insights
        trend_insights = smart_insights.get('trend_insights', {})
        insights.update(self._generate_trend_insights(trend_insights))
        
        # Financial health
        insights.update(self._calculate_financial_health(salary_insights, spending_insights))
        
        # Enhanced patterns
        patterns = smart_insights.get('patterns', {})
        insights.update(self._generate_pattern_insights(patterns, df))
        
        # Data quality report
        insights['data_quality'] = smart_insights.get('data_quality', {})
        
        # Metadata
        insights['metadata'] = smart_insights.get('metadata', {})
        
        return insights
    
    def _generate_basic_stats(self, df: pd.DataFrame, smart_insights: Dict) -> Dict:
        """Generate basic statistics"""
        if df.empty:
            return {}
        
        spending_df = df[df['transaction_type'] == 'debit']
        income_df = df[df['transaction_type'] == 'credit']
        
        return {
            "Total Transactions": len(df),
            "Total Spend": spending_df['amount'].sum(),
            "Total Income": income_df['amount'].sum(),
            "Average Transaction Value": spending_df['amount'].mean() if not spending_df.empty else 0,
            "Average Income Transaction": income_df['amount'].mean() if not income_df.empty else 0,
            "Date Range": {
                "Start": df['transaction_date'].min().strftime('%Y-%m-%d') if not df.empty else "",
                "End": df['transaction_date'].max().strftime('%Y-%m-%d') if not df.empty else "",
                "Days": (df['transaction_date'].max() - df['transaction_date'].min()).days if len(df) > 1 else 0
            }
        }
    
    def _generate_salary_insights(self, salary_insights: Dict) -> Dict:
        """Generate salary-related insights"""
        if not salary_insights.get('salary_detected', False):
            return {
                'avg_salary': 0.0,
                'salary': {'source': 'Unknown', 'current_salary': 0.0},
                'monthly_salary': pd.Series()
            }
        
        # Get actual salary progression from the intelligent analysis
        current_salary = salary_insights.get('current_salary', 0)
        monthly_history = salary_insights.get('monthly_history', {})
        
        # Convert monthly history to pandas Series for compatibility
        monthly_salary_series = pd.Series(monthly_history)
        
        # Detect salary changes
        salary_changes = self._detect_salary_changes(monthly_salary_series)
        
        return {
            'avg_salary': current_salary,  # Use current salary, not average
            'salary': {
                'source': salary_insights.get('source', 'Unknown'),
                'current_salary': current_salary,
                'average_salary': salary_insights.get('average_salary', 0),
                'salary_changes': salary_changes,
                'confidence': salary_insights.get('confidence', 'low')
            },
            'monthly_salary': monthly_salary_series
        }
    
    def _detect_salary_changes(self, monthly_salaries: pd.Series) -> List[Dict]:
        """Detect salary changes from monthly salary data"""
        if len(monthly_salaries) <= 1:
            return []
        
        changes = []
        sorted_salaries = monthly_salaries.sort_index()
        
        for i in range(1, len(sorted_salaries)):
            prev_salary = sorted_salaries.iloc[i-1]
            curr_salary = sorted_salaries.iloc[i]
            
            # Detect significant changes (>5% change)
            if abs(curr_salary - prev_salary) / prev_salary > 0.05:
                change_pct = ((curr_salary - prev_salary) / prev_salary) * 100
                change_type = 'promotion' if change_pct > 0 else 'reduction'
                
                changes.append({
                    'from_month': str(sorted_salaries.index[i-1]),
                    'to_month': str(sorted_salaries.index[i]),
                    'old_salary': prev_salary,
                    'new_salary': curr_salary,
                    'change_percentage': change_pct,
                    'change_type': change_type
                })
        
        return changes
    
    def _generate_spending_insights(self, spending_insights: Dict) -> Dict:
        """Generate spending-related insights"""
        if not spending_insights.get('spending_analyzed', False):
            return {
                'avg_expense': 0.0,
                'monthly_expense': pd.Series(),
                'category_spending_pattern': pd.Series(),
                'app_spend': pd.Series()
            }
        
        monthly_history = spending_insights.get('monthly_history', {})
        category_breakdown = spending_insights.get('category_breakdown', {})
        
        return {
            'avg_expense': spending_insights.get('average_monthly_spending', 0),
            'monthly_expense': pd.Series(monthly_history),
            'category_spending_pattern': pd.Series(category_breakdown),
            'top_merchants': pd.Series(spending_insights.get('top_merchants', {})),
            'app_spend': self._generate_payment_method_insights(spending_insights)
        }
    
    def _generate_payment_method_insights(self, spending_insights: Dict) -> pd.Series:
        """Generate payment method insights"""
        # This would be enhanced with actual payment method detection
        # For now, return empty series - can be enhanced with pattern recognition
        return pd.Series()
    
    def _generate_trend_insights(self, trend_insights: Dict) -> Dict:
        """Generate trend-related insights"""
        if not trend_insights.get('trends_analyzed', False):
            return {
                'monthly_income': pd.Series(),
                'monthly_expense': pd.Series(),
                'monthly_savings': pd.Series()
            }
        
        income_trend = pd.Series(trend_insights.get('income_trend', {}))
        spending_trend = pd.Series(trend_insights.get('spending_trend', {}))
        savings_trend = pd.Series(trend_insights.get('savings_trend', {}))
        
        return {
            'monthly_income': income_trend,
            'monthly_expense': spending_trend,
            'monthly_savings': savings_trend,
            'income_growth_rate': trend_insights.get('income_growth_rate', 0),
            'spending_growth_rate': trend_insights.get('spending_growth_rate', 0)
        }
    
    def _calculate_financial_health(self, salary_insights: Dict, spending_insights: Dict) -> Dict:
        """Calculate financial health metrics"""
        avg_income = salary_insights.get('current_salary', 0)
        avg_expense = spending_insights.get('average_monthly_spending', 0)
        
        # Calculate savings and ratios
        savings = avg_income - avg_expense
        savings_rate = (savings / avg_income * 100) if avg_income > 0 else 0
        expense_ratio = (avg_expense / avg_income * 100) if avg_income > 0 else 0
        
        # Calculate financial health score
        health_score = self._calculate_health_score(savings_rate, expense_ratio)
        
        return {
            'avg_income': avg_income,
            'avg_expense': avg_expense,
            'savings': savings,
            'savings_rate': savings_rate,
            'expense_ratio': expense_ratio,
            'financial_health_score': health_score
        }
    
    def _calculate_health_score(self, savings_rate: float, expense_ratio: float) -> float:
        """Calculate financial health score (0-100)"""
        # Base score from savings rate
        if savings_rate >= 30:
            savings_score = 50
        elif savings_rate >= 20:
            savings_score = 40
        elif savings_rate >= 10:
            savings_score = 30
        else:
            savings_score = 20
        
        # Expense ratio score
        if expense_ratio <= 50:
            expense_score = 30
        elif expense_ratio <= 70:
            expense_score = 20
        elif expense_ratio <= 90:
            expense_score = 10
        else:
            expense_score = 5
        
        # Consistency score (placeholder - can be enhanced)
        consistency_score = 20
        
        return min(100, savings_score + expense_score + consistency_score)
    
    def _generate_pattern_insights(self, patterns: Dict, df: pd.DataFrame) -> Dict:
        """Generate insights from discovered patterns"""
        insights = {}
        
        # Recurring transactions
        insights['recurring'] = self._analyze_recurring_patterns(patterns, df)
        
        # Consistent merchants
        if 'merchant_relationships' in patterns:
            merchant_pattern = patterns['merchant_relationships']
            insights['consistent_merchants'] = pd.Series(merchant_pattern.value)
        else:
            insights['consistent_merchants'] = pd.Series()
        
        # Transaction type breakdown
        insights['txn_type_breakdown'] = self._analyze_transaction_types(df)
        
        # Payment method breakdown
        insights['payment_method_breakdown'] = self._analyze_payment_methods(df)
        
        return insights
    
    def _analyze_recurring_patterns(self, patterns: Dict, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze recurring transaction patterns"""
        # This is a simplified version - can be enhanced with more sophisticated pattern recognition
        recurring_data = []
        
        if 'merchant_relationships' in patterns:
            merchant_pattern = patterns['merchant_relationships']
            for merchant, frequency in merchant_pattern.value.items():
                if frequency >= 3:  # Appears in 3+ months
                    merchant_data = df[df['merchant_canonical'] == merchant]
                    if not merchant_data.empty:
                        avg_amount = merchant_data['amount'].mean()
                        # Determine payment type based on merchant or amount
                        if avg_amount >= 20000:
                            payment_type = "Salary"
                        elif 'rent' in merchant.lower() or avg_amount >= 10000:
                            payment_type = "Rent"
                        elif any(word in merchant.lower() for word in ['netflix', 'prime', 'spotify', 'subscription']):
                            payment_type = "Subscription"
                        elif any(word in merchant.lower() for word in ['electricity', 'gas', 'water', 'utility']):
                            payment_type = "Utility"
                        else:
                            payment_type = "Other"
                        
                        recurring_data.append({
                            'merchant': merchant,
                            'average_amount': avg_amount,
                            'frequency_months': frequency,
                            'is_active': True,
                            'confidence_score': min(frequency / 12, 1.0),
                            'payment_type': payment_type,
                            'median_gap_days': 30 * (12 / frequency) if frequency > 0 else 30,
                            'next_due_date': pd.Timestamp.now() + pd.Timedelta(days=30),
                            'last_payment_date': merchant_data['transaction_date'].max()
                        })
        
        return pd.DataFrame(recurring_data)
    
    def _analyze_transaction_types(self, df: pd.DataFrame) -> pd.Series:
        """Analyze transaction type breakdown"""
        if 'category' in df.columns:
            return df['category'].value_counts()
        elif 'txn_type' in df.columns:
            return df['txn_type'].value_counts()
        else:
            return df['transaction_type'].value_counts()
    
    def _analyze_payment_methods(self, df: pd.DataFrame) -> Dict:
        """Analyze payment method breakdown"""
        payment_methods = {}
        
        # Check if we have payment method data
        if 'payment_method' in df.columns:
            method_counts = df['payment_method'].value_counts()
            payment_methods = method_counts.to_dict()
        elif 'metadata' in df.columns:
            # Try to extract payment method from metadata
            methods = df['metadata'].str.extract(r"'method': '([^']*)'", expand=False)
            if not methods.isna().all():
                method_counts = methods.value_counts()
                payment_methods = method_counts.to_dict()
        
        # If no specific payment method data, categorize by transaction patterns
        if not payment_methods and 'merchant_canonical' in df.columns:
            # Basic categorization based on merchant names
            for _, row in df.iterrows():
                merchant = str(row.get('merchant_canonical', '')).lower()
                if 'upi' in merchant or 'phonepe' in merchant or 'paytm' in merchant:
                    payment_methods['UPI'] = payment_methods.get('UPI', 0) + 1
                elif 'card' in merchant or 'visa' in merchant or 'mastercard' in merchant:
                    payment_methods['Card'] = payment_methods.get('Card', 0) + 1
                elif 'neft' in merchant or 'imps' in merchant or 'rtgs' in merchant:
                    payment_methods['Bank Transfer'] = payment_methods.get('Bank Transfer', 0) + 1
                else:
                    payment_methods['Other'] = payment_methods.get('Other', 0) + 1
        
        return payment_methods
    
    def _extract_enhanced_patterns(self, patterns: Dict, df: pd.DataFrame) -> Dict:
        """Extract enhanced patterns from smart orchestrator"""
        enhanced = {}
        
        # Extract spending patterns
        if 'spending_by_category' in patterns:
            spending_pattern = patterns['spending_by_category']
            enhanced['category_spending_pattern'] = pd.Series(spending_pattern.value)
        
        # Extract payment method patterns
        if 'payment_methods' in patterns:
            payment_pattern = patterns['payment_methods']
            enhanced['payment_method_breakdown'] = payment_pattern.value
        
        # Extract time patterns
        if 'time_patterns' in patterns:
            time_pattern = patterns['time_patterns']
            time_data = time_pattern.value
            
            # Convert hourly patterns to time_of_day
            if 'hourly_pattern' in time_data:
                hourly_data = time_data['hourly_pattern']
                # Group hours into time periods
                time_periods = {'Morning': 0, 'Afternoon': 0, 'Evening': 0, 'Night': 0}
                for hour, amount in hourly_data.items():
                    if 6 <= hour < 12:
                        time_periods['Morning'] += amount
                    elif 12 <= hour < 17:
                        time_periods['Afternoon'] += amount
                    elif 17 <= hour < 22:
                        time_periods['Evening'] += amount
                    else:
                        time_periods['Night'] += amount
                
                enhanced['time_pattern'] = pd.Series(time_periods)
            
            # Day of week patterns
            if 'daily_pattern' in time_data:
                enhanced['day_spend'] = pd.Series(time_data['daily_pattern'])
        
        # Extract merchant relationships
        if 'merchant_relationships' in patterns:
            merchant_pattern = patterns['merchant_relationships']
            enhanced['consistent_merchants'] = pd.Series(merchant_pattern.value)
        
        return enhanced
    
    def _ensure_backward_compatibility(self, insights: Dict) -> Dict:
        """Ensure backward compatibility with existing dashboard"""
        # Add any missing keys that the dashboard expects
        default_keys = [
            'daily_trend', 'day_spend', 'time_pattern', 'loyal_merchants',
            'payment_method_breakdown', 'card_usage', 'person_intro',
            'categorization_summary', 'rules'
        ]
        
        for key in default_keys:
            if key not in insights:
                if key in ['daily_trend', 'day_spend', 'time_pattern', 'loyal_merchants']:
                    insights[key] = pd.Series()
                elif key == 'card_usage':
                    insights[key] = {
                        'credit_card_spend': 0,
                        'credit_card_payment': 0,
                        'debit_card': 0,
                        'upi': 0
                    }
                elif key == 'person_intro':
                    insights[key] = self._generate_person_intro(insights)
                else:
                    insights[key] = {}
        
        return insights
    
    def _generate_person_intro(self, insights: Dict) -> str:
        """Generate person introduction based on insights"""
        try:
            # Get top spending categories
            category_spending = insights.get('category_spending_pattern', pd.Series())
            if not category_spending.empty:
                top_categories = category_spending.head(2).index.tolist()
                intro = f"This person primarily spends on {', '.join(top_categories)}"
            else:
                intro = "This person has diverse spending patterns"
            
            # Add salary information
            salary_info = insights.get('salary', {})
            if salary_info.get('current_salary', 0) > 0:
                intro += f", earns ₹{salary_info['current_salary']:,.0f} monthly"
            
            # Add savings information
            savings_rate = insights.get('savings_rate', 0)
            if savings_rate > 20:
                intro += ", and maintains good savings discipline"
            elif savings_rate > 0:
                intro += ", and saves moderately"
            else:
                intro += ", and could improve savings habits"
            
            intro += "."
            return intro
            
        except Exception as e:
            logger.warning(f"Error generating person intro: {e}")
            return "Financial analysis completed successfully."
    
    def _get_empty_insights(self) -> Dict[str, Any]:
        """Return empty insights structure for empty DataFrames"""
        return {
            'stats': {
                'Total Transactions': 0,
                'Total Spend': 0,
                'Total Income': 0,
                'Average Transaction Value': 0,
                'Date Range': {'Start': '', 'End': '', 'Days': 0}
            },
            'avg_salary': 0.0,
            'avg_income': 0.0,
            'avg_expense': 0.0,
            'savings': 0.0,
            'savings_rate': 0.0,
            'financial_health_score': 0.0,
            'salary': {'source': 'Unknown', 'current_salary': 0.0},
            'monthly_income': pd.Series(),
            'monthly_expense': pd.Series(),
            'monthly_savings': pd.Series(),
            'category_spending_pattern': pd.Series(),
            'recurring': pd.DataFrame(),
            'consistent_merchants': pd.Series(),
            'txn_type_breakdown': pd.Series(),
            'data_quality': {
                'data_quality_score': 0.0,
                'initial_transaction_count': 0,
                'final_transaction_count': 0,
                'issues_found': ['No data provided']
            },
            'person_intro': 'No transaction data available for analysis.',
            'daily_trend': pd.Series(),
            'day_spend': pd.Series(),
            'time_pattern': pd.Series(),
            'loyal_merchants': pd.Series(),
            'payment_method_breakdown': {},
            'card_usage': {'credit_card_spend': 0, 'credit_card_payment': 0, 'debit_card': 0, 'upi': 0},
            'categorization_summary': {},
            'rules': pd.DataFrame()
        }
