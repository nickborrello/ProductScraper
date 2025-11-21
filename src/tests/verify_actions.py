import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.scrapers.actions.registry import ActionRegistry
from src.scrapers.executor.workflow_executor import WorkflowExecutor
import src.scrapers.actions.handlers  # Register actions

class TestScraperActions(unittest.TestCase):
    def setUp(self):
        self.mock_executor = MagicMock(spec=WorkflowExecutor)
        self.mock_executor.results = {}
        self.mock_executor.browser = MagicMock()
        self.mock_executor.config = MagicMock()

    def test_registry(self):
        """Test that actions are registered."""
        actions = ActionRegistry.get_registered_actions()
        print(f"Registered actions: {list(actions.keys())}")
        self.assertIn("navigate", actions)
        self.assertIn("extract_single", actions)
        self.assertIn("combine_fields", actions)
        self.assertIn("transform_value", actions)

    def test_combine_fields(self):
        """Test combine_fields action."""
        action_cls = ActionRegistry.get_action_class("combine_fields")
        action = action_cls(self.mock_executor)
        
        self.mock_executor.results = {"brand": "Acme", "name": "Widget"}
        params = {
            "target_field": "full_name",
            "format": "{brand} {name}",
            "fields": ["brand", "name"]
        }
        action.execute(params)
        self.assertEqual(self.mock_executor.results["full_name"], "Acme Widget")

    def test_transform_value(self):
        """Test transform_value action."""
        action_cls = ActionRegistry.get_action_class("transform_value")
        action = action_cls(self.mock_executor)
        
        self.mock_executor.results = {"price": "$10.00"}
        params = {
            "field": "price",
            "transformations": [
                {"type": "replace", "pattern": "\\$", "replacement": ""},
                {"type": "strip", "chars": " "}
            ]
        }
        action.execute(params)
        self.assertEqual(self.mock_executor.results["price"], "10.00")

    def test_extract_from_json(self):
        """Test extract_from_json action."""
        action_cls = ActionRegistry.get_action_class("extract_from_json")
        action = action_cls(self.mock_executor)
        
        json_data = '{"product": {"price": 20.5}}'
        self.mock_executor.results = {"json_script": json_data}
        params = {
            "source_field": "json_script",
            "target_field": "price",
            "json_path": "product.price"
        }
        action.execute(params)
        self.assertEqual(self.mock_executor.results["price"], 20.5)

    def test_parse_weight(self):
        """Test parse_weight action."""
        action_cls = ActionRegistry.get_action_class("parse_weight")
        action = action_cls(self.mock_executor)
        
        self.mock_executor.results = {"weight": "16 oz"}
        params = {
            "field": "weight",
            "target_unit": "lb"
        }
        action.execute(params)
        self.assertEqual(self.mock_executor.results["weight"], "1.00 lb")

    def test_verify_value(self):
        """Test verify_value action."""
        action_cls = ActionRegistry.get_action_class("verify_value")
        action = action_cls(self.mock_executor)
        
        self.mock_executor.results = {"sku": "12345"}
        params = {
            "field": "sku",
            "expected": "12345",
            "match_mode": "exact"
        }
        # Should not raise error
        action.execute(params)
        
        params["expected"] = "67890"
        with self.assertRaises(Exception): # Should raise WorkflowExecutionError
            action.execute(params)

if __name__ == "__main__":
    unittest.main()
