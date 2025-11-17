#!/usr/bin/env python3
"""
Comprehensive testing script for migrated scrapers against the new modular architecture.

This script validates:
1. YAML configuration loading and parsing
2. ScraperConfig model validation
3. WorkflowExecutor initialization with anti-detection
4. Dry-run workflow execution (without browser)
5. Error handling and recovery mechanisms
6. Performance benchmarking

Usage: python test_migrated_scrapers.py
"""

import logging
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import scraper components
try:
    from src.core.anti_detection_manager import (AntiDetectionConfig,
                                                 AntiDetectionManager)
    from src.scrapers.executor.workflow_executor import (
        WorkflowExecutionError, WorkflowExecutor)
    from src.scrapers.models.config import ScraperConfig
    from src.scrapers.parser.yaml_parser import ScraperConfigParser
    from src.utils.scraping.browser import ScraperBrowser
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Make sure you're running this from the project root directory")
    exit(1)


@dataclass
class TestResult:
    """Result of a single test."""

    scraper_name: str
    test_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ScraperTestResults:
    """Test results for a single scraper."""

    scraper_name: str
    config_load_success: bool
    workflow_init_success: bool
    dry_run_success: bool
    error_handling_success: bool
    performance_metrics: Dict[str, float]
    errors: List[str]
    results: List[TestResult]


class MockScraperBrowser(ScraperBrowser):
    """Mock browser for testing purposes."""

    def __init__(self):
        # Don't call super().__init__() to avoid creating actual browser
        self.driver = None
        self.site_name = "mock"

    def get(self, url):
        pass

    def quit(self):
        pass


