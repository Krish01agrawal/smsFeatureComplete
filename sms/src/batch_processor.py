"""
Batch Processor for SMS Transaction Analysis
Handles large-scale processing of 10,000+ users with parallel processing and memory optimization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Generator
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading
import time
import psutil
import gc
from pathlib import Path

try:
    from .config import get_config
except ImportError:
    from config import get_config

try:
    from .cache_manager import cache_manager
except ImportError:
    from cache_manager import cache_manager

logger = logging.getLogger(__name__)

class BatchProcessor:
    """High-performance batch processor for large-scale data processing."""
    
    def __init__(self):
        """Initialize batch processor."""
        # Configuration
        self.user_batch_size = get_config('scalability.user_batch_size', 100)
        self.transaction_batch_size = get_config('scalability.transaction_batch_size', 1000)
        self.max_workers = get_config('scalability.max_workers', 4)
        self.parallel_processing = get_config('scalability.parallel_processing', True)
        self.memory_limit_mb = get_config('performance_limits.memory_limit_mb', 2048)
        
        # Performance monitoring
        self.processing_stats = {
            'total_users_processed': 0,
            'total_transactions_processed': 0,
            'total_processing_time': 0,
            'batch_processing_times': [],
            'memory_usage_history': []
        }
        
        # Thread safety
        self.lock = threading.Lock()
        
        logger.info(f"Batch Processor initialized with {self.max_workers} workers")
    
    def process_users_batch(self, user_ids: List[str], 
                           process_function: Callable,
                           **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        Process users in batches with memory and performance optimization.
        
        Args:
            user_ids: List of user IDs to process
            process_function: Function to process each user
            **kwargs: Additional arguments for process_function
            
        Yields:
            Processing results for each batch
        """
        total_users = len(user_ids)
        logger.info(f"Starting batch processing of {total_users} users")
        
        start_time = time.time()
        
        # Process users in batches
        for i in range(0, total_users, self.user_batch_size):
            batch_start_time = time.time()
            batch_user_ids = user_ids[i:i + self.user_batch_size]
            
            logger.info(f"Processing batch {i//self.user_batch_size + 1}/{(total_users-1)//self.user_batch_size + 1}: "
                       f"users {i+1}-{min(i+self.user_batch_size, total_users)}")
            
            # Process batch
            batch_results = self._process_user_batch(batch_user_ids, process_function, **kwargs)
            
            # Update statistics
            with self.lock:
                self.processing_stats['total_users_processed'] += len(batch_user_ids)
                self.processing_stats['batch_processing_times'].append(time.time() - batch_start_time)
                self.processing_stats['memory_usage_history'].append(self._get_memory_usage())
            
            # Yield results
            yield {
                'batch_number': i//self.user_batch_size + 1,
                'users_processed': len(batch_user_ids),
                'results': batch_results,
                'processing_time': time.time() - batch_start_time,
                'memory_usage_mb': self._get_memory_usage()
            }
            
            # Memory cleanup
            self._cleanup_memory()
            
            # Progress update
            progress = (i + len(batch_user_ids)) / total_users * 100
            logger.info(f"Progress: {progress:.1f}% ({i + len(batch_user_ids)}/{total_users} users)")
        
        # Final statistics
        total_time = time.time() - start_time
        with self.lock:
            self.processing_stats['total_processing_time'] = total_time
        
        logger.info(f"Batch processing completed in {total_time:.2f} seconds")
    
    def _process_user_batch(self, user_ids: List[str], 
                           process_function: Callable,
                           **kwargs) -> List[Dict[str, Any]]:
        """Process a batch of users."""
        if self.parallel_processing and len(user_ids) > 1:
            return self._process_parallel(user_ids, process_function, **kwargs)
        else:
            return self._process_sequential(user_ids, process_function, **kwargs)
    
    def _process_parallel(self, user_ids: List[str], 
                         process_function: Callable,
                         **kwargs) -> List[Dict[str, Any]]:
        """Process users in parallel using ThreadPoolExecutor."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_user = {
                executor.submit(process_function, user_id, **kwargs): user_id 
                for user_id in user_ids
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    result = future.result()
                    results.append({
                        'user_id': user_id,
                        'result': result,
                        'status': 'success'
                    })
                except Exception as e:
                    logger.error(f"Error processing user {user_id}: {e}")
                    results.append({
                        'user_id': user_id,
                        'result': None,
                        'status': 'error',
                        'error': str(e)
                    })
        
        return results
    
    def _process_sequential(self, user_ids: List[str], 
                           process_function: Callable,
                           **kwargs) -> List[Dict[str, Any]]:
        """Process users sequentially."""
        results = []
        
        for user_id in user_ids:
            try:
                result = process_function(user_id, **kwargs)
                results.append({
                    'user_id': user_id,
                    'result': result,
                    'status': 'success'
                })
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                results.append({
                    'user_id': user_id,
                    'result': None,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def process_transactions_batch(self, df: pd.DataFrame, 
                                 process_function: Callable,
                                 **kwargs) -> pd.DataFrame:
        """
        Process transactions in batches for memory efficiency.
        
        Args:
            df: DataFrame with transaction data
            process_function: Function to process transactions
            **kwargs: Additional arguments for process_function
            
        Returns:
            Processed DataFrame
        """
        if df.empty:
            return df
        
        total_transactions = len(df)
        logger.info(f"Starting batch processing of {total_transactions} transactions")
        
        start_time = time.time()
        processed_chunks = []
        
        # Process in batches
        for i in range(0, total_transactions, self.transaction_batch_size):
            batch_start_time = time.time()
            chunk = df.iloc[i:i + self.transaction_batch_size].copy()
            
            logger.info(f"Processing transaction batch {i//self.transaction_batch_size + 1}/{(total_transactions-1)//self.transaction_batch_size + 1}: "
                       f"transactions {i+1}-{min(i+self.transaction_batch_size, total_transactions)}")
            
            # Process chunk
            processed_chunk = process_function(chunk, **kwargs)
            processed_chunks.append(processed_chunk)
            
            # Update statistics
            with self.lock:
                self.processing_stats['total_transactions_processed'] += len(chunk)
                self.processing_stats['batch_processing_times'].append(time.time() - batch_start_time)
            
            # Memory cleanup
            self._cleanup_memory()
        
        # Combine processed chunks
        result_df = pd.concat(processed_chunks, ignore_index=True)
        
        total_time = time.time() - start_time
        logger.info(f"Transaction batch processing completed in {total_time:.2f} seconds")
        
        return result_df
    
    def process_with_memory_monitoring(self, data: Any, 
                                     process_function: Callable,
                                     **kwargs) -> Any:
        """
        Process data with continuous memory monitoring.
        
        Args:
            data: Data to process
            process_function: Function to process data
            **kwargs: Additional arguments for process_function
            
        Returns:
            Processed data
        """
        initial_memory = self._get_memory_usage()
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        start_time = time.time()
        
        try:
            result = process_function(data, **kwargs)
            
            final_memory = self._get_memory_usage()
            processing_time = time.time() - start_time
            
            logger.info(f"Processing completed in {processing_time:.2f} seconds")
            logger.info(f"Memory usage: {initial_memory:.2f} MB → {final_memory:.2f} MB "
                       f"(Δ: {final_memory - initial_memory:+.2f} MB)")
            
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _cleanup_memory(self):
        """Clean up memory to prevent memory leaks."""
        current_memory = self._get_memory_usage()
        
        if current_memory > self.memory_limit_mb * 0.8:  # If over 80% of limit
            logger.warning(f"High memory usage detected: {current_memory:.2f} MB")
            
            # Force garbage collection
            gc.collect()
            
            # Check memory again
            new_memory = self._get_memory_usage()
            if new_memory < current_memory:
                logger.info(f"Memory cleanup successful: {current_memory:.2f} MB → {new_memory:.2f} MB")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with self.lock:
            stats = self.processing_stats.copy()
        
        # Calculate additional metrics
        if stats['batch_processing_times']:
            stats['avg_batch_time'] = np.mean(stats['batch_processing_times'])
            stats['total_batches'] = len(stats['batch_processing_times'])
        
        if stats['total_users_processed'] > 0:
            stats['users_per_second'] = stats['total_users_processed'] / stats['total_processing_time']
        
        if stats['total_transactions_processed'] > 0:
            stats['transactions_per_second'] = stats['total_transactions_processed'] / stats['total_processing_time']
        
        # Current memory usage
        stats['current_memory_usage_mb'] = self._get_memory_usage()
        
        return stats
    
    def reset_stats(self):
        """Reset processing statistics."""
        with self.lock:
            self.processing_stats = {
                'total_users_processed': 0,
                'total_transactions_processed': 0,
                'total_processing_time': 0,
                'batch_processing_times': [],
                'memory_usage_history': []
            }
        logger.info("Processing statistics reset")
    
    def optimize_batch_sizes(self, sample_data: pd.DataFrame) -> Dict[str, int]:
        """
        Optimize batch sizes based on data characteristics.
        
        Args:
            sample_data: Sample data to analyze
            
        Returns:
            Dictionary with optimized batch sizes
        """
        logger.info("Optimizing batch sizes based on data characteristics")
        
        # Analyze data size
        avg_transaction_size = sample_data.memory_usage(deep=True).sum() / len(sample_data)
        total_memory = self.memory_limit_mb * 1024 * 1024
        
        # Calculate optimal batch sizes
        optimal_transaction_batch = int(total_memory * 0.3 / avg_transaction_size)  # Use 30% of memory
        optimal_user_batch = max(10, optimal_transaction_batch // 100)  # Ensure at least 10 users
        
        # Apply limits
        optimal_transaction_batch = min(optimal_transaction_batch, 5000)
        optimal_user_batch = min(optimal_user_batch, 200)
        
        optimized_sizes = {
            'transaction_batch_size': optimal_transaction_batch,
            'user_batch_size': optimal_user_batch
        }
        
        logger.info(f"Optimized batch sizes: {optimized_sizes}")
        return optimized_sizes
    
    def health_check(self) -> Dict[str, Any]:
        """Check batch processor health."""
        current_memory = self._get_memory_usage()
        memory_usage_percent = (current_memory / self.memory_limit_mb) * 100
        
        health = {
            'status': 'healthy',
            'memory_usage_mb': current_memory,
            'memory_limit_mb': self.memory_limit_mb,
            'memory_usage_percent': memory_usage_percent,
            'parallel_processing': self.parallel_processing,
            'max_workers': self.max_workers
        }
        
        # Check memory usage
        if memory_usage_percent > 90:
            health['status'] = 'critical'
            health['warning'] = 'Memory usage critical'
        elif memory_usage_percent > 80:
            health['status'] = 'warning'
            health['warning'] = 'High memory usage'
        
        # Check processing stats
        stats = self.get_processing_stats()
        if stats['total_processing_time'] > 0:
            health['avg_users_per_second'] = stats.get('users_per_second', 0)
            health['avg_transactions_per_second'] = stats.get('transactions_per_second', 0)
        
        return health

# Global batch processor instance
batch_processor = BatchProcessor()

# Convenience functions
def process_users_batch(user_ids: List[str], 
                       process_function: Callable,
                       **kwargs) -> Generator[Dict[str, Any], None, None]:
    """Process users in batches."""
    return batch_processor.process_users_batch(user_ids, process_function, **kwargs)

def process_transactions_batch(df: pd.DataFrame, 
                             process_function: Callable,
                             **kwargs) -> pd.DataFrame:
    """Process transactions in batches."""
    return batch_processor.process_transactions_batch(df, process_function, **kwargs)

def get_batch_stats() -> Dict[str, Any]:
    """Get batch processing statistics."""
    return batch_processor.get_processing_stats()
