import os
import sys

import pytest
from pydantic import ValidationError

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.scrapers.models.config import LoginConfig, ScraperConfig, SelectorConfig, WorkflowStep


class TestSelectorConfig:
    """Test cases for SelectorConfig model."""

    def test_init_minimal(self):
        """Test SelectorConfig initialization with minimal required fields."""
        config = SelectorConfig(name="test_selector", selector=".test-class")

        assert config.name == "test_selector"
        assert config.selector == ".test-class"
        assert config.attribute is None
        assert config.multiple is False

    def test_init_full(self):
        """Test SelectorConfig initialization with all fields."""
        config = SelectorConfig(
            name="price_selector", selector=".price", attribute="text", multiple=True
        )

        assert config.name == "price_selector"
        assert config.selector == ".price"
        assert config.attribute == "text"
        assert config.multiple is True

    def test_init_with_attribute(self):
        """Test SelectorConfig with attribute field."""
        config = SelectorConfig(
            name="image_selector", selector="img.product-image", attribute="src"
        )

        assert config.name == "image_selector"
        assert config.selector == "img.product-image"
        assert config.attribute == "src"
        assert config.multiple is False

    def test_equality(self):
        """Test SelectorConfig equality."""
        config1 = SelectorConfig(name="test", selector=".test", attribute="text", multiple=False)
        config2 = SelectorConfig(name="test", selector=".test", attribute="text", multiple=False)
        config3 = SelectorConfig(
            name="different", selector=".test", attribute="text", multiple=False
        )

        assert config1 == config2
        assert config1 != config3

    def test_to_dict(self):
        """Test converting SelectorConfig to dictionary."""
        config = SelectorConfig(
            name="test_selector", selector=".test", attribute="href", multiple=True
        )

        data = config.model_dump()

        expected = {
            "name": "test_selector",
            "selector": ".test",
            "attribute": "href",
            "multiple": True,
        }
        assert data == expected

    def test_from_dict(self):
        """Test creating SelectorConfig from dictionary."""
        data = {"name": "test_selector", "selector": ".test", "attribute": "href", "multiple": True}

        config = SelectorConfig(**data)

        assert config.name == "test_selector"
        assert config.selector == ".test"
        assert config.attribute == "href"
        assert config.multiple is True


class TestWorkflowStep:
    """Test cases for WorkflowStep model."""

    def test_init_minimal(self):
        """Test WorkflowStep initialization with minimal required fields."""
        step = WorkflowStep(action="navigate")

        assert step.action == "navigate"
        assert step.params == {}

    def test_init_with_params(self):
        """Test WorkflowStep initialization with parameters."""
        wait_after = 2
        params = {"url": "https://example.com", "wait_after": wait_after}
        step = WorkflowStep(action="navigate", params=params)

        assert step.action == "navigate"
        assert step.params == params

    def test_init_different_actions(self):
        """Test WorkflowStep with different action types."""
        actions = ["navigate", "click", "wait", "extract", "input_text"]

        for action in actions:
            step = WorkflowStep(action=action)
            assert step.action == action
            assert step.params == {}

    def test_equality(self):
        """Test WorkflowStep equality."""
        step1 = WorkflowStep(action="navigate", params={"url": "https://test.com"})
        step2 = WorkflowStep(action="navigate", params={"url": "https://test.com"})
        step3 = WorkflowStep(action="click", params={"url": "https://test.com"})

        assert step1 == step2
        assert step1 != step3

    def test_to_dict(self):
        """Test converting WorkflowStep to dictionary."""
        step = WorkflowStep(
            action="extract", params={"fields": ["name", "price"], "multiple": True}
        )

        data = step.model_dump()

        expected = {"action": "extract", "params": {"fields": ["name", "price"], "multiple": True}}
        assert data == expected

    def test_from_dict(self):
        """Test creating WorkflowStep from dictionary."""
        wait_after = 1
        data = {"action": "click", "params": {"selector": ".button", "wait_after": wait_after}}

        step = WorkflowStep(**data)

        assert step.action == "click"
        assert step.params == {"selector": ".button", "wait_after": wait_after}


