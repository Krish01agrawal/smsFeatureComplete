#!/usr/bin/env python3
"""
Reset User Data for Clean Testing
==================================

This script will:
1. Mark all SMS as is_processed = false in sms_data collection for a specific user
2. Delete all data from financial_transactions collection for the user  
3. Delete all data from sms_fin_rawdata collection for the user
4. Provide clean slate for testing the complete pipeline

Usage: python3 reset_user_data.py --user-id "usr_e2c5b6b5_20250921_210047_e27084c0"
"""

import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
from mongodb_operations import MongoDBOperations

# Load environment variables
load_dotenv()

def reset_user_data(user_id: str):
    """Reset all processing data for a specific user"""
    
    print(f"🔄 Resetting all data for user: {user_id}")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        print("📡 Connecting to MongoDB...")
        mongo_ops = MongoDBOperations()
        
        # Step 1: Reset is_processed = false for all SMS in sms_data collection
        print(f"📝 Resetting SMS processing status in sms_data collection...")
        
        # Update all SMS for this user to is_processed = false
        sms_update_result = mongo_ops.sms_collection.update_many(
            {"user_id": user_id},
            {
                "$set": {
                    "is_processed": False,
                    "processed_at": None
                }
            }
        )
        
        print(f"   ✅ Reset {sms_update_result.modified_count} SMS to is_processed = false")
        
        # Step 2: Delete all data from financial_transactions collection
        print(f"🗑️  Deleting financial transactions for user...")
        
        transactions_delete_result = mongo_ops.transactions_collection.delete_many(
            {"user_id": user_id}
        )
        
        print(f"   ✅ Deleted {transactions_delete_result.deleted_count} transactions from financial_transactions")
        
        # Step 3: Delete all data from sms_fin_rawdata collection  
        print(f"🗑️  Deleting financial raw SMS data for user...")
        
        fin_raw_delete_result = mongo_ops.fin_raw_collection.delete_many(
            {"user_id": user_id}
        )
        
        print(f"   ✅ Deleted {fin_raw_delete_result.deleted_count} records from sms_fin_rawdata")
        
        # Step 4: Reset user statistics
        print(f"📊 Resetting user statistics...")
        
        try:
            from user_manager import UserManager
            user_manager = UserManager()
            user_manager.connect()
            
            # Reset user stats to reflect only uploaded SMS
            sms_count = mongo_ops.sms_collection.count_documents({"user_id": user_id})
            
            user_update_result = user_manager.users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "sms_stats.total_processed": 0,
                        "sms_stats.total_financial": 0,
                        "sms_stats.last_processing": None,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            print(f"   ✅ Reset user statistics (keeping total_uploaded: {sms_count})")
            
        except Exception as e:
            print(f"   ⚠️  Warning: Could not reset user statistics: {e}")
        
        # Step 5: Verify the reset
        print(f"🔍 Verifying reset for user: {user_id}")
        
        # Count unprocessed SMS
        unprocessed_sms = mongo_ops.sms_collection.count_documents({
            "user_id": user_id,
            "is_processed": False
        })
        
        # Count remaining data
        remaining_transactions = mongo_ops.transactions_collection.count_documents({
            "user_id": user_id
        })
        
        remaining_fin_raw = mongo_ops.fin_raw_collection.count_documents({
            "user_id": user_id
        })
        
        print(f"   📊 Verification Results:")
        print(f"      Unprocessed SMS: {unprocessed_sms}")
        print(f"      Remaining transactions: {remaining_transactions}")
        print(f"      Remaining fin_raw records: {remaining_fin_raw}")
        
        if remaining_transactions == 0 and remaining_fin_raw == 0 and unprocessed_sms > 0:
            print(f"   ✅ Reset successful! Ready for clean pipeline testing")
            print(f"   🚀 You can now run: python3 mongodb_pipeline.py --user-id \"{user_id}\"")
        else:
            print(f"   ⚠️  Reset may be incomplete - please verify manually")
        
        return True
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if 'mongo_ops' in locals():
            mongo_ops.close_connection()

def main():
    parser = argparse.ArgumentParser(description='Reset user data for clean testing')
    parser.add_argument('--user-id', required=True, help='User ID to reset data for')
    parser.add_argument('--confirm', action='store_true', help='Confirm the reset operation')
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("⚠️  This will DELETE all processed data for the user!")
        print("   - Reset all SMS to is_processed = false")
        print("   - Delete all financial_transactions")  
        print("   - Delete all sms_fin_rawdata")
        print("   - Reset user statistics")
        print()
        confirm = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        if confirm.lower() != 'yes':
            print("❌ Reset cancelled")
            return 1
    
    success = reset_user_data(args.user_id)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
