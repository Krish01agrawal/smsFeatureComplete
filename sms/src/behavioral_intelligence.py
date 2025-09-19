#!/usr/bin/env python3
"""
Behavioral Intelligence Module
Analyzes transaction patterns to generate human insights about lifestyle, habits, and personality.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class BehavioralIntelligence:
    """Analyzes transaction patterns to generate behavioral insights."""
    
    def __init__(self):
        self.insights = {}
    
    def analyze_behavioral_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Comprehensive behavioral analysis of transaction patterns.
        
        Args:
            df: Preprocessed transaction DataFrame
            
        Returns:
            Dictionary with behavioral insights
        """
        if df.empty:
            return self._empty_behavioral_insights()
        
        logger.info("Starting behavioral pattern analysis")
        
        # Add time-based features
        df = self._add_behavioral_features(df)
        
        # Core behavioral analyses
        behavioral_insights = {
            'predictive_insights': self._analyze_predictive_patterns(df),
            'personality_profile': self._analyze_personality_patterns(df),
            'lifestyle_patterns': self._analyze_lifestyle_patterns(df),
            'stress_patterns': self._analyze_stress_patterns(df),
            'life_changes': self._analyze_life_changes(df),
            'social_patterns': self._analyze_social_patterns(df),
            'financial_health_signals': self._analyze_financial_health(df)
        }
        
        logger.info("Behavioral analysis completed")
        return behavioral_insights
    
    def _add_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add behavioral analysis features to DataFrame."""
        df = df.copy()
        
        # Time-based features
        df['hour'] = df['transaction_date'].dt.hour
        df['day_of_week'] = df['transaction_date'].dt.day_name()
        df['week_of_year'] = df['transaction_date'].dt.isocalendar().week
        df['month'] = df['transaction_date'].dt.month
        df['is_weekend'] = df['transaction_date'].dt.weekday >= 5
        
        # Time of day categories
        df['time_of_day'] = pd.cut(
            df['hour'], 
            bins=[0, 6, 12, 18, 24], 
            labels=['Night', 'Morning', 'Afternoon', 'Evening']
        )
        
        # Day categories
        df['day_category'] = pd.cut(
            df['transaction_date'].dt.weekday,
            bins=[-1, 4, 6],
            labels=['Weekday', 'Weekend']
        )
        
        return df
    
    def _analyze_predictive_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze patterns to predict upcoming expenses and changes."""
        insights = {}
        
        # 1. Upcoming recurring expenses
        recurring_expenses = self._detect_recurring_expenses(df)
        insights['upcoming_expenses'] = recurring_expenses
        
        # 2. Pattern breaks (unusual spending months)
        pattern_breaks = self._detect_pattern_breaks(df)
        insights['pattern_breaks'] = pattern_breaks
        
        # 3. Seasonal patterns
        seasonal_patterns = self._detect_seasonal_patterns(df)
        insights['seasonal_patterns'] = seasonal_patterns
        
        return insights
    
    def _detect_recurring_expenses(self, df: pd.DataFrame) -> List[Dict]:
        """Detect recurring expenses and predict upcoming payments."""
        recurring_expenses = []
        
        # Group by merchant and analyze frequency
        merchant_frequency = df.groupby('merchant_canonical').agg({
            'transaction_date': ['count', 'min', 'max'],
            'amount': ['mean', 'std']
        }).round(2)
        
        # Flatten column names
        merchant_frequency.columns = ['_'.join(col).strip() for col in merchant_frequency.columns]
        
        # Find merchants with regular payments (appearing in multiple months)
        df['month'] = df['transaction_date'].dt.to_period('M')
        monthly_merchants = df.groupby(['merchant_canonical', 'month']).size().reset_index(name='count')
        merchant_month_count = monthly_merchants.groupby('merchant_canonical')['month'].nunique()
        
        # Identify recurring merchants (appearing in >50% of months)
        total_months = df['month'].nunique()
        recurring_merchants = merchant_month_count[merchant_month_count >= max(2, total_months * 0.5)]
        
        for merchant in recurring_merchants.index:
            merchant_data = df[df['merchant_canonical'] == merchant]
            
            # Calculate average amount and frequency
            avg_amount = merchant_data['amount'].mean()
            avg_frequency = merchant_data.groupby('month').size().mean()
            
            # Predict next payment date
            last_payment = merchant_data['transaction_date'].max()
            days_since_last = (datetime.now() - last_payment).days
            
            # Estimate next payment (assuming monthly frequency)
            if avg_frequency >= 0.8:  # Almost monthly
                next_payment_days = 30 - days_since_last
                if next_payment_days < 0:
                    next_payment_days = 30 + next_payment_days
                
                recurring_expenses.append({
                    'merchant': merchant,
                    'avg_amount': avg_amount,
                    'frequency': 'Monthly',
                    'days_until_next': max(0, next_payment_days),
                    'last_payment': last_payment.strftime('%Y-%m-%d'),
                    'confidence': 'High' if avg_frequency >= 0.9 else 'Medium'
                })
        
        return recurring_expenses
    
    def _detect_pattern_breaks(self, df: pd.DataFrame) -> List[Dict]:
        """Detect months where spending patterns significantly deviated."""
        pattern_breaks = []
        
        # Calculate monthly spending by category
        df['month'] = df['transaction_date'].dt.to_period('M')
        monthly_spending = df[df['transaction_type'] == 'debit'].groupby(['month', 'category'])['amount'].sum().reset_index()
        
        # Calculate average and standard deviation for each category
        category_stats = monthly_spending.groupby('category').agg({
            'amount': ['mean', 'std']
        }).round(2)
        category_stats.columns = ['avg_amount', 'std_amount']
        
        # Detect deviations (>1.5 standard deviations)
        for month in monthly_spending['month'].unique():
            month_data = monthly_spending[monthly_spending['month'] == month]
            
            for _, row in month_data.iterrows():
                category = row['category']
                amount = row['amount']
                
                if category in category_stats.index:
                    avg = category_stats.loc[category, 'avg_amount']
                    std = category_stats.loc[category, 'std_amount']
                    
                    if std > 0 and abs(amount - avg) > 1.5 * std:
                        deviation_percent = ((amount - avg) / avg) * 100
                        
                        pattern_breaks.append({
                            'month': str(month),
                            'category': category,
                            'amount': amount,
                            'avg_amount': avg,
                            'deviation_percent': deviation_percent,
                            'severity': 'High' if abs(deviation_percent) > 50 else 'Medium'
                        })
        
        return pattern_breaks
    
    def _detect_seasonal_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect seasonal spending patterns."""
        seasonal_data = {}
        
        # Monthly patterns
        monthly_spending = df[df['transaction_type'] == 'debit'].groupby(df['transaction_date'].dt.month)['amount'].sum()
        
        # Find peak spending months
        peak_month = monthly_spending.idxmax()
        peak_amount = monthly_spending.max()
        
        seasonal_data['peak_spending_month'] = {
            'month': peak_month,
            'amount': peak_amount,
            'month_name': datetime(2024, peak_month, 1).strftime('%B')
        }
        
        # Weekend vs weekday patterns
        weekend_spending = df[(df['transaction_type'] == 'debit') & (df['is_weekend'])]['amount'].sum()
        weekday_spending = df[(df['transaction_type'] == 'debit') & (~df['is_weekend'])]['amount'].sum()
        
        seasonal_data['weekend_pattern'] = {
            'weekend_spending': weekend_spending,
            'weekday_spending': weekday_spending,
            'weekend_ratio': weekend_spending / (weekend_spending + weekday_spending) if (weekend_spending + weekday_spending) > 0 else 0
        }
        
        return seasonal_data
    
    def _analyze_personality_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze personality traits from spending patterns."""
        personality = {}
        
        # 1. Digital native level
        digital_payments = df[df['payment_method'].isin(['UPI', 'Credit Card', 'Debit Card'])]
        digital_ratio = len(digital_payments) / len(df) if len(df) > 0 else 0
        
        personality['digital_native_level'] = {
            'digital_ratio': digital_ratio,
            'level': 'High' if digital_ratio > 0.8 else 'Medium' if digital_ratio > 0.5 else 'Low'
        }
        
        # 2. Loyalty vs experimental
        merchant_frequency = df['merchant_canonical'].value_counts()
        total_merchants = len(merchant_frequency)
        loyal_merchants = len(merchant_frequency[merchant_frequency >= 3])
        
        personality['loyalty_index'] = {
            'total_merchants': total_merchants,
            'loyal_merchants': loyal_merchants,
            'loyalty_ratio': loyal_merchants / total_merchants if total_merchants > 0 else 0,
            'personality': 'Loyal' if loyal_merchants / total_merchants > 0.3 else 'Experimental'
        }
        
        # 3. Planning vs impulsive
        # Calculate ratio of regular bills vs one-off expenses
        regular_categories = ['Rent', 'Utilities', 'Insurance', 'Credit Card Payment']
        regular_spending = df[(df['transaction_type'] == 'debit') & 
                             (df['category'].isin(regular_categories))]['amount'].sum()
        total_spending = df[df['transaction_type'] == 'debit']['amount'].sum()
        
        planning_ratio = regular_spending / total_spending if total_spending > 0 else 0
        
        personality['planning_style'] = {
            'planning_ratio': planning_ratio,
            'style': 'Planner' if planning_ratio > 0.4 else 'Impulsive' if planning_ratio < 0.2 else 'Balanced'
        }
        
        return personality
    
    def _analyze_lifestyle_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze lifestyle and daily patterns."""
        lifestyle = {}
        
        # 1. Daily rhythm (when they spend)
        hourly_spending = df[df['transaction_type'] == 'debit'].groupby('hour')['amount'].sum()
        peak_hour = hourly_spending.idxmax()
        
        lifestyle['daily_rhythm'] = {
            'peak_spending_hour': peak_hour,
            'financial_wake_up_time': 'Early' if peak_hour < 10 else 'Mid-morning' if peak_hour < 14 else 'Late'
        }
        
        # 2. Weekend personality
        weekend_categories = df[(df['transaction_type'] == 'debit') & (df['is_weekend'])].groupby('category')['amount'].sum()
        weekday_categories = df[(df['transaction_type'] == 'debit') & (~df['is_weekend'])].groupby('category')['amount'].sum()
        
        lifestyle['weekend_personality'] = {
            'top_weekend_categories': weekend_categories.head(3).to_dict(),
            'top_weekday_categories': weekday_categories.head(3).to_dict()
        }
        
        # 3. Anchor merchants (consistently used)
        monthly_merchants = df.groupby(['merchant_canonical', 'month']).size().reset_index(name='count')
        merchant_consistency = monthly_merchants.groupby('merchant_canonical')['month'].nunique()
        total_months = df['month'].nunique()
        
        anchor_merchants = merchant_consistency[merchant_consistency >= total_months * 0.8].index.tolist()
        
        lifestyle['anchor_merchants'] = anchor_merchants
        
        return lifestyle
    
    def _analyze_stress_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze stress-related spending patterns."""
        stress_patterns = {}
        
        # 1. Comfort spending categories
        comfort_categories = ['Food & Dining', 'Entertainment', 'Shopping']
        comfort_spending = df[(df['transaction_type'] == 'debit') & 
                             (df['category'].isin(comfort_categories))].groupby('category')['amount'].sum()
        
        stress_patterns['comfort_spending'] = comfort_spending.to_dict()
        
        # 2. Stress spending detection (clusters of small transactions)
        # Look for days with multiple small transactions
        daily_transaction_count = df[df['transaction_type'] == 'debit'].groupby(df['transaction_date'].dt.date).size()
        stress_days = daily_transaction_count[daily_transaction_count > daily_transaction_count.mean() + daily_transaction_count.std()]
        
        stress_patterns['stress_spending_days'] = {
            'high_frequency_days': len(stress_days),
            'avg_daily_transactions': daily_transaction_count.mean(),
            'stress_threshold': daily_transaction_count.mean() + daily_transaction_count.std()
        }
        
        return stress_patterns
    
    def _analyze_life_changes(self, df: pd.DataFrame) -> Dict:
        """Detect potential life changes from transaction patterns."""
        life_changes = {}
        
        # 1. Income source changes
        salary_merchants = df[df['merchant_canonical'].str.contains('salary', case=False, na=False)]
        if len(salary_merchants) > 1:
            salary_sources = salary_merchants['merchant_canonical'].unique()
            if len(salary_sources) > 1:
                life_changes['income_source_change'] = {
                    'detected': True,
                    'sources': salary_sources.tolist()
                }
        
        # 2. Spending pattern changes
        # Compare first half vs second half of data
        mid_point = df['transaction_date'].median()
        first_half = df[df['transaction_date'] < mid_point]
        second_half = df[df['transaction_date'] >= mid_point]
        
        if not first_half.empty and not second_half.empty:
            first_half_spending = first_half[first_half['transaction_type'] == 'debit']['amount'].sum()
            second_half_spending = second_half[second_half['transaction_type'] == 'debit']['amount'].sum()
            
            spending_change = ((second_half_spending - first_half_spending) / first_half_spending) * 100
            
            life_changes['spending_pattern_change'] = {
                'detected': abs(spending_change) > 20,
                'change_percent': spending_change,
                'trend': 'Increasing' if spending_change > 0 else 'Decreasing'
            }
        
        return life_changes
    
    def _analyze_social_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze social and relationship patterns."""
        social_patterns = {}
        
        # 1. UPI peer-to-peer patterns
        upi_transactions = df[df['payment_method'] == 'UPI']
        if not upi_transactions.empty:
            # Look for frequent transfers to same contacts
            # This would require additional data about UPI contacts
            social_patterns['upi_patterns'] = {
                'total_upi_transactions': len(upi_transactions),
                'avg_upi_amount': upi_transactions['amount'].mean()
            }
        
        # 2. Gifting patterns
        gift_keywords = ['gift', 'archies', 'amazon gift', 'birthday', 'anniversary']
        gift_transactions = df[df['merchant_canonical'].str.contains('|'.join(gift_keywords), case=False, na=False)]
        
        social_patterns['gifting_patterns'] = {
            'gift_transactions': len(gift_transactions),
            'gift_amount': gift_transactions['amount'].sum() if not gift_transactions.empty else 0
        }
        
        return social_patterns
    
    def _analyze_financial_health(self, df: pd.DataFrame) -> Dict:
        """Analyze financial health signals."""
        financial_health = {}
        
        # 1. Credit usage patterns
        credit_transactions = df[df['payment_method'] == 'Credit Card']
        if not credit_transactions.empty:
            # Check if credit usage increases towards month end
            credit_transactions['day_of_month'] = credit_transactions['transaction_date'].dt.day
            end_month_credit = credit_transactions[credit_transactions['day_of_month'] >= 25]['amount'].sum()
            total_credit = credit_transactions['amount'].sum()
            
            financial_health['credit_usage_pattern'] = {
                'end_month_ratio': end_month_credit / total_credit if total_credit > 0 else 0,
                'stress_indicator': end_month_credit / total_credit > 0.5 if total_credit > 0 else False
            }
        
        # 2. Salary day splurge
        # Look for spending spikes right after salary credit
        salary_transactions = df[df['merchant_canonical'].str.contains('salary', case=False, na=False)]
        if not salary_transactions.empty:
            salary_dates = salary_transactions['transaction_date'].dt.date
            splurge_amount = 0
            
            for salary_date in salary_dates:
                # Check spending in next 3 days
                next_3_days = df[
                    (df['transaction_date'].dt.date > salary_date) &
                    (df['transaction_date'].dt.date <= salary_date + timedelta(days=3)) &
                    (df['transaction_type'] == 'debit')
                ]['amount'].sum()
                splurge_amount += next_3_days
            
            financial_health['salary_day_splurge'] = {
                'splurge_amount': splurge_amount,
                'salary_amount': salary_transactions['amount'].sum(),
                'splurge_ratio': splurge_amount / salary_transactions['amount'].sum() if salary_transactions['amount'].sum() > 0 else 0
            }
        
        return financial_health
    
    def _empty_behavioral_insights(self) -> Dict:
        """Return empty behavioral insights structure."""
        return {
            'predictive_insights': {},
            'personality_profile': {},
            'lifestyle_patterns': {},
            'stress_patterns': {},
            'life_changes': {},
            'social_patterns': {},
            'financial_health_signals': {}
        } 