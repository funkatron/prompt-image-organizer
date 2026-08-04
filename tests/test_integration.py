"""Integration tests for the prompt-image-organizer."""

import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import the functions we want to test
from prompt_image_organizer.core import (
    MANIFEST_FILE_NAME,
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
                f.write(filename)

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

        # Files should have been moved to per-day session folders
        self.assertEqual(len(os.listdir(self.src_dir)), 0)  # Source should be empty
        self.assertGreater(len(os.listdir(self.dst_dir)), 0)

        # Check that date folders and session folders were created
        date_pattern = re.compile(r"^\d{8}$")
        pattern = re.compile(r"^\d{8}-\d{4}-session-\d{3}-\d{3}(?:-\d{2})?$")
        date_folders = [d for d in os.listdir(self.dst_dir) if date_pattern.match(d)]
        self.assertGreater(len(date_folders), 0)
        session_folders = []
        for date_folder in date_folders:
            session_folders.extend(
                d for d in os.listdir(os.path.join(self.dst_dir, date_folder))
                if pattern.match(d)
            )
        self.assertGreater(len(session_folders), 0)
        all_dir = os.path.join(self.dst_dir, "_all")
        self.assertTrue(os.path.isdir(all_dir))
        self.assertEqual(len(os.listdir(all_dir)), 7)
        for entry in os.listdir(all_dir):
            self.assertTrue(os.path.islink(os.path.join(all_dir, entry)))
            stem, extension = os.path.splitext(entry)
            self.assertEqual(extension, ".png")
            self.assertRegex(stem, r"^[a-f0-9]{32}(?:-\d{2})?$")

    def test_actual_move_writes_manifest_per_session(self):
        """Every session folder should record original names and prompts."""
        file_data = scan_files(self.src_dir)
        original_names = {item[0] for item in file_data}

        config = {
            "src_dir": self.src_dir,
            "dst_dir": self.dst_dir,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": False,
            "workers": 2,
        }
        batches = group_by_time(file_data, config["gap"])
        process_clusters(batches, config)

        manifests = []
        for root, _, files in os.walk(self.dst_dir):
            if MANIFEST_FILE_NAME in files:
                manifests.append(os.path.join(root, MANIFEST_FILE_NAME))
        self.assertGreater(len(manifests), 0)

        recorded_names = set()
        for manifest_path in manifests:
            with open(manifest_path, encoding="utf-8") as handle:
                manifest = json.load(handle)

            session_folder = os.path.dirname(manifest_path)
            self.assertEqual(
                manifest["source_dir"], os.path.abspath(self.src_dir)
            )
            for entry in manifest["files"]:
                recorded_names.add(entry["original_name"])
                self.assertTrue(entry["prompt"])
                self.assertTrue(entry["modified_at"])
                # The stored name must point at a real file in the session.
                self.assertTrue(
                    os.path.isfile(
                        os.path.join(session_folder, entry["stored_name"])
                    )
                )

        # Every moved file must be recoverable from some manifest.
        self.assertEqual(recorded_names, original_names)

    def test_dry_run_prints_plan_with_original_filenames(self):
        """The default dry run must show where each file would go."""
        file_data = scan_files(self.src_dir)
        config = {
            "src_dir": self.src_dir,
            "dst_dir": self.dst_dir,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": True,
            "workers": 2,
            "debug": False,
        }
        batches = group_by_time(file_data, config["gap"])

        with patch("sys.stdout", new=io.StringIO()) as captured:
            process_clusters(batches, config)
        output = captured.getvalue()

        # Session folders appear as paths relative to the destination.
        self.assertRegex(output, r"\d{8}/\d{8}-\d{4}-session-\d{3}")
        # Original filenames are listed so the user can judge the grouping.
        self.assertIn("a_cat_sitting_1.png", output)
        self.assertIn("a_dog_running_1.png", output)
        self.assertIn("completely_different_prompt_1.png", output)

    def test_dry_run_writes_no_manifest(self):
        """Dry runs must not leave manifests (or anything else) behind."""
        file_data = scan_files(self.src_dir)
        config = {
            "src_dir": self.src_dir,
            "dst_dir": self.dst_dir,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": True,
            "workers": 2,
        }
        batches = group_by_time(file_data, config["gap"])
        process_clusters(batches, config)

        for root, _, files in os.walk(self.dst_dir):
            self.assertNotIn(MANIFEST_FILE_NAME, files)

    def test_custom_folder_pattern(self):
        """Ensure custom folder pattern is applied."""
        custom_src = os.path.join(self.test_dir, "pattern_src")
        custom_dst = os.path.join(self.test_dir, "pattern_dst")
        os.makedirs(custom_src, exist_ok=True)
        os.makedirs(custom_dst, exist_ok=True)

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        files = [
            ("prompt_one_1.png", base_time),
            ("prompt_one_2.png", base_time + timedelta(minutes=5)),
            ("abstract_shape_1.png", base_time + timedelta(hours=2)),
        ]

        for filename, timestamp in files:
            path = os.path.join(custom_src, filename)
            with open(path, 'w') as handle:
                handle.write(filename)
            os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))

        file_data = scan_files(custom_src)
        batches = group_by_time(file_data, timedelta(minutes=60))

        config = {
            "src_dir": custom_src,
            "dst_dir": custom_dst,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": False,
            "workers": 1,
            "debug": False,
            "folder_pattern": "{date}_{slug}_{count_padded}",
        }

        process_clusters(batches, config)

        folders = sorted(os.listdir(os.path.join(custom_dst, "20240101")))
        self.assertEqual(
            folders,
            ["20240101_abstract-shape_001", "20240101_prompt-one_002"],
        )
        self.assertEqual(len(os.listdir(os.path.join(custom_dst, "_all"))), 3)

    def test_dry_run_and_actual_move_use_same_reserved_folder_names(self):
        """Dry run should reserve names exactly as an actual run would."""
        custom_src = os.path.join(self.test_dir, "collision_src")
        dry_run_dst = os.path.join(self.test_dir, "collision_dry_run_dst")
        actual_dst = os.path.join(self.test_dir, "collision_actual_dst")
        os.makedirs(custom_src, exist_ok=True)
        os.makedirs(dry_run_dst, exist_ok=True)
        os.makedirs(actual_dst, exist_ok=True)

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        files = [
            ("cat_portrait_1.png", base_time),
            ("cat_portrait_2.png", base_time + timedelta(minutes=5)),
            ("dog_portrait_1.png", base_time + timedelta(hours=2)),
            ("dog_portrait_2.png", base_time + timedelta(hours=2, minutes=5)),
        ]

        for filename, timestamp in files:
            path = os.path.join(custom_src, filename)
            with open(path, 'w') as handle:
                handle.write(filename)
            os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))

        file_data = scan_files(custom_src)
        batches = group_by_time(file_data, timedelta(minutes=60))

        dry_run_config = {
            "src_dir": custom_src,
            "dst_dir": dry_run_dst,
            "gap": timedelta(minutes=60),
            "sim_thresh": 0.8,
            "cluster_size_limit": None,
            "dry_run": True,
            "workers": 1,
            "debug": True,
            "folder_pattern": "{date}",
        }
        actual_config = dict(dry_run_config)
        actual_config["dst_dir"] = actual_dst
        actual_config["dry_run"] = False

        with patch("sys.stdout", new=io.StringIO()) as dry_run_stdout:
            process_clusters(batches, dry_run_config)
        self.assertIn(os.path.join("20240101", "20240101"), dry_run_stdout.getvalue())
        self.assertIn(os.path.join("20240101", "20240101-02"), dry_run_stdout.getvalue())

        process_clusters(batches, actual_config)
        self.assertEqual(sorted(os.listdir(actual_dst)), ["20240101", "_all"])
        self.assertEqual(
            sorted(os.listdir(os.path.join(actual_dst, "20240101"))),
            ["20240101", "20240101-02"],
        )
        self.assertEqual(len(os.listdir(os.path.join(actual_dst, "_all"))), 4)

    def test_all_symlinks_handle_duplicate_file_names(self):
        """The aggregate directory should keep unique symlink names."""
        custom_src = os.path.join(self.test_dir, "dupe_src")
        custom_dst = os.path.join(self.test_dir, "dupe_dst")
        os.makedirs(custom_src, exist_ok=True)
        os.makedirs(custom_dst, exist_ok=True)

        day_one = datetime(2024, 1, 1, 12, 0, 0)
        day_two = datetime(2024, 1, 2, 12, 0, 0)
        files = [
            ("shared_name_1.png", day_one),
            ("shared_name_1.png", day_two),
        ]

        for index, (filename, timestamp) in enumerate(files, start=1):
            day_dir = os.path.join(custom_src, f"input_{index}")
            os.makedirs(day_dir, exist_ok=True)
            path = os.path.join(day_dir, filename)
            with open(path, 'w') as handle:
                handle.write("test content")
            os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))

        for index in range(1, 3):
            file_data = scan_files(os.path.join(custom_src, f"input_{index}"))
            batches = group_by_time(file_data, timedelta(minutes=60))
            config = {
                "src_dir": os.path.join(custom_src, f"input_{index}"),
                "dst_dir": custom_dst,
                "gap": timedelta(minutes=60),
                "sim_thresh": 0.8,
                "cluster_size_limit": None,
                "dry_run": False,
                "workers": 1,
                "debug": False,
                "folder_pattern": "{datetime}-{slug}{checksum_suffix}-{count_padded}",
            }
            process_clusters(batches, config)

        expected_hash = hashlib.md5(b"test content").hexdigest()
        self.assertEqual(
            sorted(os.listdir(os.path.join(custom_dst, "_all"))),
            [f"{expected_hash}-02.png", f"{expected_hash}.png"],
        )


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
