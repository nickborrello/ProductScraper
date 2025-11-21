import logging
import time
from typing import Any

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry

logger = logging.getLogger(__name__)


@ActionRegistry.register("wait")
class WaitAction(BaseAction):
    """Action to wait for a specified amount of time."""

    def execute(self, params: dict[str, Any]) -> None:
        seconds = params.get("seconds", params.get("timeout", 1))
        logger.debug(f"Waiting for {seconds} seconds")
        time.sleep(seconds)
