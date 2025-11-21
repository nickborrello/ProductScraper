from src.scrapers.actions.base import BaseAction

# Import handlers to ensure they are registered
from src.scrapers.actions.handlers import (
    browser,
    click,
    combine,
    conditional,
    extract,
    image,
    input,
    json,
    login,
    navigate,
    sponsored,
    table,
    transform,
    verify,
    wait,
    wait_for,
    weight,
)
from src.scrapers.actions.registry import ActionRegistry

__all__ = ["ActionRegistry", "BaseAction"]
