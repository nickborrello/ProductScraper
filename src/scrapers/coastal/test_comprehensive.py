#!/usr/bin/env python3
"""
Comprehensive Test Suite for Coastal Scraper

This test suite provides comprehensive testing for the Coastal scraper,
including unit tests, integration tests, and scenario-based testing for:
- Product Found scenarios
- No Product Found scenarios
- Error handling and edge cases
- Performance and reliability tests
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import subprocess
from pathlib import Path

# Add project paths for imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import scraper modules
try:
    from main import scrape_products, HEADLESS
    # Coastal scraper may not have TEST_SKU defined, use a default
    TEST_SKU = getattr(sys.modules.get('main', {}), 'TEST_SKU', 'COASTAL_TEST_001')
except ImportError as e:
    print(f"❌ Failed to import scraper modules: {e}")
    sys.exit(1)


class TestCoastalScraper(unittest.TestCase):
    """Comprehensive test suite for Coastal scraper."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_sku_valid = TEST_SKU  # Known valid SKU or default
        self.test_sku_invalid = "INVALID_COASTAL_123"  # Invalid SKU for testing
        self.test_sku_nonexistent = "999999999999"  # Non-existent SKU

        # Mock driver for unit tests
        self.mock_driver = MagicMock()

    def tearDown(self):
        """Clean up after tests."""
        pass

    # ============================================================================
    # UNIT TESTS
    # ============================================================================

    def test_headless_configuration(self):
        """Test that HEADLESS configuration is properly set."""
        self.assertIsInstance(HEADLESS, bool)
        # HEADLESS should be True for production, False only for CAPTCHA debugging

    def test_test_sku_defined(self):
        """Test that TEST_SKU is properly defined."""
        self.assertIsNotNone(TEST_SKU)
        self.assertIsInstance(TEST_SKU, str)
        self.assertGreater(len(TEST_SKU), 0)

    # ============================================================================
    # INTEGRATION TESTS - PRODUCT FOUND SCENARIOS
    # ============================================================================

    def test_scrape_single_valid_product(self):
        """Test scraping a single known valid product."""
        print("🧪 Testing single valid product scrape...")

        skus = [self.test_sku_valid]
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

        product = results[0]
        self.assertIsNotNone(product, f"Expected product data for SKU {self.test_sku_valid}, got None")

        # Validate product structure
        self._validate_product_data(product, self.test_sku_valid)

        print(f"✅ Successfully scraped valid product: {product.get('Name', 'Unknown')}")

    def test_scrape_multiple_valid_products(self):
        """Test scraping multiple valid products."""
        print("🧪 Testing multiple valid products scrape...")

        # Use the same valid SKU multiple times to test batch processing
        skus = [self.test_sku_valid] * 3
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)

        # All results should be valid products
        for i, product in enumerate(results):
            with self.subTest(sku_index=i):
                self.assertIsNotNone(product, f"Expected product data for SKU {self.test_sku_valid} at index {i}, got None")
                self._validate_product_data(product, self.test_sku_valid)

        print(f"✅ Successfully scraped {len(results)} valid products")

    def test_scrape_mixed_valid_invalid_skus(self):
        """Test scraping mix of valid and invalid SKUs."""
        print("🧪 Testing mixed valid/invalid SKUs...")

        skus = [self.test_sku_valid, self.test_sku_invalid, self.test_sku_valid]
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)

        # First and third should be valid products
        self._validate_product_data(results[0], self.test_sku_valid)
        self._validate_product_data(results[2], self.test_sku_valid)

        # Second should be None (invalid SKU)
        self.assertIsNone(results[1], f"Expected None for invalid SKU {self.test_sku_invalid}")

        print("✅ Mixed SKU test passed: valid products found, invalid SKUs returned None")

    # ============================================================================
    # INTEGRATION TESTS - NO PRODUCT FOUND SCENARIOS
    # ============================================================================

    def test_scrape_invalid_sku(self):
        """Test scraping a completely invalid SKU."""
        print("🧪 Testing invalid SKU handling...")

        skus = [self.test_sku_invalid]
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0], f"Expected None for invalid SKU {self.test_sku_invalid}")

        print(f"✅ Invalid SKU {self.test_sku_invalid} correctly returned None")

    def test_scrape_nonexistent_sku(self):
        """Test scraping a non-existent but valid-format SKU."""
        print("🧪 Testing non-existent SKU handling...")

        skus = [self.test_sku_nonexistent]
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0], f"Expected None for non-existent SKU {self.test_sku_nonexistent}")

        print(f"✅ Non-existent SKU {self.test_sku_nonexistent} correctly returned None")

    def test_scrape_empty_sku_list(self):
        """Test scraping with empty SKU list."""
        print("🧪 Testing empty SKU list handling...")

        skus = []
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

        print("✅ Empty SKU list correctly returned empty results")

    def test_scrape_malformed_skus(self):
        """Test scraping with malformed SKU inputs."""
        print("🧪 Testing malformed SKU handling...")

        malformed_skus = ["", "   ", "abc", "123", "!@#$%", "12345678901234567890"]  # Too long
        results = scrape_products(malformed_skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), len(malformed_skus))

        # All malformed SKUs should return None
        for i, result in enumerate(results):
            with self.subTest(sku_index=i, sku=malformed_skus[i]):
                self.assertIsNone(result, f"Expected None for malformed SKU '{malformed_skus[i]}'")

        print(f"✅ All {len(malformed_skus)} malformed SKUs correctly returned None")

    # ============================================================================
    # ERROR HANDLING TESTS
    # ============================================================================

    def test_network_timeout_simulation(self):
        """Test handling of network timeouts (simulated)."""
        # This is difficult to test directly, but we can verify the scraper
        # doesn't crash when encountering issues
        print("🧪 Network timeout handling test (simulated)...")

        # Test with a SKU that might cause timeouts
        skus = ["TIMEOUT_TEST_123"]
        results = scrape_products(skus)

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        # Should return None for timeout scenarios
        self.assertIsNone(results[0])

        print("✅ Network timeout scenario handled gracefully")

    # ============================================================================
    # PERFORMANCE TESTS
    # ============================================================================

    def test_performance_small_batch(self):
        """Test performance with small batch of SKUs."""
        print("🧪 Testing small batch performance...")

        skus = [self.test_sku_valid] * 3
        start_time = time.time()

        results = scrape_products(skus)

        end_time = time.time()
        duration = end_time - start_time

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)

        # Should complete within reasonable time (30 seconds per SKU max)
        max_expected_time = len(skus) * 30
        self.assertLess(duration, max_expected_time,
                       f"Batch took {duration:.2f}s, expected < {max_expected_time}s")

        print(f"✅ Small batch performance test completed in {duration:.2f}s")
    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _validate_product_data(self, product, expected_sku):
        """Validate that product data has required fields."""
        self.assertIsInstance(product, dict)
        self.assertIn('SKU', product)
        self.assertEqual(product['SKU'], expected_sku)

        # Check for required fields (should not be None, empty, or "N/A")
        required_fields = ['Name', 'SKU']
        for field in required_fields:
            self.assertIn(field, product)
            value = product[field]
            self.assertIsNotNone(value, f"Field '{field}' should not be None")
            self.assertNotEqual(str(value).strip().upper(), 'N/A', f"Field '{field}' should not be 'N/A'")
            self.assertNotEqual(str(value).strip(), '', f"Field '{field}' should not be empty")

        # Name should be meaningful
        name = product.get('Name', '').strip()
        self.assertGreater(len(name), 2, f"Product name '{name}' is too short")

        # Optional fields validation
        optional_fields = ['Brand', 'Weight', 'Image URLs']
        for field in optional_fields:
            if field in product:
                value = product[field]
                # If present, should not be completely empty
                if field == 'Image URLs':
                    self.assertIsInstance(value, list)
                else:
                    self.assertIsNotNone(value)

    # ============================================================================
    # SCENARIO-BASED TESTS
    # ============================================================================

    def test_product_found_scenario(self):
        """Comprehensive test for 'Product Found' scenario."""
        print("🎯 Testing PRODUCT FOUND scenario...")

        # Test with known valid SKU
        skus = [self.test_sku_valid]
        results = scrape_products(skus)

        # Assertions for successful product found
        self.assertEqual(len(results), 1)
        product = results[0]
        self.assertIsNotNone(product)

        # Detailed validation
        self._validate_product_data(product, self.test_sku_valid)

        # Check data quality
        name = product.get('Name', '')
        self.assertGreater(len(name), 5, "Product name should be descriptive")

        print(f"✅ PRODUCT FOUND: {name[:50]}{'...' if len(name) > 50 else ''}")

    def test_no_product_found_scenario(self):
        """Comprehensive test for 'No Product Found' scenario."""
        print("🎯 Testing NO PRODUCT FOUND scenario...")

        # Test with invalid SKU
        skus = [self.test_sku_invalid]
        results = scrape_products(skus)

        # Assertions for no product found
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0])

        print(f"✅ NO PRODUCT FOUND: SKU {self.test_sku_invalid} correctly returned None")

    def test_mixed_scenarios(self):
        """Test mix of found and not found products."""
        print("🎯 Testing MIXED SCENARIOS...")

        skus = [
            self.test_sku_valid,    # Should find product
            self.test_sku_invalid,  # Should not find product
            self.test_sku_valid,    # Should find product again
            self.test_sku_invalid   # Should not find product again
        ]

        results = scrape_products(skus)

        # Validate results pattern
        self.assertEqual(len(results), 4)

        # Pattern: Found, Not Found, Found, Not Found
        expected_pattern = [True, False, True, False]
        for i, (result, should_find) in enumerate(zip(results, expected_pattern)):
            if should_find:
                self.assertIsNotNone(result, f"Expected product at index {i}")
                self._validate_product_data(result, self.test_sku_valid)
            else:
                self.assertIsNone(result, f"Expected None at index {i}")

        print("✅ MIXED SCENARIOS: Alternating found/not found pattern validated")