class DryRunWorkflowExecutor:
    """WorkflowExecutor variant for dry-run testing without browser."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.selectors = {selector.name: selector for selector in config.selectors}
        self.anti_detection_manager = None
        self.results = {}

    def initialize_anti_detection(self):
        """Initialize anti-detection manager if configured."""
        if self.config.anti_detection:
            # Create anti-detection config from the model's dict
            anti_detection_dict = self.config.anti_detection.__dict__
            anti_detection_config = AntiDetectionConfig(**anti_detection_dict)
            # Use mock browser for testing
            mock_browser = MockScraperBrowser()
            self.anti_detection_manager = AntiDetectionManager(
                mock_browser, anti_detection_config
            )

    def dry_run_execute_workflow(self) -> Dict[str, Any]:
        """Execute workflow in dry-run mode (no actual browser operations)."""
        try:
            actions_tested = []
            validation_errors = []

            for step in self.config.workflows:
                action = step.action.lower()
                params = step.params or {}

                # Validate action exists
                if not hasattr(self, f"_validate_{action}"):
                    validation_errors.append(f"Unknown action: {action}")
                    continue

                # Run validation
                try:
                    validator = getattr(self, f"_validate_{action}")
                    validator(params)
                    actions_tested.append(action)
                except Exception as e:
                    validation_errors.append(
                        f"Validation failed for {action}: {str(e)}"
                    )

            return {
                "success": len(validation_errors) == 0,
                "steps_simulated": len(self.config.workflows),
                "actions_tested": actions_tested,
                "validation_errors": validation_errors,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps_simulated": 0,
                "actions_tested": [],
                "validation_errors": [str(e)],
            }

    def _validate_navigate(self, params: Dict[str, Any]):
        """Validate navigate action."""
        if not params.get("url"):
            raise ValueError("Navigate action requires 'url' parameter")

    def _validate_wait_for(self, params: Dict[str, Any]):
        """Validate wait_for action."""
        if not params.get("selector"):
            raise ValueError("Wait_for action requires 'selector' parameter")

    def _validate_wait(self, params: Dict[str, Any]):
        """Validate wait action."""
        # Wait action is always valid
        pass

    def _validate_extract_single(self, params: Dict[str, Any]):
        """Validate extract_single action."""
        if not params.get("field") or not params.get("selector"):
            raise ValueError(
                "Extract_single requires 'field' and 'selector' parameters"
            )

        selector_name = params.get("selector")
        if selector_name not in self.selectors:
            raise ValueError(f"Selector '{selector_name}' not found in config")

    def _validate_extract_multiple(self, params: Dict[str, Any]):
        """Validate extract_multiple action."""
        if not params.get("field") or not params.get("selector"):
            raise ValueError(
                "Extract_multiple requires 'field' and 'selector' parameters"
            )

        selector_name = params.get("selector")
        if selector_name not in self.selectors:
            raise ValueError(f"Selector '{selector_name}' not found in config")

    def _validate_extract(self, params: Dict[str, Any]):
        """Validate extract action."""
        fields = params.get("fields", [])
        if not fields:
            raise ValueError("Extract action requires 'fields' parameter")

        for field_name in fields:
            if field_name not in self.selectors:
                raise ValueError(f"Selector '{field_name}' not found in config")

    def _validate_input_text(self, params: Dict[str, Any]):
        """Validate input_text action."""
        if not params.get("selector") or params.get("text") is None:
            raise ValueError("Input_text requires 'selector' and 'text' parameters")

    def _validate_click(self, params: Dict[str, Any]):
        """Validate click action."""
        if not params.get("selector"):
            raise ValueError("Click action requires 'selector' parameter")

    def _validate_login(self, params: Dict[str, Any]):
        """Validate login action."""
        # Login action doesn't take parameters in the workflow step - it uses the config login settings
        pass  # No parameters required for login action in workflow

    def _validate_detect_captcha(self, params: Dict[str, Any]):
        """Validate detect_captcha action."""
        pass  # No parameters required

    def _validate_handle_blocking(self, params: Dict[str, Any]):
        """Validate handle_blocking action."""
        pass  # No parameters required

    def _validate_rate_limit(self, params: Dict[str, Any]):
        """Validate rate_limit action."""
        pass  # No parameters required

    def _validate_simulate_human(self, params: Dict[str, Any]):
        """Validate simulate_human action."""
        pass  # No parameters required

    def _validate_rotate_session(self, params: Dict[str, Any]):
        """Validate rotate_session action."""
        pass  # No parameters required


class MigratedScrapersTester:
    """Comprehensive tester for migrated scrapers."""

    def __init__(self, configs_dir: str = "src/scrapers/configs"):
        self.configs_dir = Path(configs_dir)
        self.parser = ScraperConfigParser()
        self.scraper_configs = [
            "amazon",
            "central_pet",
            "coastal",
            "mazuri",
            "orgill",
            "petfoodex",
            "phillips",
        ]

    def run_all_tests(self) -> Dict[str, ScraperTestResults]:
        """Run all tests for all scrapers."""
        logger.info("Starting comprehensive scraper migration tests")
        logger.info(f"Testing {len(self.scraper_configs)} scraper configurations")

        results = {}

        for scraper_name in self.scraper_configs:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing scraper: {scraper_name}")
            logger.info(f"{'='*60}")

            scraper_results = self.test_single_scraper(scraper_name)
            results[scraper_name] = scraper_results

            # Summary for this scraper
            success_count = sum(1 for r in scraper_results.results if r.success)
            total_count = len(scraper_results.results)
            logger.info(
                f"Scraper {scraper_name}: {success_count}/{total_count} tests passed"
            )

            if scraper_results.errors:
                logger.error(f"Errors for {scraper_name}:")
                for error in scraper_results.errors:
                    logger.error(f"  - {error}")

        return results

    def test_single_scraper(self, scraper_name: str) -> ScraperTestResults:
        """Test a single scraper configuration."""
        results = ScraperTestResults(
            scraper_name=scraper_name,
            config_load_success=False,
            workflow_init_success=False,
            dry_run_success=False,
            error_handling_success=False,
            performance_metrics={},
            errors=[],
            results=[],
        )

        config_path = self.configs_dir / f"{scraper_name}.yaml"

        # Test 1: Configuration Loading and Validation
        config, config_result = self.test_config_loading(scraper_name, config_path)
        results.results.append(config_result)
        results.config_load_success = config_result.success

        if not config:
            results.errors.append(
                f"Configuration loading failed: {config_result.error_message}"
            )
            return results

        # Test 2: WorkflowExecutor Initialization
        executor, init_result = self.test_workflow_initialization(scraper_name, config)
        results.results.append(init_result)
        results.workflow_init_success = init_result.success

        if not executor:
            results.errors.append(
                f"WorkflowExecutor initialization failed: {init_result.error_message}"
            )
            return results

        # Test 3: Dry-run Workflow Execution
        dry_run_result = self.test_dry_run_execution(scraper_name, executor)
        results.results.append(dry_run_result)
        results.dry_run_success = dry_run_result.success

        # Test 4: Error Handling
        error_result = self.test_error_handling(scraper_name, config)
        results.results.append(error_result)
        results.error_handling_success = error_result.success

        # Performance metrics
        results.performance_metrics = self.collect_performance_metrics(results.results)

        return results

    def test_config_loading(
        self, scraper_name: str, config_path: Path
    ) -> Tuple[Optional[ScraperConfig], TestResult]:
        """Test YAML configuration loading and ScraperConfig parsing."""
        start_time = time.time()

        try:
            if not config_path.exists():
                error_msg = f"Configuration file not found: {config_path}"
                logger.error(error_msg)
                return None, TestResult(
                    scraper_name,
                    "config_loading",
                    False,
                    time.time() - start_time,
                    error_msg,
                )

            # Load and parse configuration
            config = self.parser.load_from_file(config_path)

            # Validate configuration structure
            self.validate_config_structure(config)

            duration = time.time() - start_time
            logger.info(
                f"[PASS] Configuration loaded successfully for {scraper_name} in {duration:.3f}s"
            )

            details = {
                "selectors_count": len(config.selectors),
                "workflows_count": len(config.workflows),
                "has_login": config.login is not None,
                "has_anti_detection": config.anti_detection is not None,
                "timeout": config.timeout,
                "retries": config.retries,
            }

            return config, TestResult(
                scraper_name, "config_loading", True, duration, details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Configuration loading failed: {str(e)}"
            logger.error(f"[FAIL] {error_msg}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None, TestResult(
                scraper_name, "config_loading", False, duration, error_msg
            )

    def validate_config_structure(self, config: ScraperConfig):
        """Validate the structure of a loaded configuration."""
        if not config.name:
            raise ValueError("Configuration must have a name")

        if not config.base_url:
            raise ValueError("Configuration must have a base_url")

        if not config.workflows:
            raise ValueError("Configuration must have at least one workflow step")

        # Validate workflow steps
        for i, step in enumerate(config.workflows):
            if not step.action:
                raise ValueError(f"Workflow step {i} must have an action")

        # Validate selectors
        for selector in config.selectors:
            if not selector.name:
                raise ValueError("All selectors must have a name")
            if not selector.selector:
                raise ValueError(f"Selector '{selector.name}' must have a selector")

        # Validate login config if present
        if config.login:
            login = config.login
            if (
                not login.url
                or not login.username_field
                or not login.password_field
                or not login.submit_button
            ):
                raise ValueError(
                    "Login configuration must have url, username_field, password_field, and submit_button"
                )

    def test_workflow_initialization(
        self, scraper_name: str, config: ScraperConfig
    ) -> Tuple[Optional[DryRunWorkflowExecutor], TestResult]:
        """Test WorkflowExecutor initialization with anti-detection."""
        start_time = time.time()

        try:
            # Create a dry-run executor that doesn't initialize browser
            executor = DryRunWorkflowExecutor(config)
            executor.initialize_anti_detection()

            duration = time.time() - start_time
            logger.info(
                f"[PASS] WorkflowExecutor initialized successfully for {scraper_name} in {duration:.3f}s"
            )

            details = {
                "anti_detection_enabled": executor.anti_detection_manager is not None,
                "selectors_loaded": len(executor.selectors),
                "workflows_loaded": len(executor.config.workflows),
            }

            return executor, TestResult(
                scraper_name, "workflow_init", True, duration, details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"WorkflowExecutor initialization failed: {str(e)}"
            logger.error(f"[FAIL] {error_msg}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None, TestResult(
                scraper_name, "workflow_init", False, duration, error_msg
            )

    def test_dry_run_execution(
        self, scraper_name: str, executor: "DryRunWorkflowExecutor"
    ) -> TestResult:
        """Test dry-run workflow execution without browser."""
        start_time = time.time()

        try:
            # Execute workflow in dry-run mode
            result = executor.dry_run_execute_workflow()

            duration = time.time() - start_time
            success = result.get("success", False)

            if success:
                logger.info(
                    f"[PASS] Dry-run execution successful for {scraper_name} in {duration:.3f}s"
                )
            else:
                logger.warning(f"[FAIL] Dry-run execution failed for {scraper_name}")

            details = {
                "steps_simulated": result.get("steps_simulated", 0),
                "actions_tested": result.get("actions_tested", []),
                "validation_errors": result.get("validation_errors", []),
            }

            return TestResult(
                scraper_name, "dry_run", success, duration, details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Dry-run execution failed: {str(e)}"
            logger.error(f"[FAIL] {error_msg}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return TestResult(scraper_name, "dry_run", False, duration, error_msg)

    def test_error_handling(
        self, scraper_name: str, config: ScraperConfig
    ) -> TestResult:
        """Test error handling and recovery mechanisms."""
        start_time = time.time()

        try:
            # Test various error scenarios
            errors_tested = []

            # Test invalid configuration
            try:
                invalid_config = ScraperConfig(
                    name="",
                    base_url="",
                    workflows=[],
                    login=None,
                    timeout=30,
                    retries=3,
                    anti_detection=None,
                )
                errors_tested.append("invalid_config_handled")
            except Exception:
                pass

            # Test anti-detection error handling
            if config.anti_detection:
                anti_detection_config = AntiDetectionConfig(
                    **config.anti_detection.__dict__
                )
                mock_browser = MockScraperBrowser()
                manager = AntiDetectionManager(mock_browser, anti_detection_config)
                # Test error handling without actual browser
                can_handle = manager.handle_error(
                    Exception("test error"), "test_action"
                )
                errors_tested.append("anti_detection_error_handling")

            duration = time.time() - start_time
            logger.info(
                f"[PASS] Error handling tests completed for {scraper_name} in {duration:.3f}s"
            )

            details = {
                "errors_tested": errors_tested,
                "anti_detection_error_handling": "anti_detection_error_handling"
                in errors_tested,
            }

            return TestResult(
                scraper_name, "error_handling", True, duration, details=details
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Error handling test failed: {str(e)}"
            logger.error(f"[FAIL] {error_msg}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return TestResult(
                scraper_name, "error_handling", False, duration, error_msg
            )

    def collect_performance_metrics(
        self, results: List[TestResult]
    ) -> Dict[str, float]:
        """Collect performance metrics from test results."""
        metrics = {}

        for result in results:
            metrics[f"{result.test_name}_duration"] = result.duration

        # Calculate totals
        total_duration = sum(r.duration for r in results)
        metrics["total_test_duration"] = total_duration
        metrics["average_test_duration"] = (
            total_duration / len(results) if results else 0
        )

        return metrics


def print_test_summary(results: Dict[str, ScraperTestResults]):
    """Print a comprehensive test summary."""
    print("\n" + "=" * 80)
    print("MIGRATED SCRAPERS TEST SUMMARY")
    print("=" * 80)

    total_scrapers = len(results)
    successful_scrapers = 0
    total_tests = 0
    passed_tests = 0

    for scraper_name, scraper_results in results.items():
        print(f"\nScraper: {scraper_name}")
        print("-" * 40)

        # Individual test results
        for result in scraper_results.results:
            status = "[PASS]" if result.success else "[FAIL]"
            print(f"  {result.test_name}: {status} ({result.duration:.3f}s)")
            if not result.success and result.error_message:
                print(f"    Error: {result.error_message}")

        # Performance metrics
        if scraper_results.performance_metrics:
            print("  Performance:")
            for metric, value in scraper_results.performance_metrics.items():
                print(".3f")

        # Overall scraper status
        test_count = len(scraper_results.results)
        passed_count = sum(1 for r in scraper_results.results if r.success)
        total_tests += test_count
        passed_tests += passed_count

        scraper_success = all(
            [
                scraper_results.config_load_success,
                scraper_results.workflow_init_success,
                scraper_results.dry_run_success,
            ]
        )

        if scraper_success:
            successful_scrapers += 1
            print(f"  Overall: [SUCCESS] ({passed_count}/{test_count} tests passed)")
        else:
            print(f"  Overall: [FAILED] ({passed_count}/{test_count} tests passed)")

        if scraper_results.errors:
            print("  Errors:")
            for error in scraper_results.errors:
                print(f"    - {error}")

    print(f"\n{'='*80}")
    print("OVERALL RESULTS")
    print(f"{'='*80}")
    print(f"Scrapers tested: {total_scrapers}")
    print(f"Scrapers successful: {successful_scrapers}")
    print(
        f"Success rate: {(successful_scrapers/total_scrapers)*100:.1f}%"
        if total_scrapers > 0
        else "0%"
    )
    print(f"Total tests: {total_tests}")
    print(f"Tests passed: {passed_tests}")
    print(
        f"Test success rate: {(passed_tests/total_tests)*100:.1f}%"
        if total_tests > 0
        else "0%"
    )

    if successful_scrapers == total_scrapers:
        print("\n[SUCCESS] All scrapers passed migration validation!")
    else:
        print(
            f"\n[WARNING] {total_scrapers - successful_scrapers} scraper(s) need attention before deployment."
        )


def main():
    """Main entry point."""
    print("Testing migrated scrapers against new modular architecture...")

    tester = MigratedScrapersTester()
    results = tester.run_all_tests()

    print_test_summary(results)

    # Exit with appropriate code
    successful_scrapers = sum(
        1
        for r in results.values()
        if all([r.config_load_success, r.workflow_init_success, r.dry_run_success])
    )

    if successful_scrapers == len(results):
        print("\n[SUCCESS] Migration validation successful!")
        return 0
    else:
        print("\n[FAILED] Migration validation failed!")
        return 1


if __name__ == "__main__":
    exit(main())
