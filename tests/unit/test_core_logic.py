import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call, Mock

# Add project root to sys.path to allow imports from the main project directory
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from src.scrapers.main import run_scraping, run_db_refresh

# --- Test Fixtures ---


@pytest.fixture
def mock_callbacks():
    """Provides mock progress and log callbacks."""
    progress_mock = MagicMock()
    log_mock = MagicMock()
    log_mock.emit = log_mock  # Make emit the same as the mock itself
    return progress_mock, log_mock


@pytest.fixture
def mock_scraper():
    """Fixture to mock the ProductScraper class."""
    with patch("src.scrapers.master.ProductScraper", autospec=True) as mock:
        yield mock


@pytest.fixture
def mock_db_refresh_func():
    """Fixture to mock the refresh_database_from_xml function."""
    with patch("src.scrapers.main.refresh_database_from_xml", autospec=True) as mock:
        yield mock


@pytest.fixture
def mock_excel_validation():
    """Fixture to mock validate_excel_columns."""
    with patch("src.scrapers.main.validate_excel_columns", autospec=True) as mock:
        yield mock


@pytest.fixture
def mock_pandas_read():
    """Fixture to mock pandas.read_excel."""
    with patch("pandas.read_excel", autospec=True) as mock:
        yield mock


@pytest.fixture
def mock_os_remove():
    """Fixture to mock os.remove."""
    with patch("os.remove", autospec=True) as mock:
        yield mock


# --- Tests for run_scraping ---


def test_run_scraping_success(
    mock_callbacks, mock_scraper
):
    """Test a successful run of the scraping process."""
    progress_callback, log_callback = mock_callbacks
    file_path = "dummy/path/to/file.xlsx"

    with patch("src.scrapers.main.PRODUCT_SCRAPER_AVAILABLE", True), \
         patch("src.scrapers.main.validate_excel_columns", return_value=(True, "Validation passed")), \
         patch("pandas.read_excel") as mock_read:
        
        mock_read.return_value.empty = False
        
        run_scraping(file_path, progress_callback, log_callback)

    # Assertions
    log_callback.assert_any_call(f"🚀 run_scraping called with file: {file_path}")
    log_callback.assert_any_call(f"📂 Selected file: {os.path.basename(file_path)}")
    log_callback.assert_any_call("🚀 Starting scraper...")
    log_callback.assert_any_call("✅ Product scraping completed!")
    mock_scraper.assert_called_once_with(
        file_path,
        interactive=True,
        selected_sites=None,
        log_callback=log_callback,
        progress_callback=progress_callback,
        editor_callback=None,
        status_callback=None,
    )
    mock_scraper.return_value.run.assert_called_once()
    assert progress_callback.emit.call_count == 5  # 10, 20, 30, 40, 90


def test_run_scraping_scraper_not_available(mock_callbacks):
    """Test run_scraping when the scraper module is not available."""
    progress_callback, log_callback = mock_callbacks
    with patch("src.scrapers.main.PRODUCT_SCRAPER_AVAILABLE", False):
        run_scraping("any/path", progress_callback, log_callback)

    log_callback.assert_called_with(
        "❌ ProductScraper module not available. Please check your installation."
    )
    progress_callback.emit.assert_not_called()


def test_run_scraping_invalid_excel(mock_callbacks):
    """Test run_scraping with an invalid Excel file."""
    _, log_callback = mock_callbacks
    file_path = "dummy/path/to/invalid.xlsx"
    
    with patch("src.scrapers.main.PRODUCT_SCRAPER_AVAILABLE", True), \
         patch("src.scrapers.main.validate_excel_columns", return_value=(False, "Missing columns")):
        
        run_scraping(file_path, None, log_callback)

    log_callback.assert_any_call("Missing columns")
    log_callback.assert_any_call("⚠️ Please update the Excel file with required data.")


def test_run_scraping_empty_excel(
    mock_callbacks, mock_os_remove
):
    """Test run_scraping with an empty Excel file that should be deleted."""
    _, log_callback = mock_callbacks
    file_path = "dummy/path/to/empty.xlsx"

    with patch("src.scrapers.main.PRODUCT_SCRAPER_AVAILABLE", True), \
         patch("src.scrapers.main.validate_excel_columns", return_value=(True, "Validation passed")), \
         patch("pandas.read_excel") as mock_read:
        
        mock_read.return_value.empty = True
        
        run_scraping(file_path, None, log_callback)

    log_callback.assert_any_call(f"⚠️ Input file '{file_path}' is empty. Deleting file.")
    mock_os_remove.assert_called_once_with(file_path)
    log_callback.assert_any_call(f"🗑️ Deleted empty input file: {file_path}")


# --- Tests for run_db_refresh ---


def test_run_db_refresh_success(mock_callbacks, mock_db_refresh_func):
    """Test a successful database refresh."""
    progress_callback, log_callback = mock_callbacks
    xml_path = os.path.join(
        PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
    )

    mock_db_refresh_func.return_value = (True, "DB updated")

    with patch("os.path.exists", return_value=True):
        run_db_refresh(progress_callback, log_callback)

    log_callback.assert_any_call("💾 Refreshing database from XML file...")
    log_callback.assert_any_call("🔄 Processing XML and updating database...")
    mock_db_refresh_func.assert_called_once_with(xml_path)
    log_callback.assert_any_call("DB updated")
    log_callback.assert_any_call("💡 Database updated successfully.")
    assert progress_callback.emit.call_count == 3  # 10, 30, 90


def test_run_db_refresh_xml_not_found(mock_callbacks):
    """Test database refresh when the XML file is not found."""
    progress_callback, log_callback = mock_callbacks
    xml_path = os.path.join(
        PROJECT_ROOT, "data", "databases", "shopsite_products_cleaned.xml"
    )

    with patch("os.path.exists", return_value=False):
        run_db_refresh(progress_callback, log_callback)

    log_callback.assert_any_call(f"❌ XML file not found: {xml_path}")
    log_callback.assert_any_call(
        "💡 Please download the XML from ShopSite first (Option 4 in CLI)."
    )
    progress_callback.emit.assert_called_once_with(10)


def test_run_db_refresh_exception(mock_callbacks, mock_db_refresh_func):
    """Test database refresh when an exception occurs."""
    progress_callback, log_callback = mock_callbacks
    mock_db_refresh_func.side_effect = Exception("DB connection failed")

    with patch("os.path.exists", return_value=True):
        with pytest.raises(Exception, match="DB connection failed"):
            run_db_refresh(progress_callback, log_callback)

    log_callback.assert_any_call("❌ XML processing failed: DB connection failed")
