import logging
import re
from typing import Any

from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.exceptions import WorkflowExecutionError

logger = logging.getLogger(__name__)


@ActionRegistry.register("transform_value")
class TransformValueAction(BaseAction):
    """Action to transform/clean a value in the results."""

    def execute(self, params: dict[str, Any]) -> None:
        field = params.get("field")
        transformations = params.get("transformations", [])

        if not field:
            raise WorkflowExecutionError("Transform_value requires 'field' parameter")

        value = self.executor.results.get(field)
        if value is None:
            logger.warning(f"Field {field} not found in results, skipping transformation")
            return

        # Handle list of values or single value
        if isinstance(value, list):
            self.executor.results[field] = [
                self._apply_transformations(v, transformations) for v in value
            ]
        else:
            self.executor.results[field] = self._apply_transformations(str(value), transformations)

        logger.debug(f"Transformed {field}: {self.executor.results[field]}")

    def _apply_transformations(self, value: str, transformations: list) -> str:
        result = value
        for transform in transformations:
            t_type = transform.get("type")

            if t_type == "replace":
                pattern = transform.get("pattern")
                replacement = transform.get("replacement", "")
                if pattern:
                    result = re.sub(pattern, replacement, result, flags=re.IGNORECASE).strip()

            elif t_type == "strip":
                chars = transform.get("chars")
                result = result.strip(chars)

            elif t_type == "lower":
                result = result.lower()

            elif t_type == "upper":
                result = result.upper()

            elif t_type == "title":
                result = result.title()

            elif t_type == "regex_extract":
                pattern = transform.get("pattern")
                group = transform.get("group", 1)
                if pattern:
                    match = re.search(pattern, result, flags=re.IGNORECASE)
                    if match:
                        try:
                            result = match.group(group)
                        except IndexError:
                            pass  # Keep original if group not found

        return result
