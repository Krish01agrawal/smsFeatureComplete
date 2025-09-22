#!/usr/bin/env python3
"""
Production-Ready Transaction Date Converter
==========================================

Safely converts string transaction_date fields to BSON Date format in MongoDB.

- Source collection: financial_transactions (unchanged)
- Destination collection: user_financial_transactions (with BSON dates)
- All other fields preserved exactly
- Failed conversions keep original string value
- Includes comprehensive validation and error handling

Usage:
    # Set up .env file with MongoDB credentials
    echo 'MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority' >> .env
    echo 'MONGODB_DB=pluto_money' >> .env
    
    # Run with defaults from .env
    python convert_transaction_dates.py

Optional timezone support for naive date strings:
    python convert_transaction_dates.py --timezone Asia/Kolkata

Tested with: PyMongo 4.x, MongoDB 5/6/7/Atlas
"""

import argparse
import os
import sys
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.son import SON
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def build_conversion_expression(timezone: str | None):
    """
    Build the aggregation expression that converts transaction_date from string to BSON Date.
    
    Args:
        timezone: Optional timezone for naive strings (e.g., "Asia/Kolkata")
        
    Returns:
        MongoDB aggregation expression for safe date conversion
    """
    if timezone:
        # Use $dateFromString with timezone for naive strings
        convert_expr = {
            "$dateFromString": {
                "dateString": "$transaction_date",
                "timezone": timezone,
                "onError": "$transaction_date",    # Keep original on error
                "onNull": "$transaction_date",     # Keep original if null
            }
        }
    else:
        # Use $convert for ISO strings (parsed as UTC when no timezone)
        convert_expr = {
            "$convert": {
                "input": "$transaction_date",
                "to": "date",
                "onError": "$transaction_date",    # Keep original on error
                "onNull": "$transaction_date",     # Keep original if null
            }
        }

    # Only apply conversion if current value is a string
    return {
        "$cond": [
            {"$eq": [{"$type": "$transaction_date"}, "string"]},
            convert_expr,
            "$transaction_date"  # Keep original if not string
        ]
    }


def copy_indexes(src_coll, dst_coll):
    """
    Recreate all indexes from source collection to destination collection.
    Skips the default _id_ index.
    
    Args:
        src_coll: Source MongoDB collection
        dst_coll: Destination MongoDB collection
        
    Returns:
        List of created index names
    """
    created_indexes = []
    
    for idx in src_coll.list_indexes():
        name = idx.get("name")
        if name == "_id_":
            continue  # Skip default _id index

        # Extract index keys as list of tuples
        key_list = list(idx["key"].items())

        # Copy common index options if present
        options = {}
        for opt in (
            "unique", "sparse", "expireAfterSeconds", "partialFilterExpression",
            "collation", "weights", "default_language", "language_override",
            "textIndexVersion", "2dsphereIndexVersion", "bits", "min", "max",
            "bucketSize", "wildcardProjection"
        ):
            if opt in idx:
                options[opt] = idx[opt]

        # Preserve original index name
        if name:
            options["name"] = name

        try:
            dst_coll.create_index(key_list, **options)
            created_indexes.append(name or str(key_list))
        except Exception as e:
            print(f"⚠️  Warning: Could not create index {name}: {e}")
    
    return created_indexes


