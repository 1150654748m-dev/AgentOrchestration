"""Webhook event delivery with idempotency support."""

import hashlib
import time
from typing import Dict, Optional, Set
from threading import Lock


class IdempotencyStore:
    """Store for tracking processed idempotency keys."""
    
    def __init__(self, ttl: int = 86400):
        """
        Initialize the idempotency store.
        
        Args:
            ttl: Time-to-live in seconds for idempotency keys (default: 24 hours)
        """
        self._ttl = ttl
        self._store: Dict[str, float] = {}
        self._lock = Lock()
    
    def _cleanup_expired(self) -> None:
        """Remove expired idempotency keys."""
        now = time.time()
        expired = [key for key, timestamp in self._store.items() if now - timestamp > self._ttl]
        for key in expired:
            del self._store[key]
    
    def is_processed(self, key: str) -> bool:
        """Check if an idempotency key has been processed."""
        with self._lock:
            self._cleanup_expired()
            return key in self._store
    
    def mark_processed(self, key: str) -> None:
        """Mark an idempotency key as processed."""
        with self._lock:
            self._store[key] = time.time()
    
    def clear(self) -> None:
        """Clear all stored keys (useful for testing)."""
        with self._lock:
            self._store.clear()


class WebhookEvent:
    """Represents a webhook event to be delivered."""
    
    def __init__(self, event_type: str, payload: Dict, event_id: Optional[str] = None):
        self.event_type = event_type
        self.payload = payload
        self.event_id = event_id or self._generate_event_id()
        self.timestamp = time.time()
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        data = f"{self.event_type}:{self.payload}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_idempotency_key(self) -> str:
        """
        Generate an idempotency key for this event.
        
        The key is based on event type and payload content to ensure
        identical events produce the same key.
        """
        # Sort payload keys for consistent hashing
        payload_str = str(sorted(self.payload.items()) if self.payload else "")
        data = f"{self.event_type}:{payload_str}"
        return hashlib.sha256(data.encode()).hexdigest()


class WebhookDelivery:
    """Handles webhook event delivery with idempotency support."""
    
    def __init__(self, idempotency_store: Optional[IdempotencyStore] = None):
        self._idempotency_store = idempotency_store or IdempotencyStore()
        self._delivered_events: Set[str] = set()
        self._lock = Lock()
    
    def deliver(self, event: WebhookEvent) -> Dict:
        """
        Deliver a webhook event with idempotency check.
        
        Args:
            event: The webhook event to deliver
            
        Returns:
            Dict with delivery status and metadata
        """
        idempotency_key = event.get_idempotency_key()
        
        # Check if this event has already been processed
        if self._idempotency_store.is_processed(idempotency_key):
            return {
                "status": "skipped",
                "reason": "duplicate",
                "event_id": event.event_id,
                "idempotency_key": idempotency_key,
                "message": "Event already processed"
            }
        
        # Mark as processed before delivery to prevent race conditions
        self._idempotency_store.mark_processed(idempotency_key)
        
        with self._lock:
            self._delivered_events.add(event.event_id)
        
        # Simulate delivery (in real implementation, this would make HTTP request)
        return {
            "status": "delivered",
            "event_id": event.event_id,
            "idempotency_key": idempotency_key,
            "timestamp": time.time(),
            "event_type": event.event_type
        }
    
    def is_delivered(self, event_id: str) -> bool:
        """Check if an event has been delivered."""
        with self._lock:
            return event_id in self._delivered_events
    
    def get_delivery_count(self) -> int:
        """Get the total number of delivered events."""
        with self._lock:
            return len(self._delivered_events)


class WebhookSubscription:
    """Manages webhook subscriptions and event delivery."""
    
    def __init__(self):
        self._subscriptions: Dict[str, Dict] = {}
        self._delivery_handler = WebhookDelivery()
        self._lock = Lock()
    
    def register(self, endpoint: str, event_types: list, subscription_id: Optional[str] = None) -> str:
        """
        Register a new webhook subscription.
        
        Args:
            endpoint: The URL to deliver events to
            event_types: List of event types to subscribe to
            subscription_id: Optional custom subscription ID
            
        Returns:
            The subscription ID
        """
        import uuid
        sub_id = subscription_id or str(uuid.uuid4())
        
        with self._lock:
            self._subscriptions[sub_id] = {
                "endpoint": endpoint,
                "event_types": event_types,
                "enabled": True,
                "created_at": time.time()
            }
        
        return sub_id
    
    def disable(self, subscription_id: str) -> bool:
        """Disable a subscription."""
        with self._lock:
            if subscription_id in self._subscriptions:
                self._subscriptions[subscription_id]["enabled"] = False
                return True
            return False
    
    def is_enabled(self, subscription_id: str) -> bool:
        """Check if a subscription is enabled."""
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            return sub is not None and sub.get("enabled", False)
    
    def send_event(self, event: WebhookEvent, subscription_id: str) -> Dict:
        """
        Send an event to a specific subscription.
        
        Args:
            event: The event to send
            subscription_id: The target subscription
            
        Returns:
            Delivery result
        """
        with self._lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                return {
                    "status": "failed",
                    "reason": "subscription_not_found",
                    "event_id": event.event_id
                }
            
            if not subscription.get("enabled", False):
                return {
                    "status": "failed",
                    "reason": "subscription_disabled",
                    "event_id": event.event_id
                }
            
            if event.event_type not in subscription["event_types"]:
                return {
                    "status": "failed",
                    "reason": "event_type_not_subscribed",
                    "event_id": event.event_id
                }
        
        # Create subscription-scoped idempotency key
        # This ensures the same event can be delivered to different subscriptions
        # but is idempotent within a single subscription
        scoped_key = f"{subscription_id}:{event.get_idempotency_key()}"
        
        # Check if this event has already been processed for this subscription
        if self._delivery_handler._idempotency_store.is_processed(scoped_key):
            return {
                "status": "skipped",
                "reason": "duplicate",
                "event_id": event.event_id,
                "message": "Event already processed for this subscription"
            }
        
        # Mark as processed before delivery to prevent race conditions
        self._delivery_handler._idempotency_store.mark_processed(scoped_key)
        
        with self._delivery_handler._lock:
            self._delivery_handler._delivered_events.add(event.event_id)
        
        # Simulate delivery (in real implementation, this would make HTTP request)
        return {
            "status": "delivered",
            "event_id": event.event_id,
            "idempotency_key": scoped_key,
            "timestamp": time.time(),
            "event_type": event.event_type
        }


# Global instance for application-wide use
webhook_delivery = WebhookDelivery()
