"""Tests for webhook event delivery with idempotency support."""

import pytest
import time
from src.common.webhook import (
    IdempotencyStore,
    WebhookEvent,
    WebhookDelivery,
    WebhookSubscription
)


class TestIdempotencyStore:
    def test_is_processed_new_key(self):
        store = IdempotencyStore()
        assert not store.is_processed("new-key")
    
    def test_mark_processed(self):
        store = IdempotencyStore()
        store.mark_processed("test-key")
        assert store.is_processed("test-key")
    
    def test_cleanup_expired_keys(self):
        store = IdempotencyStore(ttl=0.1)  # 100ms TTL for testing
        store.mark_processed("expiring-key")
        assert store.is_processed("expiring-key")
        time.sleep(0.15)
        assert not store.is_processed("expiring-key")
    
    def test_clear(self):
        store = IdempotencyStore()
        store.mark_processed("key1")
        store.mark_processed("key2")
        store.clear()
        assert not store.is_processed("key1")
        assert not store.is_processed("key2")


class TestWebhookEvent:
    def test_event_id_generation(self):
        event = WebhookEvent("test.event", {"data": "value"})
        assert event.event_id is not None
        assert len(event.event_id) == 16
    
    def test_idempotency_key_consistency(self):
        """Same event data should produce same idempotency key."""
        event1 = WebhookEvent("user.created", {"user_id": 123})
        event2 = WebhookEvent("user.created", {"user_id": 123})
        assert event1.get_idempotency_key() == event2.get_idempotency_key()
    
    def test_idempotency_key_uniqueness(self):
        """Different event data should produce different idempotency keys."""
        event1 = WebhookEvent("user.created", {"user_id": 123})
        event2 = WebhookEvent("user.created", {"user_id": 456})
        assert event1.get_idempotency_key() != event2.get_idempotency_key()
    
    def test_idempotency_key_different_types(self):
        """Different event types should produce different keys."""
        event1 = WebhookEvent("user.created", {"id": 1})
        event2 = WebhookEvent("user.deleted", {"id": 1})
        assert event1.get_idempotency_key() != event2.get_idempotency_key()


class TestWebhookDelivery:
    def setup_method(self):
        self.delivery = WebhookDelivery()
    
    def test_deliver_new_event(self):
        event = WebhookEvent("test.event", {"data": "value"})
        result = self.delivery.deliver(event)
        assert result["status"] == "delivered"
        assert result["event_id"] == event.event_id
        assert "idempotency_key" in result
    
    def test_deliver_duplicate_event(self):
        """Regression test: duplicate events should be skipped."""
        event = WebhookEvent("test.event", {"data": "value"})
        
        # First delivery
        result1 = self.delivery.deliver(event)
        assert result1["status"] == "delivered"
        
        # Duplicate delivery attempt
        result2 = self.delivery.deliver(event)
        assert result2["status"] == "skipped"
        assert result2["reason"] == "duplicate"
    
    def test_deliver_different_events(self):
        """Different events should both be delivered."""
        event1 = WebhookEvent("test.event", {"data": "value1"})
        event2 = WebhookEvent("test.event", {"data": "value2"})
        
        result1 = self.delivery.deliver(event1)
        result2 = self.delivery.deliver(event2)
        
        assert result1["status"] == "delivered"
        assert result2["status"] == "delivered"
    
    def test_is_delivered(self):
        event = WebhookEvent("test.event", {})
        assert not self.delivery.is_delivered(event.event_id)
        self.delivery.deliver(event)
        assert self.delivery.is_delivered(event.event_id)
    
    def test_get_delivery_count(self):
        assert self.delivery.get_delivery_count() == 0
        
        event1 = WebhookEvent("test.event", {"id": 1})
        event2 = WebhookEvent("test.event", {"id": 2})
        
        self.delivery.deliver(event1)
        assert self.delivery.get_delivery_count() == 1
        
        self.delivery.deliver(event2)
        assert self.delivery.get_delivery_count() == 2
        
        # Duplicate should not increase count
        self.delivery.deliver(event1)
        assert self.delivery.get_delivery_count() == 2


