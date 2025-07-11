"""CLI tests for the prompt-image-organizer."""

import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

# Import the functions we want to test
from prompt_image_organizer.cli import parse_config, print_help, main


class TestCLI(unittest.TestCase):
    """Test command line interface functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_print_help(self):
        """Test help text output."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            print_help()
            output = mock_stdout.getvalue()

            # Check that help text contains expected content
            self.assertIn("Prompt Image Organizer", output)
            self.assertIn("Usage:", output)
            self.assertIn("Arguments:", output)
            self.assertIn("Options:", output)
            self.assertIn("Examples:", output)
            self.assertIn("--gap", output)
            self.assertIn("--sim", output)
            self.assertIn("--limit", output)
            self.assertIn("-x", output)

    def test_parse_config_help_flag(self):
        """Test that help flag exits with status 0."""
        with patch('sys.argv', ['script.py', '--help']), \
             patch('sys.exit') as mock_exit:
            parse_config()
            mock_exit.assert_called_with(0)

    def test_parse_config_h_flag(self):
        """Test that -h flag exits with status 0."""
        with patch('sys.argv', ['script.py', '-h']), \
             patch('sys.exit') as mock_exit:
            parse_config()
            mock_exit.assert_called_with(0)

    def test_parse_config_no_args(self):
        """Test configuration parsing with no arguments."""
        with patch('sys.argv', ['script.py']):
            config = parse_config()

            # Check default values
            self.assertEqual(config["src_dir"], ".")
            self.assertEqual(config["dst_dir"], "./sessions")
            self.assertEqual(config["gap"].total_seconds(), 3600)  # 60 minutes
            self.assertEqual(config["sim_thresh"], 0.8)
            self.assertIsNone(config["cluster_size_limit"])
            self.assertTrue(config["dry_run"])
            self.assertEqual(config["workers"], 8)

    def test_parse_config_with_src_dst(self):
        """Test configuration parsing with source and destination directories."""
        with patch('sys.argv', ['script.py', '/path/to/src', '/path/to/dst']):
            config = parse_config()

            self.assertEqual(config["src_dir"], "/path/to/src")
            self.assertEqual(config["dst_dir"], "/path/to/dst")

    def test_parse_config_with_options(self):
        """Test configuration parsing with all options."""
        with patch('sys.argv', [
            'script.py',
            '/src',
            '/dst',
            '--gap', '30',
            '--sim', '0.9',
            '--limit', '50',
            '--workers', '4',
            '-x'
        ]):
            config = parse_config()

            self.assertEqual(config["src_dir"], "/src")
            self.assertEqual(config["dst_dir"], "/dst")
            self.assertEqual(config["gap"].total_seconds(), 1800)  # 30 minutes
            self.assertEqual(config["sim_thresh"], 0.9)
            self.assertEqual(config["cluster_size_limit"], 50)
            self.assertFalse(config["dry_run"])
            self.assertEqual(config["workers"], 4)

    def test_parse_config_invalid_gap(self):
        """Test configuration parsing with invalid gap value."""
        with patch('sys.argv', ['script.py', '--gap', 'invalid']):
            with self.assertRaises(SystemExit):
                parse_config()

    def test_parse_config_invalid_sim(self):
        """Test configuration parsing with invalid similarity value."""
        with patch('sys.argv', ['script.py', '--sim', 'invalid']):
            with self.assertRaises(SystemExit):
                parse_config()

    def test_parse_config_invalid_limit(self):
        """Test configuration parsing with invalid limit value."""
        with patch('sys.argv', ['script.py', '--limit', 'invalid']):
            with self.assertRaises(SystemExit):
                parse_config()

    def test_parse_config_invalid_workers(self):
        """Test configuration parsing with invalid workers value."""
        with patch('sys.argv', ['script.py', '--workers', 'invalid']):
            with self.assertRaises(SystemExit):
                parse_config()

    def test_parse_config_environment_variables(self):
        """Test configuration parsing with environment variables."""
        env_vars = {
            'SRC_DIR': '/env/src',
            'DST_DIR': '/env/dst',
            'SESSION_GAP_MINUTES': '45',
            'PROMPT_SIMILARITY': '0.7',
            'SESSION_CLUSTER_LIMIT': '25',
            'SESSION_WORKERS': '6'
        }

        with patch('sys.argv', ['script.py']), \
             patch.dict(os.environ, env_vars):
            config = parse_config()

            self.assertEqual(config["src_dir"], "/env/src")
            self.assertEqual(config["dst_dir"], "/env/dst")
            self.assertEqual(config["gap"].total_seconds(), 2700)  # 45 minutes
            self.assertEqual(config["sim_thresh"], 0.7)
            self.assertEqual(config["cluster_size_limit"], 25)
            self.assertEqual(config["workers"], 6)

    def test_parse_config_mixed_args_and_env(self):
        """Test that command line arguments override environment variables."""
        env_vars = {
            'SRC_DIR': '/env/src',
            'DST_DIR': '/env/dst',
            'SESSION_GAP_MINUTES': '30',
            'PROMPT_SIMILARITY': '0.6',
            'SESSION_CLUSTER_LIMIT': '20',
            'SESSION_WORKERS': '4'
        }

        with patch('sys.argv', [
            'script.py',
            '/cli/src',
            '/cli/dst',
            '--gap', '60',
            '--sim', '0.8',
            '--limit', '100',
            '--workers', '8'
        ]), patch.dict(os.environ, env_vars):
            config = parse_config()

            # CLI args should override env vars
            self.assertEqual(config["src_dir"], "/cli/src")
            self.assertEqual(config["dst_dir"], "/cli/dst")
            self.assertEqual(config["gap"].total_seconds(), 3600)  # 60 minutes
            self.assertEqual(config["sim_thresh"], 0.8)
            self.assertEqual(config["cluster_size_limit"], 100)
            self.assertEqual(config["workers"], 8)

    def test_main_function_basic(self):
        """Test main function with basic arguments."""
        # Create test directories
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        # Create a test image file
        test_file = os.path.join(src_dir, "test_image.png")
        with open(test_file, 'w') as f:
            f.write("test content")

        with patch('sys.argv', ['script.py', src_dir, dst_dir]):
            # Should run without errors
            main()

    def test_main_function_with_options(self):
        """Test main function with various options."""
        # Create test directories
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        # Create test image files
        test_files = [
            "a_cat_sitting_1.png",
            "a_cat_sitting_2.png",
            "a_dog_running_1.png"
        ]

        for filename in test_files:
            filepath = os.path.join(src_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        with patch('sys.argv', [
            'script.py',
            src_dir,
            dst_dir,
            '--gap', '30',
            '--sim', '0.9',
            '--limit', '10',
            '--workers', '2'
        ]):
            # Should run without errors
            main()

    def test_main_function_dry_run(self):
        """Test main function in dry run mode."""
        # Create test directories
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        # Create a test image file
        test_file = os.path.join(src_dir, "test_image.png")
        with open(test_file, 'w') as f:
            f.write("test content")

        with patch('sys.argv', ['script.py', src_dir, dst_dir]):
            # Should run without errors (dry run by default)
            main()

            # File should not have been moved
            self.assertTrue(os.path.exists(test_file))

    def test_main_function_actual_move(self):
        """Test main function with actual file movement."""
        # Create test directories
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        # Create test image files
        test_files = [
            "a_cat_sitting_1.png",
            "a_cat_sitting_2.png"
        ]

        for filename in test_files:
            filepath = os.path.join(src_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        with patch('sys.argv', ['script.py', src_dir, dst_dir, '-x']):
            # Should run without errors
            main()

            # Files should have been moved
            self.assertEqual(len(os.listdir(src_dir)), 0)
            self.assertGreater(len(os.listdir(dst_dir)), 0)

    def test_main_function_invalid_source(self):
        """Test main function with invalid source directory."""
        with patch('sys.argv', ['script.py', '/non/existent/dir', self.temp_dir]):
            with self.assertRaises(SystemExit):
                main()

    def test_main_function_no_images(self):
        """Test main function with no image files."""
        # Create test directories
        src_dir = os.path.join(self.temp_dir, "src")
        dst_dir = os.path.join(self.temp_dir, "dst")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(dst_dir, exist_ok=True)

        # Create non-image files
        test_files = ["document.txt", "script.py"]
        for filename in test_files:
            filepath = os.path.join(src_dir, filename)
            with open(filepath, 'w') as f:
                f.write("test content")

        with patch('sys.argv', ['script.py', src_dir, dst_dir]), \
             patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_with(0)


if __name__ == '__main__':
    unittest.main()