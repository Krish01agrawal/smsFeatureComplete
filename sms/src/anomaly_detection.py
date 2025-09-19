"""
Anomaly detection module for SMS transaction analysis.
Detects spending spikes, pattern breaks, and unusual behavior.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Advanced anomaly detection for transaction patterns."""
    
    def __init__(self):
        """Initialize anomaly detector."""
        pass
    
    def detect_anomalies(self, df: pd.DataFrame) -> Dict:
        """
        Detect various types of anomalies in transaction data.
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            Dictionary with anomaly detection results
        """
        if df.empty:
            return self._empty_anomaly_results()
        
        anomalies = {}
        
        # Pattern break detection
        anomalies.update(self._detect_pattern_breaks(df))
        
        # Spending spikes detection
        anomalies.update(self._detect_spending_spikes(df))
        
        # Panic spending detection
        anomalies.update(self._detect_panic_spending(df))
        
        # Relationship changes detection
        anomalies.update(self._detect_relationship_changes(df))
        
        # Health spending patterns
        anomalies.update(self._detect_health_patterns(df))
        
        return anomalies
    
    def _detect_pattern_breaks(self, df: pd.DataFrame) -> Dict:
        """Detect months where spending patterns break significantly."""
        try:
            monthly = df.groupby(df['transaction_date'].dt.to_period('M'))['amount'].sum()
            
            if len(monthly) < 2:
                return {"pattern_break_months": pd.Series(), "pattern_break_chart": None}
            
            mean, std = monthly.mean(), monthly.std()
            threshold = 1.5 * std
            
            pattern_break = monthly[(monthly > mean + threshold) | (monthly < mean - threshold)]
            
            # Create visualization data
            monthly_df = monthly.reset_index()
            monthly_df['transaction_date'] = monthly_df['transaction_date'].astype(str)
            monthly_df['is_anomaly'] = monthly_df['amount'].apply(lambda x: x in pattern_break.values)
            
            # Create chart (will be handled by visualization module)
            chart_data = {
                'data': monthly_df,
                'mean': mean,
                'threshold': threshold,
                'anomalies': pattern_break
            }
            
            return {
                "pattern_break_months": pattern_break,
                "pattern_break_chart_data": chart_data,
                "pattern_break_reasons": self._detect_pattern_break_reasons(df, pattern_break)
            }
            
        except Exception as e:
            logger.warning(f"Pattern break detection failed: {e}")
            return {"pattern_break_months": pd.Series(), "pattern_break_chart_data": None}
    
    def _detect_pattern_break_reasons(self, df: pd.DataFrame, break_months) -> Dict:
        """Detect why spending patterns broke in specific months."""
        try:
            df['month'] = df['transaction_date'].dt.to_period('M')
            
            # Add category if not present
            if 'category' not in df.columns:
                df['category'] = df['merchant_canonical'].apply(self._basic_categorization)
            
            reasons = {}
            for month in break_months.index:
                month_data = df[df['month'] == month]
                cat_spend = month_data.groupby('category')['amount'].sum()
                reasons[str(month)] = cat_spend.sort_values(ascending=False).head(3).to_dict()
            
            return reasons
            
        except Exception as e:
            logger.warning(f"Pattern break reasons detection failed: {e}")
            return {}
    
    def _detect_spending_spikes(self, df: pd.DataFrame) -> Dict:
        """Detect days with unusual spending spikes with enhanced analysis."""
        try:
            # Only consider debit transactions for spending analysis
            spending_df = df[df['transaction_type'] == 'debit']
            daily = spending_df.groupby('transaction_date')['amount'].sum()
            
            if len(daily) < 2:
                return {"emotional_spikes": pd.DataFrame(), "emotional_spike_chart_data": None}
            
            # Enhanced spike detection with multiple thresholds
            mean_spend = daily.mean()
            std_spend = daily.std()
            
            # Define different spike levels
            moderate_spikes = daily[daily > mean_spend + 1.5 * std_spend]
            high_spikes = daily[daily > mean_spend + 2.5 * std_spend]
            extreme_spikes = daily[daily > mean_spend + 3.5 * std_spend]
            
            # Analyze spike patterns
            spike_analysis = self._analyze_spike_patterns(spending_df, daily, moderate_spikes, high_spikes, extreme_spikes)
            
            # Get detailed spike data for visualization
            all_spike_days = set(moderate_spikes.index) | set(high_spikes.index) | set(extreme_spikes.index)
            
            if len(all_spike_days) > 0:
                spike_data = spending_df[spending_df['transaction_date'].isin(all_spike_days)]
                merchant_spike = spike_data.groupby(['transaction_date','merchant_canonical'])['amount'].sum().reset_index()
                
                # Add spike level information
                merchant_spike['spike_level'] = merchant_spike['transaction_date'].apply(
                    lambda x: self._get_spike_level(x, moderate_spikes, high_spikes, extreme_spikes)
                )
                
                return {
                    "emotional_spikes": merchant_spike,
                    "emotional_spike_chart_data": {
                        'data': merchant_spike,
                        'spike_days': list(all_spike_days),
                        'spike_analysis': spike_analysis,
                        'moderate_spikes': moderate_spikes,
                        'high_spikes': high_spikes,
                        'extreme_spikes': extreme_spikes
                    }
                }
            else:
                return {"emotional_spikes": pd.DataFrame(), "emotional_spike_chart_data": None}
                
        except Exception as e:
            logger.warning(f"Spending spike detection failed: {e}")
            return {"emotional_spikes": pd.DataFrame(), "emotional_spike_chart_data": None}
    
    def _analyze_spike_patterns(self, spending_df: pd.DataFrame, daily: pd.Series, 
                               moderate_spikes: pd.Series, high_spikes: pd.Series, 
                               extreme_spikes: pd.Series) -> Dict:
        """Analyze spending spike patterns for insights."""
        analysis = {
            'total_spikes': len(set(moderate_spikes.index)),
            'high_spikes': len(set(high_spikes.index)),
            'extreme_spikes': len(set(extreme_spikes.index)),
            'spike_categories': {},
            'spike_timing': {},
            'spike_merchants': {},
            'behavioral_insights': []
        }
        
        # Analyze spike categories
        all_spike_days = set(moderate_spikes.index)
        spike_data = spending_df[spending_df['transaction_date'].isin(all_spike_days)]
        
        if not spike_data.empty:
            # Category analysis
            if 'category' in spike_data.columns:
                category_spikes = spike_data.groupby('category')['amount'].sum().sort_values(ascending=False)
                analysis['spike_categories'] = category_spikes.head(5).to_dict()
            
            # Merchant analysis
            merchant_spikes = spike_data.groupby('merchant_canonical')['amount'].sum().sort_values(ascending=False)
            analysis['spike_merchants'] = merchant_spikes.head(10).to_dict()
            
            # Timing analysis
            spike_data['day_of_week'] = spike_data['transaction_date'].dt.day_name()
            spike_data['month'] = spike_data['transaction_date'].dt.month_name()
            
            day_spikes = spike_data.groupby('day_of_week')['amount'].sum().sort_values(ascending=False)
            month_spikes = spike_data.groupby('month')['amount'].sum().sort_values(ascending=False)
            
            analysis['spike_timing'] = {
                'day_of_week': day_spikes.to_dict(),
                'month': month_spikes.to_dict()
            }
            
            # Behavioral insights
            analysis['behavioral_insights'] = self._generate_spike_insights(
                spike_data, daily, moderate_spikes, high_spikes, extreme_spikes
            )
        
        return analysis
    
    def _get_spike_level(self, date, moderate_spikes: pd.Series, high_spikes: pd.Series, 
                        extreme_spikes: pd.Series) -> str:
        """Get the spike level for a given date."""
        if date in extreme_spikes.index:
            return 'Extreme'
        elif date in high_spikes.index:
            return 'High'
        elif date in moderate_spikes.index:
            return 'Moderate'
        else:
            return 'Normal'
    
    def _generate_spike_insights(self, spike_data: pd.DataFrame, daily: pd.Series,
                                moderate_spikes: pd.Series, high_spikes: pd.Series,
                                extreme_spikes: pd.Series) -> List[str]:
        """Generate behavioral insights from spending spikes."""
        insights = []
        
        # Frequency analysis
        total_days = len(daily)
        spike_frequency = len(set(moderate_spikes.index)) / total_days * 100
        
        if spike_frequency > 20:
            insights.append(f"High spending volatility: {spike_frequency:.1f}% of days show above-average spending")
        elif spike_frequency > 10:
            insights.append(f"Moderate spending volatility: {spike_frequency:.1f}% of days show above-average spending")
        else:
            insights.append(f"Low spending volatility: {spike_frequency:.1f}% of days show above-average spending")
        
        # Extreme spike analysis
        if len(extreme_spikes) > 0:
            insights.append(f"⚠️ {len(extreme_spikes)} extreme spending days detected - consider reviewing these patterns")
        
        # Category insights
        if 'category' in spike_data.columns:
            top_spike_category = spike_data.groupby('category')['amount'].sum().idxmax()
            insights.append(f"🎯 Top spike category: {top_spike_category}")
        
        # Timing insights
        if 'day_of_week' in spike_data.columns:
            peak_day = spike_data.groupby('day_of_week')['amount'].sum().idxmax()
            insights.append(f"📅 Peak spending day: {peak_day}")
        
        # Merchant insights
        top_merchant = spike_data.groupby('merchant_canonical')['amount'].sum().idxmax()
        insights.append(f"🏪 Top spike merchant: {top_merchant}")
        
        return insights
    
    def _detect_panic_spending(self, df: pd.DataFrame) -> Dict:
        """Detect panic spending (high frequency of small amounts)."""
        try:
            # Only consider debit transactions for spending analysis
            spending_df = df[df['transaction_type'] == 'debit']
            
            # Define small transactions (less than ₹200)
            small_txn = spending_df[spending_df['amount'] < 200]
            
            if small_txn.empty:
                return {"panic_spends": pd.Series()}
            
            # Count small transactions per day
            daily_small_counts = small_txn.groupby('transaction_date').size()
            
            # Days with more than 5 small transactions
            panic_days = daily_small_counts[daily_small_counts > 5]
            
            return {"panic_spends": panic_days}
            
        except Exception as e:
            logger.warning(f"Panic spending detection failed: {e}")
            return {"panic_spends": pd.Series()}
    
    def _detect_relationship_changes(self, df: pd.DataFrame) -> Dict:
        """Detect changes in merchant relationships over time."""
        try:
            # Look at recent months vs older months
            recent_months = df['transaction_date'].max() - pd.DateOffset(months=2)
            
            recent_merchants = set(df[df['transaction_date'] >= recent_months]['merchant_canonical'])
            old_merchants = set(df[df['transaction_date'] < recent_months]['merchant_canonical'])
            
            # New merchants in recent months
            new_merchants = recent_merchants - old_merchants
            
            # Merchants that disappeared
            disappeared_merchants = old_merchants - recent_merchants
            
            return {
                "relationship_change_merchants": new_merchants,
                "disappeared_merchants": disappeared_merchants,
                "relationship_change_summary": {
                    "new_merchants_count": len(new_merchants),
                    "disappeared_merchants_count": len(disappeared_merchants),
                    "total_merchants": len(recent_merchants | old_merchants)
                }
            }
            
        except Exception as e:
            logger.warning(f"Relationship change detection failed: {e}")
            return {"relationship_change_merchants": set(), "disappeared_merchants": set()}
    
    def _detect_health_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect health-related spending patterns."""
        try:
            # Only consider debit transactions for spending analysis
            spending_df = df[df['transaction_type'] == 'debit']
            
            # Identify health-related transactions
            health_txn = spending_df[spending_df['merchant_canonical'].apply(self._is_health_related)]
            
            if health_txn.empty:
                return {"health_spending": pd.Series()}
            
            health_spending = health_txn.groupby('merchant_canonical')['amount'].sum()
            
            # Detect health spending trends
            health_trend = health_txn.groupby(health_txn['transaction_date'].dt.to_period('M'))['amount'].sum()
            
            return {
                "health_spending": health_spending,
                "health_spending_trend": health_trend,
                "health_spending_summary": {
                    "total_health_spending": health_spending.sum(),
                    "health_merchants_count": len(health_spending),
                    "avg_health_transaction": health_txn['amount'].mean()
                }
            }
            
        except Exception as e:
            logger.warning(f"Health pattern detection failed: {e}")
            return {"health_spending": pd.Series()}
    
    def _basic_categorization(self, merchant_name: str) -> str:
        """Basic merchant categorization for pattern break analysis."""
        merchant_lower = str(merchant_name).lower()
        
        if any(x in merchant_lower for x in ['swiggy', 'zomato', 'restaurant', 'food']):
            return 'Food & Dining'
        elif any(x in merchant_lower for x in ['uber', 'ola', 'travel']):
            return 'Travel'
        elif any(x in merchant_lower for x in ['amazon', 'flipkart', 'shopping']):
            return 'Shopping'
        elif any(x in merchant_lower for x in ['airtel', 'jio', 'mobile']):
            return 'Utilities'
        else:
            return 'Others'
    
    def _is_health_related(self, merchant_name: str) -> bool:
        """Check if merchant is health-related."""
        name = str(merchant_name).lower()
        health_keywords = [
            'pharmacy', 'hospital', 'clinic', 'fitness', 'yoga', 'health', 'medical',
            'doctor', 'physician', 'surgeon', 'dentist', 'orthodontist', 'optometrist',
            'ophthalmologist', 'cardiologist', 'dermatologist', 'neurologist',
            'chemist', 'drugstore', 'medical store', 'healthcare', 'wellness',
            'gym', 'fitness center', 'health club', 'spa', 'massage', 'therapy',
            'insurance', 'policy', 'lic', 'health insurance', 'medical insurance',
            'diagnostic', 'laboratory', 'lab', 'pathology', 'radiology', 'x-ray',
            'ultrasound', 'mri', 'ct scan', 'blood test', 'vaccination', 'vaccine',
            'medicine', 'medication', 'prescription', 'generic', 'ayurvedic',
            'homeopathic', 'naturopathic', 'physiotherapy', 'occupational therapy',
            'speech therapy', 'mental health', 'psychiatrist', 'psychologist',
            'counseling', 'therapy', 'rehabilitation', 'nursing', 'ambulance',
            'emergency', 'urgent care', 'walk-in clinic', 'primary care'
        ]
        return any(keyword in name for keyword in health_keywords)
    
    def _empty_anomaly_results(self) -> Dict:
        """Return empty anomaly detection results."""
        return {
            "pattern_break_months": pd.Series(),
            "pattern_break_chart_data": None,
            "pattern_break_reasons": {},
            "emotional_spikes": pd.DataFrame(),
            "emotional_spike_chart_data": None,
            "panic_spends": pd.Series(),
            "relationship_change_merchants": set(),
            "disappeared_merchants": set(),
            "relationship_change_summary": {},
            "health_spending": pd.Series(),
            "health_spending_trend": pd.Series(),
            "health_spending_summary": {}
        } 