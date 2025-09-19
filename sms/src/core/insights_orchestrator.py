#!/usr/bin/env python3
"""
Optimized Insights Orchestrator
Follows SOLID principles for better maintainability and performance.
"""

import asyncio
import concurrent.futures
from typing import Dict, List, Optional, Callable
import pandas as pd
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class AnalysisTask:
    """Represents an analysis task with priority and dependencies."""
    name: str
    function: Callable
    priority: int = 1
    dependencies: List[str] = None
    cache_key: str = None
    timeout: int = 30

class InsightsOrchestrator:
    """
    Optimized orchestrator that manages analysis tasks efficiently.
    Follows Single Responsibility Principle and Dependency Inversion.
    """
    
    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager
        self.tasks: Dict[str, AnalysisTask] = {}
        self.results: Dict[str, any] = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
    def register_task(self, task: AnalysisTask):
        """Register an analysis task."""
        self.tasks[task.name] = task
        
    async def execute_analysis(self, df: pd.DataFrame, progress_callback=None) -> Dict:
        """
        Execute analysis tasks in parallel with dependency management.
        
        Args:
            df: Input DataFrame
            progress_callback: Callback for progress updates
            
        Returns:
            Dictionary with all analysis results
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return {}
        
        logger.info(f"Starting optimized analysis for {len(df)} transactions")
        
        # Check cache first
        if self.cache_manager:
            cached_results = self.cache_manager.get_cached_results(df)
            if cached_results:
                logger.info("Using cached results")
                return cached_results
        
        # Execute tasks in parallel based on dependencies
        await self._execute_tasks_parallel(df, progress_callback)
        
        # Cache results
        if self.cache_manager:
            self.cache_manager.cache_results(df, self.results)
        
        return self.results
    
    async def _execute_tasks_parallel(self, df: pd.DataFrame, progress_callback=None):
        """Execute tasks in parallel with dependency resolution."""
        completed_tasks = set()
        total_tasks = len(self.tasks)
        completed_count = 0
        
        # Sort tasks by priority and dependencies
        sorted_tasks = self._sort_tasks_by_dependencies()
        
        # Execute tasks in batches
        for batch in self._create_task_batches(sorted_tasks):
            # Execute batch in parallel
            loop = asyncio.get_event_loop()
            futures = []
            
            for task_name in batch:
                task = self.tasks[task_name]
                if self._can_execute_task(task, completed_tasks):
                    future = loop.run_in_executor(
                        self.executor, 
                        self._execute_single_task, 
                        task, df
                    )
                    futures.append((task_name, future))
            
            # Wait for batch completion
            for task_name, future in futures:
                try:
                    result = await asyncio.wait_for(future, timeout=30)
                    self.results[task_name] = result
                    completed_tasks.add(task_name)
                    completed_count += 1
                    
                    if progress_callback:
                        progress = (completed_count / total_tasks) * 100
                        progress_callback(progress, f"Completed {task_name}")
                        
                except asyncio.TimeoutError:
                    logger.error(f"Task {task_name} timed out")
                    self.results[task_name] = None
                except Exception as e:
                    logger.error(f"Task {task_name} failed: {e}")
                    self.results[task_name] = None
    
    def _execute_single_task(self, task: AnalysisTask, df: pd.DataFrame):
        """Execute a single analysis task."""
        try:
            logger.info(f"Executing task: {task.name}")
            result = task.function(df)
            logger.info(f"Task {task.name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            raise
    
    def _sort_tasks_by_dependencies(self) -> List[str]:
        """Sort tasks based on dependencies using topological sort."""
        # Simple topological sort implementation
        in_degree = {name: 0 for name in self.tasks}
        graph = {name: [] for name in self.tasks}
        
        # Build dependency graph
        for task_name, task in self.tasks.items():
            if task.dependencies:
                for dep in task.dependencies:
                    if dep in self.tasks:
                        graph[dep].append(task_name)
                        in_degree[task_name] += 1
        
        # Topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        sorted_tasks = []
        
        while queue:
            task_name = queue.pop(0)
            sorted_tasks.append(task_name)
            
            for dependent in graph[task_name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return sorted_tasks
    
    def _create_task_batches(self, sorted_tasks: List[str]) -> List[List[str]]:
        """Create batches of tasks that can run in parallel."""
        batches = []
        current_batch = []
        
        for task_name in sorted_tasks:
            task = self.tasks[task_name]
            current_batch.append(task_name)
            
            # Start new batch if current is full or has high priority tasks
            if len(current_batch) >= 3 or task.priority == 1:
                batches.append(current_batch)
                current_batch = []
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _can_execute_task(self, task: AnalysisTask, completed_tasks: set) -> bool:
        """Check if a task can be executed based on dependencies."""
        if not task.dependencies:
            return True
        
        return all(dep in completed_tasks for dep in task.dependencies)

class CacheManager:
    """Manages caching of analysis results for performance optimization."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
    def get_cache_key(self, df: pd.DataFrame) -> str:
        """Generate cache key based on data hash."""
        # Simple hash based on data shape and first few rows
        data_hash = hash((len(df), df.iloc[:10].to_string()))
        return f"analysis_{data_hash}"
    
    def get_cached_results(self, df: pd.DataFrame) -> Optional[Dict]:
        """Get cached results if available and valid."""
        cache_key = self.get_cache_key(df)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if self._is_cache_valid(cached_data):
                return cached_data['results']
        return None
    
    def cache_results(self, df: pd.DataFrame, results: Dict):
        """Cache analysis results."""
        cache_key = self.get_cache_key(df)
        self.cache[cache_key] = {
            'results': results,
            'timestamp': pd.Timestamp.now()
        }
    
    def _is_cache_valid(self, cached_data: Dict) -> bool:
        """Check if cached data is still valid."""
        timestamp = cached_data['timestamp']
        age = (pd.Timestamp.now() - timestamp).total_seconds()
        return age < self.cache_ttl

class AnalysisTaskFactory:
    """Factory for creating analysis tasks following Factory Pattern."""
    
    @staticmethod
    def create_basic_stats_task() -> AnalysisTask:
        """Create basic statistics analysis task."""
        return AnalysisTask(
            name="basic_stats",
            function=lambda df: df.describe(),
            priority=1,
            cache_key="basic_stats"
        )
    
    @staticmethod
    def create_financial_analysis_task() -> AnalysisTask:
        """Create financial analysis task."""
        return AnalysisTask(
            name="financial_analysis",
            function=lambda df: {"total_spend": df['amount'].sum()},
            priority=1,
            cache_key="financial_analysis"
        )
    
    @staticmethod
    def create_behavioral_analysis_task() -> AnalysisTask:
        """Create behavioral analysis task."""
        return AnalysisTask(
            name="behavioral_analysis",
            function=lambda df: {"behavioral_insights": "analyzed"},
            priority=2,
            dependencies=["basic_stats"],
            cache_key="behavioral_analysis"
        ) 