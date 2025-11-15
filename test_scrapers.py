#!/usr/bin/env python3
"""
Command-line test runner for scraper integration tests.
"""

import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.utils.run_scraper import run_scraper_integration_tests

def main():
    parser = argparse.ArgumentParser(description="Run scraper integration tests")
    parser.add_argument("--all", action="store_true", help="Run all scraper tests")
    parser.add_argument("--scraper", type=str, help="Run test for specific scraper")
    parser.add_argument("--list", action="store_true", help="List available scrapers")
    parser.add_argument("--validate", type=str, help="Validate scraper structure only")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--skus", nargs='+', help="Custom SKUs to test")

    args = parser.parse_args()

    if args.list:
        # List available scrapers
        scrapers_dir = os.path.join(project_root, "src", "scrapers")
        scraper_dirs = [d for d in os.listdir(scrapers_dir)
                       if os.path.isdir(os.path.join(scrapers_dir, d)) and
                       not d.startswith('.') and d != 'archive']
        print("Available scrapers:")
        for scraper in sorted(scraper_dirs):
            print(f"  - {scraper}")
        return

    if args.validate:
        # Validate scraper structure
        scraper_name = args.validate
        scrapers_dir = os.path.join(project_root, "src", "scrapers")
        scraper_path = os.path.join(scrapers_dir, scraper_name)

        if not os.path.exists(scraper_path):
            print(f"❌ Scraper '{scraper_name}' not found")
            return

        required_files = [
            "src/main.py",
            ".actor/actor.json",
            ".actor/input_schema.json",
            ".actor/output_schema.json",
            ".actor/dataset_schema.json",
            "Dockerfile",
            "requirements.txt"
        ]

        print(f"Validating structure for {scraper_name}:")
        all_good = True
        for file_path in required_files:
            full_path = os.path.join(scraper_path, file_path)
            if os.path.exists(full_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path} - MISSING")
                all_good = False

        if all_good:
            print(f"✅ {scraper_name} structure is valid")
        else:
            print(f"❌ {scraper_name} structure has issues")
        return

    # Run integration tests
    print("Running scraper integration tests...")
    success = run_scraper_integration_tests()

    if success:
        print("\n✅ Tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()