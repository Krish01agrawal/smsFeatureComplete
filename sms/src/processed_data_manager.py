#!/usr/bin/env python3
"""
Processed Data Manager
Handles storing and retrieving preprocessed transaction data for efficient caching.
"""

import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging
import os
import json

try:
    from .mongodb_connection_manager import mongodb_manager
except ImportError:
    from mongodb_connection_manager import mongodb_manager

# Configure logging
logger = logging.getLogger(__name__)

class ProcessedDataManager:
    """Manages storage and retrieval of processed transaction data in MongoDB."""
    
    def __init__(self, connection_string: str = None, database_name: str = None):
        """
        Initialize ProcessedDataManager.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Database name (default: pluto_money)
        """
        # Use PROCESSED_MONGODB_URI if available, otherwise fall back to MONGODB_URI
        self.connection_string = connection_string or os.getenv("PROCESSED_MONGODB_URI") or os.getenv("MONGODB_URI")
        self.database_name = database_name or os.getenv("PROCESSED_MONGODB_DB", "pluto_money")
        
        if not self.connection_string:
            raise ValueError("MongoDB connection string not provided")
        
        try:
            # Use the centralized connection manager with consistent ID
            connection_id = "processed_data_manager"
            self.client = mongodb_manager.get_connection(self.connection_string, connection_id)
            self.db = self.client[self.database_name]
            self.processed_collection = self.db[os.getenv("PROCESSED_COLLECTION_NAME", "processed_financial_transactions")]
            
            # Raw collection should use the original MongoDB URI (not processed URI)
            raw_connection_string = os.getenv("MONGODB_URI")
            if raw_connection_string and raw_connection_string != self.connection_string:
                # Use connection manager for raw data connection too
                raw_connection_id = "processed_data_manager_raw"
                self.raw_client = mongodb_manager.get_connection(raw_connection_string, raw_connection_id)
                self.raw_db = self.raw_client[os.getenv("MONGODB_DB", "pluto_money")]
                self.raw_collection = self.raw_db["user_financial_transactions"]
            else:
                # Same database for both raw and processed
                self.raw_collection = self.db["user_financial_transactions"]
            
            # Test connection
            self.client.admin.command('ping')
            collection_name = os.getenv("PROCESSED_COLLECTION_NAME", "processed_financial_transactions")
            logger.info(f"✅ Connected to MongoDB: {self.database_name}.{collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def store_processed_data(self, user_id: str, processed_df: pd.DataFrame, 
                           processing_metadata: Dict = None, force_clean_slate: bool = True) -> bool:
        """
        Store processed data for a specific user with clean slate processing.
        
        Args:
            user_id: User identifier
            processed_df: Preprocessed DataFrame
            processing_metadata: Metadata about the processing (optional)
            force_clean_slate: If True, completely removes all existing data before storing new data
            
        Returns:
            bool: Success status
        """
        if processed_df.empty:
            logger.warning(f"Empty DataFrame provided for user {user_id}")
            return False
        
        try:
            logger.info(f"🧹 CLEAN SLATE PROCESSING for user {user_id}: {len(processed_df)} transactions")
            
            if force_clean_slate:
                # STEP 1: Complete cleanup - remove ALL existing processed data for this user
                logger.info(f"🗑️ STEP 1: Removing ALL existing processed data for user {user_id}")
                delete_result = self.processed_collection.delete_many({"user_id": user_id})
                logger.info(f"✅ Cleaned {delete_result.deleted_count} existing processed records")
                
                # STEP 2: Verify cleanup
                remaining_count = self.processed_collection.count_documents({"user_id": user_id})
                if remaining_count > 0:
                    logger.warning(f"⚠️ Warning: {remaining_count} records still exist after cleanup")
                else:
                    logger.info(f"✅ STEP 2: Cleanup verified - 0 records remaining")
            
            # STEP 3: Convert DataFrame to clean records
            logger.info(f"🔄 STEP 3: Converting {len(processed_df)} transactions to MongoDB format")
            records = self._dataframe_to_mongodb_records(processed_df, user_id, processing_metadata)
            
            # STEP 4: Insert fresh processed data
            logger.info(f"💾 STEP 4: Storing {len(records)} fresh processed transactions")
            insert_result = self.processed_collection.insert_many(records)
            
            # STEP 5: Verify storage
            final_count = self.processed_collection.count_documents({"user_id": user_id})
            logger.info(f"✅ STEP 5: Storage verified - {final_count} records now in database")
            
            # Create index for efficient querying
            self._ensure_indexes()
            
            logger.info(f"🎉 CLEAN SLATE PROCESSING COMPLETED for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store processed data for user {user_id}: {e}")
            return False
    
    def get_processed_data(self, user_id: str, limit: int = None) -> Optional[pd.DataFrame]:
        """
        Retrieve processed data for a specific user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of records to retrieve
            
        Returns:
            pd.DataFrame or None if not found
        """
        try:
            logger.info(f"📥 Retrieving processed data for user {user_id}")
            
            # Build query - FIXED: Use proper field selection
            query = {"user_id": user_id}
            cursor = self.processed_collection.find(query).sort("transaction_date", -1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            records = list(cursor)
            
            if not records:
                logger.info(f"No processed data found for user {user_id}")
                return None
            
            logger.info(f"✅ Retrieved {len(records)} processed records for user {user_id}")
            
            # Convert back to DataFrame
            df = self._mongodb_records_to_dataframe(records)
            
            logger.info(f"✅ Retrieved {len(df)} processed transactions for user {user_id}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve processed data for user {user_id}: {e}")
            return None
    
    def get_processing_status(self, user_id: str = None) -> Dict[str, Any]:
        """
        Get processing status for users.
        
        Args:
            user_id: Specific user ID (optional, if None returns all users)
            
        Returns:
            Dictionary with processing status information
        """
        try:
            if user_id:
                # Status for specific user
                processed_count = self.processed_collection.count_documents({"user_id": user_id})
                raw_count = self.raw_collection.count_documents({"user_id": user_id})
                
                # Get latest processing timestamp
                latest_processed = self.processed_collection.find_one(
                    {"user_id": user_id}, 
                    sort=[("processed_at", -1)]
                )
                
                return {
                    "user_id": user_id,
                    "raw_transactions": raw_count,
                    "processed_transactions": processed_count,
                    "processing_coverage": f"{(processed_count/raw_count*100):.1f}%" if raw_count > 0 else "0%",
                    "last_processed": latest_processed.get("processed_at") if latest_processed else None,
                    "needs_processing": processed_count == 0 or processed_count < raw_count
                }
            else:
                # Status for all users
                pipeline = [
                    {"$group": {"_id": "$user_id", "processed_count": {"$sum": 1}}},
                    {"$sort": {"processed_count": -1}}
                ]
                
                processed_users = list(self.processed_collection.aggregate(pipeline))
                
                # Get raw data counts
                raw_pipeline = [
                    {"$group": {"_id": "$user_id", "raw_count": {"$sum": 1}}},
                    {"$sort": {"raw_count": -1}}
                ]
                
                raw_users = list(self.raw_collection.aggregate(raw_pipeline))
                
                # Combine data
                user_status = {}
                
                # Add processed counts
                for user in processed_users:
                    user_id = user["_id"]
                    user_status[user_id] = {
                        "processed_transactions": user["processed_count"],
                        "raw_transactions": 0
                    }
                
                # Add raw counts
                for user in raw_users:
                    user_id = user["_id"]
                    if user_id not in user_status:
                        user_status[user_id] = {"processed_transactions": 0}
                    user_status[user_id]["raw_transactions"] = user["raw_count"]
                
                # Calculate coverage
                for user_id, status in user_status.items():
                    raw = status["raw_transactions"]
                    processed = status["processed_transactions"]
                    status["processing_coverage"] = f"{(processed/raw*100):.1f}%" if raw > 0 else "0%"
                    status["needs_processing"] = processed == 0 or processed < raw
                
                return {
                    "total_users": len(user_status),
                    "users_with_processed_data": len([u for u in user_status.values() if u["processed_transactions"] > 0]),
                    "users_needing_processing": len([u for u in user_status.values() if u["needs_processing"]]),
                    "user_details": user_status
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get processing status: {e}")
            return {}
    
    def _dataframe_to_mongodb_records(self, df: pd.DataFrame, user_id: str, 
                                    processing_metadata: Dict = None) -> List[Dict]:
        """Convert DataFrame to MongoDB-compatible records."""
        records = []
        
        # Add processing metadata
        base_metadata = {
            "user_id": user_id,
            "processed_at": datetime.now(timezone.utc),
            "processing_version": "2.0",  # FIXED: Updated to latest version
            "total_records": len(df)
        }
        
        # Merge processing metadata from preprocessing (takes priority)
        if processing_metadata:
            base_metadata.update(processing_metadata)
            # Ensure processed_at is always current
            base_metadata["processed_at"] = datetime.now(timezone.utc)
        
        for idx, row in df.iterrows():
            record = {}
            
            for column, value in row.items():
                # CRITICAL FIX: Skip _id field to prevent duplicate key errors
                if column == '_id':
                    continue
                    
                # Handle different data types for MongoDB compatibility
                try:
                    # CRITICAL FIX: Handle array/complex values that break pd.isna()
                    if hasattr(value, '__len__') and not isinstance(value, (str, bytes)):
                        # Handle arrays, lists, or complex objects
                        if len(value) == 0:
                            record[column] = None
                        else:
                            record[column] = str(value)  # Convert complex objects to string
                    elif pd.isna(value):
                        record[column] = None
                    elif isinstance(value, (np.integer, int)):
                        record[column] = int(value)
                    elif isinstance(value, (np.floating, float)):
                        if np.isfinite(value):
                            record[column] = float(value)
                        else:
                            record[column] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        record[column] = value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value
                    elif isinstance(value, bool):
                        record[column] = bool(value)
                    elif isinstance(value, str):
                        record[column] = str(value)
                    else:
                        # Convert other types to string
                        record[column] = str(value)
                except Exception as e:
                    # FALLBACK: If any conversion fails, convert to string
                    logger.warning(f"Data conversion failed for column '{column}', value '{value}': {e}")
                    record[column] = str(value) if value is not None else None
            
            # Add metadata to each record
            record.update(base_metadata)
            records.append(record)
        
        return records
    
    def _mongodb_records_to_dataframe(self, records: List[Dict]) -> pd.DataFrame:
        """Convert MongoDB records back to DataFrame."""
        if not records:
            return pd.DataFrame()
        
        # Remove MongoDB-specific fields
        clean_records = []
        for record in records:
            clean_record = {k: v for k, v in record.items() 
                          if k not in ['_id', 'processed_at', 'processing_version', 'total_records']}
            clean_records.append(clean_record)
        
        df = pd.DataFrame(clean_records)
        
        # Restore data types
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Restore boolean columns
        bool_columns = ['is_weekend', 'is_salary', 'is_recurring']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        
        return df
    
    def _ensure_indexes(self):
        """Ensure proper indexes exist for efficient querying."""
        try:
            # Index on user_id for fast user-specific queries
            self.processed_collection.create_index("user_id")
            
            # Compound index on user_id and transaction_date for sorted queries
            self.processed_collection.create_index([("user_id", 1), ("transaction_date", -1)])
            
            # Index on processed_at for maintenance queries
            self.processed_collection.create_index("processed_at")
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    def delete_processed_data(self, user_id: str) -> bool:
        """
        Delete processed data for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: Success status
        """
        try:
            result = self.processed_collection.delete_many({"user_id": user_id})
            logger.info(f"🗑️  Deleted {result.deleted_count} processed records for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete processed data for user {user_id}: {e}")
            return False
    
    def get_all_users_with_raw_data(self) -> List[str]:
        """Get list of all users who have raw transaction data."""
        try:
            users = self.raw_collection.distinct("user_id")
            logger.info(f"Found {len(users)} users with raw transaction data")
            return users
        except Exception as e:
            logger.error(f"❌ Failed to get users list: {e}")
            return []
    
    def close(self):
        """Close MongoDB connection."""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")
