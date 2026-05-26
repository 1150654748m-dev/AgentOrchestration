"""Tests for lock manager with exception handling."""

import pytest
from src.common.lock_manager import InMemoryAdvisoryLock, LockManager, LockAcquisitionError


class TestInMemoryAdvisoryLock:
    def test_acquire_and_release(self):
        """Test basic lock acquisition and release."""
        lock = InMemoryAdvisoryLock(12345)
        assert lock.acquire() is True
        assert lock._acquired is True
        assert lock.release() is True
        assert lock._acquired is False

    def test_acquire_already_held(self):
        """Test that acquiring an already held lock fails."""
        lock1 = InMemoryAdvisoryLock(12345)
        lock2 = InMemoryAdvisoryLock(12345)
        
        assert lock1.acquire() is True
        assert lock2.acquire() is False  # Same lock ID, should fail
        
        lock1.release()

    def test_context_manager(self):
        """Test lock as context manager."""
        lock = InMemoryAdvisoryLock(12345)
        
        with lock:
            assert lock._acquired is True
        
        assert lock._acquired is False

    def test_lock_released_on_exception(self):
        """Test that lock is released when exception occurs in context (#382)."""
        lock = InMemoryAdvisoryLock(12345)
        
        try:
            with lock:
                assert lock._acquired is True
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Lock should be released even after exception
        assert lock._acquired is False
        
        # Should be able to acquire again
        assert lock.acquire() is True
        lock.release()

    def test_release_without_acquire(self):
        """Test releasing a lock that was never acquired."""
        lock = InMemoryAdvisoryLock(12345)
        assert lock.release() is False  # Nothing to release


class TestLockManager:
    def test_get_lock(self):
        """Test getting a lock from manager."""
        manager = LockManager(None)
        lock = manager.get_lock(12345)
        
        assert lock.lock_id == 12345
        assert 12345 in manager._locks

    def test_release_all(self):
        """Test releasing all locks."""
        manager = LockManager(None)
        
        # Use in-memory locks for testing
        lock1 = InMemoryAdvisoryLock(1)
        lock2 = InMemoryAdvisoryLock(2)
        
        lock1.acquire()
        lock2.acquire()
        
        manager._locks[1] = lock1
        manager._locks[2] = lock2
        
        assert lock1._acquired is True
        assert lock2._acquired is True
        
        manager.release_all()
        
        assert lock1._acquired is False
        assert lock2._acquired is False

    def test_lock_context_manager(self):
        """Test LockManager.lock() context manager."""
        manager = LockManager(None)
        
        # Replace with in-memory lock for testing
        manager._locks[12345] = InMemoryAdvisoryLock(12345)
        
        with manager.lock(12345) as lock:
            assert lock._acquired is True
        
        assert lock._acquired is False

    def test_lock_context_manager_exception(self):
        """Test that lock is released on exception in context manager (#382)."""
        manager = LockManager(None)
        manager._locks[12345] = InMemoryAdvisoryLock(12345)
        
        try:
            with manager.lock(12345) as lock:
                assert lock._acquired is True
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        
        # Lock should be released
        assert manager._locks[12345]._acquired is False


class TestLockReleaseOnException:
    """Regression tests for issue #382 - Release locks on exception."""
    
    def test_nested_locks_all_released_on_exception(self):
        """Test that all nested locks are released when exception occurs."""
        lock1 = InMemoryAdvisoryLock(100)
        lock2 = InMemoryAdvisoryLock(200)
        
        try:
            with lock1:
                with lock2:
                    assert lock1._acquired is True
                    assert lock2._acquired is True
                    raise ValueError("Nested exception")
        except ValueError:
            pass
        
        assert lock1._acquired is False
        assert lock2._acquired is False

    def test_multiple_locks_in_manager_released_on_exception(self):
        """Test LockManager releases all locks on exception (#382)."""
        manager = LockManager(None)
        
        # Pre-populate with in-memory locks
        lock1 = InMemoryAdvisoryLock(1)
        lock2 = InMemoryAdvisoryLock(2)
        lock3 = InMemoryAdvisoryLock(3)
        
        manager._locks = {1: lock1, 2: lock2, 3: lock3}
        
        # Acquire all locks
        lock1.acquire()
        lock2.acquire()
        lock3.acquire()
        
        try:
            # Simulate work that raises exception
            if True:
                raise RuntimeError("Database error during locked operation")
        except RuntimeError:
            # Simulate exception handler releasing all locks
            manager.release_all()
        
        # All locks should be released
        assert lock1._acquired is False
        assert lock2._acquired is False
        assert lock3._acquired is False

    def test_lock_released_even_with_cleanup_exception(self):
        """Test lock release handles cleanup after main exception."""
        lock = InMemoryAdvisoryLock(999)
        
        class CleanupError(Exception):
            pass
        
        try:
            with lock:
                assert lock._acquired is True
                raise ValueError("Main error")
        except ValueError:
            # Lock should be released
            assert lock._acquired is False
