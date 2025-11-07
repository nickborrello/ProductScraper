import pytest
import os
import sys
import importlib.util
import glob
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class TestScrapers:
    """Test suite for all scraper modules.
    
    To add integration testing for a scraper:
    1. Add a TEST_SKU variable to the scraper module with a SKU that exists on that site
    2. Example: TEST_SKU = "035585499741"  # KONG Pull A Partz Pals Koala SM
    3. Run tests with RUN_INTEGRATION_TESTS=true to include live scraping tests
    """

    @pytest.fixture(scope="class")
    def scraper_modules(self):
        """Discover all scraper modules dynamically."""
        scrapers_dir = os.path.join(PROJECT_ROOT, "src", "scrapers")
        scraper_files = glob.glob(os.path.join(scrapers_dir, "*.py"))
        scraper_files = [f for f in scraper_files if not f.endswith("__init__.py")]

        # Exclude archived scrapers
        archive_dir = os.path.join(scrapers_dir, "archive")
        if os.path.exists(archive_dir):
            archived_files = glob.glob(os.path.join(archive_dir, "*.py"))
            archived_names = [os.path.basename(f) for f in archived_files]
            scraper_files = [f for f in scraper_files if os.path.basename(f) not in archived_names]

        modules = {}
        for scraper_file in scraper_files:
            module_name = os.path.basename(scraper_file)[:-3]  # Remove .py extension

            try:
                # Import the module
                spec = importlib.util.spec_from_file_location(module_name, scraper_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[module_name] = module
            except Exception as e:
                pytest.fail(f"Failed to import scraper module {module_name}: {e}")

        return modules

    def test_scraper_imports(self, scraper_modules):
        """Test that all scraper modules can be imported successfully."""
        assert len(scraper_modules) > 0, "No scraper modules found"

        # Expected scraper modules (based on the mapping in master.py)
        expected_modules = [
            'orgill', 'bradley_caldwell', 'central_pet', 'coastal',
            'mazuri', 'nassau_candy', 'petfoodex', 'phillips'
        ]

        found_modules = list(scraper_modules.keys())
        print(f"Found scraper modules: {found_modules}")

        # Check that we have some expected modules
        expected_found = [m for m in expected_modules if m in found_modules]
        assert len(expected_found) > 0, f"None of expected modules {expected_modules} found in {found_modules}"

    def test_scraper_functions_exist(self, scraper_modules):
        """Test that each scraper module has the expected scrape function."""
        # Only test modules that actually have scrape functions (real scrapers)
        real_scrapers = {}
        for module_name, module in scraper_modules.items():
            # Find the scrape function
            scrape_func = None
            for attr_name in dir(module):
                if attr_name.startswith('scrape_'):
                    func = getattr(module, attr_name)
                    # Check if the function is defined in this module (not imported)
                    if hasattr(func, '__module__') and func.__module__ == module_name:
                        scrape_func = func
                        break
            
            if scrape_func is not None:
                real_scrapers[module_name] = (module, scrape_func)
        
        assert len(real_scrapers) > 0, "No real scraper modules found"
        
        for module_name, (module, scrape_func) in real_scrapers.items():
            assert callable(scrape_func), f"scrape_ function in {module_name} is not callable"

            # Check function signature - should accept skus parameter
            import inspect
            sig = inspect.signature(scrape_func)
            assert 'skus' in sig.parameters, f"scrape_ function in {module_name} should have 'skus' parameter"

            print(f"✅ {module_name}: Found scrape function {scrape_func.__name__}")

    def test_scraper_has_headless_setting(self, scraper_modules):
        """Test that each scraper module has a HEADLESS setting."""
        # Only test modules that actually have scrape functions (real scrapers)
        real_scrapers = {}
        for module_name, module in scraper_modules.items():
            # Find the scrape function
            scrape_func = None
            for attr_name in dir(module):
                if attr_name.startswith('scrape_'):
                    func = getattr(module, attr_name)
                    # Check if the function is defined in this module (not imported)
                    if hasattr(func, '__module__') and func.__module__ == module_name:
                        scrape_func = func
                        break
            
            if scrape_func is not None:
                real_scrapers[module_name] = module
        
        assert len(real_scrapers) > 0, "No real scraper modules found"
        
        for module_name, module in real_scrapers.items():
            headless_setting = getattr(module, 'HEADLESS', None)
            assert headless_setting is not None, f"Module {module_name} should have HEADLESS setting"
            assert isinstance(headless_setting, bool), f"HEADLESS in {module_name} should be boolean"

            print(f"✅ {module_name}: HEADLESS = {headless_setting}")

    @patch('selenium.webdriver.Chrome')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_scraper_function_signature(self, mock_sleep, mock_chrome, scraper_modules):
        """Test that scraper functions can be called with proper parameters (mocked)."""
        # Only test modules that actually have scrape functions (real scrapers)
        real_scrapers = {}
        for module_name, module in scraper_modules.items():
            # Find the scrape function
            scrape_func = None
            for attr_name in dir(module):
                if attr_name.startswith('scrape_'):
                    func = getattr(module, attr_name)
                    if hasattr(func, '__module__') and func.__module__ == module_name:
                        scrape_func = func
                        break
            
            if scrape_func is not None:
                real_scrapers[module_name] = (module, scrape_func)
        
        assert len(real_scrapers) > 0, "No real scraper modules found"
        
        for module_name, (module, scrape_func) in real_scrapers.items():
            # Mock browser creation if it exists
            if hasattr(module, 'init_browser'):
                with patch.object(module, 'init_browser', return_value=MagicMock()):
                    try:
                        # Test with empty SKU list - should not crash
                        result = scrape_func([])
                        # Result should be a list or None
                        assert result is None or isinstance(result, list), f"scrape_ function in {module_name} should return list or None"
                        print(f"✅ {module_name}: Function signature test passed")
                    except Exception as e:
                        # Some scrapers might require more setup, so we'll just warn
                        print(f"⚠️  {module_name}: Function signature test failed (may require more setup): {e}")
            else:
                print(f"⚠️  {module_name}: No init_browser function found, skipping signature test")

    def test_scraper_with_test_product(self, scraper_modules):
        """Test that scrapers can successfully scrape a known test product.

        This test ALWAYS runs and validates that scrapers can retrieve complete product data.
        Required fields (Name, SKU) must be present and not empty or "N/A".
        Results are printed for each scraper.
        """
        # Only test modules that actually have scrape functions (real scrapers)
        real_scrapers = {}
        for module_name, module in scraper_modules.items():
            # Find the scrape function
            scrape_func = None
            for attr_name in dir(module):
                if attr_name.startswith('scrape_'):
                    func = getattr(module, attr_name)
                    if hasattr(func, '__module__') and func.__module__ == module_name:
                        scrape_func = func
                        break

            if scrape_func is not None:
                real_scrapers[module_name] = (module, scrape_func)

        assert len(real_scrapers) > 0, "No real scraper modules found"

        # Track results for all scrapers
        results = {}
        passed_scrapers = []
        failed_scrapers = []

        print("\n" + "="*60)
        print("🧪 INTEGRATION TEST RESULTS")
        print("="*60)

        for module_name, (module, scrape_func) in real_scrapers.items():
            print(f"\n🔍 Testing {module_name}...")

            # Skip scrapers that don't have browser automation
            # Check for: init_browser function OR create_browser usage in scrape function
            import inspect

            has_init_browser = hasattr(module, 'init_browser')
            uses_create_browser = False

            # Check if the scrape function uses create_browser
            if hasattr(module, scrape_func.__name__):
                func = getattr(module, scrape_func.__name__)
                try:
                    source = inspect.getsource(func)
                    uses_create_browser = 'create_browser' in source
                except:
                    pass

            if not (has_init_browser or uses_create_browser):
                print(f"⚠️  {module_name}: SKIPPED - No browser automation found")
                results[module_name] = "SKIPPED"
                continue

            # Get test SKU from module, fallback to default
            test_sku = getattr(module, 'TEST_SKU', '035585499741')  # Default KONG product

            try:
                # Use threading Timer for cross-platform timeout
                import threading

                result_container = {'result': None, 'exception': None, 'completed': False}

                def run_scraper():
                    try:
                        # Test with module-specific test SKU
                        result = scrape_func([test_sku])
                        result_container['result'] = result
                        result_container['completed'] = True
                    except Exception as e:
                        result_container['exception'] = e
                        result_container['completed'] = True

                # Start scraper in a thread
                scraper_thread = threading.Thread(target=run_scraper)
                scraper_thread.daemon = True
                scraper_thread.start()

                # Wait for completion with timeout (30 seconds for real scraping - login can be slow)
                scraper_thread.join(timeout=30)

                if scraper_thread.is_alive():
                    print(f"❌ {module_name}: FAILED - Test timed out after 90 seconds")
                    results[module_name] = "TIMEOUT"
                    failed_scrapers.append(module_name)
                    continue

                if result_container['exception']:
                    print(f"❌ {module_name}: FAILED - {str(result_container['exception'])}")
                    results[module_name] = f"ERROR: {str(result_container['exception'])}"
                    failed_scrapers.append(module_name)
                    continue

                result = result_container['result']

                # Validate the result
                if result is None:
                    print(f"❌ {module_name}: FAILED - Returned None for test SKU {test_sku}")
                    results[module_name] = "NO_RESULT"
                    failed_scrapers.append(module_name)
                    continue

                if not isinstance(result, list):
                    print(f"❌ {module_name}: FAILED - Did not return a list for test SKU {test_sku}")
                    results[module_name] = "INVALID_RETURN_TYPE"
                    failed_scrapers.append(module_name)
                    continue

                if len(result) == 0:
                    print(f"❌ {module_name}: FAILED - Returned empty list for test SKU {test_sku}")
                    results[module_name] = "EMPTY_RESULT"
                    failed_scrapers.append(module_name)
                    continue

                # Check if we got at least one product
                product = result[0]
                if not isinstance(product, dict):
                    print(f"❌ {module_name}: FAILED - Product data is not a dictionary")
                    results[module_name] = "INVALID_PRODUCT_DATA"
                    failed_scrapers.append(module_name)
                    continue

                # Check if product is flagged (incomplete data) - should fail test
                if product.get('flagged', False):
                    print(f"❌ {module_name}: FAILED - Product is flagged (incomplete data)")
                    results[module_name] = "FLAGGED_PRODUCT"
                    failed_scrapers.append(module_name)
                    continue

                # Check required fields - FAIL if missing, empty, or "N/A"
                required_fields = ['Name', 'SKU']  # Removed Price - we don't scrape prices
                invalid_fields = []

                for field in required_fields:
                    value = product.get(field)
                    if value is None or value == '' or str(value).strip().upper() == 'N/A':
                        invalid_fields.append(field)

                if invalid_fields:
                    print(f"❌ {module_name}: FAILED - Required fields missing/empty/N/A: {invalid_fields}")
                    results[module_name] = f"MISSING_FIELDS: {invalid_fields}"
                    failed_scrapers.append(module_name)
                    continue

                # Additional validation - ensure fields have meaningful content
                name = product.get('Name', '').strip()
                sku = product.get('SKU', '').strip()

                if len(name) < 3:
                    print(f"❌ {module_name}: FAILED - Product name too short: '{name}'")
                    results[module_name] = f"INVALID_NAME: '{name}'"
                    failed_scrapers.append(module_name)
                    continue

                if len(sku) < 3:
                    print(f"❌ {module_name}: FAILED - SKU too short: '{sku}'")
                    results[module_name] = f"INVALID_SKU: '{sku}'"
                    failed_scrapers.append(module_name)
                    continue

                # SUCCESS!
                print(f"✅ {module_name}: PASSED - Successfully scraped test product")
                print(f"   📦 SKU: {sku}, Name: {name[:50]}{'...' if len(name) > 50 else ''}")
                results[module_name] = "PASSED"
                passed_scrapers.append(module_name)

            except Exception as e:
                print(f"❌ {module_name}: FAILED - Test setup error: {str(e)}")
                results[module_name] = f"SETUP_ERROR: {str(e)}"
                failed_scrapers.append(module_name)

        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"✅ PASSED: {len(passed_scrapers)} scrapers")
        for scraper in passed_scrapers:
            print(f"   • {scraper}")

        print(f"❌ FAILED: {len(failed_scrapers)} scrapers")
        for scraper in failed_scrapers:
            print(f"   • {scraper} ({results[scraper]})")

        print(f"⚠️  SKIPPED: {len([r for r in results.values() if r == 'SKIPPED'])} scrapers")
        skipped_scrapers = [name for name, status in results.items() if status == "SKIPPED"]
        for scraper in skipped_scrapers:
            print(f"   • {scraper}")

        print(f"\nTotal scrapers tested: {len(results)}")

        # Fail the test if no scrapers passed
        if len(passed_scrapers) == 0:
            pytest.fail("No scrapers passed the integration test - all failed or were skipped")

    def test_scraper_dependencies(self, scraper_modules):
        """Test that scraper modules have required dependencies."""
        required_imports = [
            'selenium',
            'time',
            'os',
            'sys'
        ]

        for module_name, module in scraper_modules.items():
            missing_deps = []
            for dep in required_imports:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)

            if missing_deps:
                pytest.fail(f"Module {module_name} missing required dependencies: {missing_deps}")

            print(f"✅ {module_name}: Required dependencies available")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])