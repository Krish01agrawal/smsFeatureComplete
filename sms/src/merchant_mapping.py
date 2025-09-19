"""
Merchant mapping module for SMS transaction analysis.
Handles merchant categorization with fuzzy matching capabilities.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

# Try to import rapidfuzz for fuzzy matching, fallback to basic matching
try:
    from rapidfuzz import process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logging.warning("rapidfuzz not available, using basic string matching")

# Configure logging
logger = logging.getLogger(__name__)


class MerchantMapper:
    """Advanced merchant categorization with fuzzy matching and ML-ready features."""
    
    def __init__(self, mapping_file: Optional[Path] = None, fuzzy_threshold: float = 85):
        """
        Initialize merchant mapper.
        
        Args:
            mapping_file: Path to merchant mapping JSON file
            fuzzy_threshold: Threshold for fuzzy matching (0-100)
        """
        if mapping_file is None:
            mapping_file = Path(__file__).parent.parent / "resources" / "merchant_mapping.json"
        
        self.mapping = self._load_mapping(mapping_file)
        self.fuzzy_threshold = fuzzy_threshold
        self.fuzzy_available = FUZZY_AVAILABLE
        
        logger.info(f"Loaded {len(self.mapping)} merchant mappings")
        if not self.fuzzy_available:
            logger.warning("Fuzzy matching disabled - install rapidfuzz for better matching")
    
    def _load_mapping(self, mapping_file: Path) -> Dict[str, str]:
        """Load merchant mapping from JSON file."""
        try:
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
            return mapping
        except FileNotFoundError:
            logger.error(f"Mapping file not found: {mapping_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in mapping file: {e}")
            return {}
    
    def categorize_merchant(self, merchant_name: str) -> str:
        """
        Categorize a merchant using direct mapping and fuzzy matching.
        
        Args:
            merchant_name: Name of the merchant
            
        Returns:
            Category name
        """
        if not merchant_name or pd.isna(merchant_name):
            return "Unknown"
        
        merchant_lower = str(merchant_name).lower().strip()
        
        # Direct mapping (exact match)
        for key, category in self.mapping.items():
            if key.lower() in merchant_lower:
                return category
        
        # Fuzzy matching if available
        if self.fuzzy_available:
            return self._fuzzy_match(merchant_lower)
        
        # Fallback to rule-based categorization
        return self._rule_based_categorization(merchant_lower)
    
    def _fuzzy_match(self, merchant_lower: str) -> str:
        """Perform fuzzy matching on merchant name."""
        try:
            # Get best match from mapping keys
            best_match = process.extractOne(
                merchant_lower, 
                list(self.mapping.keys()),
                scorer=fuzz.partial_ratio
            )
            
            if best_match and best_match[1] >= self.fuzzy_threshold:
                return self.mapping[best_match[0]]
            
        except Exception as e:
            logger.warning(f"Fuzzy matching failed: {e}")
        
        # Fallback to rule-based categorization
        return self._rule_based_categorization(merchant_lower)
    
    def _rule_based_categorization(self, merchant_lower: str) -> str:
        """Rule-based categorization as fallback."""
        # Food & Dining
        food_keywords = ['swiggy', 'zomato', 'restaurant', 'pizza', 'burger', 'food', 'dining', 'cafe']
        if any(keyword in merchant_lower for keyword in food_keywords):
            return 'Food & Dining'
        
        # Travel & Transport
        travel_keywords = ['uber', 'ola', 'rapido', 'bus', 'metro', 'train', 'flight', 'travel']
        if any(keyword in merchant_lower for keyword in travel_keywords):
            return 'Travel & Transport'
        
        # Entertainment
        entertainment_keywords = ['netflix', 'prime', 'hotstar', 'cinema', 'movie', 'streaming', 'entertainment']
        if any(keyword in merchant_lower for keyword in entertainment_keywords):
            return 'Entertainment'
        
        # Utilities - Telecom
        telecom_keywords = ['airtel', 'jio', 'vodafone', 'bsnl', 'mobile', 'phone', 'internet']
        if any(keyword in merchant_lower for keyword in telecom_keywords):
            return 'Utilities - Telecom'
        
        # Shopping
        shopping_keywords = ['amazon', 'flipkart', 'myntra', 'shop', 'store', 'mall', 'retail']
        if any(keyword in merchant_lower for keyword in shopping_keywords):
            return 'Shopping'
        
        # Banking
        banking_keywords = ['hdfc', 'sbi', 'icici', 'axis', 'kotak', 'bank', 'atm']
        if any(keyword in merchant_lower for keyword in banking_keywords):
            return 'Banking'
        
        # Healthcare
        healthcare_keywords = ['pharmacy', 'hospital', 'clinic', 'medical', 'health', 'doctor']
        if any(keyword in merchant_lower for keyword in healthcare_keywords):
            return 'Healthcare'
        
        # Education
        education_keywords = ['school', 'college', 'university', 'education', 'course', 'training']
        if any(keyword in merchant_lower for keyword in education_keywords):
            return 'Education'
        
        # Real Estate
        real_estate_keywords = ['housing', 'property', 'real estate', 'rent', 'accommodation']
        if any(keyword in merchant_lower for keyword in real_estate_keywords):
            return 'Real Estate'
        
        # Insurance
        insurance_keywords = ['insurance', 'policy', 'lic', 'premium']
        if any(keyword in merchant_lower for keyword in insurance_keywords):
            return 'Insurance'
        
        # Investment
        investment_keywords = ['investment', 'mutual fund', 'stock', 'trading', 'portfolio']
        if any(keyword in merchant_lower for keyword in investment_keywords):
            return 'Investment'
        
        # Digital Payments
        payment_keywords = ['paytm', 'phonepe', 'google pay', 'upi', 'digital payment']
        if any(keyword in merchant_lower for keyword in payment_keywords):
            return 'Digital Payments'
        
        # Salary and Income
        salary_keywords = ['salary', 'payroll', 'income', 'company']
        if any(keyword in merchant_lower for keyword in salary_keywords):
            return 'Salary'
        
        # Rent
        rent_keywords = ['rent', 'landlord', 'property owner']
        if any(keyword in merchant_lower for keyword in rent_keywords):
            return 'Rent'
        
        # Family Transfer
        transfer_keywords = ['family', 'transfer', 'home transfer']
        if any(keyword in merchant_lower for keyword in transfer_keywords):
            return 'Family Transfer'
        
        # Loan EMI
        loan_keywords = ['loan', 'emi', 'mortgage']
        if any(keyword in merchant_lower for keyword in loan_keywords):
            return 'Loan EMI'
        
        # Credit Card Payment
        cc_keywords = ['credit card', 'cc payment']
        if any(keyword in merchant_lower for keyword in cc_keywords):
            return 'Credit Card Payment'
        
        return 'Others'
    
    def categorize_dataframe(self, df: pd.DataFrame, column: str = 'merchant_canonical') -> pd.DataFrame:
        """
        Categorize all merchants in a DataFrame.
        
        Args:
            df: DataFrame with merchant data
            column: Name of the merchant column
            
        Returns:
            DataFrame with added 'category' column
        """
        if df.empty or column not in df.columns:
            return df
        
        logger.info(f"Categorizing {len(df)} merchants")
        
        # Apply categorization to each merchant
        df['category'] = df[column].apply(self.categorize_merchant)
        
        # Log categorization distribution
        category_counts = df['category'].value_counts()
        logger.info(f"Category distribution: {category_counts.to_dict()}")
        
        return df
    
    def get_categorization_confidence(self, merchant_name: str) -> float:
        """
        Calculate confidence score for categorization.
        
        Args:
            merchant_name: Name of the merchant
            
        Returns:
            Confidence score between 0 and 1
        """
        if not merchant_name or pd.isna(merchant_name):
            return 0.0
        
        merchant_lower = str(merchant_name).lower().strip()
        
        # Direct mapping has highest confidence
        for key, category in self.mapping.items():
            if key.lower() in merchant_lower:
                return 1.0
        
        # Fuzzy matching confidence
        if self.fuzzy_available:
            try:
                best_match = process.extractOne(
                    merchant_lower, 
                    list(self.mapping.keys()),
                    scorer=fuzz.partial_ratio
                )
                
                if best_match:
                    return best_match[1] / 100.0
                    
            except Exception:
                pass
        
        # Rule-based categorization has lower confidence
        return 0.7
    
    def get_categorization_features(self, merchant_name: str) -> Dict[str, float]:
        """
        Extract features for ML-based categorization.
        
        Args:
            merchant_name: Name of the merchant
            
        Returns:
            Dictionary of features
        """
        if not merchant_name or pd.isna(merchant_name):
            return {"text_length": 0, "has_numbers": 0, "has_special_chars": 0}
        
        merchant_lower = str(merchant_name).lower().strip()
        
        features = {
            'text_length': len(merchant_lower),
            'has_numbers': float(any(c.isdigit() for c in merchant_lower)),
            'has_special_chars': float(any(c in '.-@#$%&*' for c in merchant_lower)),
            'has_food_keywords': float(any(k in merchant_lower for k in ['swiggy', 'zomato', 'restaurant', 'food'])),
            'has_travel_keywords': float(any(k in merchant_lower for k in ['uber', 'ola', 'travel', 'transport'])),
            'has_shopping_keywords': float(any(k in merchant_lower for k in ['amazon', 'flipkart', 'shop', 'store'])),
            'has_banking_keywords': float(any(k in merchant_lower for k in ['hdfc', 'sbi', 'icici', 'bank'])),
            'has_telecom_keywords': float(any(k in merchant_lower for k in ['airtel', 'jio', 'vodafone', 'mobile'])),
            'has_entertainment_keywords': float(any(k in merchant_lower for k in ['netflix', 'prime', 'cinema', 'movie'])),
            'has_healthcare_keywords': float(any(k in merchant_lower for k in ['pharmacy', 'hospital', 'medical', 'health'])),
            'has_education_keywords': float(any(k in merchant_lower for k in ['school', 'college', 'education', 'course'])),
            'has_insurance_keywords': float(any(k in merchant_lower for k in ['insurance', 'policy', 'lic'])),
            'has_investment_keywords': float(any(k in merchant_lower for k in ['investment', 'mutual', 'stock', 'trading'])),
            'has_payment_keywords': float(any(k in merchant_lower for k in ['paytm', 'phonepe', 'upi', 'payment'])),
            'has_salary_keywords': float(any(k in merchant_lower for k in ['salary', 'payroll', 'company'])),
            'has_rent_keywords': float(any(k in merchant_lower for k in ['rent', 'landlord', 'property'])),
            'has_loan_keywords': float(any(k in merchant_lower for k in ['loan', 'emi', 'mortgage']))
        }
        
        return features
    
    def get_categorization_summary(self, df: pd.DataFrame, category_column: str = 'category') -> Dict:
        """
        Get summary of categorization results.
        
        Args:
            df: DataFrame with category column
            category_column: Name of the category column
            
        Returns:
            Categorization summary dictionary
        """
        if category_column not in df.columns:
            return {"error": "No categorization data found"}
        
        summary = {
            "total_merchants": len(df),
            "unique_merchants": df['merchant_canonical'].nunique(),
            "category_distribution": df[category_column].value_counts().to_dict(),
            "category_percentage": (df[category_column].value_counts() / len(df) * 100).to_dict(),
            "unknown_count": len(df[df[category_column] == 'Unknown']),
            "unknown_percentage": len(df[df[category_column] == 'Unknown']) / len(df) * 100,
            "others_count": len(df[df[category_column] == 'Others']),
            "others_percentage": len(df[df[category_column] == 'Others']) / len(df) * 100
        }
        
        return summary


# Convenience function for backward compatibility
def categorize_merchant(merchant_name: str) -> str:
    """
    Legacy categorization function (kept for backward compatibility).
    
    Args:
        merchant_name: Name of the merchant
        
    Returns:
        Category name
    """
    mapper = MerchantMapper()
    return mapper.categorize_merchant(merchant_name) 