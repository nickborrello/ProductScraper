import logging
from typing import Any

from selenium.webdriver.common.by import By

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


@ActionRegistry.register("parse_table")
class ParseTableAction(BaseAction):
    """Action to parse an HTML table into a dictionary or list."""

    def execute(self, params: dict[str, Any]) -> None:
        selector = params.get("selector")
        target_field = params.get("target_field")
        key_column = params.get("key_column", 0)
        value_column = params.get("value_column", 1)

        if not selector or not target_field:
            raise WorkflowExecutionError("Parse_table requires 'selector' and 'target_field'")

        try:
            table = self.executor.browser.driver.find_element(By.CSS_SELECTOR, selector)
            rows = table.find_elements(By.TAG_NAME, "tr")

            result_data = {}

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, "th")

                if len(cells) >= max(key_column, value_column) + 1:
                    key = cells[key_column].text.strip().rstrip(":")
                    value = cells[value_column].text.strip()
                    if key:
                        result_data[key] = value

            self.executor.results[target_field] = result_data
            logger.debug(f"Parsed table into {target_field}: {len(result_data)} entries")

        except Exception as e:
            logger.warning(f"Failed to parse table: {e}")
            self.executor.results[target_field] = {}
