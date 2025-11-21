#!/usr/bin/env python3
"""
Demo script showing how to use the WorkflowExecutor for scraper automation.

This example demonstrates:
- Loading a YAML configuration
- Creating and executing a workflow
- Handling results and errors
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.executor import WorkflowExecutor
from src.scrapers.schemas.scraper_config_schema import validate_config_dict


def demo_workflow_execution():
    """Demonstrate workflow execution with a sample configuration."""

    # Sample configuration as a dictionary (normally loaded from YAML)
    config_dict = {
        "name": "Demo Product Scraper",
        "base_url": "https://httpbin.org",
        "timeout": 10,
        "retries": 2,
        "selectors": [
            {
                "name": "page_title",
                "selector": "h1",
                "attribute": "text",
                "multiple": False
            },
            {
                "name": "json_data",
                "selector": "pre",
                "attribute": "text",
                "multiple": False
            }
        ],
        "workflows": [
            {
                "action": "navigate",
                "params": {
                    "url": "https://httpbin.org/html",
                    "wait_after": 1
                }
            },
            {
                "action": "wait_for",
                "params": {
                    "selector": "h1",
                    "timeout": 5
                }
            },
            {
                "action": "extract",
                "params": {
                    "fields": ["page_title"]
                }
            },
            {
                "action": "navigate",
                "params": {
                    "url": "https://httpbin.org/json",
                    "wait_after": 1
                }
            },
            {
                "action": "extract",
                "params": {
                    "fields": ["json_data"]
                }
            }
        ]
    }

    try:
        # Validate and parse configuration
        print("Loading and validating configuration...")
        config = validate_config_dict(config_dict)
        print(f"Configuration loaded: {config.name}")

        # Create workflow executor
        print("Initializing workflow executor...")
        executor = WorkflowExecutor(config, headless=True)
        print("Workflow executor ready")

        # Execute workflow
        print("Executing workflow...")
        result = executor.execute_workflow()

        # Display results
        print("\nEXECUTION RESULTS:")
        print(f"Status: {'Success' if result['success'] else 'Failed'}")
        print(f"Steps Executed: {result['steps_executed']}")
        print(f"Configuration: {result['config_name']}")

        print("\nEXTRACTED DATA:")
        for key, value in result['results'].items():
            if isinstance(value, str) and len(value) > 100:
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")

        print("\nDemo completed successfully!")
        return True

    except Exception as e:
        print(f"Demo failed: {e}")
        return False


def demo_error_handling():
    """Demonstrate error handling in workflow execution."""

    # Configuration with an invalid action
    config_dict = {
        "name": "Error Demo",
        "base_url": "https://example.com",
        "timeout": 5,
        "selectors": [],
        "workflows": [
            {
                "action": "invalid_action",  # This will cause an error
                "params": {}
            }
        ]
    }

    try:
        config = validate_config_dict(config_dict)
        executor = WorkflowExecutor(config, headless=True)
        executor.execute_workflow()
        print("Expected error but execution succeeded")
        return False
    except Exception as e:
        print(f"Error handling works: {type(e).__name__}: {e}")
        return True


if __name__ == "__main__":
    print("WorkflowExecutor Demo")
    print("=" * 50)

    print("\n1. Basic Workflow Execution Demo:")
    success1 = demo_workflow_execution()

    print("\n2. Error Handling Demo:")
    success2 = demo_error_handling()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("All demos completed successfully!")
    else:
        print("Some demos failed")
        sys.exit(1)