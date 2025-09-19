"""
Main insights module for SMS transaction analysis.
Orchestrates all analysis components and provides comprehensive insights.

Enhanced with Smart Data Orchestrator for intelligent, adaptive insights.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from mlxtend.frequent_patterns import apriori, association_rules

# Import our modules
from .classification import TransactionClassifier
from .merchant_mapping import MerchantMapper
from .savings_calculator import SavingsCalculator
from .anomaly_detection import AnomalyDetector
from .recurring_detector import RecurringDetector
from .behavioral_intelligence import BehavioralIntelligence

# Import enhanced insights system
from .enhanced_insights import EnhancedInsightsGenerator

# Configure logging
logger = logging.getLogger(__name__)


class TransactionInsights:
    """Comprehensive transaction insights analyzer with modular architecture."""
    
    def __init__(self, use_enhanced_system: bool = True, user_id: str = None):
        """Initialize insights analyzer with all components."""
        self.use_enhanced_system = use_enhanced_system
        self.user_id = user_id
        
        if use_enhanced_system:
            # Initialize both enhanced and legacy systems for hybrid approach
            self.enhanced_generator = EnhancedInsightsGenerator(user_id=user_id)
            # Also initialize legacy components for hybrid calculations
            self.classifier = TransactionClassifier()
            self.mapper = MerchantMapper()
            self.savings_calculator = SavingsCalculator()
            self.anomaly_detector = AnomalyDetector()
            self.recurring_detector = RecurringDetector()
            self.behavioral_intelligence = BehavioralIntelligence()
            logger.info(f"TransactionInsights initialized with Hybrid System (Enhanced + Legacy) for user: {user_id}")
        else:
            # Use legacy system for backward compatibility
            self.classifier = TransactionClassifier()
            self.mapper = MerchantMapper()
            self.savings_calculator = SavingsCalculator()
            self.anomaly_detector = AnomalyDetector()
            self.recurring_detector = RecurringDetector()
            self.behavioral_intelligence = BehavioralIntelligence()
            logger.info("TransactionInsights initialized with legacy components")
    
    def calculate_insights(self, df: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive transaction insights using hybrid approach.
        
        Args:
            df: Preprocessed DataFrame with transaction data
            
        Returns:
            Dictionary with all calculated insights combining best of both systems
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for insights calculation")
            return self._empty_insights()
        
        logger.info(f"Calculating insights for {len(df)} transactions")
        
        if self.use_enhanced_system:
            # HYBRID APPROACH: Use enhanced system for advanced features, legacy for reliability
            logger.info("Using Hybrid Insights System (Enhanced + Legacy)")
            return self._calculate_hybrid_insights(df)
        else:
            # Use legacy system
            logger.info("Using legacy system for backward compatibility")
            return self._calculate_legacy_insights(df)
    
    def _calculate_hybrid_insights(self, df: pd.DataFrame) -> Dict:
        """
        HYBRID APPROACH: Combine best of Enhanced and Legacy systems.
        
        Enhanced System Strengths:
        - Advanced salary detection and progression tracking
        - Intelligent behavioral insights and pattern recognition
        - Rich categorization and merchant mapping
        - Sophisticated anomaly detection
        
        Legacy System Strengths:
        - Accurate monthly trends calculation
        - Reliable transaction classification
        - Proper payment method breakdown
        - Simple, consistent financial metrics
        """
        logger.info("🔄 Starting Hybrid Analysis: Enhanced + Legacy")
        
        # STEP 1: Get Enhanced Insights (for advanced features)
        logger.info("📈 Calculating Enhanced Insights...")
        enhanced_insights = self.enhanced_generator.generate_comprehensive_insights(df)
        
        # STEP 2: Get Legacy Insights (for reliable calculations)
        logger.info("📊 Calculating Legacy Insights...")
        legacy_insights = self._calculate_legacy_insights(df)
        
        # STEP 3: HYBRID MERGE - Best of both worlds
        logger.info("🔀 Merging insights using hybrid approach...")
        hybrid_insights = {}
        
        # === USE ENHANCED SYSTEM FOR ===
        # Advanced salary detection and progression
        if 'salary' in enhanced_insights:
            hybrid_insights['salary'] = enhanced_insights['salary']
            hybrid_insights['avg_salary'] = enhanced_insights.get('avg_salary', 0)
        
        # Advanced behavioral insights
        for key in ['behavioral_insights', 'spending_personality', 'lifestyle_patterns', 
                   'relationship_changes', 'health_spending', 'anomalies']:
            if key in enhanced_insights:
                hybrid_insights[key] = enhanced_insights[key]
        
        # Time-based patterns from enhanced system
        for key in ['time_patterns', 'hourly_pattern', 'daily_pattern', 'day_spend', 
                   'time_of_day_spending', 'daily_spending_trend']:
            if key in enhanced_insights:
                hybrid_insights[key] = enhanced_insights[key]
        
        # Intelligent categorization (prefer enhanced, but ensure drill-down data from legacy)
        if 'category_spending' in enhanced_insights:
            hybrid_insights['category_spending'] = enhanced_insights['category_spending']
        
        # Enhanced category pattern (for pie chart)
        if 'category_spending_pattern' in enhanced_insights:
            hybrid_insights['category_spending_pattern'] = enhanced_insights['category_spending_pattern']
        
        # CRITICAL: Ensure we get detailed categorization data from Legacy for drill-down
        legacy_categorization_keys = ['categorization_summary', 'merchant_category_spend', 'category_spend']
        for key in legacy_categorization_keys:
            if key in legacy_insights:
                hybrid_insights[key] = legacy_insights[key]
        
        # Advanced recurring detection (prefer enhanced, fallback to legacy)
        if 'recurring' in enhanced_insights and not enhanced_insights['recurring'].empty:
            hybrid_insights['recurring'] = enhanced_insights['recurring']
        elif 'recurring' in legacy_insights and not legacy_insights['recurring'].empty:
            hybrid_insights['recurring'] = legacy_insights['recurring']
        else:
            # Ensure we have an empty DataFrame rather than None
            hybrid_insights['recurring'] = pd.DataFrame()
        
        # === USE LEGACY SYSTEM FOR ===
        # Reliable monthly trends (this is where legacy excels)
        for key in ['monthly_income', 'monthly_expense', 'monthly_savings', 
                   'monthly_salary', 'monthly_other_income']:
            if key in legacy_insights:
                hybrid_insights[key] = legacy_insights[key]
        
        # Accurate transaction classification
        for key in ['txn_type_breakdown', 'classification_summary']:
            if key in legacy_insights:
                hybrid_insights[key] = legacy_insights[key]
        
        # Reliable payment method breakdown
        if 'app_spend' in legacy_insights:
            hybrid_insights['app_spend'] = legacy_insights['app_spend']
        
        # Simple, consistent financial metrics
        for key in ['avg_income', 'avg_expense', 'savings', 'savings_rate', 
                   'expense_ratio', 'financial_health_score']:
            if key in legacy_insights:
                hybrid_insights[key] = legacy_insights[key]
        
        # === MERGE COMMON ELEMENTS (prefer enhanced when available) ===
        # Use enhanced if available, fallback to legacy
        for key in ['stats', 'top_merchants', 'day_spend', 'loyal_merchants', 
                   'consistent_merchants', 'card_usage', 'person_intro']:
            if key in enhanced_insights:
                hybrid_insights[key] = enhanced_insights[key]
            elif key in legacy_insights:
                hybrid_insights[key] = legacy_insights[key]
        
        # Time patterns - prefer enhanced, fallback to legacy behavioral insights
        time_pattern_keys = ['hourly_pattern', 'daily_pattern', 'time_of_day_spending', 
                           'daily_spending_trend', 'behavioral_insights']
        for key in time_pattern_keys:
            if key not in hybrid_insights:  # Only if not already set from enhanced
                if key in legacy_insights:
                    hybrid_insights[key] = legacy_insights[key]
        
        # Map legacy time_pattern to expected dashboard keys
        if 'time_pattern' in legacy_insights and 'hourly_pattern' not in hybrid_insights:
            # Legacy system provides time_pattern, map it to hourly_pattern
            hybrid_insights['hourly_pattern'] = legacy_insights['time_pattern']
            hybrid_insights['time_of_day_spending'] = legacy_insights['time_pattern']
        
        # Map enhanced time_pattern if available
        if 'time_pattern' in enhanced_insights:
            hybrid_insights['time_pattern'] = enhanced_insights['time_pattern']
            if 'hourly_pattern' not in hybrid_insights:
                hybrid_insights['hourly_pattern'] = enhanced_insights['time_pattern']
        
        # Calculate daily trend if not available from either system
        if 'daily_trend' not in hybrid_insights:
            hybrid_insights['daily_trend'] = self._calculate_daily_trend_hybrid(df)
        
        # === QUALITY ASSURANCE ===
        # Ensure we have all required keys
        hybrid_insights = self._ensure_required_keys(hybrid_insights, legacy_insights)
        
        logger.info("✅ Hybrid insights calculation completed")
        logger.info(f"📊 Enhanced features: {len([k for k in enhanced_insights.keys() if k in hybrid_insights])}")
        logger.info(f"📈 Legacy features: {len([k for k in legacy_insights.keys() if k in hybrid_insights])}")
        
        return hybrid_insights
    
    def _calculate_daily_trend_hybrid(self, df: pd.DataFrame) -> pd.Series:
        """Calculate daily spending trend for hybrid system."""
        try:
            # Get spending transactions only
            spending_df = df[df['transaction_type'] == 'debit'].copy()
            
            if spending_df.empty:
                return pd.Series()
            
            # Group by date and sum amounts
            daily_spending = spending_df.groupby(spending_df['transaction_date'].dt.date)['amount'].sum()
            
            # Convert to pandas Series with proper index
            daily_trend = pd.Series(daily_spending.values, index=daily_spending.index)
            
            logger.info(f"Calculated daily trend: {len(daily_trend)} days")
            return daily_trend
            
        except Exception as e:
            logger.error(f"Error calculating daily trend: {e}")
            return pd.Series()
    
    def _ensure_required_keys(self, hybrid_insights: Dict, fallback_insights: Dict) -> Dict:
        """Ensure all required keys are present in hybrid insights."""
        required_keys = [
            'stats', 'monthly_income', 'monthly_expense', 'avg_salary', 
            'avg_income', 'savings_rate', 'txn_type_breakdown'
        ]
        
        for key in required_keys:
            if key not in hybrid_insights:
                if key in fallback_insights:
                    hybrid_insights[key] = fallback_insights[key]
                else:
                    # Provide safe defaults
                    if key == 'stats':
                        hybrid_insights[key] = {}
                    elif key in ['monthly_income', 'monthly_expense']:
                        hybrid_insights[key] = pd.Series()
                    elif key in ['avg_salary', 'avg_income', 'savings_rate']:
                        hybrid_insights[key] = 0.0
                    elif key == 'txn_type_breakdown':
                        hybrid_insights[key] = pd.Series()
        
        return hybrid_insights
    
    def _calculate_legacy_insights(self, df: pd.DataFrame) -> Dict:
        """Legacy insights calculation method (kept for backward compatibility)"""
        insights = {}
        
        # Step 1: Transaction Classification (CRITICAL for salary detection)
        df = self.classifier.classify_dataframe(df)
        
        # Step 2: Merchant Categorization
        df = self.mapper.categorize_dataframe(df)
        insights['categorization_summary'] = self.mapper.get_categorization_summary(df)
        
        # Step 3: Basic Statistics
        insights['stats'] = self._calculate_basic_stats(df)
        
        # Step 4: Financial Analysis (now with proper classification)
        salary_info = self.savings_calculator.detect_salary_source(df)
        financial_analysis = self.savings_calculator.calculate_expenditure_and_savings(df, salary_info)
        
        # CRITICAL FIX: Don't let financial_analysis override hybrid insights salary values
        salary_keys_to_preserve = ['salary', 'avg_salary']
        preserved_salary_values = {k: insights.get(k) for k in salary_keys_to_preserve if k in insights}
        
        insights.update(financial_analysis)
        
        # Restore preserved salary values (enhanced insights take priority)
        for key, value in preserved_salary_values.items():
            if value is not None:
                insights[key] = value
        
        # Ensure salary information is properly stored with current salary
        # CRITICAL FIX: Don't override enhanced insights salary with legacy salary
        if 'salary' not in insights:  # Only set if not already set by enhanced insights
            insights['salary'] = salary_info
        if 'avg_salary' not in insights and 'current_salary' in salary_info:  # Only set if not already set
            insights['avg_salary'] = salary_info['current_salary']  # Use current salary for display
        
        # Calculate monthly savings for visualization
        if 'monthly_income' in insights and 'monthly_expense' in insights:
            monthly_income = insights['monthly_income']
            monthly_expense = insights['monthly_expense']
            monthly_savings = monthly_income - monthly_expense
            insights['monthly_savings'] = monthly_savings
        
        # Step 5: Spending Patterns
        insights.update(self._calculate_spending_patterns(df))
        
        # Step 6: Recurring Transactions
        insights['recurring'] = self.recurring_detector.detect_recurring_transactions(df)
        
        # Step 7: Anomaly Detection
        insights.update(self.anomaly_detector.detect_anomalies(df))
        
        # Step 8: Association Rules
        insights['rules'] = self._calculate_association_rules(df)
        
        # Step 9: Behavioral Insights
        insights.update(self._calculate_behavioral_insights(df))
        
        # Step 10: Advanced Behavioral Intelligence
        behavioral_insights = self.behavioral_intelligence.analyze_behavioral_patterns(df)
        insights['behavioral_intelligence'] = behavioral_insights
        
        # Step 11: Bank and Payment Analysis
        insights.update(self._calculate_bank_payment_insights(df))
        
        # Step 12: Person Introduction
        insights['person_intro'] = self._generate_person_intro(insights)
        
        logger.info("Legacy insights calculation completed")
        return insights
    
    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict:
        """Calculate basic transaction statistics."""
        # Separate spending (debit) from income (credit) for accurate metrics
        spending_df = df[df['transaction_type'] == 'debit']
        income_df = df[df['transaction_type'] == 'credit']
        
        return {
            "Total Transactions": len(df),
            "Total Spend": spending_df['amount'].sum(),  # Only debit transactions
            "Total Income": income_df['amount'].sum(),   # Only credit transactions
            "Average Transaction Value": spending_df['amount'].mean(),  # Only debit transactions
            "Average Income Transaction": income_df['amount'].mean(),   # Only credit transactions
            "Median Transaction Value": spending_df['amount'].median(),
            "Min Transaction Value": spending_df['amount'].min(),
            "Max Transaction Value": spending_df['amount'].max(),
            "Date Range": {
                "Start": df['transaction_date'].min().strftime('%Y-%m-%d'),
                "End": df['transaction_date'].max().strftime('%Y-%m-%d'),
                "Days": (df['transaction_date'].max() - df['transaction_date'].min()).days
            }
        }
    
    def _calculate_spending_patterns(self, df: pd.DataFrame) -> Dict:
        """Calculate spending patterns by various dimensions."""
        patterns = {}
        
        # Daily trend - only include debit transactions (actual spending)
        spending_df = df[df['transaction_type'] == 'debit']
        patterns['daily_trend'] = spending_df.groupby(spending_df['transaction_date'].dt.date)['amount'].sum()
        
        # Top merchants - only spending merchants (debit transactions)
        patterns['top_merchants'] = spending_df.groupby('merchant_canonical')['amount'].sum().sort_values(ascending=False).head(10)
        
        # Spending by day of week - only debit transactions
        patterns['day_spend'] = spending_df.groupby('day_of_week')['amount'].sum().sort_values(ascending=False)
        
        # Spending by category - only debit transactions
        if 'category' in spending_df.columns:
            patterns['category_spend'] = spending_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        else:
            patterns['category_spend'] = spending_df.groupby('merchant_canonical')['amount'].sum().sort_values(ascending=False)
        
        # Category spending pattern - only debit transactions
        patterns['category_spending_pattern'] = spending_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        
        # Merchant category spend - only debit transactions
        merchant_category_spend = spending_df.groupby(['category', 'merchant_canonical'])['amount'].sum().reset_index()
        patterns['merchant_category_spend'] = merchant_category_spend
        
        # Payment app detection - only debit transactions
        patterns['app_spend'] = self._detect_payment_apps(df)
        
        return patterns
    
    def _detect_payment_apps(self, df: pd.DataFrame) -> pd.Series:
        """Detect payment app usage patterns with proper UPI app categorization."""
        def detect_app(merchant, payment_method=None):
            name = str(merchant).lower()
            payment_method = str(payment_method).lower() if payment_method else ""
            
            # UPI-based app detection (most common in India)
            upi_app_patterns = {
                'Google Pay': ['google', 'gpay', 'googlepay', 'g pay'],
                'PhonePe': ['phonepe', 'phone pe', 'phonpe', 'pe'],
                'Paytm': ['paytm', 'paytm payments'],
                'Amazon Pay': ['amazon', 'amazonpay', 'amazon pay'],
                'BHIM': ['bhim', 'bharat', 'qr', 'bharatqr'],
                'Cred': ['cred'],
                'Freecharge': ['freecharge', 'free charge'],
                'MobiKwik': ['mobikwik', 'mobi kwik']
            }
            
            # Check for specific UPI apps first (these are the primary apps people use)
            for app_name, patterns in upi_app_patterns.items():
                if any(pattern in name for pattern in patterns):
                    return app_name
            
            # Check if it's a UPI transaction but with unknown app
            if 'upi' in name or 'upi' in payment_method:
                return 'Other UPI Apps'  # Generic UPI transactions
            
            # Non-UPI payment methods
            payment_method_patterns = {
                'Net Banking': ['neft', 'imps', 'rtgs', 'netbanking', 'net banking'],
                'Debit Card': ['debit', 'pos', 'card'],
                'Credit Card': ['credit'],
                'ATM/Cash': ['atm', 'cash', 'withdrawal'],
                'Bank Transfer': ['transfer', 'fund transfer']
            }
            
            # Check payment methods
            for method_name, patterns in payment_method_patterns.items():
                if any(pattern in payment_method for pattern in patterns):
                    return method_name
            
            # Check merchant names for payment method clues
            for method_name, patterns in payment_method_patterns.items():
                if any(pattern in name for pattern in patterns):
                    return method_name
            
            # Data-driven categorization for unknown patterns
            return self._categorize_by_pattern(merchant, payment_method)
        
        # Apply payment app detection
        df['payment_app'] = df.apply(
            lambda row: detect_app(
                row['merchant_canonical'], 
                row.get('payment_method', '')
            ), 
            axis=1
        )
        
        # Calculate spending by payment app (only debit transactions)
        spending_df = df[df['transaction_type'] == 'debit']
        app_spend = spending_df.groupby('payment_app')['amount'].sum().sort_values(ascending=False)
        
        # No consolidation needed - each app should be shown separately
        # This gives a clear view of which specific apps are used most
        
        return app_spend
    
    def _categorize_by_pattern(self, merchant: str, payment_method: str) -> str:
        """Categorize payment method using data-driven pattern analysis."""
        merchant_lower = merchant.lower()
        payment_method_lower = payment_method.lower()
        
        # Check for specific payment patterns
        if any(keyword in merchant_lower for keyword in ['atm', 'cash', 'withdrawal']):
            return 'ATM/Cash'
        
        # Bank transfer indicators (NEFT, IMPS, RTGS)
        if any(indicator in payment_method_lower for indicator in ['neft', 'imps', 'rtgs']):
            return 'Net Banking'
        
        # Card payment indicators
        if any(indicator in payment_method_lower for indicator in ['debit', 'credit', 'card']):
            return 'Debit Card' if 'debit' in payment_method_lower else 'Credit Card'
        
        # Check for wallet/digital payment patterns
        wallet_patterns = ['wallet', 'balance', 'prepaid', 'digital']
        if any(pattern in merchant_lower for pattern in wallet_patterns):
            return 'Digital Wallet'
        
        # Bank-to-bank transfers
        if any(indicator in merchant_lower for indicator in ['transfer', 'fund transfer', 'bank']):
            return 'Bank Transfer'
        
        # Default for unrecognized patterns
        return 'Other Payment Methods'
    
    def _consolidate_payment_categories(self, app_spend: pd.Series) -> Dict:
        """Consolidate payment categories using data-driven approach."""
        consolidated_spend = {}
        
        # Group UPI transactions
        upi_total = sum(amount for app, amount in app_spend.items() if 'UPI' in app)
        if upi_total > 0:
            consolidated_spend['UPI Payments'] = upi_total
        
        # Group digital payments
        digital_total = sum(amount for app, amount in app_spend.items() if 'Digital Payment' in app)
        if digital_total > 0:
            consolidated_spend['Digital Payments'] = digital_total
        
        # Group bank transfers
        bank_total = sum(amount for app, amount in app_spend.items() if 'Bank Transfer' in app)
        if bank_total > 0:
            consolidated_spend['Bank Transfers'] = bank_total
        
        # Group card payments
        card_total = sum(amount for app, amount in app_spend.items() if 'Card Payment' in app)
        if card_total > 0:
            consolidated_spend['Card Payments'] = card_total
        
        # Group ATM/cash
        atm_total = sum(amount for app, amount in app_spend.items() if 'ATM/Cash' in app)
        if atm_total > 0:
            consolidated_spend['ATM/Cash'] = atm_total
        
        # Add specific apps that are significant
        for app, amount in app_spend.items():
            if ('UPI' not in app and 'Digital Payment' not in app and 
                'Bank Transfer' not in app and 'Card Payment' not in app and 
                'ATM/Cash' not in app and app != 'Unknown'):
                consolidated_spend[app] = amount
        
        # Add unknown if significant
        if 'Unknown' in app_spend and app_spend['Unknown'] > app_spend.sum() * 0.1:
            consolidated_spend['Other Payments'] = app_spend['Unknown']
        
        return consolidated_spend
    
    def _calculate_association_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate association rules between merchants."""
        try:
            basket = df.groupby(['transaction_id', 'merchant_canonical'])['amount'].sum().unstack().fillna(0)
            basket = basket.applymap(lambda x: 1 if x > 0 else 0)
            
            if basket.shape[1] > 1 and basket.shape[0] > 0:
                # Try with different min_support values
                min_support_values = [0.05, 0.03, 0.01, 0.005]
                frequent_itemsets = None
                
                for min_support in min_support_values:
                    try:
                        frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)
                        if not frequent_itemsets.empty and len(frequent_itemsets) > 0:
                            break
                    except Exception:
                        continue
                
                if frequent_itemsets is not None and not frequent_itemsets.empty and len(frequent_itemsets) > 0:
                    try:
                        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=0.5)
                        if not rules.empty:
                            return rules
                    except Exception:
                        return frequent_itemsets
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"Association rules calculation failed: {e}")
            return pd.DataFrame()
    
    def _calculate_behavioral_insights(self, df: pd.DataFrame) -> Dict:
        """Calculate behavioral insights."""
        behavioral = {}
        
        # Time-of-day patterns (only for spending transactions)
        spending_df = df[df['transaction_type'] == 'debit']
        behavioral['time_pattern'] = spending_df.groupby('time_of_day')['amount'].sum()
        
        # Merchant loyalty
        loyalty = df.groupby('merchant_canonical').size().sort_values(ascending=False)
        behavioral['loyal_merchants'] = loyalty[loyalty >= 5]  # Merchants with 5+ transactions
        
        # Consistent merchants (habits)
        df['year_month'] = df['transaction_date'].dt.to_period('M')
        merchant_month_count = df.groupby(['merchant_canonical','year_month']).size().reset_index(name='count')
        
        # Merchants with at least 3 transactions in a month
        habit_merchant = merchant_month_count[merchant_month_count['count'] >= 3]
        habit_summary = habit_merchant.groupby('merchant_canonical')['year_month'].nunique()
        months_count = df['year_month'].nunique()
        consistent_merchants = habit_summary[habit_summary >= (0.7 * months_count)]
        behavioral['consistent_merchants'] = consistent_merchants
        
        # Transaction type breakdown
        if 'txn_type' in df.columns:
            behavioral['txn_type_breakdown'] = df['txn_type'].value_counts()
        else:
            behavioral['txn_type_breakdown'] = pd.Series()
        
        # Payment method breakdown
        if 'payment_method' in df.columns:
            behavioral['payment_method_breakdown'] = df['payment_method'].value_counts()
        else:
            behavioral['payment_method_breakdown'] = pd.Series()
        
        return behavioral
    
    def _calculate_bank_payment_insights(self, df: pd.DataFrame) -> Dict:
        """Calculate bank and payment method insights."""
        bank_payment = {}
        
        # Bank information
        bank_payment['bank_info'] = self._extract_bank_info(df)
        
        # Card usage
        bank_payment['card_usage'] = self._calculate_card_usage(df)
        
        return bank_payment
    
    def _extract_bank_info(self, df: pd.DataFrame) -> pd.Series:
        """Extract bank information from transactions."""
        bank_keywords = [
            'HDFC', 'SBI', 'ICICI', 'AXIS', 'KOTAK', 'PNB', 'YES', 'BOB', 
            'IDBI', 'CANARA', 'UNION', 'BANK OF BARODA', 'INDIAN BANK',
            'PUNJAB NATIONAL BANK', 'STATE BANK OF INDIA'
        ]
        
        def detect_bank(text):
            text = str(text).upper()
            for bank in bank_keywords:
                if bank in text:
                    return bank
            return "Unknown"
        
        df['bank_detected'] = df['merchant_canonical'].apply(detect_bank)
        return df['bank_detected'].value_counts()
    
    def _calculate_card_usage(self, df: pd.DataFrame) -> Dict:
        """Calculate card usage statistics."""
        # Use payment_method column for accurate card usage detection
        if 'payment_method' not in df.columns:
            return {
                "credit_card_spend": 0,
                "credit_card_payment": 0,
                "debit_card": 0,
                "upi": 0
            }
        
        # Calculate based on payment method
        upi_spend = df[df['payment_method'] == 'UPI']['amount'].sum()
        
        # For debit/credit cards, we need to infer from merchant names and transaction patterns
        # Look for credit card payments (usually to credit card companies)
        credit_payment = df[
            (df['merchant_canonical'].str.contains('Credit Card', case=False, na=False)) |
            (df['merchant_canonical'].str.contains('HDFC Credit Card', case=False, na=False)) |
            (df['merchant_canonical'].str.contains('SBI Credit Card', case=False, na=False)) |
            (df['merchant_canonical'].str.contains('ICICI Credit Card', case=False, na=False))
        ]['amount'].sum()
        
        # Look for credit card spending (usually from credit card transactions)
        credit_spend = df[
            (df['txn_type'] == 'credit_card_spend') |
            (df['merchant_canonical'].str.contains('Credit Card', case=False, na=False))
        ]['amount'].sum()
        
        # Debit card spending (infer from NEFT/IMPS transactions that are expenses)
        debit_spend = df[
            (df['payment_method'].isin(['NEFT', 'IMPS'])) &
            (df['transaction_type'] == 'debit')
        ]['amount'].sum()
        
        return {
            "credit_card_spend": credit_spend,
            "credit_card_payment": credit_payment,
            "debit_card": debit_spend,
            "upi": upi_spend
        }
    
    def _generate_person_intro(self, insights: Dict) -> str:
        """Generate person introduction based on insights."""
        try:
            top_cats = insights.get('category_spending_pattern', pd.Series()).head(2).index.tolist()
            habits = insights.get('consistent_merchants', pd.Series()).index.tolist()
            
            intro = f"This person spends primarily on {', '.join(top_cats[:2])}"
            
            if habits:
                intro += f", has consistent payments to {', '.join(habits[:3])}"
            
            intro += ", and occasionally spikes on discretionary spending."
            
            return intro
        except Exception:
            return "Unable to generate person introduction."
    
    def _empty_insights(self) -> Dict:
        """Return empty insights structure."""
        return {
            "stats": {},
            "classification_summary": {},
            "categorization_summary": {},
            "daily_trend": pd.Series(),
            "top_merchants": pd.Series(),
            "day_spend": pd.Series(),
            "category_spend": pd.Series(),
            "category_spending_pattern": pd.Series(),
            "merchant_category_spend": pd.DataFrame(),
            "app_spend": pd.Series(),
            "recurring": pd.DataFrame(),
            "rules": pd.DataFrame(),
            "time_pattern": pd.Series(),
            "loyal_merchants": pd.Series(),
            "consistent_merchants": pd.Series(),
            "txn_type_breakdown": pd.Series(),
            "bank_info": pd.Series(),
            "card_usage": {},
            "person_intro": "No data available for analysis.",
            "avg_salary": 0.0,
            "avg_other_income": 0.0,
            "avg_income": 0.0,
            "avg_expense": 0.0,
            "savings": 0.0,
            "savings_rate": 0.0,
            "expense_ratio": 0.0,
            "monthly_income": pd.Series(),
            "monthly_expense": pd.Series(),
            "monthly_salary": pd.Series(),
            "monthly_other_income": pd.Series(),
            "bonus_months": {},
            "financial_health_score": 0.0,
            "salary": {"source": "Unknown", "avg_salary": 0.0}
        }


# Convenience function for backward compatibility
def calculate_insights(df: pd.DataFrame) -> Dict:
    """
    Legacy insights calculation function (kept for backward compatibility).
    
    Args:
        df: Preprocessed transaction DataFrame
        
    Returns:
        Dictionary with all insights
    """
    analyzer = TransactionInsights()
    return analyzer.calculate_insights(df) 