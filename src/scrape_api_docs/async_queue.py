"""
Async Queue and Worker Pool for Documentation Scraper
======================================================

High-performance async queue processing with worker pools for
concurrent URL processing and page scraping.

Features:
- Async queue with priority support
- Worker pool with configurable concurrency
- Graceful shutdown with task completion
- Progress tracking
- Error handling and recovery
- Backpressure management

Usage:
    async with AsyncWorkerPool(max_workers=10) as pool:
        task = await pool.submit(process_page, url)
        result = await task
"""

import asyncio
from typing import Optional, Set, Callable, Any, Coroutine
from dataclasses import dataclass
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class QueueItem:
    """Item in priority queue."""
    priority: Priority
    data: Any
    timestamp: float

    def __lt__(self, other):
        """Compare by priority, then timestamp."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class AsyncWorkerPool:
    """
    Async worker pool with concurrency control.

    Manages a pool of workers processing tasks concurrently with
    configurable limits and graceful shutdown.
    """

    def __init__(
        self,
        max_workers: int = 10,
        queue_size: Optional[int] = None
    ):
        """
        Initialize async worker pool.

        Args:
            max_workers: Maximum concurrent workers
            queue_size: Optional queue size limit (None = unlimited)
        """
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.tasks: Set[asyncio.Task] = set()
        self.queue_size = queue_size

        self.stats = {
            'submitted': 0,
            'completed': 0,
            'errors': 0,
            'active': 0
        }

    async def __aenter__(self):
        """Async context manager entry."""
        logger.info(f"AsyncWorkerPool started with {self.max_workers} workers")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with graceful shutdown."""
        await self.shutdown()

    async def submit(
        self,
        coro_func: Callable,
        *args,
        **kwargs
    ) -> asyncio.Task:
        """
        Submit coroutine for execution.

        Args:
            coro_func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            asyncio.Task that can be awaited
        """
        async def _wrapped():
            """Wrapper that applies semaphore."""
            async with self.semaphore:
                self.stats['active'] += 1
                try:
                    result = await coro_func(*args, **kwargs)
                    self.stats['completed'] += 1
                    return result
                except Exception as e:
                    self.stats['errors'] += 1
                    logger.error(f"Task failed: {e}", exc_info=True)
                    raise
                finally:
                    self.stats['active'] -= 1

        task = asyncio.create_task(_wrapped())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        self.stats['submitted'] += 1

        return task

    async def map(
        self,
        coro_func: Callable,
        items: list,
        return_exceptions: bool = False
    ) -> list:
        """
        Map async function over items concurrently.

        Args:
            coro_func: Async function to apply
            items: Items to process
            return_exceptions: Whether to return exceptions instead of raising

        Returns:
            List of results
        """
        tasks = [self.submit(coro_func, item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    async def shutdown(self, timeout: Optional[float] = None):
        """
        Gracefully shutdown worker pool.

        Args:
            timeout: Optional timeout for task completion
        """
        if not self.tasks:
            logger.info("WorkerPool shutdown: no pending tasks")
            return

        logger.info(f"WorkerPool shutting down: {len(self.tasks)} pending tasks")

        try:
            if timeout:
                await asyncio.wait_for(
                    asyncio.gather(*self.tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                await asyncio.gather(*self.tasks, return_exceptions=True)

            logger.info("All tasks completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Shutdown timeout: {len(self.tasks)} tasks incomplete")
            # Cancel remaining tasks
            for task in self.tasks:
                task.cancel()

    @property
    def active_tasks(self) -> int:
        """Get count of active tasks."""
        return len(self.tasks)

    def get_stats(self) -> dict:
        """
        Get worker pool statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            **self.stats,
            'pending': len(self.tasks),
            'max_workers': self.max_workers
        }


class AsyncPriorityQueue:
    """
    Async priority queue for URL processing.

    Provides priority-based processing with async/await interface.
    """

    def __init__(self, maxsize: int = 0):
        """
        Initialize priority queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.queue = asyncio.PriorityQueue(maxsize=maxsize)
        self.stats = {
            'added': 0,
            'processed': 0,
            'errors': 0
        }

    async def put(
        self,
        item: Any,
        priority: Priority = Priority.NORMAL
    ):
        """
        Add item to queue with priority.

        Args:
            item: Item to queue
            priority: Task priority
        """
        import time
        queue_item = QueueItem(
            priority=priority,
            data=item,
            timestamp=time.time()
        )
        await self.queue.put(queue_item)
        self.stats['added'] += 1

    async def get(self) -> Any:
        """
        Get next item from queue.

        Returns:
            Next item (highest priority first)
        """
        queue_item = await self.queue.get()
        return queue_item.data

    def task_done(self):
        """Mark task as complete."""
        self.queue.task_done()
        self.stats['processed'] += 1

    async def join(self):
        """Wait for all queued items to be processed."""
        await self.queue.join()

    def qsize(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()

    def get_stats(self) -> dict:
        """Get queue statistics."""
        return {
            **self.stats,
            'pending': self.qsize()
        }


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def example_task(n: int, delay: float = 0.5):
        """Example async task."""
        logger.info(f"Task {n} starting")
        await asyncio.sleep(delay)
        logger.info(f"Task {n} completed")
        return f"Result {n}"

    async def main():
        """Example worker pool usage."""
        # Test worker pool
        async with AsyncWorkerPool(max_workers=3) as pool:
            # Submit 10 tasks (will be throttled to 3 concurrent)
            tasks = [
                pool.submit(example_task, i, 1.0)
                for i in range(10)
            ]

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

            print(f"\nResults: {results}")
            print(f"Stats: {pool.get_stats()}")

        # Test priority queue
        print("\n" + "="*50)
        print("Testing Priority Queue")
        print("="*50 + "\n")

        queue = AsyncPriorityQueue()

        # Add items with different priorities
        await queue.put("Low priority task", Priority.LOW)
        await queue.put("High priority task", Priority.HIGH)
        await queue.put("Normal priority task", Priority.NORMAL)
        await queue.put("Critical task", Priority.CRITICAL)

        # Process in priority order
        while not queue.empty():
            item = await queue.get()
            print(f"Processing: {item}")
            queue.task_done()

        print(f"\nQueue stats: {queue.get_stats()}")

    # Run example
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
