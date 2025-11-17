"""
Test login functionality for workflow executor.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.scrapers.executor.workflow_executor import (WorkflowExecutionError,
                                                     WorkflowExecutor)
from src.scrapers.models.config import LoginConfig, ScraperConfig


@pytest.fixture
def login_config():
    """Create a sample config with login."""
    return ScraperConfig(
        name="Test Scraper with Login",
        base_url="https://example.com",
        timeout=30,
        retries=3,
        selectors=[],
        workflows=[],
        login=LoginConfig(
            url="https://example.com/login",
            username_field="#username",
            password_field="#password",
            submit_button="#login-btn",
            success_indicator=".dashboard",
        ),
    )


class TestLoginFunctionality:
    """Test login functionality."""

    def test_login_action_success(self, login_config):
        """Test successful login action."""
        with patch(
            "src.scrapers.executor.workflow_executor.create_browser"
        ) as mock_create:
            mock_browser = MagicMock()
            mock_create.return_value = mock_browser

            executor = WorkflowExecutor(login_config, headless=True)

            # Mock the login elements
            mock_username_field = MagicMock()
            mock_password_field = MagicMock()
            mock_submit_button = MagicMock()
            mock_success_indicator = MagicMock()

            mock_browser.driver.find_element.side_effect = [
                mock_username_field,
                mock_password_field,
                mock_submit_button,
                mock_success_indicator,
            ]

            params = {
                "username": "testuser",
                "password": "testpass",
                "url": "https://example.com/login",
                "username_field": "#username",
                "password_field": "#password",
                "submit_button": "#login-btn",
                "success_indicator": ".dashboard",
            }

            # This should not raise an exception
            executor._action_login(params)

            # Verify calls
            mock_browser.get.assert_called_once_with("https://example.com/login")
            assert mock_username_field.send_keys.called
            assert mock_password_field.send_keys.called
            assert mock_submit_button.click.called

    def test_login_action_missing_params(self, login_config):
        """Test login action with missing parameters."""
        with patch("src.scrapers.executor.workflow_executor.create_browser"):
            executor = WorkflowExecutor(login_config, headless=True)

            params = {
                "username": "testuser",
                # Missing password
                "url": "https://example.com/login",
                "username_field": "#username",
                "password_field": "#password",
                "submit_button": "#login-btn",
            }

            with pytest.raises(
                WorkflowExecutionError,
                match="Login action requires username, password, url, username_field, password_field, and submit_button parameters",
            ):
                executor._action_login(params)

    def test_login_action_no_success_indicator(self, login_config):
        """Test login action without success indicator."""
        with patch(
            "src.scrapers.executor.workflow_executor.create_browser"
        ) as mock_create:
            mock_browser = MagicMock()
            mock_create.return_value = mock_browser

            executor = WorkflowExecutor(login_config, headless=True)

            # Mock the login elements
            mock_username_field = MagicMock()
            mock_password_field = MagicMock()
            mock_submit_button = MagicMock()

            mock_browser.driver.find_element.side_effect = [
                mock_username_field,
                mock_password_field,
                mock_submit_button,
            ]

            params = {
                "username": "testuser",
                "password": "testpass",
                "url": "https://example.com/login",
                "username_field": "#username",
                "password_field": "#password",
                "submit_button": "#login-btn",
                # No success_indicator
            }

            # This should not raise an exception
            executor._action_login(params)

            # Should wait for URL change instead
            mock_browser.get.assert_called_once_with("https://example.com/login")