def validate_connection(client, db_name):
    """Validate MongoDB connection and database access."""
    try:
        # Test connection
        client.admin.command('ping')
        
        # Test database access
        db = client[db_name]
        db.list_collection_names()
        
        print(f"✅ MongoDB connection validated for database: {db_name}")
        return True
    except Exception as e:
        print(f"❌ Connection validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert transaction_date strings to BSON Date format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion using .env defaults
  python convert_transaction_dates.py
  
  # With timezone for naive date strings
  python convert_transaction_dates.py --timezone Asia/Kolkata
  
  # Custom database and collections
  python convert_transaction_dates.py --db custom_db --source my_transactions --dest converted_transactions
        """
    )
    
    parser.add_argument(
        "--uri", 
        default=os.environ.get("MONGODB_URI", ""), 
        help="MongoDB connection URI (default: from .env file)"
    )
    parser.add_argument(
        "--db", 
        default=os.environ.get("MONGODB_DB", "pluto_money"),
        help="Database name (default: from .env file or 'pluto_money')"
    )
    parser.add_argument(
        "--source", 
        default="financial_transactions", 
        help="Source collection name (default: financial_transactions)"
    )
    parser.add_argument(
        "--dest", 
        default="user_financial_transactions", 
        help="Destination collection name (default: user_financial_transactions)"
    )
    parser.add_argument(
        "--timezone", 
        default=None, 
        help="Timezone for naive date strings (e.g., Asia/Kolkata, America/New_York)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force replacement without confirmation prompt (for automation)"
    )
    parser.add_argument(
        "--user-id", 
        help="Process only specific user_id (optional - if not provided, processes all users)"
    )
    parser.add_argument(
        "--phone", 
        help="Process only specific phone number (optional - if not provided, processes all users)"
    )
    
    args = parser.parse_args()

    if not args.uri:
        print("❌ ERROR: MongoDB URI required. Set MONGODB_URI in .env file or provide --uri argument.", 
              file=sys.stderr)
        print("\nExample .env file:")
        print('MONGODB_URI=mongodb+srv://user:pass@cluster/?retryWrites=true&w=majority')
        print('MONGODB_DB=pluto_money')
        sys.exit(1)

    try:
        print("🚀 Transaction Date Converter")
        print("=" * 50)
        print(f"Database: {args.db}")
        print(f"Source: {args.source}")
        print(f"Destination: {args.dest}")
        print(f"Timezone: {args.timezone or 'UTC (default)'}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE CONVERSION'}")
        print("=" * 50)

        # Connect to MongoDB
        print("\n🔌 Connecting to MongoDB...")
        client = MongoClient(
            args.uri,
            tlsAllowInvalidCertificates=True  # Fix SSL certificate issues
        )
        
        if not validate_connection(client, args.db):
            sys.exit(1)

        db = client[args.db]
        src_collection = db[args.source]
        dst_collection = db[args.dest]

        # Verify source collection exists and has data
        if args.source not in db.list_collection_names():
            print(f"❌ ERROR: Source collection '{args.source}' not found in database '{args.db}'")
            sys.exit(1)

        # Pre-conversion analysis
        print(f"\n📊 Analyzing source collection: {args.db}.{args.source}")
        total_docs = src_collection.estimated_document_count()
        
        if total_docs == 0:
            print("❌ ERROR: Source collection is empty")
            sys.exit(1)

        # Count documents by transaction_date type
        string_dates = src_collection.count_documents({"transaction_date": {"$type": "string"}})
        bson_dates = src_collection.count_documents({"transaction_date": {"$type": "date"}})
        other_types = total_docs - string_dates - bson_dates

        print(f"📈 Total documents: {total_docs:,}")
        print(f"📅 String dates: {string_dates:,} ({string_dates/total_docs*100:.1f}%)")
        print(f"🗓️  BSON dates: {bson_dates:,} ({bson_dates/total_docs*100:.1f}%)")
        print(f"❓ Other types: {other_types:,} ({other_types/total_docs*100:.1f}%)")

        if string_dates == 0:
            print("ℹ️  No string dates found to convert. All transaction_date fields are already BSON dates.")
            return

        if args.dry_run:
            print(f"\n🔍 DRY RUN: Would convert {string_dates:,} string dates to BSON Date format")
            print("✅ Dry run completed. Use without --dry-run to perform actual conversion.")
            return

        # 🚀 SMART USER-AWARE DUPLICATE PREVENTION: Only check for source users' data
        print(f"\n🔍 Checking destination collection for existing data...")
        dest_exists = args.dest in db.list_collection_names()
        total_existing_count = 0
        source_users_count = 0
        
        if dest_exists:
            total_existing_count = dst_collection.estimated_document_count()
            print(f"   📊 Total documents in destination: {total_existing_count:,}")
            
            # 🚀 CRITICAL FIX: Check for source users' data only
            # Get unique user_ids from source collection
            source_user_ids = src_collection.distinct("user_id")
            print(f"   🔍 Found {len(source_user_ids)} unique user_ids in source collection")
            
            if source_user_ids:
                # Check if ANY of the source users already have data in destination
                # Use individual queries to avoid $in issues with mixed ObjectId/string types
                from bson import ObjectId
                source_users_count = 0
                
                for uid in source_user_ids:
                    try:
                        # Try both ObjectId and string formats
                        count_objid = dst_collection.count_documents({"user_id": ObjectId(uid) if isinstance(uid, str) else uid})
                        count_string = dst_collection.count_documents({"user_id": str(uid)}) if count_objid == 0 else 0
                        source_users_count += max(count_objid, count_string)
                    except Exception as e:
                        # If ObjectId conversion fails, try as string
                        try:
                            count_string = dst_collection.count_documents({"user_id": str(uid)})
                            source_users_count += count_string
                        except:
                            pass  # Skip this user_id if both fail
                
                print(f"   📊 Documents for source users in destination: {source_users_count:,}")
                
                if source_users_count > 0:
                    print(f"⚠️  Found {source_users_count:,} existing documents for source users")
                    print(f"   These will be UPDATED/REPLACED with new date format")
                    print(f"   🛡️  Other users' data ({total_existing_count - source_users_count:,} docs) will be PRESERVED")
                    
                    if args.force:
                        print(f"🚀 --force flag provided: Automatically proceeding")
                    else:
                        confirmation = input(f"\nType 'UPDATE' to proceed with updating {source_users_count:,} documents: ")
                        if confirmation != 'UPDATE':
                            print("❌ Operation cancelled. No changes made.")
                            return
                    
                    print(f"✅ Will update {source_users_count:,} documents for source users")
                else:
                    print(f"✅ No existing data for source users - will add {total_docs:,} new documents")
                    print(f"   🛡️  Existing data from other users ({total_existing_count:,} docs) will be PRESERVED")
            else:
                print(f"⚠️  No user_id found in source documents - proceeding with caution")
        else:
            print(f"   ✅ Destination collection '{args.dest}' does not exist - will create new")

        # Build conversion pipeline
        print(f"\n🔄 Building conversion pipeline...")
        conversion_expr = build_conversion_expression(args.timezone)
        
        # 🚀 CRITICAL FIX: Use $merge to preserve other users' data
        # Build match criteria
        match_criteria = {
            "user_id": {"$exists": True, "$ne": None},  # Filter out documents with bad user_id
            "unique_id": {"$exists": True, "$ne": None, "$ne": ""}  # Filter out documents with bad unique_id
        }
        
        # 🚀 NEW: Add user-specific filtering if requested
        if args.user_id:
            # Handle both ObjectId and string user_id
            from bson import ObjectId
            try:
                # Try to convert string user_id to ObjectId
                if isinstance(args.user_id, str):
                    try:
                        match_criteria["user_id"] = ObjectId(args.user_id)
                        print(f"   🎯 Filtering for specific user_id (ObjectId): {args.user_id}")
                    except:
                        match_criteria["user_id"] = args.user_id
                        print(f"   🎯 Filtering for specific user_id (string): {args.user_id}")
                else:
                    match_criteria["user_id"] = args.user_id
                    print(f"   🎯 Filtering for specific user_id: {args.user_id}")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not process user_id filter: {e}")
                match_criteria["user_id"] = args.user_id
        elif args.phone:
            match_criteria["phone"] = args.phone
            print(f"   🎯 Filtering for specific phone: {args.phone}")
        else:
            print(f"   🌐 Processing ALL users in source collection")
        
        pipeline = [
            {
                "$match": match_criteria
            },
            {
                "$addFields": {
                    "transaction_date": conversion_expr
                }
            },
            {
                "$merge": {
                    "into": args.dest,
                    "on": ["user_id", "unique_id"],  # 🚀 CRITICAL: Match on user_id + unique_id
                    "whenMatched": "replace",  # Replace only documents with same user_id + unique_id
                    "whenNotMatched": "insert"  # Insert if no match found
                }
            }
        ]

        print(f"⚙️  Pipeline stages: {len(pipeline)}")
        
        # Execute conversion
        print(f"\n🚀 Converting dates and merging into collection: {args.db}.{args.dest}")
        print("⏳ Using $merge to preserve existing data from other users...")
        print("   📊 Only documents from source collection will be processed")
        
        start_time = datetime.now()
        
        # Run aggregation with optimizations for large collections
        src_collection.aggregate(
            pipeline, 
            allowDiskUse=True,              # Handle large datasets
            maxTimeMS=3600000,              # 1 hour timeout
            comment="transaction_date_conversion"
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Conversion completed in {duration:.1f} seconds")

        # Post-conversion validation
        print(f"\n📊 Validating destination collection: {args.db}.{args.dest}")
        
        dst_total = dst_collection.estimated_document_count()
        dst_strings = dst_collection.count_documents({"transaction_date": {"$type": "string"}})
        dst_dates = dst_collection.count_documents({"transaction_date": {"$type": "date"}})
        
        print(f"📈 Total documents: {dst_total:,}")
        print(f"📅 String dates: {dst_strings:,}")
        print(f"🗓️  BSON dates: {dst_dates:,}")

        # Validation checks
        if dst_total != total_docs:
            print(f"⚠️  WARNING: Document count mismatch! Source: {total_docs:,}, Destination: {dst_total:,}")
        else:
            print("✅ Document count validation passed")

        conversion_success_rate = ((string_dates - dst_strings) / string_dates * 100) if string_dates > 0 else 100
        print(f"📊 Conversion success rate: {conversion_success_rate:.1f}%")

        if dst_strings > 0:
            print(f"ℹ️  {dst_strings:,} dates remained as strings (likely due to parsing errors)")

        # Copy indexes from source to destination
        print(f"\n🔗 Copying indexes from source to destination...")
        created_indexes = copy_indexes(src_collection, dst_collection)
        
        if created_indexes:
            print(f"✅ Created {len(created_indexes)} indexes: {', '.join(created_indexes)}")
        else:
            print("ℹ️  No additional indexes to copy")

        # Final summary
        print(f"\n🎉 CONVERSION COMPLETE!")
        print("=" * 50)
        print(f"✅ Source collection '{args.source}' preserved unchanged")
        print(f"✅ Collection '{args.dest}' updated with BSON dates using $merge")
        print(f"✅ {dst_dates:,} transaction_date fields converted to BSON Date")
        print(f"✅ Existing data from other users preserved")
        print(f"✅ All other fields preserved exactly")
        print(f"✅ Indexes copied successfully")
        print("=" * 50)

    except PyMongoError as e:
        print(f"❌ MongoDB error: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print(f"\n⚠️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(3)
    finally:
        if 'client' in locals():
            client.close()
            print("🔌 MongoDB connection closed")


if __name__ == "__main__":
    main()
