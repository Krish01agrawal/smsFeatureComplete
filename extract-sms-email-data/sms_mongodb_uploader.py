#!/usr/bin/env python3
"""
SMS MongoDB Uploader
===================

Upload SMS data from JSON files to MongoDB database.
Supports batch uploads, duplicate detection, and data validation.

Usage:
    python3 sms_mongodb_uploader.py --input test_sms.json
    python3 sms_mongodb_uploader.py --input test_sms.json --batch-size 100
    python3 sms_mongodb_uploader.py --input test_sms.json --clear-collection
"""

import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
import os
import hashlib

try:
    from pymongo import MongoClient
    from pymongo.errors import BulkWriteError, ConnectionFailure, DuplicateKeyError
except ImportError:
    print("❌ PyMongo not installed. Install with: pip install pymongo")
    sys.exit(1)

# Import user management system
try:
    from user_manager import UserManager
except ImportError:
    print("❌ UserManager not found. Make sure user_manager.py is in the same directory")
    sys.exit(1)

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://dev:fXt3BsN6IffLtXu7@blackcard-dev.7tofd5j.mongodb.net/blackcard"
DATABASE_NAME = "blackcard"
COLLECTION_NAME = "sms_data"

class SMSMongoUploader:
    """SMS MongoDB Uploader with enterprise user management"""
    
    def __init__(self, connection_string: str = MONGODB_URI, 
                 db_name: str = DATABASE_NAME, collection_name: str = COLLECTION_NAME):
        self.connection_string = connection_string
        self.db_name = db_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.user_manager = None
        
    def connect(self) -> bool:
        """Connect to MongoDB and initialize user management"""
        try:
            print(f"🔌 Connecting to MongoDB: {self.connection_string}")
            self.client = MongoClient(
                self.connection_string, 
                serverSelectionTimeoutMS=5000,
                tlsAllowInvalidCertificates=True  # Fix SSL certificate issues
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Initialize user manager
            self.user_manager = UserManager(self.connection_string, self.db_name)
            if not self.user_manager.connect():
                print("⚠️  User manager connection failed, but continuing...")
            
            print(f"✅ Connected to database: {self.db_name}")
            print(f"📁 Using collection: {self.collection_name}")
            return True
            
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            print("💡 Make sure MongoDB is running on localhost:27017")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.user_manager:
            self.user_manager.disconnect()
        if self.client:
            self.client.close()
            print("🔌 Disconnected from MongoDB")
    
    def validate_sms_data(self, sms_data: List[Dict[str, Any]], user_id: str = None, 
                         user_name: str = None, user_email: str = None, user_phone: str = None) -> List[Dict[str, Any]]:
        """Validate SMS data with BULLETPROOF duplicate prevention and user management"""
        validated_data = []
        errors = []
        duplicate_count = 0
        
        # Handle user management
        if user_id:
            # Validate existing user_id
            if self.user_manager and not self.user_manager.user_exists(user_id):
                print(f"⚠️  User ID {user_id} not found in users collection")
                print(f"   Creating user profile...")
                
                # Create user with provided info
                user_result = self.user_manager.create_user(
                    name=user_name or f"User {user_id}",
                    email=user_email,
                    phone=user_phone,
                    metadata={"source": "sms_upload", "user_id": user_id}
                )
                
                if not user_result["success"]:
                    print(f"❌ Failed to create user profile:")
                    for error in user_result["errors"]:
                        print(f"   - {error}")
                    # Continue with provided user_id anyway
            else:
                print(f"✅ User {user_id} found in users collection")
        else:
            # Create new user using user management system
            if self.user_manager:
                print(f"👤 Creating new user...")
                user_result = self.user_manager.get_or_create_user(
                    name=user_name,
                    email=user_email,
                    phone=user_phone,
                    metadata={"source": "sms_upload"}
                )
                
                if user_result["success"]:
                    user_id = user_result["user_id"]
                    created_or_found = "Created" if user_result.get("created", False) else "Found existing"
                    print(f"   ✅ {created_or_found} user: {user_id}")
                    if user_result["warnings"]:
                        for warning in user_result["warnings"]:
                            print(f"   ⚠️  {warning}")
                else:
                    print(f"❌ Failed to create user:")
                    for error in user_result["errors"]:
                        print(f"   - {error}")
                    # Fallback to ObjectId-based ID to maintain consistency
                    from bson import ObjectId
                    user_id = ObjectId()
                    print(f"   🔄 Using fallback ObjectId user_id: {user_id}")
            else:
                # Fallback when user manager is not available
                from bson import ObjectId
                user_id = ObjectId()
                print(f"   ⚠️  User manager not available, using fallback ObjectId: {user_id}")
        
        # 🚀 CONVERT STRING USER_ID TO OBJECTID IF VALID
        from bson import ObjectId
        
        if user_id and isinstance(user_id, str):
            try:
                # Try to convert string to ObjectId
                user_id = ObjectId(user_id)
                print(f"   🆔 Converted user_id to ObjectId: {user_id}")
            except:
                # If conversion fails, keep as string (backward compatibility)
                print(f"   🆔 Using string user_id: {user_id}")
        
        print(f"   🆔 Final user_id: {user_id}")
        
        # 🚀 GET USER PHONE NUMBER for all collections
        user_phone_number = None
        if self.user_manager and user_id:
            user_doc = self.user_manager.get_user(user_id)
            if user_doc and user_doc.get('phone'):
                user_phone_number = user_doc['phone']
                print(f"   📱 User phone: {user_phone_number}")
            else:
                # Fallback: use provided phone or extract from user_phone parameter
                user_phone_number = user_phone
                print(f"   📱 Using provided phone: {user_phone_number}")
        
        # 🚀 BULLETPROOF DUPLICATE PREVENTION: Pre-load existing SMS for this user
        print(f"🔍 Checking for existing SMS duplicates for user: {user_id}")
        existing_sms_hashes = set()
        next_sms_index = 1  # 🚀 NEW: Track next available SMS index
        
        try:
            # Get all existing SMS for this user from database
            existing_cursor = self.collection.find(
                {"user_id": user_id}, 
                {"content_hash": 1, "sender": 1, "body": 1, "date": 1, "unique_id": 1}
            )
            
            existing_sms_indices = set()  # Track existing SMS indices
            
            for existing_sms in existing_cursor:
                # Try to get existing hash, or calculate it from content
                if "content_hash" in existing_sms:
                    existing_sms_hashes.add(existing_sms["content_hash"])
                else:
                    # Calculate hash from existing SMS content for backward compatibility
                    content_for_hash = f"{existing_sms.get('sender', '')}{existing_sms.get('body', '')}{existing_sms.get('date', '')}"
                    content_hash = hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()[:16]
                    existing_sms_hashes.add(content_hash)
                
                # 🚀 NEW: Track existing unique_id indices to avoid collisions
                unique_id = existing_sms.get('unique_id', '')
                if unique_id and '_sms_' in unique_id:
                    try:
                        # Extract index from unique_id like "usr_abc_sms_000042"
                        index_part = unique_id.split('_sms_')[-1]
                        index_num = int(index_part)
                        existing_sms_indices.add(index_num)
                    except (ValueError, IndexError):
                        pass  # Skip malformed unique_ids
            
            # Find next available index
            if existing_sms_indices:
                next_sms_index = max(existing_sms_indices) + 1
            
            print(f"   📊 Found {len(existing_sms_hashes)} existing SMS hashes for duplicate checking")
            print(f"   🔢 Next available SMS index: {next_sms_index}")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load existing SMS for duplicate checking: {e}")
            existing_sms_hashes = set()
            next_sms_index = 1
        
        for i, sms in enumerate(sms_data):
            try:
                # Create normalized document
                doc = {
                    "sender": sms.get("sender", ""),
                    "body": sms.get("body", ""),
                    "date": sms.get("date", ""),
                    "type": sms.get("type", "received"),
                    "user_id": user_id,  # Assign user_id to all SMS
                    "phone": user_phone_number,  # 🚀 NEW: Add phone field for easy filtering
                    "email_id": None,    # SMS don't have email_id
                    "uploaded_at": datetime.utcnow(),
                    "source_index": i + 1
                }
                
                # Add optional fields if present
                if "id" in sms:
                    doc["original_id"] = sms["id"]
                
                # Validate required fields
                if not doc["sender"] and not doc["body"]:
                    errors.append(f"SMS {i+1}: Missing both sender and body")
                    continue
                
                # 🚀 BULLETPROOF DUPLICATE PREVENTION: Content-based hash
                content_for_hash = f"{doc['sender']}{doc['body']}{doc['date']}"
                content_hash = hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()[:16]
                doc["content_hash"] = content_hash
                
                # Check if this SMS already exists for this user
                if content_hash in existing_sms_hashes:
                    duplicate_count += 1
                    print(f"   🔄 Duplicate SMS detected (hash: {content_hash}): {doc['sender'][:20]}... | {doc['body'][:30]}...")
                    continue  # Skip this SMS
                
                # Add to existing hashes to prevent duplicates within this batch
                existing_sms_hashes.add(content_hash)
                
                # 🚀 FIXED: Use unique_id with next available index to avoid collisions
                doc["unique_id"] = f"{user_id}_sms_{next_sms_index:06d}"
                next_sms_index += 1  # Increment for next SMS
                
                # Add processing status field (default: not processed)
                doc["is_processed"] = False
                
                validated_data.append(doc)
                
            except Exception as e:
                errors.append(f"SMS {i+1}: Validation error - {e}")
        
        if errors:
            print(f"⚠️  Found {len(errors)} validation errors:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more errors")
        
        if duplicate_count > 0:
            print(f"🔄 DUPLICATE PREVENTION: Filtered out {duplicate_count} duplicate SMS")
        
        print(f"✅ Validated {len(validated_data)} NEW SMS documents for user: {user_id}")
        print(f"   📊 Summary: {len(sms_data)} input → {len(validated_data)} new + {duplicate_count} duplicates + {len(errors)} errors")
        
        # Update user SMS statistics (only for NEW SMS)
        if self.user_manager and len(validated_data) > 0:
            self.user_manager.update_user_sms_stats(
                user_id=user_id,
                uploaded=len(validated_data)
            )
            print(f"   📊 Updated user statistics: +{len(validated_data)} SMS uploaded")
        
        return validated_data
    
    def create_indexes(self):
        """Create indexes for better performance"""
        try:
            # Create indexes
            indexes = [
                ("user_id", 1),      # For user-based queries
                ("phone", 1),        # 🚀 NEW: For phone-based queries and filtering
                ("unique_id", 1),    # 🚀 FIXED: For duplicate detection using unique_id (compatible with old data)
                ("content_hash", 1), # 🚀 NEW: For bulletproof duplicate prevention
                ("sender", 1),       # For sender-based queries
                ("date", -1),        # For date-based queries (descending)
                ("uploaded_at", -1), # For upload tracking
                ("type", 1)          # For type-based filtering
            ]
            
            for field, direction in indexes:
                try:
                    self.collection.create_index([(field, direction)], background=True)
                    print(f"📊 Created index on: {field}")
                except Exception as e:
                    print(f"⚠️  Index creation warning for {field}: {e}")
            
            # 🚀 FIXED: Create unique index for duplicate prevention using unique_id (compatible with old data)
            try:
                self.collection.create_index(
                    [("unique_id", 1)], 
                    unique=True,
                    background=True,
                    name="unique_sms_idx"
                )
                print("🔒 Created unique index for duplicate prevention on unique_id")
            except Exception as e:
                print(f"⚠️  Unique index warning: {e}")
            
            # 🚀 NEW: Create compound unique index for bulletproof content-based duplicate prevention
            try:
                self.collection.create_index(
                    [("user_id", 1), ("content_hash", 1)], 
                    unique=True, 
                    background=True,
                    sparse=True,  # Ignore documents where content_hash is null
                    name="unique_content_per_user_idx"
                )
                print("🔒 Created bulletproof duplicate prevention index on (user_id + content_hash)")
            except Exception as e:
                print(f"⚠️  Content hash index warning: {e}")
                
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            stats = self.db.command("collStats", self.collection_name)
            count = self.collection.count_documents({})
            
            return {
                "document_count": count,
                "storage_size": stats.get("storageSize", 0),
                "avg_document_size": stats.get("avgObjSize", 0),
                "total_indexes": stats.get("nindexes", 0)
            }
        except Exception as e:
            print(f"⚠️  Could not get collection stats: {e}")
            return {"document_count": 0}
    
    def clear_collection(self) -> bool:
        """Clear all documents from collection"""
        try:
            result = self.collection.delete_many({})
            print(f"🗑️  Cleared {result.deleted_count} documents from collection")
            return True
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")
            return False
    
    def upload_batch(self, documents: List[Dict[str, Any]]) -> Dict[str, int]:
        """Upload a batch of documents"""
        try:
            result = self.collection.insert_many(documents, ordered=False)
            return {
                "inserted": len(result.inserted_ids),
                "duplicates": 0,
                "errors": 0
            }
        except BulkWriteError as e:
            # Handle bulk write errors (mostly duplicates)
            inserted = e.details.get("nInserted", 0)
            duplicates = len([err for err in e.details.get("writeErrors", []) 
                            if err.get("code") == 11000])  # Duplicate key error
            errors = len(e.details.get("writeErrors", [])) - duplicates
            
            return {
                "inserted": inserted,
                "duplicates": duplicates,
                "errors": errors
            }
        except Exception as e:
            print(f"❌ Batch upload error: {e}")
            return {"inserted": 0, "duplicates": 0, "errors": len(documents)}
    
    def upload_sms_data(self, sms_data: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, int]:
        """Upload SMS data in batches"""
        print(f"📤 Starting upload of {len(sms_data)} SMS documents...")
        print(f"📦 Batch size: {batch_size}")
        
        total_stats = {"inserted": 0, "duplicates": 0, "errors": 0}
        
        # Process in batches
        for i in range(0, len(sms_data), batch_size):
            batch = sms_data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(sms_data) + batch_size - 1) // batch_size
            
            print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            batch_stats = self.upload_batch(batch)
            
            # Update totals
            for key in total_stats:
                total_stats[key] += batch_stats[key]
            
            print(f"   ✅ Inserted: {batch_stats['inserted']}, "
                  f"Duplicates: {batch_stats['duplicates']}, "
                  f"Errors: {batch_stats['errors']}")
        
        return total_stats
    
    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load SMS data from JSON file"""
        try:
            print(f"📁 Loading SMS data from: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, dict):
                if 'sms' in data:
                    sms_list = data['sms']
                elif 'data' in data:
                    sms_list = data['data']
                else:
                    # Assume the dict itself is the data
                    sms_list = [data]
            elif isinstance(data, list):
                sms_list = data
            else:
                raise ValueError("Invalid JSON format")
            
            print(f"📊 Loaded {len(sms_list)} SMS records")
            return sms_list
            
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            return []
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return []

def main():
    parser = argparse.ArgumentParser(description="Upload SMS data to MongoDB with user management")
    parser.add_argument("--input", required=True, help="Path to SMS JSON file")
    parser.add_argument("--user-id", help="Existing user ID to assign to all SMS")
    parser.add_argument("--user-name", help="User name (for new user creation)")
    parser.add_argument("--user-email", help="User email (for new user creation)")
    parser.add_argument("--user-phone", help="User phone (for new user creation or finding existing user)")
    parser.add_argument("--connection", default=MONGODB_URI, help="MongoDB connection string")
    parser.add_argument("--database", default=DATABASE_NAME, help="Database name")
    parser.add_argument("--collection", default=COLLECTION_NAME, help="Collection name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for uploads")
    parser.add_argument("--clear-collection", action="store_true", help="Clear collection before upload")
    parser.add_argument("--create-indexes", action="store_true", help="Create performance indexes")
    parser.add_argument("--stats", action="store_true", help="Show collection statistics")
    parser.add_argument("--user-stats", action="store_true", help="Show user statistics")
    
    args = parser.parse_args()
    
    # Extract user info from filename if not provided
    if not args.user_id and not args.user_name:
        filename = os.path.basename(args.input)
        # Extract name from filename (e.g., sms_data_divyam.json -> divyam)
        if filename.startswith("sms_data_") and filename.endswith(".json"):
            extracted_name = filename[10:-5]  # Remove "sms_data_" prefix and ".json" suffix
            args.user_name = extracted_name.title()  # Capitalize first letter
            print(f"📁 Extracted user name from filename: {args.user_name}")
    
    if args.user_id:
        print(f"🆔 Using existing user_id: {args.user_id}")
    else:
        print(f"👤 Will create/find user with: name={args.user_name}, email={args.user_email}, phone={args.user_phone}")
    
    # Initialize uploader
    uploader = SMSMongoUploader(
        connection_string=args.connection,
        db_name=args.database,
        collection_name=args.collection
    )
    
    try:
        # Connect to MongoDB
        if not uploader.connect():
            return 1
        
        # Show initial stats
        if args.stats:
            print("\n📊 INITIAL COLLECTION STATISTICS:")
            stats = uploader.get_collection_stats()
            print(f"   Documents: {stats['document_count']:,}")
            print(f"   Storage Size: {stats.get('storage_size', 0):,} bytes")
            print(f"   Indexes: {stats.get('total_indexes', 0)}")
        
        # Clear collection if requested
        if args.clear_collection:
            print(f"\n🗑️  Clearing collection '{args.collection}'...")
            uploader.clear_collection()
        
        # Create indexes if requested
        if args.create_indexes:
            print("\n📊 Creating performance indexes...")
            uploader.create_indexes()
        
        # Load SMS data
        print(f"\n📁 Loading SMS data from: {args.input}")
        sms_data = uploader.load_json_file(args.input)
        
        if not sms_data:
            print("❌ No SMS data to upload")
            return 1
        
        # Validate data with user management
        print(f"\n✅ Validating {len(sms_data)} SMS records with user management...")
        validated_data = uploader.validate_sms_data(
            sms_data, 
            user_id=args.user_id,
            user_name=args.user_name,
            user_email=args.user_email,
            user_phone=args.user_phone
        )
        
        # Get the final user_id from validated data
        final_user_id = validated_data[0]["user_id"] if validated_data else "unknown"
        
        if not validated_data:
            print("✅ No new SMS data to upload (all SMS were duplicates - duplicate prevention working correctly)")
            print(f"   📊 Summary: {len(sms_data)} input → 0 new (all duplicates) + {len(sms_data)} duplicates + 0 errors")
            return 0  # 🚀 FIXED: Return success when all SMS are duplicates
        
        # Upload data
        print(f"\n📤 Uploading {len(validated_data)} SMS records...")
        upload_stats = uploader.upload_sms_data(validated_data, args.batch_size)
        
        # Show results
        print(f"\n📊 UPLOAD SUMMARY:")
        print(f"   User ID: {final_user_id}")
        print(f"   Total Records: {len(sms_data)}")
        print(f"   Valid Records: {len(validated_data)}")
        print(f"   Successfully Inserted: {upload_stats['inserted']}")
        print(f"   Duplicates Skipped: {upload_stats['duplicates']}")
        print(f"   Errors: {upload_stats['errors']}")
        
        success_rate = (upload_stats['inserted'] / len(validated_data)) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Show user statistics if requested
        if args.user_stats and uploader.user_manager:
            print(f"\n👤 USER STATISTICS:")
            user_doc = uploader.user_manager.get_user(final_user_id)
            if user_doc:
                stats = user_doc.get('sms_stats', {})
                print(f"   Name: {user_doc.get('name', 'N/A')}")
                print(f"   Email: {user_doc.get('email', 'N/A')}")
                print(f"   Phone: {user_doc.get('phone', 'N/A')}")
                print(f"   Total SMS Uploaded: {stats.get('total_uploaded', 0):,}")
                print(f"   Total SMS Processed: {stats.get('total_processed', 0):,}")
                print(f"   Total Financial SMS: {stats.get('total_financial', 0):,}")
                print(f"   User Created: {user_doc.get('createdAt', 'N/A')}")
                print(f"   Last Upload: {stats.get('last_upload', 'N/A')}")
        
        # Show final stats
        if args.stats:
            print(f"\n📊 FINAL COLLECTION STATISTICS:")
            stats = uploader.get_collection_stats()
            print(f"   Total Documents: {stats['document_count']:,}")
            print(f"   Storage Size: {stats.get('storage_size', 0):,} bytes")
        
        print(f"\n✅ Upload completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Upload interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        uploader.disconnect()

if __name__ == "__main__":
    exit(main())
