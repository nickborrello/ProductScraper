from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

from src.core.anti_detection_manager import AntiDetectionConfig


class SelectorConfig(BaseModel):
    """Configuration for CSS selectors used in scraping."""

    name: str = Field(..., description="Name of the field to extract")
    selector: str = Field(..., description="CSS selector for the field")
    attribute: Optional[str] = Field(
        None, description="Attribute to extract (e.g., 'text', 'href', 'src')"
    )
    multiple: bool = Field(False, description="Whether to extract multiple elements")


class WorkflowStep(BaseModel):
    """A single step in the scraping workflow."""

    action: str = Field(
        ..., description="Action type (e.g., 'navigate', 'click', 'wait', 'extract')"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )


class LoginConfig(BaseModel):
    """Configuration for login handling."""

    url: str = Field(..., description="Login page URL")
    username_field: str = Field(..., description="CSS selector for username input")
    password_field: str = Field(..., description="CSS selector for password input")
    submit_button: str = Field(..., description="CSS selector for submit button")
    success_indicator: Optional[str] = Field(
        None, description="CSS selector indicating successful login"
    )


class ScraperConfig(BaseModel):
    """Main configuration for a scraper."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="Name of the scraper")
    base_url: str = Field(..., description="Base URL for the scraper")
    selectors: List[SelectorConfig] = Field(
        default_factory=list, description="List of selectors for data extraction"
    )
    workflows: List[WorkflowStep] = Field(
        default_factory=list, description="List of workflow steps"
    )
    login: Optional[LoginConfig] = Field(
        None, description="Login configuration if required"
    )
    timeout: int = Field(30, description="Default timeout in seconds")
    retries: int = Field(3, description="Number of retries on failure")
    anti_detection: Optional[AntiDetectionConfig] = Field(
        None, description="Anti-detection configuration"
    )
