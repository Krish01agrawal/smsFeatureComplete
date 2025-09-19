"""
MongoDB-based Pattern Storage System
Provides persistent learning storage for transaction patterns
"""

import logging
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, OperationFailure

logger = logging.getLogger(__name__)

class PatternStorage:
    """MongoDB-based storage for user learning patterns"""
    
    def __init__(self, connection_string: str = None, database_name: str = "pluto_money"):
        """
        Initialize MongoDB pattern storage using the connection manager
        
        Args:
            connection_string: MongoDB connection string (uses env var if not provided)
            database_name: Database name for storing patterns
        """
        import os
        from .mongodb_connection_manager import mongodb_manager
        
        self.connection_string = connection_string or os.getenv("MONGODB_URI")
        self.database_name = database_name
        self.client = None
        self.db = None
        self.patterns_collection = None
        self.connected = False
        
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection using the connection manager"""
        try:
            from .mongodb_connection_manager import mongodb_manager
            
            # Use the connection manager for consistent connection reuse
            connection_id = "pattern_storage"
            self.client = mongodb_manager.get_connection(self.connection_string, connection_id)
            
            self.db = self.client[self.database_name]
            self.patterns_collection = self.db['transaction_patterns']
            
            # Create indexes for performance
            self.patterns_collection.create_index("user_id", unique=True)
            self.patterns_collection.create_index("last_updated")
            
            self.connected = True
            logger.info(f"✅ Connected to MongoDB: {self.database_name}.transaction_patterns")
            
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection error: {e} - falling back to in-memory storage")
            self.connected = False
    
    def save_user_patterns(self, user_id: str, merchant_patterns: Dict, 
                          amount_patterns: Dict, user_corrections: Dict, 
                          confidence_scores: Dict) -> bool:
        """
        Save user learning patterns to MongoDB
        
        Args:
            user_id: Unique user identifier
            merchant_patterns: Merchant categorization patterns
            amount_patterns: Amount-based patterns
            user_corrections: Manual user corrections
            confidence_scores: Pattern confidence scores
            
        Returns:
            bool: True if saved successfully
        """
        if not self.connected:
            logger.debug(f"MongoDB not connected - skipping pattern save for user {user_id}")
            return False
        
        try:
            # Prepare document for MongoDB
            pattern_doc = {
                "user_id": user_id,
                "merchant_patterns": self._serialize_patterns(merchant_patterns),
                "amount_patterns": self._serialize_patterns(amount_patterns),
                "user_corrections": dict(user_corrections),
                "confidence_scores": dict(confidence_scores),
                "last_updated": datetime.utcnow(),
                "metadata": {
                    "total_merchants": len(merchant_patterns),
                    "total_corrections": len(user_corrections),
                    "system_version": "2.0"
                }
            }
            
            # Upsert pattern document
            result = self.patterns_collection.replace_one(
                {"user_id": user_id}, 
                pattern_doc, 
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                logger.info(f"✅ Saved learning patterns for user {user_id}")
                return True
            else:
                logger.warning(f"⚠️ No changes made to patterns for user {user_id}")
                return False
                
        except OperationFailure as e:
            logger.error(f"❌ MongoDB operation failed for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to save patterns for user {user_id}: {e}")
            return False
    
    def load_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Load user learning patterns from MongoDB
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict containing user patterns or empty dict if not found
        """
        if not self.connected:
            logger.debug(f"MongoDB not connected - returning empty patterns for user {user_id}")
            return {}
        
        try:
            pattern_doc = self.patterns_collection.find_one({"user_id": user_id})
            
            if not pattern_doc:
                logger.info(f"No existing patterns found for user {user_id}")
                return {}
            
            # Deserialize patterns
            patterns = {
                "merchant_patterns": self._deserialize_patterns(
                    pattern_doc.get("merchant_patterns", {})
                ),
                "amount_patterns": self._deserialize_patterns(
                    pattern_doc.get("amount_patterns", {})
                ),
                "user_corrections": defaultdict(dict, pattern_doc.get("user_corrections", {})),
                "confidence_scores": defaultdict(float, pattern_doc.get("confidence_scores", {})),
                "last_updated": pattern_doc.get("last_updated"),
                "metadata": pattern_doc.get("metadata", {})
            }
            
            logger.info(f"✅ Loaded learning patterns for user {user_id}")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to load patterns for user {user_id}: {e}")
            return {}
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get user learning statistics
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict containing user statistics
        """
        if not self.connected:
            return {"connected": False}
        
        try:
            pattern_doc = self.patterns_collection.find_one(
                {"user_id": user_id}, 
                {"metadata": 1, "last_updated": 1}
            )
            
            if not pattern_doc:
                return {"user_found": False}
            
            return {
                "user_found": True,
                "connected": True,
                "last_updated": pattern_doc.get("last_updated"),
                "total_merchants": pattern_doc.get("metadata", {}).get("total_merchants", 0),
                "total_corrections": pattern_doc.get("metadata", {}).get("total_corrections", 0),
                "system_version": pattern_doc.get("metadata", {}).get("system_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats for user {user_id}: {e}")
            return {"connected": True, "error": str(e)}
    
    def cleanup_old_patterns(self, days_old: int = 90) -> int:
        """
        Clean up old pattern data
        
        Args:
            days_old: Remove patterns older than this many days
            
        Returns:
            Number of documents removed
        """
        if not self.connected:
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = self.patterns_collection.delete_many({
                "last_updated": {"$lt": cutoff_date}
            })
            
            logger.info(f"🧹 Cleaned up {result.deleted_count} old pattern documents")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old patterns: {e}")
            return 0
    
    def _serialize_patterns(self, patterns: Any) -> Dict:
        """Convert defaultdict patterns to regular dict for MongoDB storage"""
        if isinstance(patterns, defaultdict):
            return {k: dict(v) if isinstance(v, defaultdict) else v 
                   for k, v in patterns.items()}
        return dict(patterns) if patterns else {}
    
    def _deserialize_patterns(self, patterns: Dict) -> defaultdict:
        """Convert dict patterns back to defaultdict"""
        result = defaultdict(dict)
        for k, v in patterns.items():
            if isinstance(v, dict):
                result[k] = defaultdict(int, v) if any(isinstance(val, (int, float)) for val in v.values()) else dict(v)
            else:
                result[k] = v
        return result
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close()


# Singleton instance for global use
_pattern_storage_instance = None

def get_pattern_storage() -> PatternStorage:
    """Get global pattern storage instance"""
    global _pattern_storage_instance
    if _pattern_storage_instance is None:
        _pattern_storage_instance = PatternStorage()
    return _pattern_storage_instance
