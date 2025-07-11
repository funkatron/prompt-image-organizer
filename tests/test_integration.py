"""Integration tests for the prompt-image-organizer."""

import unittest
import tempfile
import os
import shutil
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import the functions we want to test
from prompt_image_organizer.core import (
    scan_files,
    process_clusters,
    move_file_worker,
    group_by_time,
    cluster_prompts,
)
from prompt_image_organizer.cli import parse_config


class TestIntegration(unittest.TestCase):
    """Integration tests for the full workflow."""

    def setUp(self):
        """Set up test directories and files."""
        self.test_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.test_dir, "source")
        self.dst_dir = os.path.join(self.test_dir, "destination")

        # Create directories
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dst_dir, exist_ok=True)

        # Create test image files with different timestamps
        self.create_test_files()

    def tearDown(self):
        """Clean up test directories."""
        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Create test image files with realistic timestamps."""
        base_time = datetime.now() - timedelta(hours=2)

        test_files = [
            ("a_cat_sitting_1.png", base_time),
            ("a_cat_sitting_2.png", base_time + timedelta(minutes=5)),
            ("a_cat_sitting_on_a_chair_1.png", base_time + timedelta(minutes=10)),
            ("a_dog_running_1.png", base_time + timedelta(minutes=30)),
            ("a_dog_running_2.png", base_time + timedelta(minutes=35)),
            ("completely_different_prompt_1.png", base_time + timedelta(minutes=90)),
            ("completely_different_prompt_2.png", base_time + timedelta(minutes=95)),
        ]

        for filename, timestamp in test_files:
            filepath = os.path.join(self.src_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test image content")

            # Set the file modification time
            os.utime(filepath, (timestamp.timestamp(), timestamp.timestamp()))

    def test_scan_files(self):
        """Test file scanning functionality."""
        file_data = scan_files(self.src_dir)

        # Should find all image files
        self.assertEqual(len(file_data), 7)

        # Check that files are sorted by modification time
        for i in range(len(file_data) - 1):
            self.assertLessEqual(file_data[i][1], file_data[i + 1][1])

        # Check that prompts are extracted correctly
        prompts = [item[2] for item in file_data]
        expected_prompts = [
            "a_cat_sitting",
            "a_cat_sitting",
            "a_cat_sitting_on_a_chair",
            "a_dog_running",
            "a_dog_running",
            "completely_different_prompt",
            "completely_different_prompt",
        ]
        self.assertEqual(prompts, expected_prompts)

    def test_parse_config_defaults(self):
        """Test configuration parsing with defaults."""
        with patch('sys.argv', ['script.py']):
            config = parse_config()

            self.assertEqual(config["src_dir"], ".")
            self.assertEqual(config["dst_dir"], "./sessions")
            self.assertEqual(config["gap"], timedelta(minutes=60))
            self.assertEqual(config["sim_thresh"], 0.8)
            self.assertIsNone(config["cluster_size_limit"])
            self.assertTrue(config["dry_run"])
            self.assertEqual(config["workers"], 8)

    def test_parse_config_with_args(self):
        """Test configuration parsing with command line arguments."""
        with patch('sys.argv', [
            'script.py',
            '/custom/src',
            '/custom/dst',
            '--gap', '45',
            '--sim', '0.9',
            '--limit', '100',
            '--workers', '4',
            '-x'
        ]):
            config = parse_config()

            self.assertEqual(config["src_dir"], "/custom/src")
            self.assertEqual(config["dst_dir"], "/custom/dst")
            self.assertEqual(config["gap"], timedelta(minutes=45))
            self.assertEqual(config["sim_thresh"], 0.9)
            self.assertEqual(config["cluster_size_limit"], 100)
            self.assertFalse(config["dry_run"])
            self.assertEqual(config["workers"], 4)

    def test_parse_config_with_env_vars(self):
        """Test configuration parsing with environment variables."""
        env_vars = {
            'SRC_DIR': '/env/src',
            'DST_DIR': '/env/dst',
            'SESSION_GAP_MINUTES': '30',
            'PROMPT_SIMILARITY': '0.7',
            'SESSION_CLUSTER_LIMIT': '50',
            'SESSION_WORKERS': '6'
        }

        with patch('sys.argv', ['script.py']), patch.dict(os.environ, env_vars):
            config = parse_config()

            self.assertEqual(config["src_dir"], "/env/src")
            self.assertEqual(config["dst_dir"], "/env/dst")
            self.assertEqual(config["gap"], timedelta(minutes=30))
            self.assertEqual(config["sim_thresh"], 0.7)
            self.assertEqual(config["cluster_size_limit"], 50)
            self.assertEqual(config["workers"], 6)

    def test_move_file_worker_dry_run(self):
        """Test file worker in dry run mode."""
        src_file = os.path.join(self.src_dir, "test.png")
        dst_file = os.path.join(self.dst_dir, "test.png")

        # Create a test file
        with open(src_file, 'w') as f:
            f.write("test content")

        # Test dry run (should not actually move the file)
        result = move_file_worker(src_file, dst_file, self.dst_dir, dry_run=True)
        src, dst, success, error = result

        self.assertEqual(src, src_file)
        self.assertEqual(dst, dst_file)
        self.assertTrue(success)
        self.assertIsNone(error)

        # File should not have been moved
        self.assertTrue(os.path.exists(src_file))
        self.assertFalse(os.path.exists(dst_file))

    def test_move_file_worker_actual_move(self):
        """Test file worker with actual file movement."""
        src_file = os.path.join(self.src_dir, "test.png")
        dst_file = os.path.join(self.dst_dir, "test.png")

        # Create a test file
        with open(src_file, 'w') as f:
            f.write("test content")

        # Test actual move
        result = move_file_worker(src_file, dst_file, self.dst_dir, dry_run=False)
        src, dst, success, error = result

        self.assertEqual(src, src_file)
        self.assertEqual(dst, dst_file)
        self.assertTrue(success)
        self.assertIsNone(error)

        # File should have been moved
        self.assertFalse(os.path.exists(src_file))
        self.assertTrue(os.path.exists(dst_file))

    def test_move_file_worker_error_handling(self):
        """Test file worker error handling."""
        non_existent_src = "/non/existent/file.png"
        dst_file = os.path.join(self.dst_dir, "test.png")

        # Test with non-existent source file
        result = move_file_worker(non_existent_src, dst_file, self.dst_dir, dry_run=False)
        src, dst, success, error = result

        self.assertEqual(src, non_existent_src)
        self.assertEqual(dst, dst_file)
        self.assertFalse(success)
        self.assertIsNotNone(error)

    def test_full_workflow_dry_run(self):
        """Test the complete workflow in dry run mode."""
        # Scan files
        file_data = scan_files(self.src_dir)

        # Create configuration for testing
        config = {
            "src_dir": self.src_dir,
            "dst_dir": self.dst_dir,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": True,
            "workers": 2
        }

        # Group by time
        batches = group_by_time(file_data, config["gap"])

        # Process clusters
        session_count, total_files, move_errors = process_clusters(batches, config)

        # Verify results
        self.assertGreater(session_count, 0)
        self.assertEqual(total_files, 7)  # All test files
        self.assertEqual(move_errors, 0)  # No errors in dry run

        # Files should not have been moved (dry run)
        for filename in os.listdir(self.src_dir):
            self.assertTrue(os.path.exists(os.path.join(self.src_dir, filename)))

    def test_full_workflow_actual_move(self):
        """Test the complete workflow with actual file movement."""
        # Scan files
        file_data = scan_files(self.src_dir)

        # Create configuration for testing
        config = {
            "src_dir": self.src_dir,
            "dst_dir": self.dst_dir,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": False,
            "workers": 2
        }

        # Group by time
        batches = group_by_time(file_data, config["gap"])

        # Process clusters
        session_count, total_files, move_errors = process_clusters(batches, config)

        # Verify results
        self.assertGreater(session_count, 0)
        self.assertEqual(total_files, 7)  # All test files
        self.assertEqual(move_errors, 0)  # No errors

        # Files should have been moved to session folders
        self.assertEqual(len(os.listdir(self.src_dir)), 0)  # Source should be empty
        self.assertGreater(len(os.listdir(self.dst_dir)), 0)  # Destination should have session folders

        # Check that session folders were created
        session_folders = [d for d in os.listdir(self.dst_dir) if d.startswith("session_")]
        self.assertGreater(len(session_folders), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test directory."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)

    def test_empty_source_directory(self):
        """Test behavior with empty source directory."""
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir, exist_ok=True)

        # Should not raise an error
        file_data = scan_files(empty_dir)
        self.assertEqual(len(file_data), 0)

    def test_no_image_files(self):
        """Test behavior when no image files are present."""
        no_images_dir = os.path.join(self.test_dir, "no_images")
        os.makedirs(no_images_dir, exist_ok=True)

        # Create non-image files
        test_files = ["document.txt", "script.py", "data.json"]
        for filename in test_files:
            filepath = os.path.join(no_images_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        # Should not find any image files
        file_data = scan_files(no_images_dir)
        self.assertEqual(len(file_data), 0)

    def test_invalid_source_directory(self):
        """Test behavior with invalid source directory."""
        non_existent_dir = "/non/existent/directory"

        # Should raise an error when trying to scan non-existent directory
        with self.assertRaises(FileNotFoundError):
            scan_files(non_existent_dir)

    def test_permission_errors(self):
        """Test handling of permission errors."""
        # Create a file that we can't write to (simulate permission error)
        test_file = os.path.join(self.test_dir, "test.png")
        with open(test_file, 'w') as f:
            f.write("test content")

        # Make file read-only
        os.chmod(test_file, 0o444)

        # Try to move the file (should fail due to permissions)
        dst_file = os.path.join(self.test_dir, "moved.png")
        result = move_file_worker(test_file, dst_file, self.test_dir, dry_run=False)
        src, dst, success, error = result

        if success:
            self.skipTest("Permission error not enforced on this platform")
        self.assertFalse(success)
        self.assertIsNotNone(error)


if __name__ == '__main__':
    unittest.main()