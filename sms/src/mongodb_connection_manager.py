"""
MongoDB Connection Manager - Singleton pattern for efficient connection reuse
Prevents repeated connection attempts and provides centralized connection management
"""

import os
import ssl
import logging
from pymongo import MongoClient
from typing import Optional, Dict, Any
import threading
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class MongoDBConnectionManager:
    """
    Singleton MongoDB Connection Manager
    Ensures only one connection per database and provides connection reuse
    """
    _instance = None
    _lock = threading.Lock()
    _connections: Dict[str, MongoClient] = {}
    _connection_info: Dict[str, Dict[str, Any]] = {}
    
    # Global connection mapping - ALL connections use single_connection
    _connection_type_mapping = {
        'mongodb_loader': 'single_connection',
        'processed_data_manager': 'single_connection',
        'processed_data_manager_raw': 'single_connection',
        'pattern_storage': 'single_connection',
        'data_loader': 'single_connection',
        'data_freshness_manager': 'single_connection',  # Added missing mapping
        'main_data_connection': 'single_connection',    # Redirect old mappings
        'default': 'single_connection',                 # Catch-all for any unmapped connections
    }
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDBConnectionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("🔧 MongoDB Connection Manager initialized")
    
    def get_connection(self, connection_string: str, connection_id: str = "default") -> MongoClient:
        """
        Get or create a MongoDB connection with ENFORCED single connection
        
        Args:
            connection_string: MongoDB connection URI
            connection_id: Unique identifier for this connection
            
        Returns:
            MongoClient: Reused single MongoDB client
        """
        # FORCE ALL CONNECTIONS TO USE SINGLE CONNECTION
        actual_connection_id = self._connection_type_mapping.get(connection_id, 'single_connection')
        
        # Additional safety: if somehow not mapped, force to single_connection
        if actual_connection_id != 'single_connection':
            logger.warning(f"🔧 Forcing connection '{connection_id}' to use single_connection")
            actual_connection_id = 'single_connection'
        
        # Check if we already have this connection
        if actual_connection_id in self._connections:
            try:
                # Test if connection is still alive
                client = self._connections[actual_connection_id]
                client.admin.command('ping')
                logger.info(f"♻️ Reusing existing MongoDB connection '{connection_id}' → '{actual_connection_id}'")
                return client
            except Exception as e:
                logger.warning(f"⚠️ Existing connection '{actual_connection_id}' failed ping test: {e}")
                # Remove dead connection
                del self._connections[actual_connection_id]
                if actual_connection_id in self._connection_info:
                    del self._connection_info[actual_connection_id]
        
        # Create new connection
        logger.info(f"🔌 Creating new MongoDB connection '{connection_id}' → '{actual_connection_id}': {connection_string[:50]}...")
        client = self._create_atlas_connection(connection_string)
        
        # Store connection using the actual connection ID
        self._connections[actual_connection_id] = client
        self._connection_info[actual_connection_id] = {
            'connection_string': connection_string[:50] + '...',
            'created_at': datetime.now(),
            'connection_count': len(self._connections),
            'original_request': connection_id,
            'mapped_to': actual_connection_id
        }
        
        logger.info(f"✅ MongoDB connection '{connection_id}' → '{actual_connection_id}' established successfully")
        return client
    
    def _create_atlas_connection(self, connection_string: str) -> MongoClient:
        """Create MongoDB connection with Atlas SSL support"""
        is_atlas = connection_string.startswith("mongodb+srv://") or "mongodb.net" in connection_string
        
        if is_atlas:
            logger.info("🔐 Configuring MongoDB Atlas SSL...")
            
            # Try multiple SSL configurations for Atlas
            ssl_configs = [
                {
                    "name": "Standard Atlas SSL",
                    "config": {
                        "tls": True,
                        "serverSelectionTimeoutMS": 30000,
                        "connectTimeoutMS": 20000,
                        "socketTimeoutMS": 20000,
                        "maxPoolSize": 50,
                        "retryWrites": True,
                        "w": "majority"
                    }
                },
                {
                    "name": "Allow Invalid Certificates",
                    "config": {
                        "tls": True,
                        "tlsAllowInvalidCertificates": True,
                        "serverSelectionTimeoutMS": 30000,
                        "connectTimeoutMS": 20000,
                        "socketTimeoutMS": 20000,
                        "maxPoolSize": 50,
                        "retryWrites": True,
                        "w": "majority"
                    }
                },
                {
                    "name": "Insecure TLS Mode",
                    "config": {
                        "tls": True,
                        "tlsInsecure": True,
                        "serverSelectionTimeoutMS": 30000,
                        "connectTimeoutMS": 20000,
                        "socketTimeoutMS": 20000,
                        "maxPoolSize": 50,
                        "retryWrites": True,
                        "w": "majority"
                    }
                }
            ]
            
            # Try each SSL configuration
            for ssl_config in ssl_configs:
                try:
                    logger.info(f"🔄 Trying {ssl_config['name']}...")
                    client = MongoClient(connection_string, **ssl_config['config'])
                    
                    # Test the connection
                    client.admin.command('ping')
                    logger.info(f"✅ {ssl_config['name']} successful!")
                    
                    # Test database listing
                    db_names = client.list_database_names()
                    logger.info(f"📊 Connected to Atlas. Available databases: {len(db_names)}")
                    
                    return client
                    
                except Exception as e:
                    logger.warning(f"⚠️ {ssl_config['name']} failed: {str(e)[:100]}...")
                    continue
            
            # If all Atlas configurations failed
            raise Exception("❌ All MongoDB Atlas SSL configurations failed")
            
        else:
            # Local MongoDB connection (no SSL needed)
            logger.info("🔧 Configuring local MongoDB connection...")
            connection_options = {
                'serverSelectionTimeoutMS': 5000,
                'connectTimeoutMS': 10000,
                'socketTimeoutMS': 30000,
                'maxPoolSize': 20,
                'retryWrites': True,
                'w': 'majority'
            }
            
            client = MongoClient(connection_string, **connection_options)
            
            # Test connection
            client.admin.command('ping')
            logger.info("✅ Local MongoDB connection successful")
            
            return client
    
    def get_connection_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active connections"""
        return self._connection_info.copy()
    
    def close_connection(self, connection_id: str) -> bool:
        """Close a specific connection"""
        if connection_id in self._connections:
            try:
                self._connections[connection_id].close()
                del self._connections[connection_id]
                if connection_id in self._connection_info:
                    del self._connection_info[connection_id]
                logger.info(f"🔒 Closed MongoDB connection '{connection_id}'")
                return True
            except Exception as e:
                logger.error(f"❌ Error closing connection '{connection_id}': {e}")
                return False
        return False
    
    def close_all_connections(self):
        """Close all connections"""
        for connection_id in list(self._connections.keys()):
            self.close_connection(connection_id)
        logger.info("🔒 All MongoDB connections closed")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self._connections),
            "connection_ids": list(self._connections.keys()),
            "connection_info": self._connection_info,
            "status": "healthy" if len(self._connections) > 0 else "no_connections"
        }

# Global instance
mongodb_manager = MongoDBConnectionManager()

def get_global_mongodb_client(connection_string: str = None, purpose: str = "default") -> MongoClient:
    """
    Get a global MongoDB client for any purpose
    This ensures maximum connection reuse across the entire application
    
    Args:
        connection_string: MongoDB connection URI (uses env var if not provided)
        purpose: Purpose of the connection (for logging only)
    
    Returns:
        MongoClient: Shared MongoDB client
    """
    import os
    if not connection_string:
        connection_string = os.getenv("MONGODB_URI")
    
    if not connection_string:
        raise ValueError("MongoDB connection string not provided and MONGODB_URI not set")
    
    # Always use the same connection ID for all data operations
    return mongodb_manager.get_connection(connection_string, "main_data_connection")

# Global flag to prevent multiple force_single_connection calls
_single_connection_forced = False

def force_single_connection():
    """
    Force all components to use a single MongoDB connection (ONE TIME ONLY)
    This is the ultimate solution for connection reuse
    """
    global _single_connection_forced
    
    if _single_connection_forced:
        # Already forced, just log and return
        print("🔧 Single connection mode already active")
        return
    
    # Mark as forced to prevent multiple calls
    _single_connection_forced = True
    
    # Clear any existing connections to start fresh
    mongodb_manager._connections.clear()
    mongodb_manager._connection_info.clear()
    
    # Update the mapping to ensure everything goes to one connection
    mongodb_manager._connection_type_mapping.update({
        'mongodb_loader': 'single_connection',
        'processed_data_manager': 'single_connection',
        'processed_data_manager_raw': 'single_connection', 
        'pattern_storage': 'single_connection',
        'data_loader': 'single_connection',
        'data_freshness_manager': 'single_connection',
        'main_data_connection': 'single_connection',
        'default': 'single_connection'
    })
    
    print("🔧 Forced single connection mode - all components will share one MongoDB connection")
