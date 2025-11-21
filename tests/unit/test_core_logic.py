from unittest.mock import MagicMock, patch

import pytest

from src.scrapers.main import run_db_refresh

# --- Test Fixtures ---


@pytest.fixture
def mock_callbacks():
    """Provides mock progress and log callbacks."""
    progress_mock = MagicMock()
    log_mock = MagicMock()
    log_mock.emit.return_value = None
    return progress_mock, log_mock


@pytest.fixture
def mock_db_refresh_func():
    """Fixture to mock the refresh_database_from_xml function."""
    with patch("src.scrapers.main.refresh_database_from_xml", autospec=True) as mock:
        yield mock


# --- Tests for run_scraping ---


def test_run_scraping_success(tmp_path, capsys):
    """Test a successful run of the scraping process with available configs."""
    from src.scrapers.main import run_scraping
    
    # Create config directory with sample configs
    config_dir = tmp_path / "src" / "scrapers" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "amazon.yaml").write_text("name: amazon\n")
    (config_dir / "phillips.yaml").write_text("name: phillips\n")
    
    excel_file = tmp_path / "test.xlsx"
    excel_file.write_text("")
    
    with patch("src.scrapers.main.project_root", tmp_path):
        run_scraping(str(excel_file))
    
    captured = capsys.readouterr()
    assert "🚀 Starting scraping" in captured.out
    assert "✅ New modular scraper system initialized" in captured.out


def test_run_scraping_scraper_not_available(tmp_path, capsys):
    """Test run_scraping when no scraper configs are available."""
    from src.scrapers.main import run_scraping
    
    excel_file = tmp_path / "test.xlsx"
    excel_file.write_text("")
    
    with patch("src.scrapers.main.project_root", tmp_path):
        run_scraping(str(excel_file))
    
    captured = capsys.readouterr()
    assert "❌ No scraper configurations found" in captured.out


def test_run_scraping_invalid_excel(tmp_path, capsys):
    """Test run_scraping with a non-existent Excel file (stub doesn't validate yet)."""
    from src.scrapers.main import run_scraping
    
    config_dir = tmp_path / "src" / "scrapers" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "test.yaml").write_text("name: test\n")
    
    excel_file = tmp_path / "nonexistent.xlsx"
    
    with patch("src.scrapers.main.project_root", tmp_path):
        run_scraping(str(excel_file))
    
    captured = capsys.readouterr()
    assert "🚀 Starting scraping" in captured.out


def test_run_scraping_empty_excel(tmp_path, capsys):
    """Test run_scraping with selected sites that don't exist."""
    from src.scrapers.main import run_scraping
    
    config_dir = tmp_path / "src" / "scrapers" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "amazon.yaml").write_text("name: amazon\n")
    
    excel_file = tmp_path / "test.xlsx"
    excel_file.write_text("")
    
    with patch("src.scrapers.main.project_root", tmp_path):
        run_scraping(str(excel_file), selected_sites=["NonExistent", "AlsoFake"])
    
    captured = capsys.readouterr()
    assert "❌ None of the selected sites are available" in captured.out


# --- Tests for run_db_refresh ---


def test_run_db_refresh_success(mock_callbacks, mock_db_refresh_func):
    """Test a successful database refresh."""
    progress_callback, log_callback = mock_callbacks
    expected_call_count = 3

    mock_db_refresh_func.return_value = (True, "DB updated")

    run_db_refresh(progress_callback, log_callback)

    log_callback.emit.assert_any_call("💾 Refreshing database from XML file...")
    log_callback.emit.assert_any_call("🔄 Processing XML and updating database...")
    mock_db_refresh_func.assert_called_once()
    log_callback.emit.assert_any_call("💡 Database updated successfully.")
    assert progress_callback.emit.call_count == expected_call_count  # 10, 30, 90


def test_run_db_refresh_failure(mock_callbacks, mock_db_refresh_func):
    """Test a failed database refresh."""
    progress_callback, log_callback = mock_callbacks

    mock_db_refresh_func.return_value = (False, "DB update failed")

    run_db_refresh(progress_callback, log_callback)

    log_callback.emit.assert_any_call("💾 Refreshing database from XML file...")
    log_callback.emit.assert_any_call("🔄 Processing XML and updating database...")
    mock_db_refresh_func.assert_called_once()

    # Check that the success message was NOT called
    for call_args in log_callback.emit.call_args_list:
        assert "💡 Database updated successfully." not in call_args[0]


def test_run_db_refresh_exception(mock_callbacks, mock_db_refresh_func):
    """Test database refresh when an exception occurs."""
    progress_callback, log_callback = mock_callbacks
    mock_db_refresh_func.side_effect = ConnectionError("DB connection failed")

    with pytest.raises(ConnectionError, match="DB connection failed"):
        run_db_refresh(progress_callback, log_callback)
