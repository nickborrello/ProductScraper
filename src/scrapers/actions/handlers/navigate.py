import logging
import time
from typing import Any

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


@ActionRegistry.register("navigate")
class NavigateAction(BaseAction):
    """Action to navigate to a URL."""

    def execute(self, params: dict[str, Any]) -> None:
        url = params.get("url")
        if not url:
            raise WorkflowExecutionError("Navigate action requires 'url' parameter")

        logger.info(f"Navigating to: {url}")
        self.executor.browser.get(url)

        # Check HTTP status if monitoring is enabled
        if self.executor.config.http_status and self.executor.config.http_status.enabled:
            self.executor._check_http_status_after_navigation(url, params)

        # Optional wait after navigation
        wait_time = params.get("wait_after", 0)
        if wait_time > 0:
            time.sleep(wait_time)

        # Mark that first navigation is done
        self.executor.first_navigation_done = True
