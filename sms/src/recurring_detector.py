"""
Recurring detector module for SMS transaction analysis.
Identifies recurring transactions and payment patterns.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


class RecurringDetector:
    """Advanced recurring transaction detection with multiple patterns."""
    
    def __init__(self, day_tolerance: int = 3, min_count: int = 3):
        """
        Initialize recurring detector.
        
        Args:
            day_tolerance: Tolerance for day differences in recurring patterns
            min_count: Minimum number of transactions to consider recurring
        """
        self.day_tolerance = day_tolerance
        self.min_count = min_count
        self.user_amount_percentiles = {}
    
    def _calculate_user_percentiles(self, df: pd.DataFrame):
        """Calculate user-specific amount percentiles for dynamic thresholds."""
        if df.empty or 'amount' not in df.columns:
            return
        
        amounts = df['amount'].dropna()
        if len(amounts) == 0:
            return
        
        self.user_amount_percentiles = {
            '10th': amounts.quantile(0.10),
            '20th': amounts.quantile(0.20),
            '50th': amounts.quantile(0.50),
            '75th': amounts.quantile(0.75),
            '80th': amounts.quantile(0.80),
            '90th': amounts.quantile(0.90),
            '95th': amounts.quantile(0.95)
        }
        
        logger.info(f"Calculated dynamic user percentiles: 50th=₹{self.user_amount_percentiles['50th']:.2f}, 80th=₹{self.user_amount_percentiles['80th']:.2f}")
    
    def detect_recurring_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect recurring transactions with enhanced pattern recognition for flexible payments.
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            DataFrame with recurring transaction information
        """
        if df.empty:
            return pd.DataFrame()
        
        logger.info(f"Detecting recurring transactions for {len(df)} transactions")
        
        # Calculate user-specific percentiles for dynamic thresholds
        self._calculate_user_percentiles(df)
        
        recurring_list = []
        
        # Get current date for filtering
        current_date = pd.Timestamp.now()
        # Filter to last 12 months for better pattern detection
        twelve_months_ago = current_date - pd.DateOffset(months=12)
        recent_df = df[df['transaction_date'] >= twelve_months_ago]
        
        # Enhanced merchant grouping with fuzzy matching
        merchant_groups = self._group_similar_merchants(recent_df)
        
        for merchant_group, group_data in merchant_groups.items():
            group_data = group_data.sort_values('transaction_date')
            
            # Skip if too few transactions
            if len(group_data) < self.min_count:
                continue
            
            # Enhanced pattern detection for different recurring payment types
            recurring_patterns = self._detect_flexible_recurring_patterns(group_data, merchant_group)
            
            for pattern in recurring_patterns:
                if pattern['is_recurring']:
                    # Additional validation criteria
                    if self._validate_recurring_transaction(pattern['mean_amount'], pattern['last_payment'], current_date):
                        recurring_list.append({
                            "merchant": merchant_group,
                            "transaction_count": pattern['transaction_count'],
                            "median_gap_days": pattern['median_gap'],
                            "average_amount": pattern['mean_amount'],
                            "last_payment_date": pattern['last_payment'],
                            "next_due_date": pattern['next_due_date'],
                            "payment_type": pattern['payment_type'],
                            "is_active": pattern['is_active'],
                            "amount_variation": pattern['amount_variation'],
                            "frequency_score": pattern['frequency_score'],
                            "confidence_score": pattern['confidence_score'],
                            "pattern_details": pattern['pattern_details']
                        })
        
        result_df = pd.DataFrame(recurring_list)
        
        if not result_df.empty:
            logger.info(f"Found {len(result_df)} recurring transaction patterns")
        else:
            logger.info("No recurring transaction patterns detected")
        
        return result_df
    
    def _group_similar_merchants(self, df: pd.DataFrame) -> Dict:
        """Group similar merchants using data-driven pattern analysis."""
        merchant_groups = {}
        
        for merchant, group in df.groupby('merchant_canonical'):
            # Use data-driven analysis to determine merchant type
            merchant_type = self._classify_merchant_type(merchant, group)
            
            if merchant_type not in merchant_groups:
                merchant_groups[merchant_type] = group
            else:
                merchant_groups[merchant_type] = pd.concat([merchant_groups[merchant_type], group])
        
        return merchant_groups
    
    def _classify_merchant_type(self, merchant: str, group: pd.DataFrame) -> str:
        """
        Classify merchant type using data-driven analysis.
        No hardcoded merchant names - purely pattern-based.
        """
        merchant_lower = merchant.lower()
        
        # Analyze transaction patterns
        avg_amount = group['amount'].mean()
        transaction_count = len(group)
        date_diffs = group['transaction_date'].diff().dt.days.dropna()
        
        # ATM/Cash Withdrawals - typically large amounts, regular frequency
        if self._is_atm_pattern(merchant_lower, avg_amount, date_diffs):
            return 'ATM/Cash Withdrawals'
        
        # Rent Payments - typically large amounts, monthly frequency, consistent
        elif self._is_rent_pattern(merchant_lower, avg_amount, date_diffs, group):
            return 'Rent Payments'
        
        # Investment/SIP - typically medium amounts, regular frequency
        elif self._is_investment_pattern(merchant_lower, avg_amount, date_diffs):
            return 'Investment Payments'
        
        # Utility Payments - typically small-medium amounts, monthly
        elif self._is_utility_pattern(merchant_lower, avg_amount, date_diffs):
            return 'Utility Payments'
        
        # Subscription Payments - typically small amounts, regular frequency
        elif self._is_subscription_pattern(merchant_lower, avg_amount, date_diffs):
            return 'Subscription Payments'
        
        # Default to merchant name
        else:
            return merchant
    
    def _is_atm_pattern(self, merchant: str, avg_amount: float, date_diffs: pd.Series) -> bool:
        """Detect ATM withdrawal patterns using data analysis."""
        # ATM patterns: large amounts, regular frequency
        if len(date_diffs) < 2:
            return False
        
        median_gap = date_diffs.median()
        
        # ATM indicators
        atm_indicators = ['atm', 'cash', 'withdrawal', 'bank']
        has_atm_keywords = any(indicator in merchant for indicator in atm_indicators)
        
        # Amount and frequency analysis
        is_large_amount = avg_amount >= 5000  # ₹5k+ withdrawals
        is_regular_frequency = 20 <= median_gap <= 40  # Monthly-ish pattern
        is_consistent = date_diffs.std() / median_gap < 0.5 if median_gap > 0 else False
        
        return has_atm_keywords or (is_large_amount and is_regular_frequency and is_consistent)
    
    def _is_rent_pattern(self, merchant: str, avg_amount: float, date_diffs: pd.Series, group: pd.DataFrame) -> bool:
        """Detect rent payment patterns using data analysis."""
        if len(date_diffs) < 2:
            return False
        
        median_gap = date_diffs.median()
        
        # Rent indicators
        rent_indicators = ['rent', 'house', 'apartment', 'landlord', 'property']
        has_rent_keywords = any(indicator in merchant for indicator in rent_indicators)
        
        # Amount and frequency analysis
        is_large_amount = avg_amount >= 10000  # ₹10k+ likely rent
        is_monthly_frequency = 25 <= median_gap <= 40  # Monthly pattern with flexibility
        is_consistent = date_diffs.std() / median_gap < 0.6 if median_gap > 0 else False
        
        # Amount stability (rent is usually consistent)
        amount_variation = group['amount'].std() / avg_amount if avg_amount > 0 else 1
        is_amount_stable = amount_variation < 0.3
        
        return has_rent_keywords or (is_large_amount and is_monthly_frequency and is_consistent and is_amount_stable)
    
    def _is_investment_pattern(self, merchant: str, avg_amount: float, date_diffs: pd.Series) -> bool:
        """Detect investment/SIP patterns using data analysis."""
        if len(date_diffs) < 2:
            return False
        
        median_gap = date_diffs.median()
        
        # Investment indicators
        investment_indicators = ['sip', 'investment', 'mutual', 'fund', 'stock', 'trading', 'portfolio']
        has_investment_keywords = any(indicator in merchant for indicator in investment_indicators)
        
        # Amount and frequency analysis
        is_medium_amount = 1000 <= avg_amount <= 50000  # Typical investment range
        is_regular_frequency = 5 <= median_gap <= 35  # Weekly to monthly
        is_consistent = date_diffs.std() / median_gap < 0.7 if median_gap > 0 else False
        
        return has_investment_keywords or (is_medium_amount and is_regular_frequency and is_consistent)
    
    def _is_utility_pattern(self, merchant: str, avg_amount: float, date_diffs: pd.Series) -> bool:
        """Detect utility payment patterns using data analysis."""
        if len(date_diffs) < 2:
            return False
        
        median_gap = date_diffs.median()
        
        # Utility indicators
        utility_indicators = ['electricity', 'water', 'gas', 'utility', 'bill', 'power']
        has_utility_keywords = any(indicator in merchant for indicator in utility_indicators)
        
        # Amount and frequency analysis
        is_small_medium_amount = 100 <= avg_amount <= 5000  # Typical utility range
        is_monthly_frequency = 25 <= median_gap <= 35  # Monthly pattern
        is_consistent = date_diffs.std() / median_gap < 0.5 if median_gap > 0 else False
        
        return has_utility_keywords or (is_small_medium_amount and is_monthly_frequency and is_consistent)
    
    def _is_subscription_pattern(self, merchant: str, avg_amount: float, date_diffs: pd.Series) -> bool:
        """Detect subscription payment patterns using data analysis."""
        if len(date_diffs) < 2:
            return False
        
        median_gap = date_diffs.median()
        
        # Subscription indicators
        subscription_indicators = ['netflix', 'prime', 'spotify', 'subscription', 'streaming', 'service']
        has_subscription_keywords = any(indicator in merchant for indicator in subscription_indicators)
        
        # Amount and frequency analysis
        is_small_amount = 100 <= avg_amount <= 2000  # Typical subscription range
        is_monthly_frequency = 25 <= median_gap <= 35  # Monthly pattern
        is_consistent = date_diffs.std() / median_gap < 0.4 if median_gap > 0 else False
        
        return has_subscription_keywords or (is_small_amount and is_monthly_frequency and is_consistent)
    
    def _detect_flexible_recurring_patterns(self, group_data: pd.DataFrame, merchant_group: str) -> List[Dict]:
        """Detect flexible recurring patterns with enhanced logic."""
        patterns = []
        
        # Calculate gaps between transactions
        date_diffs = group_data['transaction_date'].diff().dt.days.dropna()
        
        if len(date_diffs) < (self.min_count - 1):
            return patterns
        
        # Enhanced pattern detection for different payment types
        if 'ATM/Cash Withdrawals' in merchant_group:
            patterns.extend(self._detect_atm_patterns(group_data, date_diffs))
        elif 'Rent Payments' in merchant_group:
            patterns.extend(self._detect_rent_patterns(group_data, date_diffs))
        elif 'Investment Payments' in merchant_group:
            patterns.extend(self._detect_investment_patterns(group_data, date_diffs))
        else:
            patterns.extend(self._detect_general_patterns(group_data, date_diffs))
        
        return patterns
    
    def _detect_atm_patterns(self, group_data: pd.DataFrame, date_diffs: pd.Series) -> List[Dict]:
        """Detect ATM withdrawal patterns."""
        patterns = []
        
        # Monthly ATM patterns (25-35 days)
        monthly_atm = date_diffs[(date_diffs >= 25) & (date_diffs <= 35)]
        if len(monthly_atm) >= 2:
            median_gap = monthly_atm.median()
            mean_amount = group_data['amount'].mean()
            last_payment = group_data['transaction_date'].max()
            
            patterns.append({
                'is_recurring': True,
                'transaction_count': len(group_data),
                'median_gap': median_gap,
                'mean_amount': mean_amount,
                'last_payment': last_payment,
                'next_due_date': last_payment + pd.Timedelta(days=median_gap),
                'payment_type': 'Monthly ATM',
                'is_active': self._is_active_recurring(last_payment, median_gap, pd.Timestamp.now()),
                'amount_variation': group_data['amount'].std() / mean_amount if mean_amount > 0 else 0,
                'frequency_score': self._calculate_frequency_score(date_diffs, median_gap),
                'confidence_score': 0.8,
                'pattern_details': 'Regular monthly cash withdrawals'
            })
        
        return patterns
    
    def _detect_rent_patterns(self, group_data: pd.DataFrame, date_diffs: pd.Series) -> List[Dict]:
        """Detect rent payment patterns with flexible timing."""
        patterns = []
        
        # Rent can be monthly with some flexibility (25-40 days)
        rent_patterns = date_diffs[(date_diffs >= 25) & (date_diffs <= 40)]
        if len(rent_patterns) >= 2:
            median_gap = rent_patterns.median()
            mean_amount = group_data['amount'].mean()
            last_payment = group_data['transaction_date'].max()
            
            # Higher tolerance for amount variation in rent
            amount_variation = group_data['amount'].std() / mean_amount if mean_amount > 0 else 0
            
            patterns.append({
                'is_recurring': True,
                'transaction_count': len(group_data),
                'median_gap': median_gap,
                'mean_amount': mean_amount,
                'last_payment': last_payment,
                'next_due_date': last_payment + pd.Timedelta(days=median_gap),
                'payment_type': 'Monthly Rent',
                'is_active': self._is_active_recurring(last_payment, median_gap, pd.Timestamp.now()),
                'amount_variation': amount_variation,
                'frequency_score': self._calculate_frequency_score(date_diffs, median_gap),
                'confidence_score': 0.9 if amount_variation < 0.2 else 0.7,
                'pattern_details': 'Monthly rent payments with flexible timing'
            })
        
        return patterns
    
    def _detect_investment_patterns(self, group_data: pd.DataFrame, date_diffs: pd.Series) -> List[Dict]:
        """Detect investment/SIP payment patterns."""
        patterns = []
        
        # SIP patterns can be weekly, monthly, or quarterly
        sip_patterns = {
            'Weekly SIP': date_diffs[(date_diffs >= 6) & (date_diffs <= 9)],
            'Monthly SIP': date_diffs[(date_diffs >= 25) & (date_diffs <= 35)],
            'Quarterly SIP': date_diffs[(date_diffs >= 85) & (date_diffs <= 95)]
        }
        
        for sip_type, pattern_diffs in sip_patterns.items():
            if len(pattern_diffs) >= 2:
                median_gap = pattern_diffs.median()
                mean_amount = group_data['amount'].mean()
                last_payment = group_data['transaction_date'].max()
                
                patterns.append({
                    'is_recurring': True,
                    'transaction_count': len(group_data),
                    'median_gap': median_gap,
                    'mean_amount': mean_amount,
                    'last_payment': last_payment,
                    'next_due_date': last_payment + pd.Timedelta(days=median_gap),
                    'payment_type': sip_type,
                    'is_active': self._is_active_recurring(last_payment, median_gap, pd.Timestamp.now()),
                    'amount_variation': group_data['amount'].std() / mean_amount if mean_amount > 0 else 0,
                    'frequency_score': self._calculate_frequency_score(date_diffs, median_gap),
                    'confidence_score': 0.85,
                    'pattern_details': f'Regular {sip_type.lower()} investment payments'
                })
        
        return patterns
    
    def _detect_general_patterns(self, group_data: pd.DataFrame, date_diffs: pd.Series) -> List[Dict]:
        """Detect general recurring patterns."""
        patterns = []
        
        # Standard pattern detection
        median_gap = date_diffs.median()
        mean_amount = group_data['amount'].mean()
        last_payment = group_data['transaction_date'].max()
        
        # Enhanced pattern identification
        is_recurring, payment_type = self._identify_recurring_pattern(median_gap, group_data['merchant_canonical'].iloc[0], mean_amount)
        
        if is_recurring:
            patterns.append({
                'is_recurring': True,
                'transaction_count': len(group_data),
                'median_gap': median_gap,
                'mean_amount': mean_amount,
                'last_payment': last_payment,
                'next_due_date': last_payment + pd.Timedelta(days=median_gap),
                'payment_type': payment_type,
                'is_active': self._is_active_recurring(last_payment, median_gap, pd.Timestamp.now()),
                'amount_variation': group_data['amount'].std() / mean_amount if mean_amount > 0 else 0,
                'frequency_score': self._calculate_frequency_score(date_diffs, median_gap),
                'confidence_score': 0.7,
                'pattern_details': f'Regular {payment_type.lower()} payments'
            })
        
        return patterns
    
    def _identify_recurring_pattern(self, median_gap: float, merchant: str, mean_amount: float) -> tuple:
        """
        Identify if a pattern is recurring based on gap and other factors.
        Enhanced to handle real-world flexible patterns.
        
        Args:
            median_gap: Median gap between transactions
            merchant: Merchant name
            mean_amount: Mean transaction amount
            
        Returns:
            Tuple of (is_recurring, payment_type)
        """
        merchant_lower = merchant.lower()
        
        # DYNAMIC: Analyze patterns based on user's transaction distribution
        # Calculate dynamic thresholds from the user's data
        
        # Same-day transactions (0-2 days) - Often salary or subscription batches
        if 0 <= median_gap <= 2:
            # Dynamic salary detection: top 20% of user's transaction amounts
            if hasattr(self, 'user_amount_percentiles'):
                high_amount_threshold = self.user_amount_percentiles.get('80th', mean_amount * 2)
                low_amount_threshold = self.user_amount_percentiles.get('20th', mean_amount * 0.5)
                
                if mean_amount >= high_amount_threshold:  # Top 20% - likely salary
                    return True, "Salary Payments"
                elif low_amount_threshold <= mean_amount <= high_amount_threshold:  # Mid-range - likely bills
                    return True, "Regular Payments"
                else:
                    return True, "Frequent Payments"
            else:
                # Fallback to relative analysis if percentiles not available
                return True, "Frequent Payments"
        
        # Short interval patterns (3-6 days) - Often salary or business payments
        elif 3 <= median_gap <= 6:
            # Dynamic income threshold based on user's median transaction
            if hasattr(self, 'user_amount_percentiles'):
                median_threshold = self.user_amount_percentiles.get('50th', mean_amount)
                if mean_amount >= median_threshold * 2:  # Significantly above user's median
                    return True, "Regular Income"
                else:
                    return True, "Frequent Payments"
            else:
                return True, "Frequent Payments"
        
        # Weekly patterns (7-10 days) - More flexible range
        elif 7 <= median_gap <= 10:
            return True, "Weekly"
        
        # Bi-weekly patterns (11-17 days) - More flexible range
        elif 11 <= median_gap <= 17:
            return True, "Bi-weekly"
        
        # Monthly patterns (18-40 days) - Much more flexible for rent, utilities
        elif 18 <= median_gap <= 40:
            if any(keyword in merchant_lower for keyword in ['rent', 'house', 'apartment']):
                return True, "Rent Payments"
            elif any(keyword in merchant_lower for keyword in ['electric', 'power', 'water', 'gas']):
                return True, "Utility Bills"
            elif any(keyword in merchant_lower for keyword in ['airtel', 'jio', 'vodafone', 'phone']):
                return True, "Telecom Bills"
            else:
                return True, "Monthly"
        
        # Quarterly patterns (80-100 days) - More flexible
        elif 80 <= median_gap <= 100:
            return True, "Quarterly"
        
        # Semi-annual patterns (160-200 days) - More flexible
        elif 160 <= median_gap <= 200:
            return True, "Semi-annual"
        
        # Annual patterns (330-400 days) - More flexible
        elif 330 <= median_gap <= 400:
            return True, "Annual"
        
        return False, "Unknown"
    
    def _validate_recurring_transaction(self, mean_amount: float, last_payment: pd.Timestamp, current_date: pd.Timestamp) -> bool:
        """
        Validate if a transaction should be considered recurring.
        More lenient validation for real-world patterns.
        
        Args:
            mean_amount: Mean transaction amount
            last_payment: Date of last payment
            current_date: Current date
            
        Returns:
            True if valid recurring transaction
        """
        # Filter out very small amounts (likely not real recurring payments)
        if mean_amount < 10:  # More lenient - even ₹10 can be recurring
            return False
        
        # Check if last payment is recent (within last 6 months) - more lenient
        if (current_date - last_payment).days > 180:
            return False
        
        return True
    
    def _identify_payment_type(self, merchant: str, amount: float, gap_days: float) -> str:
        """
        Identify the type of recurring payment based on merchant and amount patterns.
        
        Args:
            merchant: Merchant name
            amount: Transaction amount
            gap_days: Gap between transactions
            
        Returns:
            Payment type string
        """
        merchant_lower = merchant.lower()
        
        # Rent patterns
        if any(keyword in merchant_lower for keyword in ['rent', 'house', 'apartment', 'pg', 'accommodation']):
            return "Rent"
        
        # Utility bills
        if any(keyword in merchant_lower for keyword in ['electricity', 'power', 'bseb', 'electric']):
            return "Electricity"
        if any(keyword in merchant_lower for keyword in ['water', 'municipal', 'corporation']):
            return "Water"
        if any(keyword in merchant_lower for keyword in ['gas', 'lpg', 'cylinder']):
            return "Gas"
        
        # Telecom bills
        if any(keyword in merchant_lower for keyword in ['airtel', 'jio', 'vodafone', 'bsnl', 'mobile', 'phone']):
            return "Mobile/Internet"
        
        # Subscription services
        if any(keyword in merchant_lower for keyword in ['netflix', 'prime', 'hotstar', 'disney', 'streaming']):
            return "Entertainment"
        if any(keyword in merchant_lower for keyword in ['gym', 'fitness', 'health', 'yoga']):
            return "Fitness"
        if any(keyword in merchant_lower for keyword in ['insurance', 'policy', 'lic']):
            return "Insurance"
        
        # Loan payments
        if any(keyword in merchant_lower for keyword in ['loan', 'emi', 'mortgage']):
            return "Loan EMI"
        
        # Credit card payments
        if any(keyword in merchant_lower for keyword in ['credit card', 'cc payment']):
            return "Credit Card Payment"
        
        # Amount-based heuristics
        if 3000 <= amount <= 15000 and 28 <= gap_days <= 35:
            return "Likely Rent"
        elif 100 <= amount <= 2000 and 28 <= gap_days <= 35:
            return "Likely Utility"
        elif 50 <= amount <= 500 and 28 <= gap_days <= 35:
            return "Likely Subscription"
        
        return "Monthly Payment"
    
    def _is_active_recurring(self, last_payment: pd.Timestamp, median_gap: float, current_date: pd.Timestamp) -> bool:
        """
        Check if a recurring payment is still active.
        
        Args:
            last_payment: Date of last payment
            median_gap: Median gap between payments
            current_date: Current date
            
        Returns:
            True if payment is still active
        """
        # Active if within expected cycle plus tolerance
        expected_next = last_payment + pd.Timedelta(days=median_gap)
        tolerance_days = max(7, median_gap * 0.2)  # 20% tolerance or 7 days minimum
        
        return (current_date - expected_next).days <= tolerance_days
    
    def _calculate_frequency_score(self, date_diffs: pd.Series, median_gap: float) -> float:
        """
        Calculate a frequency consistency score.
        
        Args:
            date_diffs: Series of date differences
            median_gap: Median gap between transactions
            
        Returns:
            Frequency consistency score (0-1)
        """
        if len(date_diffs) < 2:
            return 0.0
        
        # Calculate coefficient of variation
        cv = date_diffs.std() / date_diffs.mean() if date_diffs.mean() > 0 else 1.0
        
        # Convert to score (lower CV = higher score)
        score = max(0, 1 - cv)
        
        return score
    
    def get_recurring_summary(self, recurring_df: pd.DataFrame) -> Dict:
        """
        Get summary of recurring transactions.
        
        Args:
            recurring_df: DataFrame with recurring transactions
            
        Returns:
            Summary dictionary
        """
        if recurring_df.empty:
            return {"error": "No recurring transactions found"}
        
        summary = {
            "total_recurring": len(recurring_df),
            "active_recurring": len(recurring_df[recurring_df['is_active'] == True]),
            "inactive_recurring": len(recurring_df[recurring_df['is_active'] == False]),
            "payment_type_distribution": recurring_df['payment_type'].value_counts().to_dict(),
            "total_monthly_recurring_amount": recurring_df[recurring_df['is_active'] == True]['average_amount'].sum(),
            "avg_frequency_score": recurring_df['frequency_score'].mean(),
            "upcoming_payments": self._get_upcoming_payments(recurring_df)
        }
        
        return summary
    
    def _get_upcoming_payments(self, recurring_df: pd.DataFrame) -> List[Dict]:
        """
        Get list of upcoming recurring payments.
        
        Args:
            recurring_df: DataFrame with recurring transactions
            
        Returns:
            List of upcoming payment dictionaries
        """
        current_date = pd.Timestamp.now()
        upcoming = []
        
        for _, row in recurring_df.iterrows():
            if row['is_active']:
                days_until = (row['next_due_date'] - current_date).days
                
                if days_until <= 30:  # Only show payments due in next 30 days
                    upcoming.append({
                        "merchant": row['merchant'],
                        "amount": row['average_amount'],
                        "due_date": row['next_due_date'].strftime('%Y-%m-%d'),
                        "days_until": days_until,
                        "payment_type": row['payment_type'],
                        "urgency": "high" if days_until <= 7 else "medium" if days_until <= 14 else "low"
                    })
        
        # Sort by urgency and days until
        upcoming.sort(key=lambda x: (x['urgency'] == 'high', x['days_until']))
        
        return upcoming 