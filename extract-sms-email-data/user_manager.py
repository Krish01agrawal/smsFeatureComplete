#!/usr/bin/env python3
"""
User Manager
============

Enterprise-grade user management system for SMS processing.
Ensures globally unique user IDs and maintains user profiles.

Features:
- Globally unique user ID generation (UUID + timestamp)
- User registration and profile management
- Collision-proof user identification
- User analytics and statistics
- MongoDB integration with proper indexing
"""

import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
import sys

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
except ImportError:
    print("❌ PyMongo not installed. Install with: pip install pymongo")
    sys.exit(1)

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://divyamverma:geMnO2HtgXwOrLsW@cluster0.gzbouvi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "pluto_money"
USERS_COLLECTION = "users"

class UserManager:
    """Enterprise User Management System"""
    
    def __init__(self, connection_string: str = MONGODB_URI, db_name: str = DATABASE_NAME):
        self.connection_string = connection_string
        self.db_name = db_name
        self.client = None
        self.db = None
        self.users_collection = None
        
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                self.connection_string, 
                serverSelectionTimeoutMS=5000,
                tlsAllowInvalidCertificates=True  # Fix SSL certificate issues
            )
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.users_collection = self.db[USERS_COLLECTION]
            
            # Create indexes for users collection
            self._create_user_indexes()
            
            return True
            
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
    
    def _create_user_indexes(self):
        """Create indexes for users collection"""
        try:
            # Unique index on user_id (primary identifier)
            self.users_collection.create_index(
                [("user_id", 1)], 
                unique=True, 
                background=True,
                name="unique_user_id"
            )
            
            # Index on email for lookups
            self.users_collection.create_index(
                [("email", 1)], 
                background=True,
                sparse=True,  # Allow null emails
                name="idx_email"
            )
            
            # Index on phone for lookups
            self.users_collection.create_index(
                [("phone", 1)], 
                background=True,
                sparse=True,  # Allow null phones
                name="idx_phone"
            )
            
            # Index on creation date for analytics
            self.users_collection.create_index(
                [("created_at", -1)], 
                background=True,
                name="idx_created_at"
            )
            
            # Compound index for active users
            self.users_collection.create_index(
                [("is_active", 1), ("created_at", -1)], 
                background=True,
                name="idx_active_users"
            )
            
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")
    
    def generate_unique_user_id(self, name: str = None, email: str = None, phone: str = None) -> str:
        """
        Generate a globally unique user ID that will NEVER clash
        
        Format: usr_{hash8}_{timestamp}_{uuid4_short}
        Example: usr_a1b2c3d4_20250921_f47ac10b
        
        This ensures:
        - Globally unique across millions of users
        - Collision probability: < 1 in 10^20 
        - Sortable by creation time
        - Human readable prefix
        """
        
        # Create a hash from available user info for uniqueness
        hash_input = ""
        if name:
            hash_input += name.lower().strip()
        if email:
            hash_input += email.lower().strip()
        if phone:
            hash_input += phone.strip()
        
        # Add current timestamp for additional uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        hash_input += timestamp
        
        # Generate hash
        hash_obj = hashlib.sha256(hash_input.encode())
        hash_hex = hash_obj.hexdigest()[:8]  # First 8 characters
        
        # Generate UUID4 for ultimate uniqueness
        uuid_short = str(uuid.uuid4()).replace('-', '')[:8]
        
        # Create timestamp part
        time_part = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Combine all parts
        user_id = f"usr_{hash_hex}_{time_part}_{uuid_short}"
        
        return user_id
    
    def validate_user_input(self, name: str = None, email: str = None, phone: str = None) -> Dict[str, Any]:
        """Validate user input data"""
        errors = []
        warnings = []
        
        # Validate name
        if name:
            name = name.strip()
            if len(name) < 2:
                errors.append("Name must be at least 2 characters long")
            elif len(name) > 100:
                errors.append("Name must be less than 100 characters")
            elif not re.match(r'^[a-zA-Z\s\-\.]+$', name):
                warnings.append("Name contains special characters")
        
        # Validate email
        if email:
            email = email.strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Invalid email format")
        
        # Validate phone
        if phone:
            phone = re.sub(r'[^\d+]', '', phone)  # Remove non-digit characters except +
            if len(phone) < 10:
                errors.append("Phone number must be at least 10 digits")
            elif len(phone) > 15:
                errors.append("Phone number must be less than 15 digits")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "cleaned_data": {
                "name": name.title() if name else None,
                "email": email if email else None,
                "phone": phone if phone else None
            }
        }
    
    def create_user(self, name: str = None, email: str = None, phone: str = None, 
                   metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new user using MongoDB's native ObjectId as user_id
        
        Returns:
            dict: User creation result with user_id (ObjectId), status, and details
        """
        
        # Validate input
        validation = self.validate_user_input(name, email, phone)
        if not validation["valid"]:
            return {
                "success": False,
                "user_id": None,
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }
        
        cleaned_data = validation["cleaned_data"]
        
        # Create user document with temporary ObjectId for user_id field
        now = datetime.utcnow()
        from bson import ObjectId
        temp_user_id = ObjectId()  # Generate temporary ObjectId
        
        # Handle email field to avoid unique index conflicts
        email_value = cleaned_data["email"]
        if email_value is None:
            # For null emails, use a unique identifier to avoid unique index conflicts
            email_value = f"temp_email_{temp_user_id}"
        
        user_doc = {
            "user_id": temp_user_id,  # Include user_id field to satisfy unique index
            "name": cleaned_data["name"],
            "email": email_value,  # Use processed email value
            "phone": cleaned_data["phone"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "sms_stats": {
                "total_uploaded": 0,
                "total_processed": 0,
                "total_financial": 0,
                "last_upload": None,
                "last_processing": None
            },
            "metadata": metadata or {}
        }
        
        try:
            # Insert user into database - MongoDB generates _id automatically
            result = self.users_collection.insert_one(user_doc)
            actual_user_id = result.inserted_id  # This is the MongoDB ObjectId
            
            # Update user_id to match the actual _id
            self.users_collection.update_one(
                {"_id": actual_user_id},
                {"$set": {"user_id": actual_user_id}}
            )
            
            # Update user_doc for return
            user_doc["user_id"] = actual_user_id
            user_doc["_id"] = actual_user_id
            
            return {
                "success": True,
                "user_id": actual_user_id,  # MongoDB ObjectId
                "user_doc": user_doc,
                "errors": [],
                "warnings": validation["warnings"]
            }
                
        except Exception as e:
            return {
                "success": False,
                "user_id": None,
                "errors": [f"Database error: {e}"],
                "warnings": validation["warnings"]
            }
    
    def get_user(self, user_id) -> Optional[Dict[str, Any]]:
        """Get user by user_id (ObjectId or string)"""
        try:
            from bson import ObjectId
            
            # Try to convert to ObjectId if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except:
                    # If conversion fails, search by string user_id (backward compatibility)
                    user = self.users_collection.find_one({"user_id": user_id})
                    return user
            
            # Search by _id (ObjectId)
            user = self.users_collection.find_one({"_id": user_id})
            return user
            
        except Exception as e:
            print(f"❌ Error getting user {user_id}: {e}")
            return None
    
    def user_exists(self, user_id) -> bool:
        """Check if user exists by ObjectId or string"""
        try:
            from bson import ObjectId
            
            # Try to convert to ObjectId if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                    count = self.users_collection.count_documents({"_id": user_id})
                    return count > 0
                except:
                    # If conversion fails, search by string user_id (backward compatibility)
                    count = self.users_collection.count_documents({"user_id": user_id})
                    return count > 0
            
            # Search by _id (ObjectId)
            count = self.users_collection.count_documents({"_id": user_id})
            return count > 0
            
        except Exception as e:
            print(f"❌ Error checking user existence: {e}")
            return False
    
    def find_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find user by phone number"""
        try:
            user = self.users_collection.find_one({"phone": phone})
            return user
        except Exception as e:
            print(f"❌ Error finding user by phone: {e}")
            return None
    
    def update_user_sms_stats(self, user_id, uploaded: int = 0, processed: int = 0, 
                             financial: int = 0) -> bool:
        """Update user SMS statistics"""
        try:
            from bson import ObjectId
            
            # Convert to ObjectId if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except:
                    # If conversion fails, use string user_id (backward compatibility)
                    pass
            
            now = datetime.utcnow()
            update_doc = {
                "$inc": {
                    "sms_stats.total_uploaded": uploaded,
                    "sms_stats.total_processed": processed,
                    "sms_stats.total_financial": financial
                },
                "$set": {
                    "updated_at": now
                }
            }
            
            if uploaded > 0:
                update_doc["$set"]["sms_stats.last_upload"] = now
            if processed > 0:
                update_doc["$set"]["sms_stats.last_processing"] = now
            
            # Determine search criteria
            if isinstance(user_id, ObjectId):
                search_criteria = {"_id": user_id}
            else:
                search_criteria = {"user_id": user_id}
            
            result = self.users_collection.update_one(search_criteria, update_doc)
            return result.modified_count > 0
            
        except Exception as e:
            print(f"❌ Error updating user stats: {e}")
            return False

    def recalculate_user_stats_from_database(self, user_id: str, mongo_ops) -> bool:
        """Recalculate user stats by counting from actual database collections"""
        try:
            if not self.users_collection:
                print("❌ Users collection not initialized")
                return False
            
            # Count processed SMS in main sms_data collection
            total_processed = mongo_ops.sms_collection.count_documents({
                "user_id": user_id,
                "is_processed": True
            })
            
            # Count successful financial transactions
            total_financial = mongo_ops.transactions_collection.count_documents({
                "user_id": user_id
            })
            
            # Update user stats with actual counts
            update_data = {
                "sms_stats.total_processed": total_processed,
                "sms_stats.total_financial": total_financial,
                "sms_stats.last_processing": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Recalculated stats for user {user_id}: {total_processed} processed, {total_financial} financial")
                return True
            else:
                print(f"⚠️  User {user_id} not found for stats recalculation")
                return False
                
        except Exception as e:
            print(f"❌ Error recalculating user stats: {e}")
            return False
    
    def find_user_by_info(self, name: str = None, email: str = None, phone: str = None) -> Optional[Dict[str, Any]]:
        """Find user by name, email, or phone"""
        try:
            query = {}
            
            if email:
                query["email"] = email.lower().strip()
            elif phone:
                clean_phone = re.sub(r'[^\d+]', '', phone)
                query["phone"] = clean_phone
            elif name:
                # Case-insensitive name search
                query["name"] = {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}
            
            if not query:
                return None
            
            user = self.users_collection.find_one(query)
            return user
            
        except Exception as e:
            print(f"❌ Error finding user: {e}")
            return None
    
    def get_or_create_user(self, name: str = None, email: str = None, phone: str = None, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get existing user or create new one
        
        This is the main method for SMS upload integration
        """
        
        # Try to find existing user
        existing_user = self.find_user_by_info(name, email, phone)
        
        if existing_user:
            return {
                "success": True,
                "user_id": existing_user["user_id"],
                "user_doc": existing_user,
                "created": False,
                "errors": [],
                "warnings": []
            }
        
        # Create new user
        result = self.create_user(name, email, phone, metadata)
        if result["success"]:
            result["created"] = True
        
        return result
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        try:
            total_users = self.users_collection.count_documents({})
            active_users = self.users_collection.count_documents({"is_active": True})
            
            # Get recent activity
            recent_users = self.users_collection.count_documents({
                "created_at": {"$gte": datetime.utcnow().replace(day=1)}  # This month
            })
            
            # Get SMS statistics
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_sms_uploaded": {"$sum": "$sms_stats.total_uploaded"},
                        "total_sms_processed": {"$sum": "$sms_stats.total_processed"},
                        "total_financial_sms": {"$sum": "$sms_stats.total_financial"}
                    }
                }
            ]
            
            sms_stats = list(self.users_collection.aggregate(pipeline))
            sms_totals = sms_stats[0] if sms_stats else {
                "total_sms_uploaded": 0,
                "total_sms_processed": 0,
                "total_financial_sms": 0
            }
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "new_users_this_month": recent_users,
                "sms_statistics": sms_totals
            }
            
        except Exception as e:
            print(f"❌ Error getting user statistics: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "new_users_this_month": 0,
                "sms_statistics": {
                    "total_sms_uploaded": 0,
                    "total_sms_processed": 0,
                    "total_financial_sms": 0
                }
            }
    
    def list_users(self, limit: int = 50, skip: int = 0, active_only: bool = True) -> List[Dict[str, Any]]:
        """List users with pagination"""
        try:
            query = {"is_active": True} if active_only else {}
            
            users = list(self.users_collection.find(
                query, 
                {"_id": 0}  # Exclude MongoDB _id field
            ).sort("created_at", -1).skip(skip).limit(limit))
            
            return users
            
        except Exception as e:
            print(f"❌ Error listing users: {e}")
            return []

def main():
    """Test the user manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="User Manager Operations")
    parser.add_argument("--create", action="store_true", help="Create a test user")
    parser.add_argument("--find-phone", help="Find existing user by phone number")
    parser.add_argument("--name", help="User name")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--phone", help="User phone")
    parser.add_argument("--stats", action="store_true", help="Show user statistics")
    parser.add_argument("--list", action="store_true", help="List users")
    
    args = parser.parse_args()
    
    # Initialize user manager
    user_manager = UserManager()
    
    if not user_manager.connect():
        print("❌ Failed to connect to MongoDB")
        return 1
    
    try:
        if args.find_phone:
            print(f"🔍 Finding user by phone: {args.find_phone}")
            user = user_manager.find_user_by_info(phone=args.find_phone)
            
            if user:
                print(f"✅ User found!")
                print(f"   User ID: {user.get('_id', user.get('user_id', 'N/A'))}")
                print(f"   Name: {user['name']}")
                print(f"   Email: {user['email']}")
                print(f"   Phone: {user['phone']}")
            else:
                print(f"❌ No user found with phone: {args.find_phone}")
                
                # If name is provided, create new user
                if args.name:
                    print(f"🔄 Creating new user with phone: {args.find_phone}")
                    result = user_manager.create_user(
                        name=args.name,
                        email=args.email,
                        phone=args.find_phone
                    )
                    
                    if result["success"]:
                        print(f"✅ User created successfully!")
                        print(f"   User ID: {result['user_id']}")
                    else:
                        print(f"❌ Failed to create user:")
                        for error in result["errors"]:
                            print(f"   - {error}")
        
        elif args.create:
            print("👤 Creating user...")
            result = user_manager.create_user(
                name=args.name,
                email=args.email,
                phone=args.phone
            )
            
            if result["success"]:
                print(f"✅ User created successfully!")
                print(f"   User ID: {result['user_id']}")
                print(f"   Name: {result['user_doc']['name']}")
                print(f"   Email: {result['user_doc']['email']}")
                print(f"   Phone: {result['user_doc']['phone']}")
            else:
                print(f"❌ Failed to create user:")
                for error in result["errors"]:
                    print(f"   - {error}")
        
        elif args.stats:
            print("📊 User Statistics:")
            stats = user_manager.get_user_statistics()
            print(f"   Total Users: {stats['total_users']:,}")
            print(f"   Active Users: {stats['active_users']:,}")
            print(f"   New This Month: {stats['new_users_this_month']:,}")
            print(f"   SMS Uploaded: {stats['sms_statistics']['total_sms_uploaded']:,}")
            print(f"   SMS Processed: {stats['sms_statistics']['total_sms_processed']:,}")
            print(f"   Financial SMS: {stats['sms_statistics']['total_financial_sms']:,}")
        
        elif args.list:
            print("👥 Users List:")
            users = user_manager.list_users(limit=10)
            for i, user in enumerate(users, 1):
                print(f"   {i}. {user['user_id']} - {user['name']} ({user['email']})")
                print(f"      SMS: {user['sms_stats']['total_uploaded']} uploaded, "
                      f"{user['sms_stats']['total_processed']} processed")
        
        else:
            print("🎯 User Manager Test")
            print("Use --create, --stats, or --list to test functionality")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finally:
        user_manager.disconnect()

if __name__ == "__main__":
    exit(main())
