"""
Preprocessing module for SMS transaction analysis.
Handles data cleaning, feature engineering, and data validation.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

try:
    from .config import get_config
except ImportError:
    from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Centralized data preprocessing class with comprehensive cleaning and feature engineering."""
    
    def __init__(self, date_range_months: int = None, store_processed_data: bool = False):
        """
        Initialize preprocessor.
        
        Args:
            date_range_months: Number of months of data to include (default: 24 months for comprehensive analysis)
            store_processed_data: Whether to store processed data in MongoDB (default: False)
        """
        # Default to ALL historical data (0 = no date filtering) for complete analysis
        # This ensures we capture ALL user transaction history
        if date_range_months is None:
            self.date_range_months = get_config('time_configurations.monthly_analysis_periods', [0])[0]
        else:
            self.date_range_months = date_range_months
        self.store_processed_data = store_processed_data
        
        # Load configuration
        self.weekend_days = get_config('time_configurations.weekend_days', [5, 6])
        self.time_bins = get_config('time_configurations.time_bins', [0, 6, 12, 18, 24])
        self.day_categories = get_config('time_configurations.day_categories', {'weekday': [0, 1, 2, 3, 4], 'weekend': [5, 6]})
        
        # Initialize processed data manager if needed
        self.processed_data_manager = None
        if self.store_processed_data:
            try:
                try:
                    from .processed_data_manager import ProcessedDataManager
                except ImportError:
                    from processed_data_manager import ProcessedDataManager
                
                self.processed_data_manager = ProcessedDataManager()
                logger.info("✅ ProcessedDataManager initialized for storing processed data")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize ProcessedDataManager: {e}")
                self.store_processed_data = False
        
        logger.info(f"DataPreprocessor initialized with {self.date_range_months} months analysis period, store_processed={self.store_processed_data}")
    
    def _remove_extreme_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        CRITICAL: Remove extreme outliers that corrupt financial analysis.
        Uses statistical methods to detect and remove impossible transaction amounts.
        """
        if df.empty or 'amount' not in df.columns:
            return df
        
        initial_count = len(df)
        
        # 1. Remove obviously corrupted data (amounts > 1 crore = 10 million)
        max_reasonable_amount = 10_000_000  # 1 crore rupees
        extreme_outliers = df[df['amount'] > max_reasonable_amount]
        
        if not extreme_outliers.empty:
            logger.warning(f"🚨 EXTREME OUTLIERS DETECTED: {len(extreme_outliers)} transactions > ₹{max_reasonable_amount:,}")
            for _, row in extreme_outliers.head(5).iterrows():
                merchant = row.get('merchant_canonical', row.get('counterparty', 'Unknown'))
                amount = row.get('amount', 0)
                date = row.get('transaction_date', 'Unknown')
                logger.warning(f"   REMOVED: ₹{amount:,.2f} from {merchant} on {date}")
            
            df = df[df['amount'] <= max_reasonable_amount]
        
        # 2. Statistical outlier detection using IQR method
        if len(df) > 10:  # Need sufficient data for statistical analysis
            amounts = df['amount'].copy()
            
            # Calculate IQR for amounts > 0 (exclude zero amounts from outlier detection)
            non_zero_amounts = amounts[amounts > 0]
            if len(non_zero_amounts) > 5:
                Q1 = non_zero_amounts.quantile(0.25)
                Q3 = non_zero_amounts.quantile(0.75)
                IQR = Q3 - Q1
                
                # Define outlier bounds (more conservative for financial data)
                lower_bound = Q1 - 3 * IQR  # 3x IQR instead of 1.5x for more conservative detection
                upper_bound = Q3 + 3 * IQR
                
                # Only remove upper outliers that are extremely high
                # Don't remove lower outliers as small transactions are normal
                statistical_outliers = df[(df['amount'] > upper_bound) & (df['amount'] > 100000)]  # Only if > 1 lakh
                
                if not statistical_outliers.empty and upper_bound > 50000:  # Only if upper bound is reasonable
                    logger.warning(f"📊 STATISTICAL OUTLIERS: {len(statistical_outliers)} transactions > ₹{upper_bound:,.2f}")
                    df = df[~((df['amount'] > upper_bound) & (df['amount'] > 100000))]
        
        # 3. Remove transactions with suspicious merchant names (likely corrupted)
        suspicious_merchants = df[df['merchant_canonical'].astype(str).str.match(r'^\d{1,4}$', na=False)]
        if not suspicious_merchants.empty:
            logger.warning(f"🔍 SUSPICIOUS MERCHANTS: {len(suspicious_merchants)} transactions from numeric-only merchants")
            for merchant in suspicious_merchants['merchant_canonical'].unique():
                total_amount = suspicious_merchants[suspicious_merchants['merchant_canonical'] == merchant]['amount'].sum()
                if total_amount > 1000000:  # > 10 lakh from suspicious merchant
                    logger.warning(f"   REMOVED: ₹{total_amount:,.2f} from suspicious merchant '{merchant}'")
            
            df = df[~df['merchant_canonical'].astype(str).str.match(r'^\d{1,4}$', na=False)]
        
        outliers_removed = initial_count - len(df)
        if outliers_removed > 0:
            logger.info(f"🛡️ OUTLIER PROTECTION: Removed {outliers_removed} extreme outliers to prevent data corruption")
        
        return df
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map MongoDB columns to expected analysis columns."""
        # Create a copy to avoid modifying the original
        df = df.copy()
        
        # Map transaction_type if it exists
        if 'transaction_type' in df.columns:
            # Map transaction types to expected format
            df['txn_type'] = df['transaction_type'].map({
                'credit': 'credit',
                'debit': 'debit',
                'other': 'other'
            }).fillna('other')
        else:
            df['txn_type'] = 'other'
        
        # Map payment method if metadata.method exists
        if 'metadata' in df.columns:
            # Extract method from metadata if it's a string representation
            df['payment_method'] = df['metadata'].str.extract(r"'method': '([^']*)'").fillna('Other')
        else:
            df['payment_method'] = 'Other'
        
        # Ensure we have all required columns for analysis
        required_columns = ['merchant_canonical', 'amount', 'transaction_date', 'txn_type', 'payment_method']
        for col in required_columns:
            if col not in df.columns:
                if col == 'txn_type':
                    df[col] = 'other'
                elif col == 'payment_method':
                    df[col] = 'Other'
                else:
                    df[col] = 'Unknown'
        
        return df

    def preprocess(self, df: pd.DataFrame, user_id: str = None) -> pd.DataFrame:
        """
        Main preprocessing pipeline.
        
        Args:
            df: Raw transaction DataFrame
            user_id: User identifier (required for storing processed data)
            
        Returns:
            Preprocessed DataFrame
        """
        logger.info(f"Starting preprocessing for {len(df)} transactions")
        
        # Step 1: Basic cleaning
        df = self._clean_data(df)
        
        # Step 2: Column mapping for compatibility
        df = self._map_columns(df)
        
        # Step 3: Date processing
        df = self._process_dates(df)
        
        # Step 4: Filter by date range
        df = self._filter_date_range(df)
        
        # Step 5: Feature engineering
        df = self._engineer_features(df)
        
        # Step 6: Data validation
        df = self._validate_processed_data(df)
        
        # Step 7: CRITICAL - Remove extreme outliers that corrupt analysis
        df = self._remove_extreme_outliers(df)
        
        logger.info(f"Preprocessing complete. Final dataset: {len(df)} transactions")
        
        # Step 8: Store processed data if enabled and user_id provided (ALWAYS CLEAN SLATE)
        if self.store_processed_data and self.processed_data_manager and user_id:
            self._store_processed_data(df, user_id, force_clean_slate=True)
        
        return df
    
    def _store_processed_data(self, processed_df: pd.DataFrame, user_id: str, force_clean_slate: bool = True):
        """
        Store processed data to MongoDB collection with clean slate processing.
        
        Args:
            processed_df: Processed DataFrame
            user_id: User identifier
            force_clean_slate: Whether to completely clean existing data before storing
        """
        try:
            # Create processing metadata
            processing_metadata = {
                "date_range_months": self.date_range_months,
                "preprocessing_version": "2.0",  # Updated version for clean slate
                "features_engineered": list(processed_df.columns),
                "original_count": len(processed_df),
                "processing_config": {
                    "weekend_days": self.weekend_days,
                    "time_bins": self.time_bins,
                    "day_categories": self.day_categories
                },
                "clean_slate_processing": force_clean_slate,
                "processed_timestamp": pd.Timestamp.now().isoformat()
            }
            
            # Store the processed data with clean slate
            success = self.processed_data_manager.store_processed_data(
                user_id=user_id,
                processed_df=processed_df,
                processing_metadata=processing_metadata,
                force_clean_slate=force_clean_slate
            )
            
            if success:
                logger.info(f"🎉 Successfully completed clean slate processing for user {user_id}")
            else:
                logger.error(f"❌ Failed to store processed data for user {user_id}")
                
        except Exception as e:
            logger.error(f"❌ Error storing processed data for user {user_id}: {e}")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean raw data by removing duplicates, handling nulls, etc."""
        initial_count = len(df)
        
        # Handle nested dictionary and list structures before drop_duplicates
        df = self._flatten_nested_structures(df)
        
        # Enhanced duplicate removal
        df = self._remove_intelligent_duplicates(df)
        
        # Handle null values in critical columns - use actual column names from MongoDB data
        # Check if required columns exist, if not create them from available data
        if 'merchant_canonical' not in df.columns:
            # Use counterparty as merchant_canonical if it exists
            if 'counterparty' in df.columns:
                df['merchant_canonical'] = df['counterparty']
            else:
                # Create a default merchant column if neither exists
                df['merchant_canonical'] = 'Unknown'
        
        # Fill missing counterparty/merchant values
        df['merchant_canonical'] = df['merchant_canonical'].fillna('Unknown')
        
        # Handle amount column - some transactions might not have amounts (promos, alerts)
        if 'amount' not in df.columns:
            df['amount'] = 0.0
        
        # Convert amount to numeric, handling missing values
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
        
        # For analysis purposes, we'll keep transactions with 0 amounts (alerts, promos)
        # but we'll filter them out for spending analysis later
        
        # Clean merchant names
        df['merchant_canonical'] = df['merchant_canonical'].astype(str).str.strip()
        df = df[df['merchant_canonical'] != '']
        
        logger.info(f"Data cleaning: {initial_count} -> {len(df)} transactions")
        return df
    
    def _flatten_nested_structures(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flatten nested dictionary and list structures to make them pandas-compatible."""
        df = df.copy()
        
        # Handle nested account information
        if 'account' in df.columns:
            # Extract bank and account_number from nested account dict
            df['bank'] = df['account'].apply(lambda x: x.get('bank', 'Unknown') if isinstance(x, dict) else 'Unknown')
            df['account_number'] = df['account'].apply(lambda x: x.get('account_number', 'Unknown') if isinstance(x, dict) else 'Unknown')
            # Remove the nested account column
            df = df.drop(columns=['account'])
        
        # Handle nested metadata information
        if 'metadata' in df.columns:
            # Extract key metadata fields
            df['sms_text'] = df['metadata'].apply(lambda x: x.get('original_text', '') if isinstance(x, dict) else '')
            df['sender'] = df['metadata'].apply(lambda x: x.get('sender', '') if isinstance(x, dict) else '')
            df['method'] = df['metadata'].apply(lambda x: x.get('method', 'Other') if isinstance(x, dict) else 'Other')
            df['reference_id'] = df['metadata'].apply(lambda x: x.get('reference_id', '') if isinstance(x, dict) else '')
            # Remove the nested metadata column
            df = df.drop(columns=['metadata'])
        
        # Handle nested date fields
        if 'created_at' in df.columns:
            df['created_at'] = df['created_at'].apply(
                lambda x: x.get('$date') if isinstance(x, dict) else x
            )
        
        if 'updated_at' in df.columns:
            df['updated_at'] = df['updated_at'].apply(
                lambda x: x.get('$date') if isinstance(x, dict) else x
            )
        
        # Handle nested _id field
        if '_id' in df.columns:
            df['_id'] = df['_id'].apply(
                lambda x: x.get('$oid') if isinstance(x, dict) else str(x)
            )
        
        # Handle tags list - convert to string
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(
                lambda x: ', '.join(x) if isinstance(x, list) else str(x)
            )
        
        # Handle confidence_score - ensure it's numeric
        if 'confidence_score' in df.columns:
            df['confidence_score'] = pd.to_numeric(df['confidence_score'], errors='coerce').fillna(0.0)
        
        # Handle currency - ensure it's string
        if 'currency' in df.columns:
            df['currency'] = df['currency'].astype(str)
        
        # Handle message_intent - ensure it's string
        if 'message_intent' in df.columns:
            df['message_intent'] = df['message_intent'].astype(str)
        
        # Handle category - ensure it's string
        if 'category' in df.columns:
            df['category'] = df['category'].astype(str)
        
        # Handle transaction_type - ensure it's string
        if 'transaction_type' in df.columns:
            df['transaction_type'] = df['transaction_type'].astype(str)
        
        # Handle summary - ensure it's string
        if 'summary' in df.columns:
            df['summary'] = df['summary'].astype(str)
        
        # Handle counterparty - ensure it's string
        if 'counterparty' in df.columns:
            df['counterparty'] = df['counterparty'].astype(str)
        
        # Handle user_id - ensure it's string
        if 'user_id' in df.columns:
            df['user_id'] = df['user_id'].astype(str)
        
        logger.info("Nested structures flattened successfully")
        return df
    
    def _process_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and standardize date columns."""
        # Handle mixed date formats more robustly
        if 'transaction_date' in df.columns:
            # Safety net: Handle any remaining BSON Date strings that might slip through
            if df['transaction_date'].dtype == 'object':
                # Check for BSON Date string format (fallback safety net)
                bson_date_pattern = r"\{'\\$date': '([^']+)'\}"
                bson_matches = df['transaction_date'].astype(str).str.match(bson_date_pattern, na=False)
                
                if bson_matches.any():
                    logger.info(f"🔄 Safety net: Found {bson_matches.sum()} BSON Date strings, extracting dates...")
                    # Extract actual date from BSON Date string format
                    extracted_dates = df['transaction_date'].astype(str).str.extract(bson_date_pattern, expand=False)
                    # Only update rows that matched the pattern
                    df.loc[bson_matches, 'transaction_date'] = extracted_dates[bson_matches]
                    logger.info(f"✅ Safety net: Successfully extracted dates from BSON format")
            
            # Convert to datetime, handling various formats
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], format='mixed', errors='coerce')
            
            # Remove rows where date parsing failed
            df = df.dropna(subset=['transaction_date'])
            
            # Sort by date
            df = df.sort_values('transaction_date')
        else:
            # If no transaction_date, try to use created_at or other date fields
            date_columns = ['created_at', 'updated_at']
            for col in date_columns:
                if col in df.columns:
                    df['transaction_date'] = pd.to_datetime(df[col], format='mixed', errors='coerce')
                    df = df.dropna(subset=['transaction_date'])
                    df = df.sort_values('transaction_date')
                    break
            else:
                # If no date column found, create a default one
                logger.warning("No date column found, using current date for all transactions")
                df['transaction_date'] = pd.Timestamp.now()
        
        return df
    
    def _filter_date_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter data to specified date range. If date_range_months is 0, process ALL data."""
        if df.empty:
            return df
        
        # Check if we have valid transaction_date column
        if 'transaction_date' not in df.columns:
            logger.warning("No transaction_date column found, skipping date filtering")
            return df
        
        # Convert transaction_date to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df['transaction_date']):
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        
        # Remove rows where date parsing failed (this maintains data quality)
        initial_count = len(df)
        df = df.dropna(subset=['transaction_date'])
        
        if len(df) < initial_count:
            logger.info(f"Removed {initial_count - len(df)} transactions with invalid dates (data quality filter)")
        
        if df.empty:
            logger.warning("All transactions had invalid dates, returning empty DataFrame")
            return df
        
        # If date_range_months is 0 or None, process ALL historical data
        if self.date_range_months == 0 or self.date_range_months is None:
            logger.info(f"Processing ALL historical data: {len(df)} transactions (no date filtering)")
            return df
        
        # Otherwise, filter by date range
        current_date = datetime.now()
        # CRITICAL FIX: Use proper date calculation instead of broken integer division
        start_date = current_date - pd.DateOffset(months=self.date_range_months)
        
        # Filter by date range
        df = df[df['transaction_date'] >= start_date]
        
        logger.info(f"Date filtering: {len(df)} transactions in last {self.date_range_months} months")
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer new features for analysis."""
        if df.empty:
            return df
        
        # Time-based features
        df['day_of_week'] = df['transaction_date'].dt.day_name()
        df['month'] = df['transaction_date'].dt.month
        df['year'] = df['transaction_date'].dt.year
        df['hour'] = df['transaction_date'].dt.hour
        df['day_of_month'] = df['transaction_date'].dt.day
        df['week_of_year'] = df['transaction_date'].dt.isocalendar().week
        df['quarter'] = df['transaction_date'].dt.quarter
        
        # Boolean features using configuration
        df['is_weekend'] = df['transaction_date'].dt.weekday.isin(self.weekend_days)
        df['is_month_start'] = df['day_of_month'] <= 3
        df['is_month_end'] = df['day_of_month'] >= 28
        
        # Time of day categories using configuration
        df['time_of_day'] = pd.cut(df['hour'], bins=self.time_bins, labels=['Night', 'Morning', 'Afternoon', 'Evening'])
        
        # Day categories using configuration
        df['day_category'] = pd.cut(
            df['transaction_date'].dt.weekday,
            bins=[-1] + [max(self.day_categories['weekday'])] + [max(self.day_categories['weekend'])],
            labels=['Weekday', 'Weekend']
        )
        
        # Amount categories
        df['amount_category'] = df['amount'].apply(self._categorize_amount)
        
        # Transaction frequency features (will be calculated per merchant)
        df['transaction_month'] = df['transaction_date'].dt.to_period('M')
        
        return df
    
    def _categorize_time_of_day(self, hour: int) -> str:
        """Categorize hour into time of day using configuration."""
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"
    
    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amount."""
        if amount < 100:
            return "Small (<₹100)"
        elif amount < 500:
            return "Medium (₹100-500)"
        elif amount < 2000:
            return "Large (₹500-2000)"
        elif amount < 10000:
            return "Very Large (₹2000-10000)"
        else:
            return "Huge (>₹10000)"
    
    def _validate_processed_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate processed data and log any issues."""
        if df.empty:
            logger.warning("Processed DataFrame is empty")
            return df
        
        # Check for data quality issues
        issues = []
        
        # Get thresholds from configuration
        pattern_break_threshold = get_config('anomaly_detection.pattern_break_threshold', 1.5)
        
        if df['amount'].min() <= 0:
            issues.append("Negative or zero amounts found")
        
        if df['transaction_date'].isnull().sum() > 0:
            issues.append("Null transaction dates found")
        
        if df['merchant_canonical'].isnull().sum() > 0:
            issues.append("Null merchant names found")
        
        # Check for reasonable date ranges
        date_range = df['transaction_date'].max() - df['transaction_date'].min()
        if date_range.days > 365 * 2:  # More than 2 years
            issues.append("Data spans more than 2 years")
        
        if issues:
            logger.warning(f"Data quality issues found: {issues}")
        else:
            logger.info("Data validation passed")
        
        return df
    
    def get_data_summary(self, df: pd.DataFrame) -> dict:
        """Get summary statistics of processed data."""
        if df.empty:
            return {"error": "DataFrame is empty"}
        
        summary = {
            "total_transactions": len(df),
            "date_range": {
                "start": df['transaction_date'].min().strftime('%Y-%m-%d'),
                "end": df['transaction_date'].max().strftime('%Y-%m-%d'),
                "days": (df['transaction_date'].max() - df['transaction_date'].min()).days
            },
            "amount_stats": {
                "total": df['amount'].sum(),
                "mean": df['amount'].mean(),
                "median": df['amount'].median(),
                "min": df['amount'].min(),
                "max": df['amount'].max(),
                "std": df['amount'].std()
            },
            "unique_merchants": df['merchant_canonical'].nunique(),
            "unique_users": df.get('user_id', pd.Series()).nunique() if 'user_id' in df.columns else 1,
            "transaction_types": df.get('transaction_type', pd.Series()).value_counts().to_dict() if 'transaction_type' in df.columns else {},
            "time_distribution": {
                "weekend_ratio": df['is_weekend'].mean(),
                "time_of_day_distribution": df['time_of_day'].value_counts().to_dict() if 'time_of_day' in df.columns else {},
                "day_category_distribution": df['day_category'].value_counts().to_dict() if 'day_category' in df.columns else {}
            }
        }
        
        return summary

    def _handle_unhashable_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle columns with unhashable types (lists, dicts) to prevent drop_duplicates errors."""
        if df.empty:
            return df
        
        # Important financial columns that must remain numeric
        numeric_columns = {'amount', 'balance', 'confidence_score', 'month', 'year', 'hour', 
                          'day_of_month', 'week_of_year', 'quarter', 'date_range_months', 'original_count'}
        
        # Boolean columns that should remain boolean
        boolean_columns = {'is_weekend', 'is_month_start', 'is_month_end'}
            
        for column in df.columns:
            try:
                # Handle numeric columns - ensure they're proper numeric types
                if column in numeric_columns:
                    # Convert numpy arrays to proper numeric values
                    if df[column].dtype == 'object':
                        sample_value = df[column].dropna().iloc[0] if not df[column].dropna().empty else None
                        if sample_value is not None and hasattr(sample_value, 'tolist'):
                            logger.info(f"Converting numeric array column '{column}' to proper numeric type")
                            df[column] = df[column].apply(lambda x: x.tolist()[0] if hasattr(x, 'tolist') and len(x.tolist()) > 0 else x)
                            df[column] = pd.to_numeric(df[column], errors='coerce')
                    continue
                    
                # Handle boolean columns - ensure they're proper boolean types  
                if column in boolean_columns:
                    if df[column].dtype == 'object':
                        sample_value = df[column].dropna().iloc[0] if not df[column].dropna().empty else None
                        if sample_value is not None and hasattr(sample_value, 'tolist'):
                            logger.info(f"Converting boolean array column '{column}' to proper boolean type")
                            df[column] = df[column].apply(lambda x: x.tolist()[0] if hasattr(x, 'tolist') and len(x.tolist()) > 0 else x)
                            df[column] = df[column].astype(bool)
                    continue
                
                # Check if column contains unhashable types
                sample_value = df[column].dropna().iloc[0] if not df[column].dropna().empty else None
                
                if sample_value is not None:
                    # Convert lists to strings
                    if isinstance(sample_value, (list, tuple)):
                        logger.info(f"Converting list column '{column}' to string representation")
                        df[column] = df[column].apply(lambda x: str(x) if isinstance(x, (list, tuple)) else x)
                    
                    # Convert dicts to strings
                    elif isinstance(sample_value, dict):
                        logger.info(f"Converting dict column '{column}' to string representation")
                        df[column] = df[column].apply(lambda x: str(x) if isinstance(x, dict) else x)
                        
                    # Convert numpy arrays to strings (but not for numeric columns)
                    elif hasattr(sample_value, 'tolist'):  # numpy array
                        logger.info(f"Converting array column '{column}' to string representation")
                        df[column] = df[column].apply(lambda x: str(x.tolist()) if hasattr(x, 'tolist') else str(x))
                        
            except Exception as e:
                # If we can't determine the type safely, only convert to string if not a critical numeric column
                if column not in numeric_columns and column not in boolean_columns:
                    logger.warning(f"Converting problematic column '{column}' to string: {e}")
                    df[column] = df[column].astype(str)
                else:
                    logger.error(f"Critical numeric/boolean column '{column}' has issues: {e}")
                
        return df

    def _remove_intelligent_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates with intelligent detection for financial transactions."""
        initial_count = len(df)
        
        # Handle unhashable columns before duplicate removal
        df = self._handle_unhashable_columns(df)
        
        # Standard duplicate removal first
        df = df.drop_duplicates()
        
        # Intelligent duplicate detection for financial transactions
        if len(df) > 1 and 'amount' in df.columns and 'transaction_date' in df.columns:
            # Group by critical financial fields
            key_columns = ['amount', 'transaction_date', 'transaction_type']
            
            # Add merchant column if available
            if 'counterparty' in df.columns:
                key_columns.append('counterparty')
            elif 'merchant_canonical' in df.columns:
                key_columns.append('merchant_canonical')
            
            # Find potential duplicates
            grouped = df.groupby(key_columns)
            indices_to_remove = []
            
            for name, group in grouped:
                if len(group) > 1:
                    # Multiple transactions with same key fields - likely duplicates
                    amount = name[0] if len(name) > 0 else 0
                    date = name[1] if len(name) > 1 else None
                    txn_type = name[2] if len(name) > 2 else None
                    merchant = name[3] if len(name) > 3 else 'Unknown'
                    
                    # For salary transactions (high-value credits), be strict about duplicates
                    if (amount >= 15000 and txn_type == 'credit'):
                        # Check if merchant suggests salary
                        merchant_str = str(merchant).lower()
                        if any(keyword in merchant_str for keyword in ['salary', 'technologies', 'pvt', 'ltd', 'company', 'station91']):
                            # Keep only the first salary transaction
                            indices_to_remove.extend(group.index[1:].tolist())
                            logger.warning(f"Detected {len(group)} duplicate salary transactions: ₹{amount:,} from {merchant} on {date}")
                        else:
                            # For other high-value credits, keep first
                            indices_to_remove.extend(group.index[1:].tolist())
                            logger.warning(f"Detected {len(group)} duplicate high-value transactions: ₹{amount:,}")
                    
                    # For regular transactions, also remove duplicates
                    elif amount >= 100:  # Minimum threshold for duplicate detection
                        indices_to_remove.extend(group.index[1:].tolist())
                        logger.info(f"Detected {len(group)} duplicate transactions: ₹{amount:,}")
            
            # Remove identified duplicates
            if indices_to_remove:
                df = df.drop(indices_to_remove)
                logger.info(f"Intelligent duplicate removal: removed {len(indices_to_remove)} transactions")
        
        total_removed = initial_count - len(df)
        if total_removed > 0:
            logger.info(f"Total duplicates removed: {total_removed} transactions")
        
        return df


# Convenience function for backward compatibility
def preprocess(df: pd.DataFrame, date_range_months: int = None) -> pd.DataFrame:
    """
    Legacy preprocessing function (kept for backward compatibility).
    
    Args:
        df: Raw transaction DataFrame
        date_range_months: Number of months of data to include
        
    Returns:
        Preprocessed DataFrame
    """
    preprocessor = DataPreprocessor(date_range_months)
    return preprocessor.preprocess(df) 