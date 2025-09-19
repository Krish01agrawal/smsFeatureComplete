"""
Transaction classification module for SMS transaction analysis.
Uses ML-based classification with fallback to pattern matching.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Import new ML classifier
try:
    try:
        from .ml_classifier import MLTransactionClassifier
    except ImportError:
        from ml_classifier import MLTransactionClassifier
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML classifier not available, using pattern-based classification")

try:
    from .config import get_config
except ImportError:
    from config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class TransactionClassifier:
    """Advanced transaction classifier using ML models with pattern matching fallback."""
    
    def __init__(self, patterns_file: Optional[Path] = None, use_ml: bool = True):
        """
        Initialize classifier with ML and pattern-based approaches.
        
        Args:
            patterns_file: Path to transaction patterns JSON file
            use_ml: Whether to use ML-based classification
        """
        self.use_ml = use_ml and ML_AVAILABLE
        
        if self.use_ml:
            try:
                self.ml_classifier = MLTransactionClassifier()
                logger.info("ML-based classifier initialized")
            except Exception as e:
                logger.warning(f"ML classifier initialization failed: {e}, falling back to pattern-based")
                self.use_ml = False
        
        # Load pattern-based classifier as fallback
        if patterns_file is None:
            patterns_file = Path(__file__).parent.parent / "resources" / "transaction_patterns.json"
        
        self.patterns = self._load_patterns(patterns_file)
        logger.info(f"Loaded {len(self.patterns)} transaction pattern categories")
        
        # Configuration
        self.confidence_threshold = get_config('transaction_classification.salary_confidence_threshold', 15.0)
        self.similarity_threshold = get_config('transaction_classification.similarity_threshold', 0.6)
    
    def _load_patterns(self, patterns_file: Path) -> Dict[str, List[str]]:
        """Load transaction patterns from JSON file."""
        try:
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)
            return patterns
        except FileNotFoundError:
            logger.error(f"Patterns file not found: {patterns_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in patterns file: {e}")
            return {}
    
    def classify_transaction(self, row: pd.Series) -> str:
        """
        Classify a single transaction using ML or pattern matching.
        
        Args:
            row: Transaction row with merchant_canonical and sms_message
            
        Returns:
            Classification category
        """
        # Try ML classification first if available
        if self.use_ml:
            try:
                transaction_data = row.to_dict()
                category, confidence = self.ml_classifier.classify_transaction(transaction_data)
                
                # Use ML result if confidence is high enough
                if confidence > self.confidence_threshold / 100:
                    return category
                else:
                    logger.debug(f"ML confidence too low ({confidence:.2f}), using pattern matching")
            except Exception as e:
                logger.warning(f"ML classification failed: {e}, using pattern matching")
        
        # Fallback to pattern-based classification
        return self._pattern_based_classification(row)
    
    def _pattern_based_classification(self, row: pd.Series) -> str:
        """Pattern-based classification as fallback."""
        # Combine merchant name and SMS message for pattern matching
        merchant = str(row.get('merchant_canonical', '')).lower()
        sms_text = str(row.get('sms_message', '')).lower()
        combined = f"{merchant} {sms_text}"
        
        # Use external patterns for classification
        for category, patterns in self.patterns.items():
            if any(p.lower() in combined for p in patterns):
                return category
        
        # Fallback to basic classification
        return self._basic_classification(combined)
    
    def _basic_classification(self, combined_text: str) -> str:
        """Basic classification using common patterns."""
        # Salary detection
        salary_keywords = ["salary", "payroll", "neft salary", "cms salary"]
        if any(keyword in combined_text for keyword in salary_keywords):
            return 'salary'
        
        # UPI detection
        upi_keywords = ["upi", "@ok", "@upi", "gpay", "google pay", "phonepe", "paytm upi"]
        if any(keyword in combined_text for keyword in upi_keywords):
            return 'upi'
        
        # Debit card detection
        debit_keywords = ["debit card", "pos debit", "atm", "atm withdrawal", "cash withdrawal"]
        if any(keyword in combined_text for keyword in debit_keywords):
            return 'debit_card'
        
        # Credit card detection
        cc_keywords = ["credit card txn", "card swipe", "cc purchase", "credit card purchase"]
        if any(keyword in combined_text for keyword in cc_keywords):
            return 'credit_card_spend'
        
        # Income detection
        income_keywords = ["credited", "credit", "cr", "received", "refund", "cashback"]
        if any(keyword in combined_text for keyword in income_keywords):
            return 'income'
        
        # Expense detection
        expense_keywords = ["debited", "debit", "dr", "payment", "purchase", "spent"]
        if any(keyword in combined_text for keyword in expense_keywords):
            return 'expense'
        
        return 'other'
    
    def classify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify all transactions in a DataFrame.
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            DataFrame with added classification columns
        """
        if df.empty:
            return df
        
        logger.info(f"Classifying {len(df)} transactions using {'ML' if self.use_ml else 'pattern-based'} approach")
        
        # Add classification columns
        df['txn_type'] = 'other'
        df['classification_method'] = 'pattern'
        df['classification_confidence'] = 0.0
        
        # Process in batches for performance
        batch_size = get_config('performance_limits.batch_size', 1000)
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            
            for idx, row in batch.iterrows():
                try:
                    if self.use_ml:
                        # ML-based classification
                        transaction_data = row.to_dict()
                        category, confidence = self.ml_classifier.classify_transaction(transaction_data)
                        
                        df.at[idx, 'txn_type'] = category
                        df.at[idx, 'classification_method'] = 'ml'
                        df.at[idx, 'classification_confidence'] = confidence
                    else:
                        # Pattern-based classification
                        category = self.classify_transaction(row)
                        df.at[idx, 'txn_type'] = category
                        df.at[idx, 'classification_method'] = 'pattern'
                        df.at[idx, 'classification_confidence'] = 1.0
                        
                except Exception as e:
                    logger.warning(f"Classification failed for row {idx}: {e}")
                    df.at[idx, 'txn_type'] = 'other'
                    df.at[idx, 'classification_method'] = 'error'
                    df.at[idx, 'classification_confidence'] = 0.0
        
        # Log classification results
        classification_summary = df['txn_type'].value_counts().to_dict()
        logger.info(f"Classification completed. Categories: {classification_summary}")
        
        return df
    
    def get_classification_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary of classification results.
        
        Args:
            df: DataFrame with classification results
            
        Returns:
            Classification summary dictionary
        """
        if df.empty:
            return {"error": "No data to analyze"}
        
        summary = {
            "total_transactions": len(df),
            "classification_methods": df['classification_method'].value_counts().to_dict(),
            "categories": df['txn_type'].value_counts().to_dict(),
            "confidence_stats": {
                "mean": df['classification_confidence'].mean(),
                "median": df['classification_confidence'].median(),
                "std": df['classification_confidence'].std()
            }
        }
        
        # Calculate accuracy if ML was used
        if 'ml' in df['classification_method'].values:
            ml_transactions = df[df['classification_method'] == 'ml']
            summary['ml_accuracy'] = {
                "transactions": len(ml_transactions),
                "high_confidence": len(ml_transactions[ml_transactions['classification_confidence'] > 0.8]),
                "medium_confidence": len(ml_transactions[
                    (ml_transactions['classification_confidence'] > 0.5) & 
                    (ml_transactions['classification_confidence'] <= 0.8)
                ]),
                "low_confidence": len(ml_transactions[ml_transactions['classification_confidence'] <= 0.5])
            }
        
        return summary
    
    def update_patterns(self, new_patterns: Dict[str, List[str]]):
        """
        Update classification patterns dynamically.
        
        Args:
            new_patterns: Dictionary of category -> patterns
        """
        logger.info("Updating classification patterns")
        
        # Update patterns
        for category, patterns in new_patterns.items():
            if category in self.patterns:
                self.patterns[category].extend(patterns)
            else:
                self.patterns[category] = patterns
        
        # Update ML model if available
        if self.use_ml:
            try:
                self.ml_classifier.update_patterns(new_patterns)
                logger.info("ML model updated with new patterns")
            except Exception as e:
                logger.warning(f"ML model update failed: {e}")
        
        logger.info("Patterns updated successfully")
    
    def get_model_performance(self) -> Dict:
        """Get ML model performance metrics if available."""
        if self.use_ml and hasattr(self.ml_classifier, 'get_model_performance'):
            return self.ml_classifier.get_model_performance()
        else:
            return {"error": "ML model not available or no performance data"}
    
    def retrain_model(self, new_training_data: pd.DataFrame):
        """Retrain ML model with new data."""
        if self.use_ml and hasattr(self.ml_classifier, 'retrain_model'):
            try:
                self.ml_classifier.retrain_model(new_training_data)
                logger.info("ML model retrained successfully")
            except Exception as e:
                logger.error(f"ML model retraining failed: {e}")
        else:
            logger.warning("ML model retraining not available")


# Convenience function for backward compatibility
def classify_transaction(row: pd.Series) -> str:
    """
    Legacy classification function (kept for backward compatibility).
    
    Args:
        row: Transaction row
        
    Returns:
        Classification category
    """
    classifier = TransactionClassifier(use_ml=False)  # Use pattern-based for backward compatibility
    return classifier.classify_transaction(row) 