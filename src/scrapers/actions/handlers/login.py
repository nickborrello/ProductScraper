import logging
from typing import Any, cast

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry

logger = logging.getLogger(__name__)


@ActionRegistry.register("login")
class LoginAction(BaseAction):
    """Action to execute login workflow."""

    def execute(self, params: dict[str, Any]) -> None:
        # Merge login details from config into params
        if self.executor.config.login:
            params.update(self.executor.config.login.model_dump())

        # Get credentials from settings manager
        scraper_name = self.executor.config.name
        if scraper_name == "phillips":
            username, password = self.executor.settings.phillips_credentials
            params["username"] = username  # type: ignore
            params["password"] = password  # type: ignore
        elif scraper_name == "orgill":
            username, password = self.executor.settings.orgill_credentials
            params["username"] = username  # type: ignore
            params["password"] = password  # type: ignore
        elif scraper_name == "petfoodex":
            username, password = self.executor.settings.petfoodex_credentials
            params["username"] = username  # type: ignore
            params["password"] = password  # type: ignore

        username = params.get("username")  # type: ignore
        password = params.get("password")  # type: ignore
        
        # Ensure credentials are strings
        if username is not None:
            username = str(username)
        if password is not None:
            password = str(password)
        login_url = params.get("url")

        # Use the executor's internal login method logic, but adapted
        # Since the original method was complex and called other actions,
        # we might want to keep the logic here or call the executor's method if we keep it temporarily.
        # For now, let's call the executor's method to ensure backward compatibility during migration
        # But ideally this should be fully refactored.

        # To avoid circular dependency or complex refactoring right now,
        # we will implement the core logic here using other actions.

        if not username or not password:
            logger.warning(f"Missing credentials for {scraper_name}, skipping login")
            return

        logger.info(f"Logging in to {scraper_name} at {login_url}")

        # Navigate
        self.executor._action_navigate({"url": login_url})

        # Input username
        username_field = params.get("username_field")
        if username_field:
            self.executor._action_input_text({"selector": username_field, "text": username})

        # Input password
        password_field = params.get("password_field")
        if password_field:
            self.executor._action_input_text({"selector": password_field, "text": password})

        # Click submit
        submit_button = params.get("submit_button")
        if submit_button:
            self.executor._action_click({"selector": submit_button})

        # Wait for success
        success_indicator = params.get("success_indicator")
        if success_indicator:
            self.executor._action_wait_for({"selector": success_indicator, "timeout": 15})
            logger.info("Login successful")
