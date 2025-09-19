"""
ML-based Transaction Classifier
Replaces hardcoded patterns with machine learning models for dynamic classification.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path
import pickle
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import re
import os

try:
    from .config import get_config
except ImportError:
    from config import get_config

logger = logging.getLogger(__name__)

class MLTransactionClassifier:
    """Machine learning-based transaction classifier with dynamic pattern learning."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize ML classifier.
        
        Args:
            model_path: Path to pre-trained model
        """
        self.model_path = model_path or get_config('ml_models.classification_model_path')
        self.vectorizer_path = str(Path(self.model_path).parent / 'text_vectorizer.pkl')
        
        # Initialize models
        self.classifier = None
        self.vectorizer = None
        self.feature_names = None
        
        # Load or create models
        self._load_or_create_models()
        
        # Configuration
        self.confidence_threshold = get_config('transaction_classification.salary_confidence_threshold', 15.0)
        self.similarity_threshold = get_config('transaction_classification.similarity_threshold', 0.6)
        
        logger.info("ML Transaction Classifier initialized")
    
    def _load_or_create_models(self):
        """Load existing models or create new ones."""
        try:
            if Path(self.model_path).exists() and Path(self.vectorizer_path).exists():
                self.classifier = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                logger.info("Pre-trained models loaded successfully")
            else:
                logger.info("No pre-trained models found, creating new ones")
                self._create_new_models()
        except Exception as e:
            logger.warning(f"Error loading models: {e}, creating new ones")
            self._create_new_models()
    
    def _create_new_models(self):
        """Create new ML models with default training data."""
        # Create default training data
        training_data = self._create_default_training_data()
        
        # Train models
        self._train_models(training_data)
        
        # Save models
        self._save_models()
    
    def _create_default_training_data(self) -> pd.DataFrame:
        """Create default training data with common transaction patterns."""
        training_data = []
        
        # Salary patterns
        salary_patterns = [
            "salary credit", "payroll", "neft salary", "cms salary", 
            "salary from", "salary deposit", "payroll credit", "company salary"
        ]
        for pattern in salary_patterns:
            training_data.append({
                'text': pattern,
                'category': 'salary',
                'confidence': 1.0
            })
        
        # UPI patterns
        upi_patterns = [
            "upi", "@upi", "@ok", "gpay", "google pay", "phonepe", "paytm upi"
        ]
        for pattern in upi_patterns:
            training_data.append({
                'text': pattern,
                'category': 'upi',
                'confidence': 1.0
            })
        
        # Debit card patterns
        debit_patterns = [
            "debit card", "pos debit", "atm", "atm withdrawal", "cash withdrawal"
        ]
        for pattern in debit_patterns:
            training_data.append({
                'text': pattern,
                'category': 'debit_card',
                'confidence': 1.0
            })
        
        # Credit card patterns
        cc_patterns = [
            "credit card txn", "card swipe", "cc purchase", "credit card purchase"
        ]
        for pattern in cc_patterns:
            training_data.append({
                'text': pattern,
                'category': 'credit_card_spend',
                'confidence': 1.0
            })
        
        # Income patterns
        income_patterns = [
            "credited", "credit", "cr", "received", "refund", "cashback"
        ]
        for pattern in income_patterns:
            training_data.append({
                'text': pattern,
                'category': 'income',
                'confidence': 1.0
            })
        
        # Expense patterns
        expense_patterns = [
            "debited", "debit", "dr", "payment", "purchase", "spent"
        ]
        for pattern in expense_patterns:
            training_data.append({
                'text': pattern,
                'category': 'expense',
                'confidence': 1.0
            })
        
        return pd.DataFrame(training_data)
    
    def _train_models(self, training_data: pd.DataFrame):
        """Train the ML models."""
        # Prepare features
        X = training_data['text'].values
        y = training_data['category'].values
        
        # Create and fit vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            stop_words='english'
        )
        X_vectorized = self.vectorizer.fit_transform(X)
        
        # Create and train classifier
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced'
        )
        self.classifier.fit(X_vectorized, y)
        
        # Store feature names
        self.feature_names = self.vectorizer.get_feature_names_out()
        
        logger.info("Models trained successfully")
    
    def _save_models(self):
        """Save trained models to disk."""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.classifier, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            logger.info(f"Models saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def extract_features(self, transaction_data: Dict) -> np.ndarray:
        """
        Extract features from transaction data for classification.
        
        Args:
            transaction_data: Dictionary with transaction information
            
        Returns:
            Feature vector for classification
        """
        # Combine relevant text fields
        text_fields = []
        
        # Merchant name
        if 'merchant_canonical' in transaction_data:
            text_fields.append(str(transaction_data['merchant_canonical']))
        
        # SMS message
        if 'sms_message' in transaction_data:
            text_fields.append(str(transaction_data['sms_message']))
        
        # Summary
        if 'summary' in transaction_data:
            text_fields.append(str(transaction_data['summary']))
        
        # Transaction type
        if 'transaction_type' in transaction_data:
            text_fields.append(str(transaction_data['transaction_type']))
        
        # Combine all text
        combined_text = ' '.join(text_fields).lower()
        
        # Clean text
        cleaned_text = re.sub(r'[^\w\s]', ' ', combined_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        # Vectorize text
        if self.vectorizer:
            features = self.vectorizer.transform([cleaned_text])
            return features
        
        return np.array([])
    
    def classify_transaction(self, transaction_data: Dict) -> Tuple[str, float]:
        """
        Classify a transaction using ML model.
        
        Args:
            transaction_data: Dictionary with transaction information
            
        Returns:
            Tuple of (category, confidence_score)
        """
        try:
            # Extract features
            features = self.extract_features(transaction_data)
            
            if features.size == 0:
                return 'other', 0.0
            
            # Predict category
            prediction = self.classifier.predict(features)[0]
            
            # Get confidence scores
            confidence_scores = self.classifier.predict_proba(features)[0]
            max_confidence = np.max(confidence_scores)
            
            # If confidence is too low, classify as 'other'
            if max_confidence < self.confidence_threshold / 100:
                return 'other', max_confidence
            
            return prediction, max_confidence
            
        except Exception as e:
            logger.warning(f"ML classification failed: {e}, using fallback")
            return self._fallback_classification(transaction_data)
    
    def _fallback_classification(self, transaction_data: Dict) -> Tuple[str, float]:
        """Fallback classification using rule-based approach."""
        text = str(transaction_data.get('merchant_canonical', '')).lower()
        
        # Simple keyword matching as fallback
        if any(word in text for word in ['salary', 'payroll']):
            return 'salary', 0.8
        elif any(word in text for word in ['upi', '@ok']):
            return 'upi', 0.8
        elif any(word in text for word in ['atm', 'debit']):
            return 'debit_card', 0.8
        elif any(word in text for word in ['credit', 'card']):
            return 'credit_card_spend', 0.8
        
        return 'other', 0.5
    
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
        
        logger.info(f"Classifying {len(df)} transactions using ML model")
        
        # Add classification columns
        df['ml_category'] = 'other'
        df['ml_confidence'] = 0.0
        
        # Process in batches for performance
        batch_size = get_config('performance_limits.batch_size', 1000)
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for idx, row in batch.iterrows():
                transaction_data = row.to_dict()
                category, confidence = self.classify_transaction(transaction_data)
                
                df.at[idx, 'ml_category'] = category
                df.at[idx, 'ml_confidence'] = confidence
        
        # Use ML classification as primary, fallback to existing if needed
        if 'txn_type' not in df.columns:
            df['txn_type'] = df['ml_category']
        else:
            # Update existing classification with ML results for high-confidence predictions
            high_confidence_mask = df['ml_confidence'] > 0.8
            df.loc[high_confidence_mask, 'txn_type'] = df.loc[high_confidence_mask, 'ml_category']
        
        logger.info(f"Classification completed. Categories: {df['ml_category'].value_counts().to_dict()}")
        return df
    
    def retrain_model(self, new_training_data: pd.DataFrame):
        """
        Retrain the model with new data.
        
        Args:
            new_training_data: DataFrame with new training examples
        """
        logger.info("Retraining ML model with new data")
        
        # Combine with existing training data
        if hasattr(self, '_training_data'):
            combined_data = pd.concat([self._training_data, new_training_data])
        else:
            combined_data = new_training_data
        
        # Train new models
        self._train_models(combined_data)
        
        # Save updated models
        self._save_models()
        
        # Store training data
        self._training_data = combined_data
        
        logger.info("Model retraining completed")
    
    def get_model_performance(self) -> Dict:
        """Get model performance metrics."""
        if not hasattr(self, '_training_data'):
            return {"error": "No training data available"}
        
        # Split data for evaluation
        X = self._training_data['text'].values
        y = self._training_data['category'].values
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Vectorize
        X_train_vec = self.vectorizer.transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)
        
        # Predictions
        y_pred = self.classifier.predict(X_test_vec)
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        return {
            "accuracy": accuracy,
            "classification_report": report,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(self.feature_names)
        }
    
    def update_patterns(self, new_patterns: Dict[str, List[str]]):
        """
        Update classification patterns dynamically.
        
        Args:
            new_patterns: Dictionary of category -> patterns
        """
        logger.info("Updating classification patterns")
        
        # Convert patterns to training data
        new_training_data = []
        for category, patterns in new_patterns.items():
            for pattern in patterns:
                new_training_data.append({
                    'text': pattern,
                    'category': category,
                    'confidence': 1.0
                })
        
        new_df = pd.DataFrame(new_training_data)
        
        # Retrain model
        self.retrain_model(new_df)
        
        logger.info("Patterns updated successfully")

# Convenience function for backward compatibility
def classify_transaction_ml(transaction_data: Dict) -> Tuple[str, float]:
    """ML-based transaction classification."""
    classifier = MLTransactionClassifier()
    return classifier.classify_transaction(transaction_data)