class TestLoginConfig:
    """Test cases for LoginConfig model."""

    def test_init_minimal_required(self):
        """Test LoginConfig initialization with required fields."""
        config = LoginConfig(
            url="https://example.com/login",
            username_field="#username",
            password_field="#password",
            submit_button="#submit",
        )

        assert config.url == "https://example.com/login"
        assert config.username_field == "#username"
        assert config.password_field == "#password"
        assert config.submit_button == "#submit"
        assert config.success_indicator is None

    def test_init_with_success_indicator(self):
        """Test LoginConfig with success indicator."""
        config = LoginConfig(
            url="https://example.com/login",
            username_field="#username",
            password_field="#password",
            submit_button="#submit",
            success_indicator=".dashboard",
        )

        assert config.url == "https://example.com/login"
        assert config.success_indicator == ".dashboard"

    def test_equality(self):
        """Test LoginConfig equality."""
        config1 = LoginConfig(
            url="https://test.com/login",
            username_field="#user",
            password_field="#pass",
            submit_button="#submit",
            success_indicator=".success",
        )
        config2 = LoginConfig(
            url="https://test.com/login",
            username_field="#user",
            password_field="#pass",
            submit_button="#submit",
            success_indicator=".success",
        )
        config3 = LoginConfig(
            url="https://different.com/login",
            username_field="#user",
            password_field="#pass",
            submit_button="#submit",
        )

        assert config1 == config2
        assert config1 != config3

    def test_to_dict(self):
        """Test converting LoginConfig to dictionary."""
        config = LoginConfig(
            url="https://example.com/login",
            username_field="#username",
            password_field="#password",
            submit_button="#submit",
            success_indicator=".welcome",
        )

        data = config.model_dump()

        expected = {
            "url": "https://example.com/login",
            "username_field": "#username",
            "password_field": "#password",
            "submit_button": "#submit",
            "success_indicator": ".welcome",
            "failure_indicators": None,
        }
        assert data == expected

    def test_from_dict(self):
        """Test creating LoginConfig from dictionary."""
        data = {
            "url": "https://example.com/login",
            "username_field": "#username",
            "password_field": "#password",
            "submit_button": "#submit",
            "success_indicator": ".dashboard",
        }

        config = LoginConfig(**data)

        assert config.url == "https://example.com/login"
        assert config.username_field == "#username"
        assert config.success_indicator == ".dashboard"


