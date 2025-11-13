#!/usr/bin/env python3
"""
Test runner script for the ProductScraper project.
Runs all tests using pytest.
"""

import subprocess
import sys
import os


def run_tests():
    """Run all tests using pytest."""
    print("🧪 Running ProductScraper Tests")
    print("=" * 50)

    # Change to the tests directory
    test_dir = os.path.join(os.path.dirname(__file__), "tests")

    # Run pytest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
        )

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Return appropriate exit code
        return result.returncode

    except FileNotFoundError:
        print("❌ pytest not found. Please install with: pip install pytest")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
