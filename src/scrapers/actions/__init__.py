from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.actions.base import BaseAction

# Import handlers to ensure they are registered
from src.scrapers.actions.handlers import (
    navigate,
    wait,
    wait_for,
    extract,
    click,
    input,
    login,
    combine,
    transform,
    json,
    image,
    table,
    verify,
    conditional,
    browser,
    sponsored,
    weight
)

__all__ = ["ActionRegistry", "BaseAction"]
