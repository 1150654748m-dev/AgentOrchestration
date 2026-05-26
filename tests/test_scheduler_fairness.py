"""Tests for scheduler fairness budgets (#4604)."""

import pytest
import asyncio
from src.orchestrator.scheduler import (
    TaskScheduler, PriorityQueue, FairnessBudget, PriorityClass
)


class TestFairnessBudget:
    def test_can_dispatch_within_budget(self):
        """Test that tasks can be dispatched within budget limits."""
        budget = FairnessBudget(PriorityClass.NORMAL, max_concurrent=2)
        
        assert budget.can_dispatch() is True
        assert budget.acquire_slot("task-1") is True
        assert budget.can_dispatch() is True
        assert budget.acquire_slot("task-2") is True
        assert budget.can_dispatch() is False  # Budget exceeded
        assert budget.acquire_slot("task-3") is False

    def test_release_slot(self):
        """Test that releasing a slot allows new dispatches."""
        budget = FairnessBudget(PriorityClass.NORMAL, max_concurrent=1)
        
        assert budget.acquire_slot("task-1") is True
        assert budget.can_dispatch() is False
        
        budget.release_slot("task-1")
        assert budget.can_dispatch() is True
        assert budget.acquire_slot("task-2") is True

    def test_get_utilization(self):
        """Test utilization calculation."""
        budget = FairnessBudget(PriorityClass.NORMAL, max_concurrent=4)
        
        assert budget.get_utilization() == 0.0
        
        budget.acquire_slot("task-1")
        assert budget.get_utilization() == 0.25
        
        budget.acquire_slot("task-2")
        assert budget.get_utilization() == 0.5

    def test_release_nonexistent_task(self):
        """Test releasing a slot for a task that wasn't acquired."""
        budget = FairnessBudget(PriorityClass.NORMAL, max_concurrent=2)
        
        # Should not raise error
        budget.release_slot("nonexistent-task")
        assert budget.can_dispatch() is True


