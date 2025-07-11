"""Pytest configuration and common fixtures."""

import pytest
import tempfile
import os
import shutil
from datetime import datetime, timedelta


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_image_files(temp_dir):
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
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"Test image content for {filename}")

        # Set the file modification time
        os.utime(filepath, (timestamp.timestamp(), timestamp.timestamp()))

    return temp_dir, test_files


@pytest.fixture
def empty_dir(temp_dir):
    """Create an empty directory for testing."""
    empty_dir = os.path.join(temp_dir, "empty")
    os.makedirs(empty_dir, exist_ok=True)
    return empty_dir


@pytest.fixture
def non_image_files(temp_dir):
    """Create non-image files for testing."""
    test_files = ["document.txt", "script.py", "data.json", "README.md"]

    for filename in test_files:
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"Test content for {filename}")

    return temp_dir, test_files