class TestWebhookSubscription:
    def setup_method(self):
        self.subscriptions = WebhookSubscription()
    
    def test_register_subscription(self):
        sub_id = self.subscriptions.register(
            "https://example.com/webhook",
            ["user.created", "user.deleted"]
        )
        assert sub_id is not None
        assert self.subscriptions.is_enabled(sub_id)
    
    def test_disable_subscription(self):
        sub_id = self.subscriptions.register(
            "https://example.com/webhook",
            ["user.created"]
        )
        assert self.subscriptions.disable(sub_id)
        assert not self.subscriptions.is_enabled(sub_id)
    
    def test_send_event_to_subscription(self):
        sub_id = self.subscriptions.register(
            "https://example.com/webhook",
            ["user.created"]
        )
        event = WebhookEvent("user.created", {"user_id": 123})
        
        result = self.subscriptions.send_event(event, sub_id)
        assert result["status"] == "delivered"
    
    def test_send_event_disabled_subscription(self):
        """Events should not be delivered to disabled subscriptions."""
        sub_id = self.subscriptions.register(
            "https://example.com/webhook",
            ["user.created"]
        )
        self.subscriptions.disable(sub_id)
        
        event = WebhookEvent("user.created", {"user_id": 123})
        result = self.subscriptions.send_event(event, sub_id)
        
        assert result["status"] == "failed"
        assert result["reason"] == "subscription_disabled"
    
    def test_send_event_wrong_type(self):
        """Events should not be delivered if type not subscribed."""
        sub_id = self.subscriptions.register(
            "https://example.com/webhook",
            ["user.created"]
        )
        
        event = WebhookEvent("user.updated", {"user_id": 123})
        result = self.subscriptions.send_event(event, sub_id)
        
        assert result["status"] == "failed"
        assert result["reason"] == "event_type_not_subscribed"
    
    def test_send_event_unknown_subscription(self):
        """Events to unknown subscriptions should fail gracefully."""
        event = WebhookEvent("user.created", {"user_id": 123})
        result = self.subscriptions.send_event(event, "unknown-id")
        
        assert result["status"] == "failed"
        assert result["reason"] == "subscription_not_found"
    
    def test_idempotent_delivery_across_subscriptions(self):
        """Same event to different subscriptions should be delivered."""
        sub1 = self.subscriptions.register("https://example1.com", ["user.created"])
        sub2 = self.subscriptions.register("https://example2.com", ["user.created"])
        
        event = WebhookEvent("user.created", {"user_id": 123})
        
        result1 = self.subscriptions.send_event(event, sub1)
        result2 = self.subscriptions.send_event(event, sub2)
        
        # Both should be delivered (different subscriptions)
        assert result1["status"] == "delivered"
        assert result2["status"] == "delivered"


class TestIntegration:
    """Integration tests for the complete webhook system."""
    
    def test_end_to_end_workflow(self):
        """Test the complete workflow from subscription to delivery."""
        subscriptions = WebhookSubscription()
        
        # Register a subscription
        sub_id = subscriptions.register(
            "https://api.example.com/webhooks",
            ["order.created", "order.updated"]
        )
        
        # Send events
        event1 = WebhookEvent("order.created", {"order_id": "ORD-001", "amount": 100})
        event2 = WebhookEvent("order.updated", {"order_id": "ORD-001", "status": "shipped"})
        
        result1 = subscriptions.send_event(event1, sub_id)
        result2 = subscriptions.send_event(event2, sub_id)
        
        assert result1["status"] == "delivered"
        assert result2["status"] == "delivered"
        
        # Duplicate should be skipped
        result1_dup = subscriptions.send_event(event1, sub_id)
        assert result1_dup["status"] == "skipped"
        assert result1_dup["reason"] == "duplicate"
    
    def test_retry_behavior_is_idempotent(self):
        """Regression test: retries should be idempotent and not duplicate state."""
        delivery = WebhookDelivery()
        event = WebhookEvent("payment.processed", {"payment_id": "PAY-123"})
        
        # First attempt
        result1 = delivery.deliver(event)
        assert result1["status"] == "delivered"
        
        # Retry attempts (simulating network retry)
        result2 = delivery.deliver(event)
        result3 = delivery.deliver(event)
        
        assert result2["status"] == "skipped"
        assert result3["status"] == "skipped"
        
        # Should only count as one delivery
        assert delivery.get_delivery_count() == 1
