"""Task Scheduler — Priority-based task queuing and dispatch."""

import asyncio
import heapq
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class PriorityClass(Enum):
    """Priority classes for workflow lanes."""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class FairnessBudget:
    """Manages fairness budget for a priority class."""
    
    def __init__(self, priority_class: PriorityClass, max_concurrent: int = 10):
        self.priority_class = priority_class
        self.max_concurrent = max_concurrent
        self._running: Set[str] = set()
        self._total_dispatched = 0
    
    def can_dispatch(self) -> bool:
        """Check if a new task can be dispatched within budget."""
        return len(self._running) < self.max_concurrent
    
    def acquire_slot(self, task_id: str) -> bool:
        """Acquire a slot for task execution."""
        if self.can_dispatch():
            self._running.add(task_id)
            self._total_dispatched += 1
            return True
        return False
    
    def release_slot(self, task_id: str) -> None:
        """Release a slot after task completion."""
        self._running.discard(task_id)
    
    def get_utilization(self) -> float:
        """Get current utilization ratio."""
        return len(self._running) / self.max_concurrent if self.max_concurrent > 0 else 0.0


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    def push(self, item: Any, priority: int = 0) -> None:
        heapq.heappush(self._queue, (-priority, self._counter, item))
        self._counter += 1

    def pop(self) -> Optional[Any]:
        if self._queue:
            return heapq.heappop(self._queue)[2]
        return None

    def peek(self) -> Optional[Any]:
        if self._queue:
            return self._queue[0][2]
        return None

    def __len__(self) -> int:
        return len(self._queue)


class TaskScheduler:
    def __init__(self):
        self._queues: Dict[str, PriorityQueue] = {}
        self._scheduled: Dict[str, float] = {}
        self._in_flight: Dict[str, Dict] = {}
        self._max_retries = 3
        # Fairness budgets by priority class (#4604)
        self._fairness_budgets: Dict[PriorityClass, FairnessBudget] = {
            PriorityClass.URGENT: FairnessBudget(PriorityClass.URGENT, max_concurrent=20),
            PriorityClass.HIGH: FairnessBudget(PriorityClass.HIGH, max_concurrent=15),
            PriorityClass.NORMAL: FairnessBudget(PriorityClass.NORMAL, max_concurrent=10),
            PriorityClass.LOW: FairnessBudget(PriorityClass.LOW, max_concurrent=5),
        }

    def _get_priority_class(self, task: Dict) -> PriorityClass:
        """Extract priority class from task configuration."""
        priority = task.get("priority", 0)
        priority_class_str = task.get("priority_class", "normal").lower()
        
        # Map string to enum
        class_map = {
            "urgent": PriorityClass.URGENT,
            "high": PriorityClass.HIGH,
            "normal": PriorityClass.NORMAL,
            "low": PriorityClass.LOW,
        }
        
        # Also map numeric priorities
        if priority >= 100:
            return PriorityClass.URGENT
        elif priority >= 50:
            return PriorityClass.HIGH
        elif priority >= 10:
            return PriorityClass.NORMAL
        
        return class_map.get(priority_class_str, PriorityClass.NORMAL)

    def _can_dispatch_task(self, task: Dict) -> bool:
        """Check if task can be dispatched within fairness budget (#4604)."""
        priority_class = self._get_priority_class(task)
        budget = self._fairness_budgets.get(priority_class)
        
        if not budget:
            return True
        
        can_dispatch = budget.can_dispatch()
        if not can_dispatch:
            logger.warning(
                f"Fairness budget exceeded for {priority_class.value} class. "
                f"Utilization: {budget.get_utilization():.1%}"
            )
        return can_dispatch

    def enqueue(self, task: Dict, queue: str = "default", priority: int = 0) -> str:
        task_id = str(uuid4())
        task["id"] = task_id
        task["enqueued_at"] = time.time()
        task["retries"] = 0

        if queue not in self._queues:
            self._queues[queue] = PriorityQueue()
        self._queues[queue].push(task, priority)
        return task_id

    def schedule(self, task: Dict, delay: float, queue: str = "default", priority: int = 0) -> str:
        task_id = str(uuid4())
        task["id"] = task_id
        self._scheduled[task_id] = time.time() + delay
        return task_id

    async def dequeue(self, queue: str = "default", timeout: float = 1.0) -> Optional[Dict]:
        now = time.time()
        expired = [tid for tid, t in self._scheduled.items() if t <= now]
        for tid in expired:
            task = self._scheduled.pop(tid)
            if task:
                self.enqueue(task, queue)

        if queue in self._queues and len(self._queues[queue]) > 0:
            task = self._queues[queue].pop()
            if task:
                # Check fairness budget before dispatching (#4604)
                if not self._can_dispatch_task(task):
                    # Re-queue the task with same priority
                    self._queues[queue].push(task, task.get("priority", 0))
                    logger.debug(f"Task {task['id']} deferred due to fairness budget")
                    return None
                
                # Acquire slot in fairness budget
                priority_class = self._get_priority_class(task)
                budget = self._fairness_budgets.get(priority_class)
                if budget:
                    budget.acquire_slot(task["id"])
                
                self._in_flight[task["id"]] = task
                return task
        return None

    def complete(self, task_id: str) -> bool:
        task = self._in_flight.pop(task_id, None)
        if task:
            # Release fairness budget slot (#4604)
            priority_class = self._get_priority_class(task)
            budget = self._fairness_budgets.get(priority_class)
            if budget:
                budget.release_slot(task_id)
            return True
        return False

    def fail(self, task_id: str, queue: str = "default") -> bool:
        task = self._in_flight.pop(task_id, None)
        if task:
            # Release fairness budget slot on failure (#4604)
            priority_class = self._get_priority_class(task)
            budget = self._fairness_budgets.get(priority_class)
            if budget:
                budget.release_slot(task_id)
            
            task["retries"] += 1
            if task["retries"] < self._max_retries:
                self.enqueue(task, queue, priority=task.get("priority", 0))
                return True
        return False

    def get_fairness_stats(self) -> Dict[str, Dict]:
        """Get fairness budget utilization statistics."""
        return {
            pc.value: {
                "max_concurrent": budget.max_concurrent,
                "running": len(budget._running),
                "utilization": budget.get_utilization(),
                "total_dispatched": budget._total_dispatched,
            }
            for pc, budget in self._fairness_budgets.items()
        }

