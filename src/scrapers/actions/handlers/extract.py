import logging
from typing import Any

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


@ActionRegistry.register("extract_single")
class ExtractSingleAction(BaseAction):
    """Action to extract a single value using a selector."""

    def execute(self, params: dict[str, Any]) -> None:
        field_name = params.get("field")
        selector_name = params.get("selector")

        if not field_name or not selector_name:
            raise WorkflowExecutionError(
                "Extract_single requires 'field' and 'selector' parameters"
            )

        selector_config = self.executor.selectors.get(selector_name)
        if not selector_config:
            raise WorkflowExecutionError(f"Selector '{selector_name}' not found in config")

        try:
            element = self.executor.browser.driver.find_element(
                By.CSS_SELECTOR, selector_config.selector
            )
            value = self.executor._extract_value_from_element(element, selector_config.attribute)
            self.executor.results[field_name] = value
            logger.debug(f"Extracted {field_name}: {value}")
        except NoSuchElementException:
            logger.warning(f"Element not found for field: {field_name}")
            self.executor.results[field_name] = None


@ActionRegistry.register("extract_multiple")
class ExtractMultipleAction(BaseAction):
    """Action to extract multiple values using a selector."""

    def execute(self, params: dict[str, Any]) -> None:
        field_name = params.get("field")
        selector_name = params.get("selector")

        if not field_name or not selector_name:
            raise WorkflowExecutionError(
                "Extract_multiple requires 'field' and 'selector' parameters"
            )

        selector_config = self.executor.selectors.get(selector_name)
        if not selector_config:
            raise WorkflowExecutionError(f"Selector '{selector_name}' not found in config")

        try:
            elements = self.executor.browser.driver.find_elements(
                By.CSS_SELECTOR, selector_config.selector
            )
            values = []
            for element in elements:
                value = self.executor._extract_value_from_element(
                    element, selector_config.attribute
                )
                if value:
                    values.append(value)
            self.executor.results[field_name] = values
            logger.debug(f"Extracted {len(values)} items for {field_name}")
        except Exception as e:
            logger.warning(f"Failed to extract multiple values for {field_name}: {e}")
            self.executor.results[field_name] = []


@ActionRegistry.register("extract")
class ExtractAction(BaseAction):
    """Action to extract multiple fields at once (legacy compatibility)."""

    def execute(self, params: dict[str, Any]) -> None:
        fields = params.get("fields", [])
        logger.debug(f"Starting extract action for fields: {fields}")
        for field_name in fields:
            selector_config = self.executor.selectors.get(field_name)
            if not selector_config:
                logger.warning(f"Selector '{field_name}' not found in config")
                continue

            try:
                locator_type = self.executor._get_locator_type(selector_config.selector)
                if selector_config.multiple:
                    elements = self.executor.browser.driver.find_elements(
                        locator_type, selector_config.selector
                    )
                    values = []
                    for element in elements:
                        value = self.executor._extract_value_from_element(
                            element, selector_config.attribute
                        )
                        if value:
                            values.append(value)
                    # Deduplicate values while preserving order
                    seen = set()
                    deduplicated_values = []
                    for value in values:
                        if value not in seen:
                            seen.add(value)
                            deduplicated_values.append(value)
                    self.executor.results[field_name] = deduplicated_values
                else:
                    element = self.executor.browser.driver.find_element(
                        locator_type, selector_config.selector
                    )
                    value = self.executor._extract_value_from_element(
                        element, selector_config.attribute
                    )
                    self.executor.results[field_name] = value
                logger.debug(f"Extracted {field_name}: {self.executor.results[field_name]}")
            except NoSuchElementException:
                logger.warning(f"Element not found for field: {field_name}")
                self.executor.results[field_name] = [] if selector_config.multiple else None
        logger.info(f"Extract action completed. Results: {self.executor.results}")
