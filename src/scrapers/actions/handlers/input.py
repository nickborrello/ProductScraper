import logging
from typing import Any, Dict

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)

@ActionRegistry.register("input_text")
class InputTextAction(BaseAction):
    """Action to input text into a form field."""

    def execute(self, params: Dict[str, Any]) -> None:
        selector = params.get("selector")
        text = params.get("text")
        clear_first = params.get("clear_first", True)

        if not selector or text is None:
            raise WorkflowExecutionError(
                "Input_text requires 'selector' and 'text' parameters"
            )

        try:
            element = self.executor.browser.driver.find_element(By.CSS_SELECTOR, selector)
            if clear_first:
                element.clear()
            element.send_keys(str(text))
            logger.debug(f"Input text into {selector}: {text}")
        except NoSuchElementException:
            raise WorkflowExecutionError(f"Input element not found: {selector}")
