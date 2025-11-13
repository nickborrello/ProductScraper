#!/usr/bin/env python3
"""
Large Scale Testing Script for Amazon Scraper

This script demonstrates the large scale testing capabilities of the enhanced Amazon scraper.
It can be used to benchmark performance with various batch sizes and SKU counts.

Usage:
    python test_large_scale.py --skus 100 --batch-size 25 --test-name "production_test"
    python test_large_scale.py --sku-file skus.txt --batch-size 50
"""

import json
import sys
import subprocess
import argparse
from pathlib import Path


def load_skus_from_file(file_path: str) -> list[str]:
    """Load SKUs from a text file (one SKU per line)."""
    try:
        with open(file_path, 'r') as f:
            skus = [line.strip() for line in f if line.strip()]
        return skus
    except FileNotFoundError:
        print(f"❌ SKU file not found: {file_path}")
        return []


def generate_test_skus(count: int) -> list[str]:
    """Generate a list of test SKUs for benchmarking."""
    # Use known working SKU as base and create variations
    base_sku = "035585499741"
    skus = [base_sku]

    # Add variations for testing (these may not exist but will test error handling)
    for i in range(1, count):
        # Create variations by modifying digits
        variation = f"{base_sku[:-3]}{str(i).zfill(3)}"
        skus.append(variation)

    return skus[:count]


def run_large_scale_test(skus: list[str], batch_size: int = 50, test_name: str = "large_scale_test"):
    """Run the large scale performance test."""
    print(f"🧪 Starting Large Scale Test: {test_name}")
    print(f"📊 Testing {len(skus)} SKUs with batch size {batch_size}")

    # Prepare input data for the scraper
    input_data = {
        "large_scale_test": True,
        "skus": skus,
        "batch_size": batch_size,
        "test_name": test_name
    }

    # Convert to JSON string for command line
    input_json = json.dumps(input_data)

    try:
        # Run the scraper with large scale testing
        cmd = [sys.executable, "src/main.py", input_json]
        print(f"🚀 Executing: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)

        # Print output
        if result.stdout:
            print("📄 Scraper Output:")
            print(result.stdout)

        if result.stderr:
            print("⚠️ Scraper Errors:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ Large scale test completed successfully!")
        else:
            print(f"❌ Large scale test failed with return code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"💥 Error running large scale test: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Large Scale Testing for Amazon Scraper")
    parser.add_argument("--skus", type=int, help="Number of SKUs to test (uses generated test data)")
    parser.add_argument("--sku-file", type=str, help="File containing SKUs (one per line)")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--test-name", type=str, default="large_scale_test", help="Name for the test run")

    args = parser.parse_args()

    # Determine SKUs to test
    if args.sku_file:
        skus = load_skus_from_file(args.sku_file)
        if not skus:
            sys.exit(1)
    elif args.skus:
        skus = generate_test_skus(args.skus)
    else:
        print("❌ Must specify either --skus <count> or --sku-file <file>")
        sys.exit(1)

    print(f"📋 Loaded {len(skus)} SKUs for testing")
    print(f"🎯 Test Name: {args.test_name}")
    print(f"📦 Batch Size: {args.batch_size}")

    # Confirm before running large tests
    if len(skus) > 100:
        response = input(f"⚠️ This will test {len(skus)} SKUs. Continue? (y/N): ")
        if response.lower() != 'y':
            print("Test cancelled.")
            sys.exit(0)

    # Run the test
    success = run_large_scale_test(skus, args.batch_size, args.test_name)

    if success:
        print("\n🎉 Large scale testing completed successfully!")
        print("📊 Check the generated JSON results file for detailed performance metrics.")
    else:
        print("\n💥 Large scale testing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()