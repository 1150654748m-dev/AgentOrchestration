"""Tests for SDK decorators."""

import pytest
from src.sdk.decorators import task, agent, on_event


class TestTaskDecorator:
    """Tests for the task decorator."""

    def test_task_with_valid_timeout(self):
        """Test that task decorator accepts valid positive timeout."""
        @task(timeout=60)
        async def valid_task():
            return "success"

        assert valid_task.__task_config__["timeout"] == 60

    def test_task_with_zero_timeout_raises(self):
        """Test that task decorator rejects zero timeout."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            @task(timeout=0)
            async def bad_task():
                return "fail"

    def test_task_with_negative_timeout_raises(self):
        """Test that task decorator rejects negative timeout."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            @task(timeout=-1)
            async def bad_task():
                return "fail"

    def test_task_with_negative_large_timeout_raises(self):
        """Test that task decorator rejects large negative timeout."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            @task(timeout=-100)
            async def bad_task():
                return "fail"

    def test_task_with_non_numeric_timeout_raises(self):
        """Test that task decorator rejects non-numeric timeout."""
        with pytest.raises(TypeError, match="timeout must be a number"):
            @task(timeout="invalid")
            async def bad_task():
                return "fail"

    def test_task_with_none_timeout_raises(self):
        """Test that task decorator rejects None timeout."""
        with pytest.raises(TypeError, match="timeout must be a number"):
            @task(timeout=None)
            async def bad_task():
                return "fail"

    def test_task_default_timeout(self):
        """Test that task decorator uses default timeout of 300."""
        @task()
        async def default_task():
            return "success"

        assert default_task.__task_config__["timeout"] == 300

    def test_task_preserves_other_config(self):
        """Test that timeout validation doesn't affect other config."""
        @task(name="custom_name", retries=3, timeout=120)
        async def configured_task():
            return "success"

        assert configured_task.__task_config__["name"] == "custom_name"
        assert configured_task.__task_config__["retries"] == 3
        assert configured_task.__task_config__["timeout"] == 120


class TestAgentDecorator:
    """Tests for the agent decorator."""

    def test_agent_decorator(self):
        """Test that agent decorator sets config correctly."""
        @agent(name="test_agent", version="2.0.0", description="A test agent")
        class TestAgent:
            pass

        assert TestAgent.__agent_config__["name"] == "test_agent"
        assert TestAgent.__agent_config__["version"] == "2.0.0"
        assert TestAgent.__agent_config__["description"] == "A test agent"


class TestOnEventDecorator:
    """Tests for the on_event decorator."""

    def test_on_event_decorator(self):
        """Test that on_event decorator sets handler correctly."""
        @on_event("test_event")
        async def handler():
            return "handled"

        assert handler.__event_handler__ == "test_event"
