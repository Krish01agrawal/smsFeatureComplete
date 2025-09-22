#!/usr/bin/env python3
"""
MongoDB Operations for LifafaV0
===============================

Handles MongoDB operations for:
1. Reading SMS data from sms_data collection
2. Storing processed financial transactions in financial_transactions collection
3. Managing user-specific data and batch processing
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, BulkWriteError
import logging
from pymongo import UpdateOne, InsertOne

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MongoDBOperations:
    """MongoDB operations for LifafaV0 financial data pipeline"""
    
    def __init__(self, connection_string: str = None, db_name: str = None):
        """Initialize MongoDB connection with connection pooling and retry mechanism"""
        # Use environment variable or default
        if connection_string is None:
            connection_string = os.getenv('MONGODB_URI', 'mongodb+srv://divyamverma:geMnO2HtgXwOrLsW@cluster0.gzbouvi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        
        if db_name is None:
            db_name = os.getenv('MONGODB_DB', 'pluto_money')
        
        self.connection_string = connection_string
        self.db_name = db_name
        
        # Retry configuration for network resilience
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        self._connect_with_retry()
    
    def _connect_with_retry(self):
        """Connect to MongoDB with retry mechanism for network resilience"""
        import time
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 MongoDB connection attempt {attempt + 1}/{self.max_retries}")
                
                # Enhanced connection with pooling and optimization
                self.client = MongoClient(
                    self.connection_string,
                    maxPoolSize=50,           # Maximum connections in pool
                    minPoolSize=10,           # Minimum connections to maintain
                    maxIdleTimeMS=30000,      # Close idle connections after 30s
                    waitQueueTimeoutMS=5000,  # Wait up to 5s for available connection
                    retryWrites=True,         # Retry write operations on failure
                    retryReads=True,          # Retry read operations on failure
                    serverSelectionTimeoutMS=10000,  # Increased server selection timeout
                    connectTimeoutMS=15000,   # Increased connection timeout
                    socketTimeoutMS=30000,    # Socket timeout
                    heartbeatFrequencyMS=10000,  # Heartbeat frequency
                    appName="LifafaV0-SMS-Processor",  # Application identifier
                    tlsAllowInvalidCertificates=True  # Fix SSL certificate issues
                )
                
                self.db = self.client[self.db_name]
                
                # Collections
                self.sms_collection = self.db['sms_data']  # Raw SMS (never modified)
                self.fin_raw_collection = self.db['sms_fin_rawdata']  # Financial SMS with processing status
                self.transactions_collection = self.db['financial_transactions']  # Final processed results
                
                # Test connection with timeout
                self.client.admin.command('ping')
                logger.info(f"✅ Connected to MongoDB: {self.connection_string}")
                logger.info(f"✅ Database: {self.db_name}")
                logger.info(f"🔗 Connection pool: max={50}, min={10}")
                
                # Create indexes
                self._create_indexes()
                return  # Success, exit retry loop
                
            except Exception as e:
                logger.warning(f"⚠️ MongoDB connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"🔄 Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ MongoDB connection failed after {self.max_retries} attempts")
                    raise
    
    def _ensure_connection(self):
        """Ensure MongoDB connection is alive, reconnect if needed"""
        try:
            # Test if connection is still alive
            self.client.admin.command('ping')
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection lost, attempting to reconnect: {e}")
            self._connect_with_retry()
    
    def _create_indexes(self):
        """Create advanced database indexes for optimal performance"""
        try:
            # SMS data collection indexes
            self._create_index_safe(self.sms_collection, [("user_id", 1)])
            self._create_index_safe(self.sms_collection, [("timestamp", -1)])
            self._create_index_safe(self.sms_collection, [("date", -1)])
            self._create_index_safe(self.sms_collection, [("sender", 1)])
            
            # Text search index for SMS content analysis
            self._create_index_safe(self.sms_collection, [("body", "text")])
            
            # Financial raw data collection indexes
            # Drop legacy unique index on unique_id if it exists (it aborts bulk writes across runs)
            try:
                for idx in self.fin_raw_collection.list_indexes():
                    # Detect legacy single-field unique index
                    if idx.get('unique') and idx.get('key') == {'unique_id': 1}:
                        self.fin_raw_collection.drop_index(idx['name'])
                        logger.info(f"🧹 Dropped legacy unique index on unique_id: {idx['name']}")
            except Exception as e:
                logger.warning(f"⚠️  Could not inspect/drop legacy unique index: {e}")

            # Keep unique_id indexed but NOT unique; enforce uniqueness using stable fields below
            self._create_index_safe(self.fin_raw_collection, [("unique_id", 1)])
            self._create_index_safe(self.fin_raw_collection, [("isprocessed", 1)])
            self._create_index_safe(self.fin_raw_collection, [("user_id", 1)])
            self._create_index_safe(self.fin_raw_collection, [("phone", 1)])  # 🚀 NEW: Phone-based filtering
            self._create_index_safe(self.fin_raw_collection, [("processing_timestamp", -1)])
            self._create_index_safe(self.fin_raw_collection, [("processing_status", 1)])
            
            # Compound indexes for common query patterns
            self._create_index_safe(self.fin_raw_collection, [
                ("user_id", 1), 
                ("isprocessed", 1), 
                ("processing_timestamp", -1)
            ])

            # Enforce true de-duplication per user: body + sender + date + user_id
            self._create_index_safe(
                self.fin_raw_collection,
                [("user_id", 1), ("sender", 1), ("date", 1), ("body", 1)],
                unique=True,
                name="uniq_user_sender_date_body"
            )
            
            # Financial transactions collection indexes  
            self._create_index_safe(self.transactions_collection, [("unique_id", 1)], unique=True)
            self._create_index_safe(self.transactions_collection, [("user_id", 1)])
            self._create_index_safe(self.transactions_collection, [("phone", 1)])  # 🚀 NEW: Phone-based filtering
            self._create_index_safe(self.transactions_collection, [("transaction_date", -1)])
            self._create_index_safe(self.transactions_collection, [("amount", 1)])
            self._create_index_safe(self.transactions_collection, [("transaction_type", 1)])
            self._create_index_safe(self.transactions_collection, [("message_intent", 1)])
            self._create_index_safe(self.transactions_collection, [("currency", 1)])

            # 🚀 FIXED: Use unique_id for duplicate prevention - consistent across all collections
            # Note: unique_id is already indexed above as unique=True
            
            # Compound indexes for common transaction queries
            self._create_index_safe(self.transactions_collection, [
                ("user_id", 1), 
                ("transaction_date", -1), 
                ("amount", 1)
            ])
            
            self._create_index_safe(self.transactions_collection, [
                ("user_id", 1), 
                ("transaction_type", 1), 
                ("transaction_date", -1)
            ])
            
            self._create_index_safe(self.transactions_collection, [
                ("message_intent", 1), 
                ("transaction_date", -1)
            ])
            
            # Partial index for active transactions (recent dates) - with unique name
            self._create_index_safe(
                self.transactions_collection,
                [("transaction_date", -1)],
                partialFilterExpression={"transaction_date": {"$gte": "2020-01-01"}},
                name="transaction_date_recent_partial"
            )
            
            # Create processing_checkpoints collection indexes
            self.db.processing_checkpoints.create_index("user_id")
            self.db.processing_checkpoints.create_index("batch_id")
            self.db.processing_checkpoints.create_index("status")
            self.db.processing_checkpoints.create_index("checkpoint_timestamp")
            self.db.processing_checkpoints.create_index([("user_id", 1), ("status", 1)])
            self.db.processing_checkpoints.create_index([("user_id", 1), ("batch_id", 1)])
            
            logger.info("✅ Advanced MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")
            # Don't raise - continue with existing indexes
    
    def _create_index_safe(self, collection, keys, **kwargs):
        """Safely create index, skip if already exists"""
        try:
            # Generate a unique name if not provided
            if 'name' not in kwargs:
                index_name = "_".join([f"{field}_{order}" for field, order in keys])
                kwargs['name'] = index_name
            
            # Check if index already exists
            existing_indexes = collection.list_indexes()
            for idx in existing_indexes:
                if idx['name'] == kwargs['name']:
                    logger.info(f"⏭️  Index {kwargs['name']} already exists, skipping")
                    return
            
            # Create the index
            collection.create_index(keys, **kwargs)
            logger.info(f"✅ Created index: {kwargs['name']}")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not create index {kwargs.get('name', 'unnamed')}: {e}")
            # Continue with other indexes
    
    def store_financial_raw_sms(self, financial_sms: List[Dict[str, Any]]) -> int:
        """Store financial SMS in sms_fin_rawdata collection"""
        try:
            if not financial_sms:
                return 0
            
            logger.info(f"🔄 Preparing {len(financial_sms)} financial SMS for storage...")
            
            # Prepare financial SMS for storage
            for i, sms in enumerate(financial_sms):
                # Remove MongoDB _id field to prevent duplicate key errors
                if '_id' in sms:
                    logger.debug(f"🗑️  Removing _id field from SMS {i+1}: {sms.get('unique_id', 'NO_ID')}")
                    del sms['_id']
                
                # 🚀 FIXED: Only use 'isprocessed' field (NOT 'is_processed')
                # 'is_processed' belongs only in sms_data collection
                # 'isprocessed' tracks LLM/rule-based processing in sms_fin_rawdata
                if 'isprocessed' not in sms:
                    sms['isprocessed'] = False
                if 'processing_timestamp' not in sms:
                    sms['processing_timestamp'] = None
                if 'processing_status' not in sms:
                    sms['processing_status'] = None
                
                # Remove 'is_processed' field if it exists (should not be in sms_fin_rawdata)
                if 'is_processed' in sms:
                    del sms['is_processed']
                    logger.debug(f"🗑️  Removed 'is_processed' field from SMS {sms.get('unique_id', 'NO_ID')}")
                
                if 'created_at' not in sms:
                    sms['created_at'] = datetime.now()
                if 'updated_at' not in sms:
                    sms['updated_at'] = datetime.now()
                
                logger.debug(f"✅ Prepared SMS {i+1}: {sms.get('unique_id', 'NO_ID')} for storage")
            
            # Use bulk operations for better performance
            bulk_operations = []
            for sms in financial_sms:
                # Use more stable fields for upsert matching to prevent duplicates
                # unique_id changes each time, so use body + sender + date instead
                match_criteria = {
                    "body": sms.get("body", ""),
                    "sender": sms.get("sender", ""),
                    "date": sms.get("date", ""),
                    "user_id": sms.get("user_id", "")
                }
                
                bulk_operations.append(
                    UpdateOne(
                        match_criteria,  # FIXED: Use stable fields instead of unique_id
                        {"$set": sms},
                        upsert=True
                    )
                )
            
            if bulk_operations:
                logger.info(f"📤 Executing bulk write operation for {len(bulk_operations)} SMS...")
                try:
                    result = self.fin_raw_collection.bulk_write(bulk_operations, ordered=False)
                    logger.info(f"💾 Successfully stored {len(financial_sms)} financial SMS in sms_fin_rawdata collection")
                    logger.info(f"📊 Bulk write result: {result.bulk_api_result}")
                    return len(financial_sms)
                except BulkWriteError as bwe:
                    details = getattr(bwe, 'details', {})
                    write_errors = details.get('writeErrors', [])
                    logger.error(f"❌ Bulk write encountered errors: {len(write_errors)} failures")
                    # Count partial success if available
                    stored = (details.get('nUpserted') or 0) + (details.get('nModified') or 0)
                    logger.info(f"💾 Partial success: {stored} SMS stored/updated before errors")
                    return stored
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error storing financial raw SMS: {e}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            if hasattr(e, 'details'):
                logger.error(f"📋 Error details: {e.details}")
            return 0
    
    def get_financial_raw_sms(self, user_id = None, unprocessed_only: bool = True, limit: int = None) -> List[Dict[str, Any]]:
        """Get financial SMS from sms_fin_rawdata collection"""
        try:
            from bson import ObjectId
            
            # Build query
            query = {}
            if user_id:
                # Convert to ObjectId if it's a string
                if isinstance(user_id, str):
                    try:
                        user_id = ObjectId(user_id)
                    except:
                        pass  # Keep as string if conversion fails
                query["user_id"] = user_id
            if unprocessed_only:
                query["isprocessed"] = {"$ne": True}
            
            # Execute query
            cursor = self.fin_raw_collection.find(query)
            
            if limit:
                cursor = cursor.limit(limit)
            
            sms_list = list(cursor)
            logger.info(f"📱 Retrieved {len(sms_list)} financial SMS from sms_fin_rawdata collection")
            return sms_list
            
        except Exception as e:
            logger.error(f"❌ Error retrieving financial raw SMS: {e}")
            return []
    
    def mark_sms_as_processed_in_main_collection(self, sms_id: str, user_id: str = None) -> bool:
        """Mark SMS as processed in main sms_data collection using SIMPLIFIED ID SYSTEM"""
        try:
            # 🚀 SIMPLIFIED APPROACH: Use sms_id field directly
            # sms_id should be in format: sms_000001, sms_000002, etc.
            
            # Extract simple SMS ID if needed
            simple_sms_id = sms_id
            if "_sms_" in sms_id:
                # Extract from long format: usr_abc123_sms_000001 → sms_000001
                parts = sms_id.split("_sms_")
                if len(parts) > 1:
                    number_part = parts[-1]
                    if not number_part.startswith("sms_"):
                        simple_sms_id = f"sms_{number_part}"
                    else:
                        simple_sms_id = number_part
            
            # Try multiple query patterns for compatibility
            queries = []
            
            if user_id:
                # 🚀 FIXED: Use ONLY sms_id + user_id
                queries.append({"sms_id": simple_sms_id, "user_id": user_id})
                # Fallback: Use pattern matching
                queries.append({
                    "unique_id": {"$regex": f".*_sms_{simple_sms_id.replace('sms_', '')}$"}, 
                    "user_id": user_id
                })
            else:
                queries.append({"sms_id": simple_sms_id})
                queries.append({"unique_id": sms_id})
            
            update_data = {
                "is_processed": True,
                "processed_at": datetime.now()
            }
            
            # Try each query until one works
            for query in queries:
                result = self.sms_collection.update_one(query, {"$set": update_data})
                
                if result.modified_count > 0:
                    logger.info(f"✅ Marked SMS {sms_id} as processed using query: {query}")
                    return True
                elif result.matched_count > 0:
                    logger.info(f"✅ SMS {sms_id} already processed")
                    return True
            
            logger.warning(f"⚠️  SMS {sms_id} not found with any query pattern")
            return False
                
        except Exception as e:
            logger.error(f"❌ Error marking SMS {sms_id} as processed: {e}")
            return False

    def mark_financial_sms_as_processed(self, sms_id: str, status: str = "success") -> bool:
        """Mark financial SMS as processed in sms_fin_rawdata collection using SIMPLIFIED ID SYSTEM"""
        try:
            logger.info(f"🔍 DEBUG: Marking SMS {sms_id} as processed with status: {status}")
            
            # Verify database connection
            if self.db is None or self.fin_raw_collection is None:
                logger.error("❌ ERROR: Database connection issue!")
                return False
            
            # 🚀 SIMPLIFIED ID EXTRACTION
            simple_sms_id = sms_id
            if "_sms_" in sms_id:
                # Extract from long format: usr_abc123_sms_000001 → sms_000001
                parts = sms_id.split("_sms_")
                if len(parts) > 1:
                    number_part = parts[-1]
                    if not number_part.startswith("sms_"):
                        simple_sms_id = f"sms_{number_part}"
                    else:
                        simple_sms_id = number_part
            
            logger.info(f"🔍 DEBUG: Simple SMS ID: {simple_sms_id}")
            
            # Update data
            update_data = {
                "isprocessed": True,
                "processing_timestamp": datetime.now(),
                "processing_status": status,
                "updated_at": datetime.now()
            }
            
            # 🚀 FIXED: PRIORITIZE EXACT FULL unique_id MATCH FIRST
            search_queries = [
                {"unique_id": sms_id},  # PRIORITY 1: Full unique_id (exact match)
                {"sms_id": simple_sms_id},  # PRIORITY 2: Simplified ID (fallback)
                {"unique_id": simple_sms_id},  # PRIORITY 3: Short format (legacy)
            ]
            
            # Try each search query
            for query in search_queries:
                existing_sms = self.fin_raw_collection.find_one(query)
                if existing_sms:
                    logger.info(f"🔍 DEBUG: Found SMS with query: {query}")
                    logger.info(f"🔍 DEBUG: Current isprocessed: {existing_sms.get('isprocessed')}")
                    
                    # Perform the update
                    result = self.fin_raw_collection.update_one(query, {"$set": update_data})
                    
                    if result.modified_count > 0:
                        logger.info(f"✅ Successfully marked SMS {sms_id} as processed")
                        return True
                    elif result.matched_count > 0:
                        logger.info(f"✅ SMS {sms_id} already processed")
                        return True
            
            logger.error(f"❌ SMS {sms_id} not found with any search pattern")
            logger.error(f"🔍 Tried queries: {search_queries}")
            return False
                
        except Exception as e:
            logger.error(f"❌ Error marking SMS {sms_id} as processed: {e}")
            logger.error(f"🔍 DEBUG: Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            return False
    
    def get_user_sms_data(self, user_id, limit: int = None, unprocessed_only: bool = True) -> List[Dict[str, Any]]:
        """Get SMS data for a specific user"""
        try:
            from bson import ObjectId
            
            # Convert to ObjectId if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except:
                    pass  # Keep as string if conversion fails
            
            query = {"user_id": user_id}
            if unprocessed_only:
                query["is_processed"] = {"$ne": True}  # 🚀 FIXED: Use correct field name
            
            cursor = self.sms_collection.find(query).sort("date", -1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            sms_list = list(cursor)
            
            # 🚀 FIXED: NO _source_id needed - use sms_id directly
            # Each SMS already has sms_id from sms_data collection
            logger.info(f"📱 Retrieved {len(sms_list)} SMS for user {user_id}")
            return sms_list
            
        except Exception as e:
            logger.error(f"❌ Error retrieving SMS data: {e}")
            return []
    
    def get_all_sms_data(self, unprocessed_only: bool = True, limit: int = None) -> List[Dict[str, Any]]:
        """Get all SMS data (for batch processing)"""
        try:
            query = {}
            if unprocessed_only:
                query["is_processed"] = {"$ne": True}  # 🚀 FIXED: Use correct field name
            
            cursor = self.sms_collection.find(query).sort("date", -1)
            
            if limit:
                cursor = cursor.limit(limit)
            
            sms_list = list(cursor)
            
            # 🚀 FIXED: NO _source_id needed - use sms_id directly
            # Each SMS already has sms_id from sms_data collection
            logger.info(f"📱 Retrieved {len(sms_list)} SMS (all users)")
            return sms_list
            
        except Exception as e:
            logger.error(f"❌ Error retrieving all SMS data: {e}")
            return []
    
    def store_financial_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Store a single financial transaction"""
        try:
            # Add metadata
            transaction_data["created_at"] = datetime.now()
            transaction_data["updated_at"] = datetime.now()
            
            # 🚀 FIXED: Use unique_id for uniqueness
            if "unique_id" in transaction_data:
                # Use upsert to avoid duplicates
                result = self.transactions_collection.update_one(
                    {"unique_id": transaction_data["unique_id"]},
                    {"$set": transaction_data},
                    upsert=True
                )
                
                if result.upserted_id:
                    logger.info(f"💾 Stored new transaction: {transaction_data.get('unique_id', 'NO_ID')}")
                else:
                    logger.info(f"🔄 Updated existing transaction: {transaction_data.get('unique_id', 'NO_ID')}")
                
                return True
            else:
                # This shouldn't happen - all transactions should have unique_id
                logger.warning(f"⚠️  Transaction missing unique_id!")
                result = self.transactions_collection.insert_one(transaction_data)
                logger.info(f"💾 Stored transaction with ID: {result.inserted_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error storing transaction: {e}")
            return False
    
    def store_financial_transactions_batch(self, transactions: List[Dict[str, Any]]) -> int:
        """Store multiple financial transactions in batch"""
        try:
            if not transactions:
                logger.info("🔍 DEBUG: No transactions to store")
                return 0
            
            logger.info(f"🔍 DEBUG: Starting to store {len(transactions)} transactions")
            logger.info(f"🔍 DEBUG: Database connection: {self.db is not None}")
            logger.info(f"🔍 DEBUG: Transactions collection: {self.transactions_collection is not None}")
            
            # Verify database connection - FIXED for Python 3.13 compatibility
            if self.db is None:
                logger.error("❌ ERROR: Database connection is None!")
                return 0
            
            if self.transactions_collection is None:
                logger.error("❌ ERROR: Transactions collection is None!")
                return 0
            
            # Add metadata to each transaction
            for i, transaction in enumerate(transactions):
                transaction["created_at"] = datetime.now()
                transaction["updated_at"] = datetime.now()
                logger.debug(f"🔍 DEBUG: Prepared transaction {i+1}: {transaction.get('unique_id', 'NO_ID')}")
            
            # Use bulk operations for better performance
            bulk_operations = []
            for i, transaction in enumerate(transactions):
                # Clean the transaction document for MongoDB
                clean_transaction = self._clean_transaction_document(transaction)
                logger.debug(f"🔍 DEBUG: Cleaned transaction {i+1}: {clean_transaction.get('unique_id', 'NO_ID')}")
                
                if "unique_id" in clean_transaction:
                    # 🚀 FIXED: Upsert operation using unique_id
                    bulk_operations.append(
                        UpdateOne(
                            {"unique_id": clean_transaction["unique_id"]},
                            {"$set": clean_transaction},
                            upsert=True
                        )
                    )
                    logger.debug(f"🔍 DEBUG: Added upsert operation for {clean_transaction['unique_id']}")
                else:
                    # Insert operation - use proper MongoDB syntax
                    bulk_operations.append(
                        InsertOne(clean_transaction)
                    )
                    logger.debug(f"🔍 DEBUG: Added insert operation for transaction {i+1}")
            
            logger.info(f"🔍 DEBUG: Created {len(bulk_operations)} bulk operations")
            
            if bulk_operations:
                logger.info(f"🔍 DEBUG: Executing bulk write operation...")
                result = self.transactions_collection.bulk_write(bulk_operations)
                logger.info(f"💾 Batch stored {len(transactions)} transactions")
                logger.info(f"🔍 DEBUG: Bulk write result: {result.bulk_api_result}")
                return len(transactions)
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error in batch transaction storage: {e}")
            logger.error(f"🔍 DEBUG: Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            # Try individual inserts as fallback
            return self._fallback_individual_inserts(transactions)
    
    def _clean_transaction_document(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Clean transaction document for MongoDB storage"""
        try:
            # Create a clean copy
            clean_transaction = {}
            
            for key, value in transaction.items():
                # Skip None values
                if value is None:
                    continue
                
                # Handle different data types
                if isinstance(value, (str, int, float, bool)):
                    clean_transaction[key] = value
                elif isinstance(value, dict):
                    # Check if it's an ObjectId in JSON format
                    if "$oid" in value:
                        from bson import ObjectId
                        clean_transaction[key] = ObjectId(value["$oid"])
                    else:
                        # Recursively clean nested dictionaries
                        clean_transaction[key] = self._clean_transaction_document(value)
                elif isinstance(value, list):
                    # Clean list items
                    clean_transaction[key] = [
                        self._clean_transaction_document(item) if isinstance(item, dict) else item
                        for item in value if item is not None
                    ]
                elif isinstance(value, datetime):
                    clean_transaction[key] = value
                elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                    # Preserve ObjectId type
                    clean_transaction[key] = value
                else:
                    # Convert other types to string
                    clean_transaction[key] = str(value)
            
            return clean_transaction
            
        except Exception as e:
            logger.error(f"❌ Error cleaning transaction document: {e}")
            return transaction
    
    def _fallback_individual_inserts(self, transactions: List[Dict[str, Any]]) -> int:
        """Fallback to individual inserts if bulk operations fail"""
        try:
            success_count = 0
            for transaction in transactions:
                try:
                    clean_transaction = self._clean_transaction_document(transaction)
                    result = self.transactions_collection.insert_one(clean_transaction)
                    if result.inserted_id:
                        success_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to insert individual transaction: {e}")
                    continue
            
            logger.info(f"💾 Fallback: Inserted {success_count} transactions individually")
            return success_count
            
        except Exception as e:
            logger.error(f"❌ Fallback individual inserts failed: {e}")
            return 0
    
    def mark_sms_as_processed(self, unique_id: str, status: str = "success") -> bool:
        """Mark SMS as processed in the database"""
        try:
            result = self.sms_collection.update_one(
                {"unique_id": unique_id},
                {
                    "$set": {
                        "isprocessed": True,
                        "processing_timestamp": datetime.now(),
                        "processing_status": status
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"🔄 Marked SMS {unique_id} as processed ({status})")
                return True
            else:
                logger.warning(f"⚠️  SMS {unique_id} not found for marking as processed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error marking SMS as processed: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            # Raw SMS collection stats
            total_sms = self.sms_collection.count_documents({})
            
            # Financial raw data collection stats
            total_financial_sms = self.fin_raw_collection.count_documents({})
            processed_financial_sms = self.fin_raw_collection.count_documents({"isprocessed": True})
            unprocessed_financial_sms = self.fin_raw_collection.count_documents({"isprocessed": {"$ne": True}})
            
            # Financial transactions collection stats
            total_transactions = self.transactions_collection.count_documents({})
            
            stats = {
                "total_raw_sms": total_sms,
                "total_financial_sms": total_financial_sms,
                "processed_financial_sms": processed_financial_sms,
                "unprocessed_financial_sms": unprocessed_financial_sms,
                "total_transactions": total_transactions,
                "financial_processing_percentage": round((processed_financial_sms / total_financial_sms * 100), 2) if total_financial_sms > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting processing stats: {e}")
            return {}
    
    def get_already_processed_sms_ids(self) -> List[str]:
        """Get list of SMS IDs that have already been processed in sms_fin_rawdata"""
        try:
            # Query sms_fin_rawdata collection for already processed SMS
            query = {
                "$or": [
                    {"isprocessed": True},
                    {"processing_status": "success"},
                    {"processing_status": "failed"}
                ]
            }
            
            cursor = self.fin_raw_collection.find(query, {"unique_id": 1})
            processed_ids = [doc.get("unique_id") for doc in cursor if doc.get("unique_id")]
            
            logger.info(f"🔍 Found {len(processed_ids)} already processed SMS IDs")
            return processed_ids
            
        except Exception as e:
            logger.error(f"❌ Error retrieving already processed SMS IDs: {e}")
            return []
    
    def is_sms_already_processed(self, sms_id: str, user_id: str = None) -> bool:
        """Check if a specific SMS is already processed in sms_fin_rawdata FOR THIS USER"""
        try:
            # Handle different ID formats
            # sms_id could be: "usr_abc123_sms_000001" or "sms_000001"
            
            # Extract user_id from sms_id if not provided
            extracted_user_id = user_id
            if not extracted_user_id and "_sms_" in sms_id:
                # Extract user_id from full unique_id: "usr_abc123_sms_000001" -> "usr_abc123"
                parts = sms_id.split("_sms_")
                if len(parts) >= 2:
                    extracted_user_id = parts[0]
            
            # Extract the base SMS ID (e.g., "sms_000001")
            base_sms_id = sms_id
            if "_sms_" in sms_id:
                base_sms_id = sms_id.split("_sms_")[-1]
                if not base_sms_id.startswith("sms_"):
                    base_sms_id = f"sms_{base_sms_id}"
            
            # 🚀 FIX: Check for BOTH user_id AND unique_id to prevent cross-user conflicts
            query = {
                "unique_id": base_sms_id,
                "$or": [
                    {"isprocessed": True},
                    {"processing_status": "success"},
                    {"processing_status": "failed"}
                ]
            }
            
            # Add user_id filter if available to prevent cross-user conflicts
            if extracted_user_id:
                query["user_id"] = extracted_user_id
            
            result = self.fin_raw_collection.find_one(query)
            is_processed = result is not None
            
            if is_processed:
                logger.info(f"🔍 SMS {sms_id} (base: {base_sms_id}) is already processed for user {extracted_user_id}")
            else:
                logger.info(f"🔍 SMS {sms_id} (base: {base_sms_id}) is not yet processed for user {extracted_user_id}")
            
            return is_processed
            
        except Exception as e:
            logger.error(f"❌ Error checking if SMS {sms_id} is processed: {e}")
            return False
    
    def create_processing_checkpoint(self, user_id: str, batch_id: int, total_sms: int, processed_sms: int, 
                                   last_processed_id: str = None) -> bool:
        """Create a processing checkpoint for resume capability"""
        try:
            checkpoint_data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "total_sms": total_sms,
                "processed_sms": processed_sms,
                "last_processed_id": last_processed_id,
                "checkpoint_timestamp": datetime.now(),
                "status": "in_progress"
            }
            
            # Upsert checkpoint
            result = self.db.processing_checkpoints.update_one(
                {"user_id": user_id, "batch_id": batch_id},
                {"$set": checkpoint_data},
                upsert=True
            )
            
            logger.info(f"💾 Created checkpoint: {user_id} - Batch {batch_id} - {processed_sms}/{total_sms} SMS")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating checkpoint: {e}")
            return False
    
    def get_processing_checkpoint(self, user_id: str, batch_id: int) -> Dict[str, Any]:
        """Get processing checkpoint for resume capability"""
        try:
            checkpoint = self.db.processing_checkpoints.find_one(
                {"user_id": user_id, "batch_id": batch_id}
            )
            
            if checkpoint:
                logger.info(f"📋 Found checkpoint: {user_id} - Batch {batch_id} - {checkpoint['processed_sms']}/{checkpoint['total_sms']} SMS")
                return checkpoint
            else:
                logger.info(f"📋 No checkpoint found for: {user_id} - Batch {batch_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving checkpoint: {e}")
            return None
    
    def update_processing_checkpoint(self, user_id: str, batch_id: int, processed_sms: int, 
                                   last_processed_id: str = None, status: str = "in_progress") -> bool:
        """Update processing checkpoint with progress"""
        try:
            update_data = {
                "processed_sms": processed_sms,
                "last_processed_id": last_processed_id,
                "checkpoint_timestamp": datetime.now(),
                "status": status
            }
            
            result = self.db.processing_checkpoints.update_one(
                {"user_id": user_id, "batch_id": batch_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"💾 Updated checkpoint: {user_id} - Batch {batch_id} - {processed_sms} SMS - {status}")
                return True
            else:
                logger.warning(f"⚠️  Checkpoint not found for update: {user_id} - Batch {batch_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating checkpoint: {e}")
            return False
    
    def mark_checkpoint_completed(self, user_id: str, batch_id: int) -> bool:
        """Mark processing checkpoint as completed"""
        try:
            result = self.db.processing_checkpoints.update_one(
                {"user_id": user_id, "batch_id": batch_id},
                {"$set": {"status": "completed", "completion_timestamp": datetime.now()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Marked checkpoint completed: {user_id} - Batch {batch_id}")
                return True
            else:
                logger.warning(f"⚠️  Checkpoint not found for completion: {user_id} - Batch {batch_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error marking checkpoint completed: {e}")
            return False
    
    def get_resume_point(self, user_id: str) -> Dict[str, Any]:
        """Get resume point for user after crash"""
        try:
            # Find the latest incomplete checkpoint
            checkpoint = self.db.processing_checkpoints.find_one(
                {"user_id": user_id, "status": "in_progress"},
                sort=[("checkpoint_timestamp", -1)]
            )
            
            if checkpoint:
                logger.info(f"🔄 Resume point found: {user_id} - Batch {checkpoint['batch_id']} - {checkpoint['processed_sms']}/{checkpoint['total_sms']} SMS")
                return checkpoint
            else:
                logger.info(f"🔄 No resume point found for: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting resume point: {e}")
            return None
    
    def close_connection(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing MongoDB connection: {e}")

    def recover_unstored_transactions(self, user_id: str) -> int:
        """Recover any processed SMS that weren't stored due to crashes"""
        try:
            print(f"🔄 Checking for unstored transactions for user: {user_id}")
            
            # Find SMS that are marked as processed but don't have corresponding transactions
            processed_sms = self.fin_raw_collection.find({
                "user_id": user_id,
                "isprocessed": True
            })
            
            recovered_count = 0
            for sms in processed_sms:
                # Check if transaction exists
                transaction_exists = self.transactions_collection.find_one({
                    "unique_id": sms.get("unique_id")
                })
                
                if not transaction_exists:
                    print(f"  🔍 Found unstored transaction for SMS: {sms.get('unique_id')}")
                    
                    # Try to reconstruct transaction data from SMS
                    transaction_data = self._reconstruct_transaction_from_sms(sms)
                    if transaction_data:
                        try:
                            # Store the recovered transaction
                            result = self.transactions_collection.insert_one(transaction_data)
                            if result.inserted_id:
                                recovered_count += 1
                                print(f"  ✅ Recovered transaction: {sms.get('unique_id')}")
                            else:
                                print(f"  ❌ Failed to recover transaction: {sms.get('unique_id')}")
                        except Exception as e:
                            print(f"  ❌ Error recovering transaction {sms.get('unique_id')}: {e}")
                    else:
                        print(f"  ⚠️  Could not reconstruct transaction for: {sms.get('unique_id')}")
            
            print(f"🔄 Recovery complete: {recovered_count} transactions recovered")
            return recovered_count
            
        except Exception as e:
            logger.error(f"❌ Error in transaction recovery: {e}")
            return 0
    
    def _reconstruct_transaction_from_sms(self, sms: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct transaction data from SMS for recovery"""
        try:
            # Basic transaction structure
            transaction = {
                "unique_id": sms.get("unique_id"),
                "user_id": sms.get("user_id"),
                "sender": sms.get("sender"),
                "body": sms.get("body"),
                "date": sms.get("date"),
                "transaction_date": sms.get("date"),
                "amount": None,  # Will need to be extracted from body
                "transaction_type": "unknown",
                "message_intent": "unknown",
                "currency": "INR",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "recovery_source": "sms_reconstruction",
                "recovery_timestamp": datetime.now()
            }
            
            # Try to extract amount from body if possible
            body = sms.get("body", "")
            if "Rs." in body or "₹" in body:
                # Simple amount extraction (can be enhanced)
                import re
                amount_match = re.search(r'[Rr]s\.?\s*(\d+(?:\.\d+)?)', body)
                if amount_match:
                    transaction["amount"] = float(amount_match.group(1))
            
            return transaction
            
        except Exception as e:
            logger.error(f"❌ Error reconstructing transaction: {e}")
            return None

def test_mongodb_connection():
    """Test MongoDB connection and basic operations"""
    try:
        mongo_ops = MongoDBOperations()
        
        # Test basic operations
        stats = mongo_ops.get_processing_stats()
        print(f"📊 MongoDB Connection Test Results:")
        print(f"   Database: {mongo_ops.db_name}")
        print(f"   SMS Collection: {mongo_ops.sms_collection.name}")
        print(f"   Transactions Collection: {mongo_ops.transactions_collection.name}")
        print(f"   Total SMS: {stats.get('total_sms', 0)}")
        print(f"   Total Transactions: {stats.get('total_transactions', 0)}")
        
        mongo_ops.close_connection()
        print("✅ MongoDB connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_mongodb_connection()
