import pytest
from src.common.config import Config, ConfigError


class TestConfig:
    def test_load_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        config = Config(str(config_file))
        assert config.get("app.name") == "test"
        assert config.get("app.port") == 8080

    def test_default_value(self):
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"

    def test_set_value(self):
        config = Config()
        config.set("database.host", "localhost")
        assert config.get("database.host") == "localhost"

    def test_nested_set(self):
        config = Config()
        config.set("a.b.c.d", "value")
        assert config.get("a.b.c.d") == "value"

    def test_to_dict(self):
        config = Config()
        config.set("key1", "value1")
        config.set("key2", "value2")
        data = config.to_dict()
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"

    def test_load_malformed_json_includes_path_and_location(self, tmp_path):
        """Test that JSON parse errors include file path, line, and column."""
        config_file = tmp_path / "bad_config.json"
        config_file.write_text('{"app": {"name": "test", "port": }')  # Missing value
        
        with pytest.raises(ConfigError) as exc_info:
            Config(str(config_file))
        
        error_msg = str(exc_info.value)
        assert "Failed to parse config file" in error_msg
        assert str(config_file) in error_msg
        assert "line" in error_msg
        assert "column" in error_msg

    def test_load_malformed_json_shows_line_and_column(self, tmp_path):
        """Test that JSON parse errors show correct line and column numbers."""
        config_file = tmp_path / "bad_config.json"
        # Create a multi-line JSON with an error on line 3
        config_file.write_text('{\n  "app": {\n    "name": "test",\n    "port": \n  }\n}')
        
        with pytest.raises(ConfigError) as exc_info:
            Config(str(config_file))
        
        error_msg = str(exc_info.value)
        # Should report the error around line 4 (where "port": has no value)
        assert "line 4" in error_msg or "line 5" in error_msg

    def test_load_missing_file_raises_config_error(self, tmp_path):
        """Test that loading a missing file raises ConfigError with path info."""
        missing_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(ConfigError) as exc_info:
            Config(str(missing_file))
        
        error_msg = str(exc_info.value)
        assert "Config file not found" in error_msg
        assert str(missing_file) in error_msg

# 2019-02-01T18:58:35 update

# 2019-07-31T13:45:15 update

# 2019-08-09T17:54:41 update

# 2019-08-14T16:29:54 update

# 2019-10-11T10:28:34 update

# 2019-10-25T09:23:55 update

# 2019-12-13T09:04:47 update

# 2020-04-09T10:21:21 update

# 2020-05-08T17:44:24 update

# 2020-07-20T13:54:19 update

# 2020-09-24T15:42:29 update

# 2020-12-09T20:16:24 update

# 2021-04-21T13:19:36 update

# 2021-05-25T09:15:06 update

# 2021-10-13T20:37:29 update

# 2021-11-18T18:37:15 update

# 2021-12-05T14:46:27 update

# 2022-01-19T12:56:31 update

# 2022-03-03T14:31:21 update

# 2022-03-23T08:42:05 update

# 2022-03-23T16:05:36 update

# 2022-07-11T19:00:31 update

# 2022-11-23T12:37:19 update

# 2023-01-16T15:28:31 update

# 2023-02-10T11:37:41 update

# 2023-08-01T09:43:10 update

# 2023-08-25T11:04:56 update

# 2023-09-07T10:18:27 update

# 2023-10-03T08:52:54 update

# 2023-10-11T19:49:55 update

# 2023-12-04T09:53:42 update

# 2024-01-29T14:34:37 update

# 2024-03-27T08:22:58 update

# 2024-07-03T09:52:12 update

# 2024-07-18T12:14:11 update

# 2024-09-12T10:59:12 update

# 2024-09-16T15:56:14 update

# 2024-09-17T19:00:45 update

# 2024-09-25T08:04:43 update

# 2024-12-10T14:49:57 update

# 2024-12-31T08:27:41 update

# 2025-03-18T15:08:24 update

# 2025-05-13T18:23:05 update

# 2025-05-15T19:05:40 update

# 2025-06-09T15:01:44 update

# 2025-07-04T18:13:41 update

# 2025-07-23T15:44:03 update

# 2025-10-16T13:53:26 update

# 2025-11-12T18:42:00 update

# 2026-02-06T08:55:54 update

# 2026-02-11T19:28:37 update

# 2026-04-17T10:00:53 update
