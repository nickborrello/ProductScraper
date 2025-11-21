import logging
import re
import time
from typing import Any

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


@ActionRegistry.register("click")
class ClickAction(BaseAction):
    """Action to click on an element with proper WebDriverWait and retry logic."""

    def execute(self, params: dict[str, Any]) -> None:
        selector = params.get("selector")
        filter_text = params.get("filter_text")
        filter_text_exclude = params.get("filter_text_exclude")
        index = params.get("index", 0)

        if not selector:
            raise WorkflowExecutionError("Click action requires 'selector' parameter")

        locator_type = self.executor._get_locator_type(selector)
        max_retries = params.get("max_retries", 3 if self.executor.is_ci else 1)

        logger.debug(
            f"Attempting to click element: {selector} (locator: {locator_type}, CI: {self.executor.is_ci}, max_retries: {max_retries})"
        )

        # Initial wait for at least one element to be present
        try:
            WebDriverWait(self.executor.browser.driver, self.executor.timeout).until(
                EC.presence_of_element_located((locator_type, selector))
            )
            logger.info("At least one element is present, proceeding to filter and click")
        except TimeoutException:
            logger.warning(f"No elements found for selector '{selector}' within timeout period.")
            raise WorkflowExecutionError(f"No elements found for selector: {selector}")

        # Now find elements and perform filtering and click
        try:
            elements = self.executor.browser.driver.find_elements(locator_type, selector)

            if not elements:
                raise NoSuchElementException(f"No elements found for selector: {selector}")

            filtered_elements = elements
            if filter_text:
                filtered_elements = [
                    el for el in filtered_elements if re.search(filter_text, el.text, re.IGNORECASE)
                ]

            if filter_text_exclude:
                filtered_elements = [
                    el
                    for el in filtered_elements
                    if not re.search(filter_text_exclude, el.text, re.IGNORECASE)
                ]

            if not filtered_elements:
                raise NoSuchElementException(
                    f"No elements remaining after filtering for selector: {selector}"
                )

            if index >= len(filtered_elements):
                raise WorkflowExecutionError(
                    f"Index {index} out of bounds for filtered elements (count: {len(filtered_elements)}) for selector: {selector}"
                )

            element_to_click = filtered_elements[index]

            # Scroll element into view if needed
            try:
                self.executor.browser.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    element_to_click,
                )
                time.sleep(0.5)  # Brief pause after scrolling
            except Exception as scroll_e:
                logger.debug(f"Could not scroll element into view: {scroll_e}")

            # Attempt click
            element_to_click.click()
            logger.info(f"Successfully clicked element: {selector} at index {index}")

            # Optional wait after click
            wait_time = params.get("wait_after", 0)
            if wait_time > 0:
                logger.debug(f"Waiting {wait_time}s after click")
                time.sleep(wait_time)

        except Exception as e:
            raise WorkflowExecutionError(f"Failed to click element after waiting: {e}")
