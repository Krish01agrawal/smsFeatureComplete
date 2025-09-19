"""
MongoDB data loader for SMS transaction analysis.
Handles connection, data retrieval, and database optimization.
"""

import os
import pandas as pd
import ssl
from pymongo import MongoClient
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta
import json

try:
    from .config import get_config
    from .mongodb_connection_manager import mongodb_manager
except ImportError:
    from config import get_config
    from mongodb_connection_manager import mongodb_manager

# Configure logging
logger = logging.getLogger(__name__)


class MongoDBLoader:
    """Advanced MongoDB loader with connection pooling and optimization."""
    
    def __init__(self, connection_string: Optional[str] = None, database_name: Optional[str] = None, 
                 collection_name: Optional[str] = None, prefer_processed_data: bool = True):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string. If None, uses environment variable MONGODB_URI
            database_name: Database name. If None, tries to detect from connection string or uses default
            collection_name: Collection name. If None, uses default 'financial_transactions'
            prefer_processed_data: Whether to prefer processed data over raw data when available
        """
        self.connection_string = connection_string or os.getenv('MONGODB_URI')
        if not self.connection_string:
            raise ValueError("MongoDB connection string not provided")
        
        # Configuration
        self.connection_pool_size = get_config('database.connection_pool_size', 10)
        self.max_connection_lifetime = get_config('database.max_connection_lifetime', 3600)
        self.index_creation_enabled = get_config('database.index_creation_enabled', True)
        self.batch_write_size = get_config('database.batch_write_size', 1000)
        self.prefer_processed_data = prefer_processed_data
        
        # Initialize connection
        self._init_connection()
        
        # Determine database name
        if database_name:
            self.db_name = database_name
        else:
            # Try to extract database name from connection string
            if 'mongodb://localhost' in self.connection_string:
                # For local MongoDB, try common database names
                self.db_name = 'pluto_money'  # Default
            else:
                # For Atlas, extract from connection string
                self.db_name = 'pluto_money'  # Default
        
        # Determine collection name
        self.collection_name = collection_name or 'user_financial_transactions'
        
        # Initialize database and collection references (lazy loading)
        self._db = None
        self._collection = None
        self._processed_collection = None
        
        # Initialize ProcessedDataManager if we prefer processed data
        self.processed_data_manager = None
        if self.prefer_processed_data:
            try:
                try:
                    from .processed_data_manager import ProcessedDataManager
                except ImportError:
                    from processed_data_manager import ProcessedDataManager
                
                self.processed_data_manager = ProcessedDataManager(
                    connection_string=self.connection_string,
                    database_name=self.db_name
                )
                logger.info("✅ ProcessedDataManager initialized for smart data loading")
            except Exception as e:
                logger.warning(f"⚠️  ProcessedDataManager initialization failed: {e}")
                self.prefer_processed_data = False
        
        # Create indexes if enabled
        if self.index_creation_enabled:
            self._create_indexes()
        
        logger.info(f"MongoDB loader initialized for {self.db_name}.{self.collection_name}")
    
    def _init_connection(self):
        """Initialize MongoDB connection using the centralized connection manager."""
        try:
            # Use the centralized connection manager with consistent ID
            connection_id = "mongodb_loader"
            self.client = mongodb_manager.get_connection(self.connection_string, connection_id)
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for optimal performance."""
        try:
            collection = self.collection
            
            # Create indexes for common query patterns
            indexes = [
                # User-based queries
                [("user_id", 1)],
                [("user_id", 1), ("transaction_date", -1)],
                [("user_id", 1), ("amount", -1)],
                
                # Date-based queries
                [("transaction_date", -1)],
                [("transaction_date", 1)],
                
                # Merchant-based queries
                [("merchant_canonical", 1)],
                [("user_id", 1), ("merchant_canonical", 1)],
                
                # Amount-based queries
                [("amount", -1)],
                [("user_id", 1), ("amount", -1)],
                
                # Transaction type queries
                [("transaction_type", 1)],
                [("user_id", 1), ("transaction_type", 1)],
                
                # Composite indexes for complex queries
                [("user_id", 1), ("transaction_date", -1), ("amount", -1)],
                [("user_id", 1), ("merchant_canonical", 1), ("transaction_date", -1)]
            ]
            
            # Create each index
            for index_spec in indexes:
                try:
                    collection.create_index(index_spec, background=True)
                    logger.debug(f"Index created: {index_spec}")
                except Exception as e:
                    logger.warning(f"Index creation failed for {index_spec}: {e}")
            
            logger.info("Database indexes created/verified")
            
        except Exception as e:
            logger.warning(f"Index creation failed: {e}")
    
    @property
    def db(self):
        """Lazy load database."""
        if self._db is None:
            self._db = self.client[self.db_name]
        return self._db
    
    @property
    def collection(self):
        """Lazy load collection."""
        if self._collection is None:
            self._collection = self.db[self.collection_name]
        return self._collection
    
    def test_collection_access(self):
        """Test access to the specific database and collection."""
        try:
            doc_count = self.collection.count_documents({})
            print(f"✅ Connected to database '{self.db_name}', collection '{self.collection_name}' with {doc_count} documents")
            return True, doc_count
        except Exception as e:
            print(f"⚠️ Warning: Could not access collection '{self.collection_name}': {e}")
            print(f"Available databases: {self.client.list_database_names()}")
            if self.db_name in self.client.list_database_names():
                available_collections = self.db.list_collection_names()
                print(f"Available collections in '{self.db_name}': {available_collections}")
            return False, str(e)
    
    def get_user_transactions(self, user_id: str, limit: Optional[int] = None, 
                            force_raw_data: bool = False, 
                            check_freshness: bool = True) -> pd.DataFrame:
        """
        Get transactions for a specific user, with intelligent data freshness checking.
        
        Args:
            user_id: User ID to fetch transactions for
            limit: Maximum number of transactions to return (None for all)
            force_raw_data: Force loading from raw collection instead of processed
            check_freshness: Check if processed data is fresh before using it
            
        Returns:
            DataFrame with user transactions (fresh processed if available, raw otherwise)
        """
        # Check data freshness if enabled
        if check_freshness and self.prefer_processed_data and not force_raw_data:
            try:
                from .data_freshness_manager import data_freshness_manager
                
                freshness_result = data_freshness_manager.check_data_freshness(user_id)
                recommendation = freshness_result.get("recommendation")
                
                if recommendation in ["reprocess_required", "force_reprocess"]:
                    logger.warning(f"🔄 Processed data for user {user_id} is stale - {freshness_result['freshness_status']['reason']}")
                    
                    # Invalidate stale processed data
                    data_freshness_manager.invalidate_processed_data(user_id)
                    
                    # Force raw data loading for reprocessing
                    force_raw_data = True
                    logger.info(f"🚀 Forcing raw data load for user {user_id} due to staleness")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error checking data freshness for user {user_id}: {e}")
        
        # Try to get processed data first (if enabled and not forced to use raw)
        if self.prefer_processed_data and self.processed_data_manager and not force_raw_data:
            try:
                processed_df = self.processed_data_manager.get_processed_data(user_id, limit)
                if processed_df is not None and not processed_df.empty:
                    logger.info(f"✅ Using fresh processed data for user {user_id}: {len(processed_df)} transactions")
                    return processed_df
                else:
                    logger.info(f"📥 No processed data found for user {user_id}, falling back to raw data")
            except Exception as e:
                logger.warning(f"⚠️  Error accessing processed data for user {user_id}: {e}")
        
        # Fall back to raw data
        try:
            # Build query
            query = {"user_id": user_id}
            
            # Execute query with limit
            if limit:
                cursor = self.collection.find(query).limit(limit)
            else:
                cursor = self.collection.find(query)
            
            # Convert to list
            transactions = list(cursor)
            
            if not transactions:
                logger.info(f"No transactions found for user: {user_id}")
                return pd.DataFrame()
            
            logger.info(f"📥 Using raw data for user {user_id}: {len(transactions)} transactions")
            
            # Flatten nested structures to make them compatible with pandas
            flattened_transactions = []
            for transaction in transactions:
                flattened = {}
                for key, value in transaction.items():
                    if isinstance(value, dict):
                        # Special handling for BSON Date objects
                        if '$date' in value:
                            # Extract the actual date string from BSON Date
                            flattened[key] = value['$date']
                        else:
                            # Convert other nested dictionaries to string representation
                            flattened[key] = str(value)
                    elif isinstance(value, list):
                        # Convert lists to string representation
                        flattened[key] = str(value)
                    else:
                        flattened[key] = value
                flattened_transactions.append(flattened)
            
            # Convert MongoDB documents to DataFrame
            df = pd.DataFrame(flattened_transactions)
            
            # Convert ObjectId to string for better compatibility
            if '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            
            logger.info(f"Retrieved {len(df)} transactions for user: {user_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving transactions for user {user_id}: {e}")
            return pd.DataFrame()
    
    def get_all_transactions(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get all transactions from the collection.
        
        Args:
            limit: Maximum number of transactions to return
            
        Returns:
            DataFrame with all transactions
        """
        try:
            # Execute query with limit
            if limit:
                cursor = self.collection.find().limit(limit)
            else:
                cursor = self.collection.find()
            
            # Convert to list
            transactions = list(cursor)
            
            if not transactions:
                logger.info("No transactions found in collection")
                return pd.DataFrame()
            
            # Flatten nested structures
            flattened_transactions = []
            for transaction in transactions:
                flattened = {}
                for key, value in transaction.items():
                    if isinstance(value, dict):
                        # Special handling for BSON Date objects
                        if '$date' in value:
                            # Extract the actual date string from BSON Date
                            flattened[key] = value['$date']
                        else:
                            # Convert other nested dictionaries to string representation
                            flattened[key] = str(value)
                    elif isinstance(value, list):
                        # Convert lists to string representation
                        flattened[key] = str(value)
                    else:
                        flattened[key] = value
                flattened_transactions.append(flattened)
            
            # Convert to DataFrame
            df = pd.DataFrame(flattened_transactions)
            
            # Convert ObjectId to string
            if '_id' in df.columns:
                df['_id'] = df['_id'].astype(str)
            
            logger.info(f"Retrieved {len(df)} transactions from collection")
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving all transactions: {e}")
            return pd.DataFrame()
    
    def discover_databases_and_collections(self) -> Dict[str, List[str]]:
        """Discover available databases and collections."""
        try:
            databases = {}
            for db_name in self.client.list_database_names():
                if db_name not in ['admin', 'local', 'config']:  # Skip system databases
                    db = self.client[db_name]
                    collections = db.list_collection_names()
                    databases[db_name] = collections
            
            return databases
        except Exception as e:
            logger.error(f"Error discovering databases: {e}")
            return {}
    
    def find_financial_data(self) -> Dict[str, Any]:
        """Find collections that might contain financial data."""
        try:
            financial_collections = {}
            
            for db_name in self.client.list_database_names():
                if db_name not in ['admin', 'local', 'config']:
                    db = self.client[db_name]
                    
                    for collection_name in db.list_collection_names():
                        # Sample a few documents to check if it's financial data
                        sample_docs = list(db[collection_name].find().limit(5))
                        
                        if sample_docs:
                            # Check for financial indicators
                            financial_indicators = ['amount', 'transaction', 'payment', 'balance', 'credit', 'debit']
                            doc_text = str(sample_docs).lower()
                            
                            indicator_count = sum(1 for indicator in financial_indicators if indicator in doc_text)
                            
                            if indicator_count >= 2:  # At least 2 financial indicators
                                financial_collections[f"{db_name}.{collection_name}"] = {
                                    'document_count': db[collection_name].count_documents({}),
                                    'sample_fields': list(sample_docs[0].keys()) if sample_docs else [],
                                    'confidence_score': indicator_count / len(financial_indicators)
                                }
            
            return financial_collections
        except Exception as e:
            logger.error(f"Error finding financial data: {e}")
            return {}
    
    def auto_discover_financial_collection(self) -> bool:
        """Automatically discover and set the correct financial collection."""
        try:
            financial_data = self.find_financial_data()
            
            if not financial_data:
                logger.warning("No financial collections found")
                return False
            
            # Find the best collection (highest confidence score)
            best_collection = max(financial_data.items(), key=lambda x: x[1]['confidence_score'])
            db_collection = best_collection[0]
            confidence = best_collection[1]['confidence_score']
            
            if confidence >= 0.5:  # At least 50% confidence
                db_name, collection_name = db_collection.split('.', 1)
                
                # Update the loader
                self.db_name = db_name
                self.collection_name = collection_name
                self._db = None
                self._collection = None
                
                logger.info(f"Auto-discovered financial collection: {db_name}.{collection_name} (confidence: {confidence:.2f})")
                
                # Test access
                success, doc_count = self.test_collection_access()
                if success:
                    # Create indexes for the new collection
                    if self.index_creation_enabled:
                        self._create_indexes()
                    return True
                else:
                    logger.error("Auto-discovered collection access failed")
                    return False
            else:
                logger.warning(f"Best collection confidence too low: {confidence:.2f}")
                return False
                
        except Exception as e:
            logger.error(f"Auto-discovery failed: {e}")
            return False
    
    def set_database_and_collection(self, database_name: str, collection_name: str) -> bool:
        """Manually set database and collection names."""
        try:
            self.db_name = database_name
            self.collection_name = collection_name
            self._db = None
            self._collection = None
            
            # Test access
            success, doc_count = self.test_collection_access()
            if success:
                # Create indexes for the new collection
                if self.index_creation_enabled:
                    self._create_indexes()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error setting database/collection: {e}")
            return False
    
    def get_available_users(self) -> List[str]:
        """Get list of available user IDs."""
        try:
            users = self.collection.distinct("user_id")
            logger.info(f"Found {len(users)} unique users")
            return users
        except Exception as e:
            logger.error(f"Error getting available users: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            stats = {
                'database': self.db_name,
                'collection': self.collection_name,
                'total_documents': self.collection.count_documents({}),
                'unique_users': len(self.get_available_users()),
                'date_range': {},
                'indexes': []
            }
            
            # Get date range
            pipeline = [
                {"$group": {
                    "_id": None,
                    "min_date": {"$min": "$transaction_date"},
                    "max_date": {"$max": "$transaction_date"}
                }}
            ]
            
            date_result = list(self.collection.aggregate(pipeline))
            if date_result:
                stats['date_range'] = {
                    'earliest': str(date_result[0]['min_date']),
                    'latest': str(date_result[0]['max_date'])
                }
            
            # Get index information
            index_info = self.collection.index_information()
            stats['indexes'] = [name for name in index_info.keys()]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def debug_mongodb_connection(self) -> str:
        """Debug MongoDB connection and return status."""
        try:
            # Test basic connection
            self.client.admin.command('ping')
            
            # Test database access
            db_names = self.client.list_database_names()
            
            # Test collection access
            success, doc_count = self.test_collection_access()
            
            if success:
                # Get collection stats
                stats = self.get_collection_stats()
                
                debug_info = f"""
✅ MongoDB Connection Status:
- Connection: Successful
- Available Databases: {len(db_names)}
- Current Database: {self.db_name}
- Current Collection: {self.collection_name}
- Documents in Collection: {doc_count}
- Collection Stats: {json.dumps(stats, indent=2, default=str)}
                """
            else:
                debug_info = f"""
⚠️ MongoDB Connection Status:
- Connection: Successful
- Available Databases: {len(db_names)}
- Database Access: Failed
- Collection Access: Failed
                """
            
            return debug_info
            
        except Exception as e:
            return f"❌ MongoDB Connection Failed: {e}"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        try:
            self.client.close()
        except Exception as e:
            logger.warning(f"Error closing MongoDB connection: {e}")


# Convenience function for backward compatibility
def get_user_transactions(user_id: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Get transactions for a user (backward compatibility)."""
    with MongoDBLoader() as loader:
        return loader.get_user_transactions(user_id, limit) 