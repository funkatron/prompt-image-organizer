#!/usr/bin/env python3
"""Test runner for prompt-image-organizer."""

import sys
import os
import unittest
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """Run all tests and return the result."""
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')

    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)

    # Run the tests
    result = runner.run(suite)

    return result.wasSuccessful()

def run_tests_with_coverage():
    """Run tests with coverage reporting."""
    try:
        import coverage
    except ImportError:
        print("Coverage not available. Install with: pip install coverage")
        return run_tests()

    # Start coverage measurement
    cov = coverage.Coverage()
    cov.start()

    # Run tests
    success = run_tests()

    # Stop coverage and generate report
    cov.stop()
    cov.save()

    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)

    # Generate coverage report
    cov.report()

    # Generate HTML report
    html_dir = os.path.join(os.path.dirname(__file__), 'htmlcov')
    cov.html_report(directory=html_dir)
    print(f"\nHTML coverage report generated in: {html_dir}")

    return success

def create_test_data():
    """Create test data for integration tests."""
    test_dir = os.path.join(os.path.dirname(__file__), 'test_data')

    # Clean up existing test data
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    os.makedirs(test_dir, exist_ok=True)

    # Create sample image files with different timestamps
    import time
    from datetime import datetime, timedelta

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
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"Test image content for {filename}")

        # Set the file modification time
        os.utime(filepath, (timestamp.timestamp(), timestamp.timestamp()))

    print(f"Test data created in: {test_dir}")
    return test_dir

def main():
    """Main test runner function."""
    import argparse

    parser = argparse.ArgumentParser(description='Run tests for prompt-image-organizer')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage reporting')
    parser.add_argument('--create-test-data', action='store_true',
                       help='Create test data for integration tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    if args.create_test_data:
        create_test_data()
        return

    if args.coverage:
        success = run_tests_with_coverage()
    else:
        success = run_tests()

    if success:
        print("\n" + "="*50)
        print("ALL TESTS PASSED! ✅")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("SOME TESTS FAILED! ❌")
        print("="*50)
        sys.exit(1)

if __name__ == '__main__':
    main()