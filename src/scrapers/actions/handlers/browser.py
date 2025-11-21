import logging
from typing import Any, Dict

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry

logger = logging.getLogger(__name__)

@ActionRegistry.register("configure_browser")
class ConfigureBrowserAction(BaseAction):
    """Action to configure browser settings dynamically."""

    def execute(self, params: Dict[str, Any]) -> None:
        block_resources = params.get("block_resources", [])
        
        # Note: Changing browser capabilities at runtime is limited in Selenium
        # But we can use CDP commands if using Chrome
        
        if block_resources and self.executor.browser.driver.name == "chrome":
            try:
                self.executor.browser.driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": block_resources})
                self.executor.browser.driver.execute_cdp_cmd("Network.enable", {})
                logger.info(f"Blocked resources: {block_resources}")
            except Exception as e:
                logger.warning(f"Failed to block resources: {e}")