# 2019-04-25T08:37:12 update

# 2019-06-04T16:40:00 update

# 2019-07-11T12:01:28 update

# 2019-08-02T12:20:21 update

# 2019-08-23T10:38:50 update

# 2019-10-31T13:55:52 update

# 2019-11-04T20:12:32 update

# 2019-12-13T12:22:36 update

# 2020-02-01T10:32:37 update

# 2020-02-26T09:44:38 update

# 2020-03-09T19:00:55 update

# 2020-05-01T18:40:34 update

# 2020-05-12T15:10:31 update

# 2020-06-30T13:24:19 update

# 2020-09-22T16:00:45 update

# 2020-10-20T10:52:48 update

# 2020-10-21T12:18:08 update

# 2020-11-06T12:35:01 update

# 2020-12-09T08:09:33 update

# 2021-01-07T08:20:36 update

# 2021-10-02T15:23:16 update

# 2021-10-06T16:14:57 update

# 2021-10-06T09:27:41 update

# 2021-11-19T08:37:40 update

# 2022-03-01T16:39:54 update

# 2022-05-26T13:43:07 update

# 2022-06-02T10:50:58 update

# 2022-06-14T10:46:48 update

# 2022-07-31T16:44:34 update

# 2022-08-30T18:20:12 update

# 2022-11-04T14:47:03 update

# 2022-12-06T10:36:49 update

# 2022-12-22T13:21:12 update

# 2022-12-26T12:24:50 update

# 2023-03-09T08:09:55 update

# 2023-05-01T10:07:37 update

# 2023-06-08T14:32:15 update

# 2023-07-14T17:24:18 update

# 2023-12-14T08:38:31 update

# 2024-02-20T13:43:58 update

# 2024-03-24T08:52:42 update

# 2024-03-28T15:27:17 update

# 2024-03-29T18:10:33 update

# 2024-04-15T20:18:31 update

# 2024-05-27T13:11:52 update

# 2024-05-27T16:42:56 update

# 2024-06-20T13:03:45 update

# 2024-06-28T12:32:58 update

# 2024-07-10T14:10:16 update

# 2024-07-26T14:18:59 update

# 2024-08-12T08:21:05 update

# 2024-08-21T16:58:40 update

# 2024-09-27T19:54:30 update

# 2024-10-21T13:47:42 update

# 2024-11-11T09:19:27 update

# 2024-12-24T08:23:41 update

# 2025-02-14T10:35:15 update

# 2025-03-31T18:09:40 update

# 2025-06-21T17:32:49 update

# 2025-07-21T16:52:28 update

# 2025-08-20T19:45:16 update

# 2025-11-04T18:54:24 update

# 2025-12-09T20:17:36 update

# 2026-01-12T15:42:32 update

# 2026-01-23T14:41:20 update

# 2026-03-18T14:43:07 update

# 2026-04-13T11:43:19 update