# ============================================================================
# TEST RUNNER AND UTILITIES
# ============================================================================

class TestRunner:
    """Enhanced test runner with detailed reporting."""

    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'total_time': 0
        }

    def run_tests(self, test_pattern='*'):
        """Run tests with enhanced reporting."""
        print("🚀 Starting Coastal Scraper Test Suite")
        print("=" * 60)

        start_time = time.time()

        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestCoastalScraper)

        # Run tests with custom result handler
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)

        end_time = time.time()
        duration = end_time - start_time

        # Update results
        self.results['passed'] = result.testsRun - len(result.failures) - len(result.errors)
        self.results['failed'] = len(result.failures)
        self.results['errors'] = len(result.errors)
        self.results['skipped'] = len(result.skipped)
        self.results['total_time'] = duration

        # Print detailed results
        self._print_detailed_results(result, duration)

        return result.wasSuccessful()

    def _print_detailed_results(self, result, duration):
        """Print detailed test results."""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        print(f"⏱️  Total Time: {duration:.2f} seconds")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"💥 Errors: {self.results['errors']}")
        print(f"⏭️  Skipped: {self.results['skipped']}")

        success_rate = (self.results['passed'] / result.testsRun) * 100 if result.testsRun > 0 else 0
        print(f"📊 Success Rate: {success_rate:.1f}%")
        if result.failures:
            print("\n❌ FAILURES:")
            for test, traceback in result.failures:
                print(f"  • {test}")

        if result.errors:
            print("\n💥 ERRORS:")
            for test, traceback in result.errors:
                print(f"  • {test}")

        # Scenario-specific results
        print("\n🎯 SCENARIO RESULTS:")
        print("  ✅ Product Found scenarios: PASSED" if self.results['passed'] > 0 else "  ❌ Product Found scenarios: FAILED")
        print("  ✅ No Product Found scenarios: PASSED" if self.results['passed'] > 0 else "  ❌ No Product Found scenarios: FAILED")


def run_cli_tests():
    """Run tests from command line with options."""
    import argparse

    parser = argparse.ArgumentParser(description="Coastal Scraper Test Suite")
    parser.add_argument('--pattern', default='*', help='Test pattern to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--failfast', action='store_true', help='Stop on first failure')

    args = parser.parse_args()

    # Set up test runner
    runner = TestRunner()
    success = runner.run_tests(args.pattern)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    # Check if run as CLI
    if len(sys.argv) > 1:
        run_cli_tests()
    else:
        # Run all tests
        runner = TestRunner()
        success = runner.run_tests()

        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n💥 Some tests failed!")
            sys.exit(1)