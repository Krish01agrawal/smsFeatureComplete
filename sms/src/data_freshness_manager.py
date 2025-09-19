#!/usr/bin/env python3
"""
Data Freshness Manager
Handles automatic detection of stale processed data and triggers reprocessing when needed.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Any
import logging
from pymongo import MongoClient
import pandas as pd

try:
    from .mongodb_connection_manager import mongodb_manager
    from .processed_data_manager import ProcessedDataManager
except ImportError:
    from mongodb_connection_manager import mongodb_manager
    from processed_data_manager import ProcessedDataManager

# Configure logging
logger = logging.getLogger(__name__)

class DataFreshnessManager:
    """
    Intelligent data freshness detection and management system.
    
    Features:
    - Detects when raw data is newer than processed data
    - Automatic cache invalidation based on data changes
    - Smart reprocessing triggers
    - User-specific freshness tracking
    """
    
    def __init__(self, connection_string: str = None, database_name: str = "pluto_money"):
        """Initialize the freshness manager"""
        self.connection_string = connection_string or os.getenv("MONGODB_URI")
        self.database_name = database_name
        
        if not self.connection_string:
            raise ValueError("MongoDB connection string not provided")
        
        # Initialize connections
        self._init_connections()
        
        # Configuration
        self.freshness_threshold_minutes = 30  # Consider data stale after 30 minutes
        self.max_processing_age_hours = 24     # Force reprocessing after 24 hours
        
        logger.info("DataFreshnessManager initialized")
    
    def _init_connections(self):
        """Initialize MongoDB connections"""
        try:
            # Use centralized connection manager
            connection_id = "data_freshness_manager"
            self.client = mongodb_manager.get_connection(self.connection_string, connection_id)
            self.db = self.client[self.database_name]
            
            # Collections
            self.raw_collection = self.db["user_financial_transactions"]
            self.processed_collection = self.db["processed_financial_transactions"]
            
            logger.info(f"✅ DataFreshnessManager connected to {self.database_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def check_data_freshness(self, user_id: str) -> Dict[str, Any]:
        """
        Check if processed data is fresh for a specific user.
        
        Args:
            user_id: User to check
            
        Returns:
            Dictionary with freshness status and recommendations
        """
        try:
            logger.info(f"🔍 Checking data freshness for user: {user_id}")
            
            # Get raw data info
            raw_info = self._get_raw_data_info(user_id)
            
            # Get processed data info
            processed_info = self._get_processed_data_info(user_id)
            
            # Determine freshness status
            freshness_status = self._analyze_freshness(raw_info, processed_info)
            
            result = {
                "user_id": user_id,
                "raw_data": raw_info,
                "processed_data": processed_info,
                "freshness_status": freshness_status,
                "recommendation": self._get_recommendation(freshness_status),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"📊 Freshness check result: {freshness_status['status']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error checking data freshness for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "freshness_status": {"status": "error"},
                "recommendation": "force_reprocess"
            }
    
    def _get_raw_data_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about raw data for a user"""
        try:
            # Count total transactions
            total_count = self.raw_collection.count_documents({"user_id": user_id})
            
            if total_count == 0:
                return {
                    "exists": False,
                    "count": 0,
                    "latest_transaction": None,
                    "latest_update": None
                }
            
            # Get latest transaction date
            latest_transaction = self.raw_collection.find_one(
                {"user_id": user_id},
                sort=[("transaction_date", -1)]
            )
            
            # Get latest update date (when data was last modified)
            latest_update = self.raw_collection.find_one(
                {"user_id": user_id},
                sort=[("updated_at", -1)]
            )
            
            return {
                "exists": True,
                "count": total_count,
                "latest_transaction": latest_transaction.get("transaction_date") if latest_transaction else None,
                "latest_update": latest_update.get("updated_at") if latest_update else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting raw data info for user {user_id}: {e}")
            return {"exists": False, "error": str(e)}
    
    def _get_processed_data_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about processed data for a user"""
        try:
            # Count processed transactions
            total_count = self.processed_collection.count_documents({"user_id": user_id})
            
            if total_count == 0:
                return {
                    "exists": False,
                    "count": 0,
                    "processed_at": None,
                    "processing_version": None
                }
            
            # Get processing metadata
            processed_record = self.processed_collection.find_one(
                {"user_id": user_id},
                sort=[("processed_at", -1)]
            )
            
            return {
                "exists": True,
                "count": total_count,
                "processed_at": processed_record.get("processed_at") if processed_record else None,
                "processing_version": processed_record.get("processing_metadata", {}).get("preprocessing_version", "unknown")
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting processed data info for user {user_id}: {e}")
            return {"exists": False, "error": str(e)}
    
    def _analyze_freshness(self, raw_info: Dict, processed_info: Dict) -> Dict[str, Any]:
        """Analyze the freshness of processed data compared to raw data"""
        
        # Case 1: No raw data
        if not raw_info.get("exists", False):
            return {
                "status": "no_raw_data",
                "reason": "No raw data found for user",
                "is_fresh": False
            }
        
        # Case 2: No processed data
        if not processed_info.get("exists", False):
            return {
                "status": "no_processed_data",
                "reason": "No processed data found - needs initial processing",
                "is_fresh": False
            }
        
        # Case 3: Count mismatch (new transactions added)
        raw_count = raw_info.get("count", 0)
        processed_count = processed_info.get("count", 0)
        
        if raw_count > processed_count:
            return {
                "status": "count_mismatch",
                "reason": f"Raw data has {raw_count} transactions, processed has {processed_count}",
                "is_fresh": False,
                "raw_count": raw_count,
                "processed_count": processed_count
            }
        
        # Case 4: Check temporal freshness
        now = datetime.now(timezone.utc)
        
        # Get timestamps
        raw_latest_update = raw_info.get("latest_update")
        processed_at = processed_info.get("processed_at")
        
        if raw_latest_update and processed_at:
            # Ensure timezone-aware comparison
            if not raw_latest_update.tzinfo:
                raw_latest_update = raw_latest_update.replace(tzinfo=timezone.utc)
            if not processed_at.tzinfo:
                processed_at = processed_at.replace(tzinfo=timezone.utc)
            
            # Check if raw data was updated after processing
            if raw_latest_update > processed_at:
                time_diff = raw_latest_update - processed_at
                return {
                    "status": "data_updated_after_processing",
                    "reason": f"Raw data updated {time_diff} after processing",
                    "is_fresh": False,
                    "raw_latest_update": raw_latest_update.isoformat(),
                    "processed_at": processed_at.isoformat()
                }
        
        # Case 5: Check processing age
        if processed_at:
            if not processed_at.tzinfo:
                processed_at = processed_at.replace(tzinfo=timezone.utc)
            
            processing_age = now - processed_at
            max_age = timedelta(hours=self.max_processing_age_hours)
            
            if processing_age > max_age:
                return {
                    "status": "processing_too_old",
                    "reason": f"Processed data is {processing_age} old (max: {max_age})",
                    "is_fresh": False,
                    "processing_age_hours": processing_age.total_seconds() / 3600
                }
        
        # Case 6: Data is fresh
        return {
            "status": "fresh",
            "reason": "Processed data is up to date",
            "is_fresh": True
        }
    
    def _get_recommendation(self, freshness_status: Dict) -> str:
        """Get recommendation based on freshness status"""
        status = freshness_status.get("status")
        
        if status in ["no_processed_data", "count_mismatch", "data_updated_after_processing"]:
            return "reprocess_required"
        elif status == "processing_too_old":
            return "reprocess_recommended"
        elif status == "no_raw_data":
            return "no_action_needed"
        elif status == "fresh":
            return "use_processed_data"
        else:
            return "force_reprocess"
    
    def should_force_reprocessing(self, user_id: str) -> bool:
        """
        Determine if reprocessing should be forced for a user.
        
        Args:
            user_id: User to check
            
        Returns:
            bool: True if reprocessing is needed
        """
        freshness_result = self.check_data_freshness(user_id)
        recommendation = freshness_result.get("recommendation")
        
        return recommendation in ["reprocess_required", "force_reprocess"]
    
    def invalidate_processed_data(self, user_id: str) -> bool:
        """
        Invalidate (delete) processed data for a user to force reprocessing.
        
        Args:
            user_id: User whose processed data to invalidate
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"🗑️ Invalidating processed data for user: {user_id}")
            
            result = self.processed_collection.delete_many({"user_id": user_id})
            
            logger.info(f"✅ Deleted {result.deleted_count} processed records for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error invalidating processed data for user {user_id}: {e}")
            return False
    
    def get_system_freshness_report(self) -> Dict[str, Any]:
        """Get a system-wide freshness report for all users"""
        try:
            logger.info("📊 Generating system-wide freshness report")
            
            # Get all users with raw data
            users_with_raw_data = self.raw_collection.distinct("user_id")
            
            # Get all users with processed data
            users_with_processed_data = self.processed_collection.distinct("user_id")
            
            # Analyze each user
            user_reports = {}
            for user_id in set(users_with_raw_data + users_with_processed_data):
                user_reports[user_id] = self.check_data_freshness(user_id)
            
            # Summary statistics
            total_users = len(user_reports)
            fresh_users = sum(1 for report in user_reports.values() 
                            if report.get("freshness_status", {}).get("is_fresh", False))
            stale_users = total_users - fresh_users
            
            return {
                "summary": {
                    "total_users": total_users,
                    "fresh_users": fresh_users,
                    "stale_users": stale_users,
                    "freshness_percentage": (fresh_users / total_users * 100) if total_users > 0 else 0
                },
                "user_reports": user_reports,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating freshness report: {e}")
            return {"error": str(e)}

# Global instance for easy access
data_freshness_manager = DataFreshnessManager()
