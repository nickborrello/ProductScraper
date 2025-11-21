import logging
from typing import Any, Dict, List

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.models.config import WorkflowStep

logger = logging.getLogger(__name__)

@ActionRegistry.register("conditional")
class ConditionalAction(BaseAction):
    """Action to execute steps conditionally."""

    def execute(self, params: Dict[str, Any]) -> None:
        condition_type = params.get("condition_type", "field_exists")
        then_steps_data = params.get("then", [])
        else_steps_data = params.get("else", [])
        
        condition_met = False
        
        if condition_type == "field_exists":
            field = params.get("field")
            condition_met = field in self.executor.results and self.executor.results[field] is not None
            
        elif condition_type == "value_match":
            field = params.get("field")
            value = params.get("value")
            actual = self.executor.results.get(field)
            condition_met = str(actual) == str(value)
            
        elif condition_type == "element_exists":
            selector = params.get("selector")
            # We need to check if element exists without throwing error
            from selenium.webdriver.common.by import By
            try:
                self.executor.browser.driver.find_element(By.CSS_SELECTOR, selector)
                condition_met = True
            except:
                condition_met = False

        logger.debug(f"Conditional check '{condition_type}': {condition_met}")
        
        steps_to_execute = then_steps_data if condition_met else else_steps_data
        
        if steps_to_execute:
            # Convert dicts to WorkflowStep objects
            workflow_steps = []
            for step_data in steps_to_execute:
                if isinstance(step_data, dict):
                    # Handle case where step is just a dict
                    workflow_steps.append(WorkflowStep(**step_data))
                elif isinstance(step_data, WorkflowStep):
                    workflow_steps.append(step_data)
            
            logger.info(f"Executing {len(workflow_steps)} conditional steps")
            self.executor.execute_steps(workflow_steps)
