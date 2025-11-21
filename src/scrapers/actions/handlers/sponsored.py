import logging
from typing import Any

from selenium.webdriver.common.by import By

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry

logger = logging.getLogger(__name__)


@ActionRegistry.register("check_sponsored")
class CheckSponsoredAction(BaseAction):
    """Action to check if an element is sponsored/ad content."""

    def execute(self, params: dict[str, Any]) -> None:
        selector = params.get("selector")
        result_field = params.get("result_field", "is_sponsored")

        if not selector:
            self.executor.results[result_field] = False
            return

        try:
            elements = self.executor.browser.driver.find_elements(By.CSS_SELECTOR, selector)
            is_sponsored = len(elements) > 0
            self.executor.results[result_field] = is_sponsored
            logger.debug(f"Checked sponsored content ({selector}): {is_sponsored}")
        except Exception:
            self.executor.results[result_field] = False