class TestTaskSchedulerFairness:
    @pytest.mark.asyncio
    async def test_urgent_tasks_have_higher_budget(self):
        """Test that urgent priority class has higher concurrency limit."""
        scheduler = TaskScheduler()
        
        urgent_budget = scheduler._fairness_budgets[PriorityClass.URGENT]
        normal_budget = scheduler._fairness_budgets[PriorityClass.NORMAL]
        
        assert urgent_budget.max_concurrent > normal_budget.max_concurrent

    @pytest.mark.asyncio
    async def test_task_deferred_when_budget_exceeded(self):
        """Test that tasks are deferred when fairness budget is exceeded (#4604)."""
        scheduler = TaskScheduler()
        
        # Set a very low budget for testing
        scheduler._fairness_budgets[PriorityClass.NORMAL] = FairnessBudget(
            PriorityClass.NORMAL, max_concurrent=1
        )
        
        # Enqueue and dequeue first task
        scheduler.enqueue({"name": "task-1", "priority_class": "normal"}, priority=0)
        task1 = await scheduler.dequeue()
        assert task1 is not None
        
        # Enqueue second task
        scheduler.enqueue({"name": "task-2", "priority_class": "normal"}, priority=0)
        
        # Second task should be deferred (returned to queue)
        task2 = await scheduler.dequeue()
        assert task2 is None  # Deferred due to budget

    @pytest.mark.asyncio
    async def test_task_dispatched_after_budget_release(self):
        """Test that tasks are dispatched after budget slots are released (#4604)."""
        scheduler = TaskScheduler()
        
        # Set a very low budget for testing
        scheduler._fairness_budgets[PriorityClass.NORMAL] = FairnessBudget(
            PriorityClass.NORMAL, max_concurrent=1
        )
        
        # Enqueue and complete first task
        scheduler.enqueue({"name": "task-1", "priority_class": "normal"}, priority=0)
        task1 = await scheduler.dequeue()
        assert task1 is not None
        
        # Complete first task to release budget
        scheduler.complete(task1["id"])
        
        # Now second task can be dispatched
        scheduler.enqueue({"name": "task-2", "priority_class": "normal"}, priority=0)
        task2 = await scheduler.dequeue()
        assert task2 is not None
        assert task2["name"] == "task-2"

    @pytest.mark.asyncio
    async def test_priority_class_mapping(self):
        """Test priority class mapping from task configuration."""
        scheduler = TaskScheduler()
        
        # Test string priority classes
        assert scheduler._get_priority_class({"priority_class": "urgent"}) == PriorityClass.URGENT
        assert scheduler._get_priority_class({"priority_class": "high"}) == PriorityClass.HIGH
        assert scheduler._get_priority_class({"priority_class": "normal"}) == PriorityClass.NORMAL
        assert scheduler._get_priority_class({"priority_class": "low"}) == PriorityClass.LOW
        
        # Test numeric priority mapping
        assert scheduler._get_priority_class({"priority": 100}) == PriorityClass.URGENT
        assert scheduler._get_priority_class({"priority": 50}) == PriorityClass.HIGH
        assert scheduler._get_priority_class({"priority": 10}) == PriorityClass.NORMAL
        assert scheduler._get_priority_class({"priority": 0}) == PriorityClass.NORMAL

    @pytest.mark.asyncio
    async def test_fail_releases_budget_slot(self):
        """Test that failing a task releases its fairness budget slot (#4604)."""
        scheduler = TaskScheduler()
        
        # Set a very low budget for testing
        scheduler._fairness_budgets[PriorityClass.NORMAL] = FairnessBudget(
            PriorityClass.NORMAL, max_concurrent=1
        )
        
        # Enqueue and dequeue task
        scheduler.enqueue({"name": "task-1", "priority_class": "normal"}, priority=0)
        task = await scheduler.dequeue()
        assert task is not None
        
        # Fail the task (should release budget)
        scheduler.fail(task["id"])
        
        # New task can now be dispatched
        scheduler.enqueue({"name": "task-2", "priority_class": "normal"}, priority=0)
        task2 = await scheduler.dequeue()
        assert task2 is not None

    def test_get_fairness_stats(self):
        """Test fairness statistics reporting."""
        scheduler = TaskScheduler()
        
        stats = scheduler.get_fairness_stats()
        
        assert "urgent" in stats
        assert "high" in stats
        assert "normal" in stats
        assert "low" in stats
        
        for pc, data in stats.items():
            assert "max_concurrent" in data
            assert "running" in data
            assert "utilization" in data
            assert "total_dispatched" in data


class TestRegressionUrgentWorkflowLanes:
    """Regression tests for urgent workflow lanes (#4604)."""
    
    @pytest.mark.asyncio
    async def test_urgent_tasks_not_blocked_by_normal(self):
        """Test that urgent tasks can still be dispatched when normal budget is full."""
        scheduler = TaskScheduler()
        
        # Fill up normal budget
        scheduler._fairness_budgets[PriorityClass.NORMAL] = FairnessBudget(
            PriorityClass.NORMAL, max_concurrent=1
        )
        scheduler.enqueue({"name": "normal-task", "priority_class": "normal"}, priority=0)
        normal_task = await scheduler.dequeue()
        assert normal_task is not None
        
        # Urgent task should still be dispatchable (separate budget)
        scheduler.enqueue({"name": "urgent-task", "priority_class": "urgent"}, priority=100)
        urgent_task = await scheduler.dequeue()
        assert urgent_task is not None
        assert urgent_task["name"] == "urgent-task"

    @pytest.mark.asyncio
    async def test_separate_budgets_by_priority_class(self):
        """Test that each priority class has independent budget (#4604)."""
        scheduler = TaskScheduler()
        
        # Set low budgets for all classes
        for pc in PriorityClass:
            scheduler._fairness_budgets[pc] = FairnessBudget(pc, max_concurrent=1)
        
        # Fill each budget
        tasks = []
        for pc in [PriorityClass.URGENT, PriorityClass.HIGH, PriorityClass.NORMAL]:
            scheduler.enqueue({"name": f"{pc.value}-task", "priority_class": pc.value}, priority=0)
            task = await scheduler.dequeue()
            assert task is not None, f"Should be able to dispatch {pc.value} task"
            tasks.append(task)
        
        # All three should be in flight (separate budgets)
        assert len(scheduler._in_flight) == 3
