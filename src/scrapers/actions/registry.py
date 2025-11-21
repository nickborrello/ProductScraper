from typing import Dict, Type, Optional
from src.scrapers.actions.base import BaseAction

class ActionRegistry:
    """Registry for managing available workflow actions."""

    _actions: Dict[str, Type[BaseAction]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register an action class."""
        def decorator(action_class: Type[BaseAction]):
            cls._actions[name.lower()] = action_class
            return action_class
        return decorator

    @classmethod
    def get_action_class(cls, name: str) -> Optional[Type[BaseAction]]:
        """Get an action class by name."""
        return cls._actions.get(name.lower())

    @classmethod
    def get_registered_actions(cls) -> Dict[str, Type[BaseAction]]:
        """Get all registered actions."""
        return cls._actions.copy()
