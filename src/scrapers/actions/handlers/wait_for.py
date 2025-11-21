import time
import logging
from typing import Any, Dict

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)

@ActionRegistry.register("wait_for")
class WaitForAction(BaseAction):
    """Action to wait for an element to be present."""

    def execute(self, params: Dict[str, Any]) -> None:
        selector_param = params.get("selector")
        timeout = params.get("timeout", self.executor.timeout)

        if not selector_param:
            raise WorkflowExecutionError(
                "Wait_for action requires 'selector' parameter"
            )

        selectors = selector_param if isinstance(selector_param, list) else [selector_param]
        
        logger.debug(f"Waiting for any of elements: {selectors} (timeout: {timeout}s, CI: {self.executor.is_ci})")

        start_time = time.time()
        try:
            conditions = [EC.presence_of_element_located((self.executor._get_locator_type(s), s)) for s in selectors]
            WebDriverWait(self.executor.browser.driver, timeout).until(EC.any_of(*conditions))
            wait_duration = time.time() - start_time
            logger.info(f"✅ Element found after {wait_duration:.2f}s from selectors: {selectors}")
        except TimeoutException:
            wait_duration = time.time() - start_time
            logger.warning(f"⏰ TIMEOUT: Element not found within {timeout}s (waited {wait_duration:.2f}s): {selectors}")
            
            # Log debugging info
            try:
                logger.debug(f"Current page URL: {self.executor.browser.driver.current_url}")
                logger.debug(f"Page title: {self.executor.browser.driver.title}")
            except:
                pass

            raise WorkflowExecutionError(
                f"Element not found within {timeout}s: {selectors}"
            )
