"""Lock Manager — Database advisory lock management with exception handling."""

import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class AdvisoryLock:
    """Represents a database advisory lock."""
    
    def __init__(self, lock_id: int, connection):
        self.lock_id = lock_id
        self.connection = connection
        self._acquired = False
    
    def acquire(self) -> bool:
        """Acquire the advisory lock."""
        try:
            # PostgreSQL advisory lock: pg_advisory_lock
            # Returns immediately if lock is available
            cursor = self.connection.cursor()
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (self.lock_id,))
            result = cursor.fetchone()
            self._acquired = result[0] if result else False
            if self._acquired:
                logger.debug(f"Acquired advisory lock {self.lock_id}")
            return self._acquired
        except Exception as e:
            logger.error(f"Failed to acquire lock {self.lock_id}: {e}")
            return False
    
    def release(self) -> bool:
        """Release the advisory lock."""
        if not self._acquired:
            return True
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT pg_advisory_unlock(%s)", (self.lock_id,))
            result = cursor.fetchone()
            released = result[0] if result else False
            if released:
                self._acquired = False
                logger.debug(f"Released advisory lock {self.lock_id}")
            return released
        except Exception as e:
            logger.error(f"Failed to release lock {self.lock_id}: {e}")
            return False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure lock is released on exit, even if exception occurred."""
        self.release()
        # Don't suppress exceptions
        return False


class LockManager:
    """Manages database advisory locks with automatic cleanup."""
    
    def __init__(self, connection):
        self.connection = connection
        self._locks: dict = {}
    
    def get_lock(self, lock_id: int) -> AdvisoryLock:
        """Get or create an advisory lock."""
        if lock_id not in self._locks:
            self._locks[lock_id] = AdvisoryLock(lock_id, self.connection)
        return self._locks[lock_id]
    
    def release_all(self) -> None:
        """Release all acquired locks."""
        for lock_id, lock in list(self._locks.items()):
            if lock._acquired:
                lock.release()
        self._locks.clear()
    
    @contextmanager
    def lock(self, lock_id: int):
        """Context manager for acquiring and releasing a lock."""
        advisory_lock = self.get_lock(lock_id)
        try:
            if advisory_lock.acquire():
                yield advisory_lock
            else:
                raise LockAcquisitionError(f"Could not acquire lock {lock_id}")
        finally:
            advisory_lock.release()


class LockAcquisitionError(Exception):
    """Raised when lock acquisition fails."""
    pass


# For non-PostgreSQL environments, provide an in-memory lock implementation
class InMemoryAdvisoryLock:
    """In-memory advisory lock for testing and non-PostgreSQL environments."""
    
    _locks: set = set()
    
    def __init__(self, lock_id: int, connection=None):
        self.lock_id = lock_id
        self.connection = connection
        self._acquired = False
    
    def acquire(self) -> bool:
        if self.lock_id in self._locks:
            return False
        self._locks.add(self.lock_id)
        self._acquired = True
        logger.debug(f"Acquired in-memory lock {self.lock_id}")
        return True
    
    def release(self) -> bool:
        if self._acquired and self.lock_id in self._locks:
            self._locks.discard(self.lock_id)
            self._acquired = False
            logger.debug(f"Released in-memory lock {self.lock_id}")
            return True
        return False
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
