"""
Data loading module for SMS transaction analysis.
Handles loading from MongoDB and local JSON files.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, List
import os
from dotenv import load_dotenv

# Import MongoDB loader
try:
    from .mongodb_loader import MongoDBLoader
except ImportError:
    from mongodb_loader import MongoDBLoader

# Load environment variables
load_dotenv()


class DataLoader:
    """Centralized data loading class with error handling and validation."""
    
    def __init__(self):
        self.mongodb_uri = os.getenv('MONGODB_URI')
        # Initialize MongoDB loader for reuse - create once, reuse always
        self._mongodb_loader = None
        self._init_mongodb_loader()
    
    def _init_mongodb_loader(self):
        """Initialize MongoDB loader once and reuse the connection."""
        if self._mongodb_loader is None and self.mongodb_uri:
            try:
                self._mongodb_loader = MongoDBLoader()
                print("✅ MongoDB loader initialized and connection cached")
            except Exception as e:
                print(f"⚠️ Failed to initialize MongoDB loader: {e}")
                self._mongodb_loader = None
    
    def load_json(self, file_path: Path) -> pd.DataFrame:
        """
        Load transaction data from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            pandas DataFrame with transaction data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data)
            
            # Validate required columns
            required_columns = ['transaction_date', 'amount', 'merchant_canonical']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            return df
            
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON file: {e}")
    
    def load_from_mongodb(self, user_id: str, limit: Optional[int] = None) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Load user transactions from MongoDB.
        
        Args:
            user_id: The user ID to fetch transactions for
            limit: Maximum number of transactions to fetch
            
        Returns:
            Tuple of (DataFrame, error_message)
        """
        if not self.mongodb_uri:
            return pd.DataFrame(), "MongoDB URI not configured"
        
        try:
            # Use cached MongoDB loader instead of creating new instances
            if not self._mongodb_loader:
                return pd.DataFrame(), "MongoDB loader not initialized"
            
            mongo_loader = self._mongodb_loader
            
            # Try to load data with current settings
            try:
                df = mongo_loader.get_user_transactions(user_id, limit)
                if not df.empty:
                    return df, None
            except Exception as e:
                print(f"⚠️ Initial load failed: {e}")
            
            # If initial load failed, try auto-discovery
            print("🔍 Attempting to auto-discover correct database/collection...")
            if mongo_loader.auto_discover_financial_collection():
                try:
                    df = mongo_loader.get_user_transactions(user_id, limit)
                    if not df.empty:
                        return df, None
                except Exception as e:
                    print(f"⚠️ Auto-discovery load failed: {e}")
            
            # If still no data, return error
            return pd.DataFrame(), f"No transactions found for user: {user_id} after auto-discovery"
                
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    def debug_mongodb_connection(self):
        """Debug MongoDB connection and discover available data."""
        if not self.mongodb_uri:
            return "MongoDB URI not configured"
        
        try:
            # Use cached MongoDB loader instead of creating new instances
            if not self._mongodb_loader:
                return "MongoDB loader not initialized"
            
            mongo_loader = self._mongodb_loader
            print("🔍 MongoDB Connection Debug Info:")
            print(f"  📡 URI: {self.mongodb_uri}")
            print(f"  🗄️  Database: {mongo_loader.db_name}")
            print(f"  📄 Collection: {mongo_loader.collection_name}")
            
            # Discover available databases and collections
            mongo_loader.discover_databases_and_collections()
            
            # Try to find financial data
            mongo_loader.find_financial_data()
            
            return "Debug completed successfully"
                
        except Exception as e:
            return f"Debug failed: {str(e)}"
    
    def get_available_users(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of available users from MongoDB.
        
        Returns:
            Tuple of (user_list, error_message)
        """
        if not self.mongodb_uri:
            return [], "MongoDB URI not configured"
        
        try:
            # Use cached MongoDB loader instead of creating new instances
            if not self._mongodb_loader:
                return [], "MongoDB loader not initialized"
            
            mongo_loader = self._mongodb_loader
            
            # Try to get users with current settings
            try:
                users = mongo_loader.collection.distinct("user_id")
                if users:
                    return users, None
            except Exception as e:
                print(f"⚠️ Initial user fetch failed: {e}")
            
            # If initial fetch failed, try auto-discovery
            print("🔍 Attempting to auto-discover correct database/collection for users...")
            if mongo_loader.auto_discover_financial_collection():
                try:
                    users = mongo_loader.collection.distinct("user_id")
                    if users:
                        return users, None
                except Exception as e:
                    print(f"⚠️ Auto-discovery user fetch failed: {e}")
            
            # If still no users, return error
            return [], "No users found after auto-discovery"
                
        except Exception as e:
            return [], str(e)
    
    def cleanup(self):
        """Clean up MongoDB connection when done."""
        if self._mongodb_loader:
            try:
                # The connection manager will handle the actual cleanup
                self._mongodb_loader = None
                print("✅ MongoDB loader connection cleaned up")
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate loaded transaction data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        if df.empty:
            issues.append("DataFrame is empty")
            return False, issues
        
        # Check required columns
        required_columns = ['transaction_date', 'amount', 'merchant_canonical']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check data types
        if 'amount' in df.columns and not pd.api.types.is_numeric_dtype(df['amount']):
            issues.append("Amount column is not numeric")
        
        if 'transaction_date' in df.columns:
            try:
                pd.to_datetime(df['transaction_date'])
            except:
                issues.append("Transaction date column cannot be parsed as datetime")
        
        # Check for null values in critical columns
        critical_columns = ['amount', 'merchant_canonical']
        for col in critical_columns:
            if col in df.columns and df[col].isnull().sum() > 0:
                null_count = df[col].isnull().sum()
                issues.append(f"Column '{col}' has {null_count} null values")
        
        return len(issues) == 0, issues


# Convenience functions for backward compatibility
def load_json(file_path: Path) -> pd.DataFrame:
    """Legacy function to load JSON file (kept for backward compatibility)"""
    loader = DataLoader()
    return loader.load_json(file_path)


def load_from_mongodb(user_id: str, limit: Optional[int] = None) -> Tuple[pd.DataFrame, Optional[str]]:
    """Legacy function to load from MongoDB (kept for backward compatibility)"""
    loader = DataLoader()
    return loader.load_from_mongodb(user_id, limit)


def get_available_users() -> Tuple[List[str], Optional[str]]:
    """Legacy function to get available users (kept for backward compatibility)"""
    loader = DataLoader()
    return loader.get_available_users()
