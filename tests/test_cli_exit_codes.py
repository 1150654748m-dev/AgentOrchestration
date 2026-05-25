"""Tests for CLI exit code propagation."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from src.cli.main import cli, cmd_deploy


class TestCLIExitCodes:
    """Test suite for CLI command exit code propagation."""

    def test_deploy_success_returns_exit_code_0(self):
        """Test that successful deploy returns exit code 0."""
        with patch('sys.argv', ['ao', 'deploy', 'valid_manifest.json']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                    exit_code = cli()
        
        assert exit_code == 0
        assert "Deployment successful" in mock_stdout.getvalue()

    def test_deploy_invalid_manifest_returns_exit_code_1(self):
        """Test that deploy with invalid manifest returns exit code 1."""
        with patch('sys.argv', ['ao', 'deploy', 'invalid_manifest.txt']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                    exit_code = cli()
        
        assert exit_code == 1
        assert "Error: Invalid manifest file" in mock_stderr.getvalue()

    def test_init_returns_exit_code_0(self):
        """Test that init command returns exit code 0."""
        with patch('sys.argv', ['ao', 'init', 'my-project']):
            with patch('sys.stdout', new_callable=StringIO):
                exit_code = cli()
        
        assert exit_code == 0

    def test_status_returns_exit_code_0(self):
        """Test that status command returns exit code 0."""
        with patch('sys.argv', ['ao', 'status']):
            with patch('sys.stdout', new_callable=StringIO):
                exit_code = cli()
        
        assert exit_code == 0

    def test_logs_returns_exit_code_0(self):
        """Test that logs command returns exit code 0."""
        with patch('sys.argv', ['ao', 'logs', 'agent-123']):
            with patch('sys.stdout', new_callable=StringIO):
                exit_code = cli()
        
        assert exit_code == 0

    def test_no_command_returns_exit_code_1(self):
        """Test that no command returns exit code 1."""
        with patch('sys.argv', ['ao']):
            with patch('sys.stdout', new_callable=StringIO):
                exit_code = cli()
        
        assert exit_code == 1

    def test_deploy_handler_returns_int(self):
        """Test that deploy handler returns an integer exit code."""
        from argparse import Namespace
        
        args = Namespace(manifest='test.json')
        result = cmd_deploy(args)
        
        assert isinstance(result, int)
        assert result == 0

    def test_main_module_exits_with_cli_return_value(self):
        """Test that __main__ exits with the return value from cli()."""
        # This tests the sys.exit(cli()) pattern in __main__
        with patch('sys.argv', ['ao', 'deploy', 'bad.txt']):
            with patch('sys.stdout', new_callable=StringIO):
                with patch('sys.stderr', new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        # Simulate what happens in __main__
                        sys.exit(cli())
        
        assert exc_info.value.code == 1

    def test_deploy_with_json_extension_succeeds(self):
        """Test that deploy with .json extension succeeds."""
        with patch('sys.argv', ['ao', 'deploy', 'agent.json']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                exit_code = cli()
        
        assert exit_code == 0
        assert "Deployment successful" in mock_stdout.getvalue()

    def test_deploy_with_yaml_extension_fails(self):
        """Test that deploy with non-.json extension fails."""
        with patch('sys.argv', ['ao', 'deploy', 'agent.yaml']):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                exit_code = cli()
        
        assert exit_code == 1
        assert "Invalid manifest file" in mock_stderr.getvalue()
