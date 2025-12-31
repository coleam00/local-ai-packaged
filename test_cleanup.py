#!/usr/bin/env python3
"""
test_cleanup.py

Simple validation tests for cleanup.py functionality.
Tests the helper functions without actually running destructive operations.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Import the cleanup module
import cleanup


class TestCleanupFunctions(unittest.TestCase):
    """Test suite for cleanup.py helper functions."""

    def test_print_header(self):
        """Test that print_header formats correctly."""
        # This should not raise any exceptions
        with patch('builtins.print') as mock_print:
            cleanup.print_header("Test Header")
            # Should call print 3 times (separator, text, separator)
            self.assertEqual(mock_print.call_count, 3)

    def test_print_item(self):
        """Test that print_item formats correctly."""
        with patch('builtins.print') as mock_print:
            cleanup.print_item("Test item")
            mock_print.assert_called_once()
            # Check that the default prefix is used
            call_args = mock_print.call_args[0][0]
            self.assertIn("  -", call_args)
            self.assertIn("Test item", call_args)

    def test_get_directories_to_remove(self):
        """Test directory discovery function."""
        dirs = cleanup.get_directories_to_remove()
        # Should return a list
        self.assertIsInstance(dirs, list)
        # All returned directories should actually exist
        for d in dirs:
            self.assertTrue(os.path.exists(d), f"Directory {d} should exist")

    def test_get_files_to_remove_preserve_env(self):
        """Test file discovery with .env preservation."""
        files = cleanup.get_files_to_remove(preserve_env=True)
        # Should return a list
        self.assertIsInstance(files, list)
        # .env should not be in the list
        self.assertNotIn(".env", files)

    def test_get_files_to_remove_delete_env(self):
        """Test file discovery without .env preservation."""
        files = cleanup.get_files_to_remove(preserve_env=False)
        # Should return a list
        self.assertIsInstance(files, list)
        # If .env exists, it should be in the list
        if os.path.exists(".env"):
            self.assertIn(".env", files)

    @patch('cleanup.docker.from_env')
    def test_get_docker_resources_success(self, mock_docker):
        """Test Docker resource discovery with successful connection."""
        # Mock Docker client
        mock_client = MagicMock()
        mock_docker.return_value = mock_client

        # Mock containers
        mock_container = Mock()
        mock_container.name = "test-container"
        mock_client.containers.list.return_value = [mock_container]

        # Mock volumes
        mock_volume = Mock()
        mock_volume.name = "localai_test_volume"
        mock_client.volumes.list.return_value = [mock_volume]

        # Mock networks
        mock_network = Mock()
        mock_network.name = "localai_test_network"
        mock_network.attrs = {"Labels": {}}
        mock_client.networks.list.return_value = [mock_network]

        containers, volumes, networks = cleanup.get_docker_resources()

        # Verify results
        self.assertEqual(len(containers), 1)
        self.assertEqual(len(volumes), 1)
        self.assertEqual(len(networks), 1)

    @patch('cleanup.docker.from_env')
    def test_get_docker_resources_docker_not_running(self, mock_docker):
        """Test Docker resource discovery when Docker is not running."""
        # Mock Docker connection error
        import docker.errors
        mock_docker.side_effect = docker.errors.DockerException("Docker not running")

        # Should exit with code 1
        with self.assertRaises(SystemExit) as cm:
            cleanup.get_docker_resources()
        self.assertEqual(cm.exception.code, 1)

    @patch('cleanup.get_docker_resources')
    @patch('cleanup.get_directories_to_remove')
    @patch('cleanup.get_files_to_remove')
    def test_preview_cleanup_has_items(self, mock_files, mock_dirs, mock_docker):
        """Test preview when there are items to clean."""
        # Mock return values
        mock_docker.return_value = ([], [], [])
        mock_dirs.return_value = ["supabase"]
        mock_files.return_value = []

        with patch('builtins.print'):
            result = cleanup.preview_cleanup(preserve_env=True)

        # Should return True since we have directories
        self.assertTrue(result)

    @patch('cleanup.get_docker_resources')
    @patch('cleanup.get_directories_to_remove')
    @patch('cleanup.get_files_to_remove')
    def test_preview_cleanup_no_items(self, mock_files, mock_dirs, mock_docker):
        """Test preview when there are no items to clean."""
        # Mock empty return values
        mock_docker.return_value = ([], [], [])
        mock_dirs.return_value = []
        mock_files.return_value = []

        with patch('builtins.print'):
            result = cleanup.preview_cleanup(preserve_env=True)

        # Should return False since we have nothing to clean
        self.assertFalse(result)

    @patch('builtins.input')
    def test_confirm_cleanup_confirmed(self, mock_input):
        """Test confirmation with correct input."""
        mock_input.return_value = "DELETE"
        with patch('builtins.print'):
            result = cleanup.confirm_cleanup()
        self.assertTrue(result)

    @patch('builtins.input')
    def test_confirm_cleanup_cancelled(self, mock_input):
        """Test confirmation with incorrect input."""
        mock_input.return_value = "no"
        with patch('builtins.print'):
            result = cleanup.confirm_cleanup()
        self.assertFalse(result)

    def test_handle_remove_readonly(self):
        """Test readonly file handler."""
        # This is platform-specific, so we'll just ensure it exists
        self.assertTrue(callable(cleanup.handle_remove_readonly))


def run_validation_tests():
    """Run all validation tests and return results."""
    print("=" * 60)
    print("  RUNNING CLEANUP.PY VALIDATION TESTS")
    print("=" * 60)

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCleanupFunctions)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("  [PASS] ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("  [FAIL] SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_validation_tests())