class TestScraperConfig:
    """Test cases for ScraperConfig model."""

    def test_init_minimal(self):
        """Test ScraperConfig initialization with minimal required fields."""
        default_timeout = 30
        default_retries = 3
        config = ScraperConfig(name="Test Scraper", base_url="https://example.com")

        assert config.name == "Test Scraper"
        assert config.base_url == "https://example.com"
        assert config.timeout == default_timeout
        assert config.retries == default_retries
        assert config.selectors == []
        assert config.workflows == []
        assert config.login is None
        assert config.anti_detection is None
        assert config.test_skus is None

    def test_init_full(self):
        """Test ScraperConfig initialization with all fields."""
        num_selectors = 2
        num_workflows = 2
        timeout = 60
        retries = 5
        selectors = [
            SelectorConfig(name="title", selector=".title"),
            SelectorConfig(name="price", selector=".price", attribute="text"),
        ]
        workflows = [
            WorkflowStep(action="navigate", params={"url": "https://example.com"}),
            WorkflowStep(action="extract", params={"fields": ["title", "price"]}),
        ]
        login = LoginConfig(
            url="https://example.com/login",
            username_field="#user",
            password_field="#pass",
            submit_button="#submit",
        )
        test_skus = ["SKU001", "SKU002"]

        config = ScraperConfig(
            name="Full Test Scraper",
            base_url="https://example.com",
            timeout=timeout,
            retries=retries,
            selectors=selectors,
            workflows=workflows,
            login=login,
            anti_detection=None,
            test_skus=test_skus,
        )

        assert config.name == "Full Test Scraper"
        assert config.timeout == timeout
        assert config.retries == retries
        assert len(config.selectors) == num_selectors
        assert len(config.workflows) == num_workflows
        assert config.login is not None
        assert config.test_skus == test_skus

    def test_init_with_selectors_and_workflows(self):
        """Test ScraperConfig with selectors and workflows."""
        num_selectors = 2
        num_workflows = 3
        wait_timeout = 10
        selectors = [
            SelectorConfig(name="product_name", selector=".product-title", attribute="text"),
            SelectorConfig(
                name="product_price", selector=".price", attribute="text", multiple=False
            ),
        ]
        workflows = [
            WorkflowStep(action="navigate", params={"url": "https://example.com/products"}),
            WorkflowStep(
                action="wait_for", params={"selector": ".products", "timeout": wait_timeout}
            ),
            WorkflowStep(action="extract", params={"fields": ["product_name", "product_price"]}),
        ]

        config = ScraperConfig(
            name="Product Scraper",
            base_url="https://example.com",
            selectors=selectors,
            workflows=workflows,
        )

        assert len(config.selectors) == num_selectors
        assert len(config.workflows) == num_workflows
        assert config.selectors[0].name == "product_name"
        assert config.workflows[0].action == "navigate"

    def test_equality(self):
        """Test ScraperConfig equality."""
        timeout = 45
        retries = 2
        config1 = ScraperConfig(
            name="Test", base_url="https://example.com", timeout=timeout, retries=retries
        )
        config2 = ScraperConfig(
            name="Test", base_url="https://example.com", timeout=timeout, retries=retries
        )
        config3 = ScraperConfig(name="Different", base_url="https://example.com")

        assert config1 == config2
        assert config1 != config3

    def test_to_dict(self):
        """Test converting ScraperConfig to dictionary."""
        timeout = 45
        retries = 2
        num_selectors = 1
        num_workflows = 1
        selectors = [SelectorConfig(name="title", selector=".title")]
        workflows = [WorkflowStep(action="navigate", params={"url": "https://test.com"})]

        config = ScraperConfig(
            name="Test Scraper",
            base_url="https://example.com",
            timeout=timeout,
            retries=retries,
            selectors=selectors,
            workflows=workflows,
            test_skus=["TEST001"],
        )

        data = config.model_dump()

        assert data["name"] == "Test Scraper"
        assert data["base_url"] == "https://example.com"
        assert data["timeout"] == timeout
        assert data["retries"] == retries
        assert len(data["selectors"]) == num_selectors
        assert len(data["workflows"]) == num_workflows
        assert data["test_skus"] == ["TEST001"]

    def test_from_dict(self):
        """Test creating ScraperConfig from dictionary."""
        timeout = 45
        retries = 2
        num_selectors = 1
        num_workflows = 1
        data = {
            "name": "Test Scraper",
            "base_url": "https://example.com",
            "timeout": timeout,
            "retries": retries,
            "selectors": [{"name": "title", "selector": ".title", "attribute": "text"}],
            "workflows": [{"action": "navigate", "params": {"url": "https://example.com"}}],
            "test_skus": ["TEST001", "TEST002"],
        }

        config = ScraperConfig(**data)

        assert config.name == "Test Scraper"
        assert config.timeout == timeout
        assert len(config.selectors) == num_selectors
        assert len(config.workflows) == num_workflows
        assert config.test_skus == ["TEST001", "TEST002"]

    def test_validation_required_fields(self):
        """Test that required fields are validated."""
        # Missing name
        with pytest.raises(ValidationError):
            ScraperConfig(base_url="https://example.com")

        # Missing base_url
        with pytest.raises(ValidationError):
            ScraperConfig(name="Test Scraper")

    def test_validation_field_types(self):
        """Test field type validation."""
        # Invalid timeout type
        with pytest.raises(ValidationError):
            ScraperConfig(name="Test", base_url="https://example.com", timeout="not_a_number")

        # Invalid retries type
        with pytest.raises(ValidationError):
            ScraperConfig(name="Test", base_url="https://example.com", retries="not_a_number")

    def test_selectors_validation(self):
        """Test selectors field validation."""
        num_selectors = 2
        # Valid selectors
        selectors = [
            SelectorConfig(name="valid", selector=".valid"),
            SelectorConfig(name="another", selector="#another", attribute="href"),
        ]

        config = ScraperConfig(name="Test", base_url="https://example.com", selectors=selectors)

        assert len(config.selectors) == num_selectors

    def test_workflows_validation(self):
        """Test workflows field validation."""
        num_workflows = 3
        wait_seconds = 2
        workflows = [
            WorkflowStep(action="navigate", params={"url": "https://test.com"}),
            WorkflowStep(action="wait", params={"seconds": wait_seconds}),
            WorkflowStep(action="extract", params={"fields": ["title"]}),
        ]

        config = ScraperConfig(name="Test", base_url="https://example.com", workflows=workflows)

        assert len(config.workflows) == num_workflows

    def test_login_config_validation(self):
        """Test login configuration validation."""
        login = LoginConfig(
            url="https://example.com/login",
            username_field="#username",
            password_field="#password",
            submit_button="#submit",
        )

        config = ScraperConfig(name="Test", base_url="https://example.com", login=login)

        assert config.login is not None
        assert config.login.url == "https://example.com/login"

    def test_test_skus_validation(self):
        """Test test_skus field validation."""
        test_skus = ["SKU001", "SKU002", "SKU003"]

        config = ScraperConfig(name="Test", base_url="https://example.com", test_skus=test_skus)

        assert config.test_skus == test_skus

    def test_empty_lists_defaults(self):
        """Test that empty lists are handled correctly."""
        config = ScraperConfig(name="Test", base_url="https://example.com")

        assert config.selectors == []
        assert config.workflows == []

    def test_none_values_handled(self):
        """Test that None values are handled correctly."""
        config = ScraperConfig(
            name="Test",
            base_url="https://example.com",
            login=None,
            anti_detection=None,
            test_skus=None,
        )

        assert config.login is None
        assert config.anti_detection is None
        assert config.test_skus is None
