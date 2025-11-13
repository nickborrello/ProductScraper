import pytest
import os
import sys
import importlib.util
import glob
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
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
        """Discover all Apify scraper modules dynamically."""
        scrapers_dir = os.path.join(PROJECT_ROOT, "src", "scrapers")
        
        # Only look for Apify scrapers in subdirectories
        scraper_dirs = []
        for item in os.listdir(scrapers_dir):
            item_path = os.path.join(scrapers_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.') and item != 'archive':
                # Check if it has Apify structure (has .actor directory or main.py with apify import)
                if self._is_apify_scraper(item_path):
                    scraper_dirs.append(item_path)

        modules = {}
        for scraper_dir in scraper_dirs:
            module_name = os.path.basename(scraper_dir)
            main_py_path = os.path.join(scraper_dir, "src", "main.py")
            
            if os.path.exists(main_py_path):
                try:
                    # Import the Apify scraper module
                    spec = importlib.util.spec_from_file_location(module_name, main_py_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Check if it has the scrape_products function (Apify scrapers)
                    if hasattr(module, 'scrape_products'):
                        modules[module_name] = module
                    else:
                        pytest.fail(f"Apify scraper {module_name} does not have scrape_products function")
                        
                except Exception as e:
                    pytest.fail(f"Failed to import Apify scraper module {module_name}: {e}")

        return modules

    def _is_apify_scraper(self, scraper_path):
        """Check if a directory contains an Apify scraper with scrape_products function."""
        main_py = os.path.join(scraper_path, "src", "main.py")
        if os.path.exists(main_py):
            try:
                with open(main_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Must have both apify import AND scrape_products function
                    has_apify = 'from apify import Actor' in content or 'import apify' in content
                    has_scrape_products = 'def scrape_products' in content
                    return has_apify and has_scrape_products
            except:
                pass
        return False

    def test_scraper_imports(self, scraper_modules):
        """Test that all Apify scraper modules can be imported successfully."""
        assert len(scraper_modules) > 0, "No Apify scraper modules found"

        found_modules = list(scraper_modules.keys())
        print(f"Found Apify scraper modules: {found_modules}")

        # Verify each module has the required scrape_products function
        for name, module in scraper_modules.items():
            assert hasattr(module, 'scrape_products'), f"Apify scraper {name} missing scrape_products function"
            assert callable(getattr(module, 'scrape_products')), f"scrape_products in {name} is not callable"

    def test_scraper_functions_exist(self, scraper_modules):
        """Test that each Apify scraper module has the expected scrape_products function."""
        for module_name, module in scraper_modules.items():
            scrape_func = getattr(module, 'scrape_products')
            assert callable(scrape_func), f"scrape_products function in {module_name} is not callable"

            # Check function signature - should accept skus parameter
            import inspect
            sig = inspect.signature(scrape_func)
            assert "skus" in sig.parameters, f"scrape_products function in {module_name} should have 'skus' parameter"

            print(f"✅ {module_name}: Found scrape_products function")

    def test_scraper_dependencies(self, scraper_modules):
        """Test that Apify scraper modules have required dependencies."""
        required_imports = ["selenium", "apify"]

        for module_name, module in scraper_modules.items():
            missing_deps = []
            for dep in required_imports:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)

            if missing_deps:
                pytest.fail(
                    f"Apify scraper {module_name} missing required dependencies: {missing_deps}"
                )

            print(f"✅ {module_name}: Required dependencies available")

    def test_scraper_with_test_product(self, scraper_modules):
        """Test each Apify scraper with a test product."""
        for scraper_name, module in scraper_modules.items():
            # Use the default test SKU from the scraper's main_local function
            test_skus = ["035585499741"]
            
            # Call the scrape_products function (Apify interface)
            try:
                products = module.scrape_products(test_skus)
                
                # Validate the response
                assert isinstance(products, list), f"{scraper_name}: scrape_products should return a list"
                assert len(products) > 0, f"{scraper_name}: scrape_products returned empty list"
                
                # Check that we got at least one valid product
                valid_products = [p for p in products if p is not None]
                assert len(valid_products) > 0, f"{scraper_name}: No valid products returned"
                
                # Validate product structure
                product = valid_products[0]
                assert isinstance(product, dict), f"{scraper_name}: Product should be a dictionary"
                
                # Check for required fields (basic validation)
                required_fields = ['SKU', 'Name']
                for field in required_fields:
                    assert field in product, f"{scraper_name}: Product missing required field '{field}'"
                    assert product[field] is not None, f"{scraper_name}: Product field '{field}' is None"
                    assert str(product[field]).strip() != "", f"{scraper_name}: Product field '{field}' is empty"
                    assert str(product[field]).strip().upper() != "N/A", f"{scraper_name}: Product field '{field}' is 'N/A'"
                
                print(f"✓ {scraper_name}: Successfully scraped test product")
                
            except Exception as e:
                pytest.fail(f"{scraper_name}: Failed to scrape test product: {e}")

    def test_scraper_dependencies(self, scraper_modules):
        """Test that scraper modules have required dependencies."""
        required_imports = ["selenium", "time", "os", "sys"]

        for module_name, module in scraper_modules.items():
            missing_deps = []
            for dep in required_imports:
                try:
                    __import__(dep)
                except ImportError:
                    missing_deps.append(dep)

            if missing_deps:
                pytest.fail(
                    f"Module {module_name} missing required dependencies: {missing_deps}"
                )

            print(f"✅ {module_name}: Required dependencies available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
