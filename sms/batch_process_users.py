#!/usr/bin/env python3
"""
Batch Processing Script for All Users
Processes and stores preprocessed data for all users in user_financial_transactions collection.
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
import time

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import required modules
try:
    from mongodb_loader import MongoDBLoader
    from preprocess import DataPreprocessor
    from processed_data_manager import ProcessedDataManager
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the DS/sms directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchProcessor:
    """Batch processor for processing all user data."""
    
    def __init__(self, date_range_months: int = 0):
        """
        Initialize batch processor.
        
        Args:
            date_range_months: Number of months of data to process (0 = ALL historical data)
        """
        self.date_range_months = date_range_months
        
        # Initialize components
        try:
            self.mongodb_loader = MongoDBLoader()
            self.processed_data_manager = ProcessedDataManager()
            self.preprocessor = DataPreprocessor(
                date_range_months=date_range_months,
                store_processed_data=True
            )
            
            logger.info("✅ BatchProcessor initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize BatchProcessor: {e}")
            raise
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status for all users."""
        logger.info("📊 Getting processing status for all users...")
        return self.processed_data_manager.get_processing_status()
    
    def process_all_users(self, force_reprocess: bool = False, max_users: int = None) -> Dict[str, Any]:
        """
        Process all users' transaction data.
        
        Args:
            force_reprocess: Force reprocessing even if processed data exists
            max_users: Maximum number of users to process (for testing)
            
        Returns:
            Processing results summary
        """
        logger.info("🚀 Starting batch processing for all users")
        start_time = datetime.now()
        
        # Get all users with raw data
        all_users = self.processed_data_manager.get_all_users_with_raw_data()
        
        if max_users:
            all_users = all_users[:max_users]
            logger.info(f"🔢 Limited to first {max_users} users for testing")
        
        logger.info(f"📋 Found {len(all_users)} users to process")
        
        # Get current processing status
        if not force_reprocess:
            status = self.get_processing_status()
            users_needing_processing = [
                user_id for user_id, details in status.get('user_details', {}).items()
                if details.get('needs_processing', True)
            ]
            
            if users_needing_processing:
                logger.info(f"📝 {len(users_needing_processing)} users need processing")
                all_users = [u for u in all_users if u in users_needing_processing]
            else:
                logger.info("✅ All users already have processed data")
                if not force_reprocess:
                    return self._create_summary([], 0, 0, 0, start_time)
        
        # Process each user
        results = {
            'successful': [],
            'failed': [],
            'skipped': [],
            'total_transactions_processed': 0
        }
        
        for i, user_id in enumerate(all_users, 1):
            logger.info(f"👤 Processing user {i}/{len(all_users)}: {user_id}")
            
            try:
                result = self.process_single_user(user_id, force_reprocess)
                
                if result['status'] == 'success':
                    results['successful'].append(user_id)
                    results['total_transactions_processed'] += result['transactions_processed']
                    logger.info(f"✅ User {user_id}: {result['transactions_processed']} transactions processed")
                    
                elif result['status'] == 'skipped':
                    results['skipped'].append(user_id)
                    logger.info(f"⏭️  User {user_id}: {result['reason']}")
                    
                else:
                    results['failed'].append(user_id)
                    logger.error(f"❌ User {user_id}: {result['error']}")
                    
            except Exception as e:
                results['failed'].append(user_id)
                logger.error(f"❌ Unexpected error processing user {user_id}: {e}")
            
            # Brief pause to avoid overwhelming the database
            time.sleep(0.1)
        
        # Create final summary
        summary = self._create_summary(
            results['successful'],
            len(results['failed']),
            len(results['skipped']),
            results['total_transactions_processed'],
            start_time
        )
        
        logger.info("🎉 Batch processing completed!")
        logger.info(f"📊 Summary: {summary['batch_processing_summary']['successful_users']} successful, {summary['batch_processing_summary']['failed_users']} failed, {summary['batch_processing_summary']['skipped_users']} skipped")
        
        return summary
    
    def process_single_user(self, user_id: str, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Process a single user's transaction data.
        
        Args:
            user_id: User identifier
            force_reprocess: Force reprocessing even if processed data exists
            
        Returns:
            Processing result
        """
        try:
            # Check if user already has processed data
            if not force_reprocess:
                existing_data = self.processed_data_manager.get_processed_data(user_id, limit=1)
                if existing_data is not None and not existing_data.empty:
                    return {
                        'status': 'skipped',
                        'reason': 'Already has processed data',
                        'transactions_processed': 0
                    }
            
            # Load raw data for user (always use raw data when force reprocessing)
            raw_df = self.mongodb_loader.get_user_transactions(user_id, force_raw_data=True)
            
            if raw_df.empty:
                return {
                    'status': 'skipped',
                    'reason': 'No raw data found',
                    'transactions_processed': 0
                }
            
            logger.info(f"📥 Loaded {len(raw_df)} raw transactions for user {user_id}")
            
            # Process the data
            processed_df = self.preprocessor.preprocess(raw_df, user_id=user_id)
            
            if processed_df.empty:
                return {
                    'status': 'failed',
                    'error': 'No data after preprocessing',
                    'transactions_processed': 0
                }
            
            return {
                'status': 'success',
                'transactions_processed': len(processed_df),
                'original_count': len(raw_df)
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing user {user_id}: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'transactions_processed': 0
            }
    
    def _create_summary(self, successful_users: List[str], failed_count: int, 
                       skipped_count: int, total_transactions: int, start_time: datetime) -> Dict[str, Any]:
        """Create processing summary."""
        end_time = datetime.now()
        duration = end_time - start_time
        
        return {
            'batch_processing_summary': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'successful_users': len(successful_users),
                'failed_users': failed_count,
                'skipped_users': skipped_count,
                'total_users_processed': len(successful_users) + failed_count + skipped_count,
                'total_transactions_processed': total_transactions,
                'date_range_months': self.date_range_months
            },
            'successful_user_ids': successful_users[:10],  # First 10 for brevity
            'processing_rate': f"{len(successful_users)}/{len(successful_users) + failed_count + skipped_count}" if (len(successful_users) + failed_count + skipped_count) > 0 else "0/0"
        }
    
    def cleanup_processed_data(self, user_id: str = None) -> bool:
        """
        Clean up processed data for a user or all users.
        
        Args:
            user_id: Specific user ID (if None, prompts for confirmation to delete all)
            
        Returns:
            Success status
        """
        if user_id:
            return self.processed_data_manager.delete_processed_data(user_id)
        else:
            # Dangerous operation - require confirmation
            confirm = input("⚠️  Are you sure you want to delete ALL processed data? (type 'DELETE ALL' to confirm): ")
            if confirm == "DELETE ALL":
                all_users = self.processed_data_manager.get_all_users_with_raw_data()
                for user in all_users:
                    self.processed_data_manager.delete_processed_data(user)
                logger.info(f"🗑️  Deleted processed data for {len(all_users)} users")
                return True
            else:
                logger.info("❌ Cleanup cancelled")
                return False

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch process user transaction data")
    parser.add_argument("--months", type=int, default=0, help="Number of months to process (default: 0 = ALL historical data)")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if data exists")
    parser.add_argument("--max-users", type=int, help="Maximum number of users to process (for testing)")
    parser.add_argument("--status-only", action="store_true", help="Only show processing status")
    parser.add_argument("--cleanup", type=str, help="Clean up processed data for user (or 'all')")
    
    args = parser.parse_args()
    
    try:
        processor = BatchProcessor(date_range_months=args.months)
        
        if args.cleanup:
            if args.cleanup == "all":
                processor.cleanup_processed_data()
            else:
                processor.cleanup_processed_data(args.cleanup)
            return
        
        if args.status_only:
            status = processor.get_processing_status()
            print("\n📊 PROCESSING STATUS REPORT")
            print("=" * 50)
            print(f"Total users: {status.get('total_users', 0)}")
            print(f"Users with processed data: {status.get('users_with_processed_data', 0)}")
            print(f"Users needing processing: {status.get('users_needing_processing', 0)}")
            
            if status.get('user_details'):
                print("\nTop 10 users by transaction count:")
                sorted_users = sorted(
                    status['user_details'].items(),
                    key=lambda x: x[1].get('raw_transactions', 0),
                    reverse=True
                )[:10]
                
                for user_id, details in sorted_users:
                    print(f"  {user_id}: {details.get('raw_transactions', 0)} raw, "
                          f"{details.get('processed_transactions', 0)} processed "
                          f"({details.get('processing_coverage', '0%')})")
            return
        
        # Run batch processing
        summary = processor.process_all_users(
            force_reprocess=args.force,
            max_users=args.max_users
        )
        
        print("\n🎉 BATCH PROCESSING COMPLETED")
        print("=" * 50)
        print(f"✅ Successful: {summary['batch_processing_summary']['successful_users']}")
        print(f"❌ Failed: {summary['batch_processing_summary']['failed_users']}")
        print(f"⏭️  Skipped: {summary['batch_processing_summary']['skipped_users']}")
        print(f"📊 Total transactions processed: {summary['batch_processing_summary']['total_transactions_processed']:,}")
        print(f"⏱️  Duration: {summary['batch_processing_summary']['duration_seconds']:.1f} seconds")
        
    except KeyboardInterrupt:
        logger.info("❌ Processing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Batch processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
