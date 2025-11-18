"""
Failure Scenario Classification System

Provides comprehensive failure detection and classification for web scraping operations.
Classifies exceptions and page content into specific failure types with confidence scores
and recovery strategies.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Enumeration of possible failure types in scraping operations."""

    NO_RESULTS = "no_results"
    LOGIN_FAILED = "login_failed"
    CAPTCHA_DETECTED = "captcha_detected"
    RATE_LIMITED = "rate_limited"
    PAGE_NOT_FOUND = "page_not_found"
    ACCESS_DENIED = "access_denied"
    NETWORK_ERROR = "network_error"
    ELEMENT_MISSING = "element_missing"


@dataclass
class FailureContext:
    """Context information for a detected failure scenario."""

    failure_type: FailureType
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    recovery_strategy: str


class FailureClassifier:
    """
    Classifies failures in web scraping operations based on exceptions and page content.

    Provides detection logic for various failure scenarios including network issues,
    anti-detection measures, and content availability problems.
    """

    def __init__(self):
        """Initialize the failure classifier with default detection patterns."""
        self.failure_patterns = {
            FailureType.NO_RESULTS: {
                "selectors": [
                    "[class*='no-results']",
                    "[id*='no-results']",
                    "[class*='empty']",
                    "[id*='empty']",
                    ".no-products",
                    "#no-products",
                ],
                "text_patterns": [
                    r"no (results?|products?|items?) found",
                    r"your search.*returned no results",
                    r"no matching products",
                    r"empty",
                ],
                "recovery_strategy": "retry_with_different_query",
            },
            FailureType.LOGIN_FAILED: {
                "selectors": [
                    "[class*='login-error']",
                    "[id*='login-error']",
                    "[class*='auth-error']",
                    "[id*='auth-error']",
                    ".login-failed",
                    "#login-failed",
                ],
                "text_patterns": [
                    r"(login|authentication).*(failed|error|invalid)",
                    r"incorrect.*(username|password|credentials)",
                    r"access denied",
                    r"unauthorized",
                ],
                "recovery_strategy": "relogin",
            },
            FailureType.CAPTCHA_DETECTED: {
                "selectors": [
                    "[class*='captcha']",
                    "[id*='captcha']",
                    "[class*='recaptcha']",
                    "[id*='recaptcha']",
                    ".g-recaptcha",
                    "#captcha-container",
                ],
                "text_patterns": [
                    r"captcha",
                    r"verify.*human",
                    r"robot.*verification",
                    r"security.*check",
                ],
                "recovery_strategy": "solve_captcha",
            },
            FailureType.RATE_LIMITED: {
                "selectors": [
                    "[class*='rate-limit']",
                    "[id*='rate-limit']",
                    "[class*='throttle']",
                    "[id*='throttle']",
                ],
                "text_patterns": [
                    r"rate limit",
                    r"too many requests",
                    r"throttl",
                    r"please wait",
                    r"temporary.*block",
                ],
                "recovery_strategy": "wait_and_retry",
            },
            FailureType.PAGE_NOT_FOUND: {
                "selectors": [
                    "[class*='404']",
                    "[id*='404']",
                    "[class*='not-found']",
                    "[id*='not-found']",
                ],
                "text_patterns": [
                    r"404",
                    r"page not found",
                    r"not found",
                    r"doesn't exist",
                ],
                "recovery_strategy": "skip_and_continue",
            },
            FailureType.ACCESS_DENIED: {
                "selectors": [
                    "[class*='access-denied']",
                    "[id*='access-denied']",
                    "[class*='forbidden']",
                    "[id*='forbidden']",
                    "[class*='blocked']",
                    "[id*='blocked']",
                ],
                "text_patterns": [
                    r"access denied",
                    r"forbidden",
                    r"blocked",
                    r"banned",
                    r"403",
                ],
                "recovery_strategy": "rotate_session",
            },
            FailureType.NETWORK_ERROR: {
                "selectors": [],
                "text_patterns": [
                    r"connection.*(failed|error|timeout)",
                    r"network.*error",
                    r"server.*error",
                    r"timeout",
                ],
                "recovery_strategy": "retry",
            },
            FailureType.ELEMENT_MISSING: {
                "selectors": [],
                "text_patterns": [],
                "recovery_strategy": "retry_with_wait",
            },
        }

    def classify_exception(
        self, exception: Exception, context: Dict[str, Any]
    ) -> FailureContext:
        """
        Classify a failure based on an exception.

        Args:
            exception: The exception that occurred
            context: Additional context information

        Returns:
            FailureContext with classification results
        """
        exception_str = str(exception).lower()
        exception_type = type(exception).__name__

        # Check for specific exception types
        if isinstance(exception, TimeoutException):
            return FailureContext(
                failure_type=FailureType.NETWORK_ERROR,
                confidence=0.9,
                details={
                    "exception_type": exception_type,
                    "exception_message": str(exception),
                    "timeout_detected": True,
                },
                recovery_strategy="retry_with_backoff",
            )

        elif isinstance(exception, NoSuchElementException):
            return FailureContext(
                failure_type=FailureType.ELEMENT_MISSING,
                confidence=0.8,
                details={
                    "exception_type": exception_type,
                    "exception_message": str(exception),
                    "element_not_found": True,
                },
                recovery_strategy="retry_with_wait",
            )

        elif isinstance(exception, WebDriverException):
            # Check for network-related WebDriver exceptions
            if any(term in exception_str for term in ["connection", "network", "timeout"]):
                return FailureContext(
                    failure_type=FailureType.NETWORK_ERROR,
                    confidence=0.8,
                    details={
                        "exception_type": exception_type,
                        "exception_message": str(exception),
                        "network_issue": True,
                    },
                    recovery_strategy="retry",
                )

        # Check exception message against patterns
        for failure_type, patterns in self.failure_patterns.items():
            if failure_type in [FailureType.ELEMENT_MISSING, FailureType.NETWORK_ERROR]:
                continue  # Already handled above

            confidence = self._calculate_text_match_confidence(
                exception_str, patterns["text_patterns"]
            )
            if confidence > 0.5:
                return FailureContext(
                    failure_type=failure_type,
                    confidence=confidence,
                    details={
                        "exception_type": exception_type,
                        "exception_message": str(exception),
                        "matched_patterns": patterns["text_patterns"],
                    },
                    recovery_strategy=patterns["recovery_strategy"],
                )

        # Default to network error for unknown exceptions
        return FailureContext(
            failure_type=FailureType.NETWORK_ERROR,
            confidence=0.3,
            details={
                "exception_type": exception_type,
                "exception_message": str(exception),
                "unknown_exception": True,
            },
            recovery_strategy="retry",
        )

    def classify_page_content(
        self, driver, context: Dict[str, Any]
    ) -> FailureContext:
        """
        Classify a failure based on page content analysis.

        Args:
            driver: WebDriver instance for page analysis
            context: Additional context information

        Returns:
            FailureContext with classification results
        """
        try:
            page_text = driver.page_source.lower()
            page_title = driver.title.lower()

            # Check each failure type
            best_match = None
            best_confidence = 0.0
            best_details = {}

            for failure_type, patterns in self.failure_patterns.items():
                confidence = 0.0
                details = {}

                # Check selectors
                selector_confidence = self._check_selectors(driver, patterns["selectors"])
                if selector_confidence > 0:
                    confidence = max(confidence, selector_confidence)
                    details["selector_match"] = True

                # Check text patterns in page content
                text_confidence = self._calculate_text_match_confidence(
                    page_text, patterns["text_patterns"]
                )
                if text_confidence > 0:
                    confidence = max(confidence, text_confidence)
                    details["text_match"] = True

                # Check title patterns
                title_confidence = self._calculate_text_match_confidence(
                    page_title, patterns["text_patterns"]
                )
                if title_confidence > 0:
                    confidence = max(confidence, title_confidence * 0.8)  # Title matches are strong indicators
                    details["title_match"] = True

                # Check for HTTP status if available
                if "status_code" in context:
                    status_confidence = self._check_status_code(
                        context["status_code"], failure_type
                    )
                    if status_confidence > 0:
                        confidence = max(confidence, status_confidence)
                        details["status_code_match"] = context["status_code"]

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = failure_type
                    details.update({
                        "matched_selectors": patterns["selectors"],
                        "matched_patterns": patterns["text_patterns"],
                    })
                    best_details = details

            if best_match and best_confidence > 0.3:
                return FailureContext(
                    failure_type=best_match,
                    confidence=best_confidence,
                    details=best_details,
                    recovery_strategy=self.failure_patterns[best_match]["recovery_strategy"],
                )

            # No clear failure detected
            return FailureContext(
                failure_type=FailureType.NO_RESULTS,  # Default assumption
                confidence=0.1,
                details={"no_failure_detected": True},
                recovery_strategy="continue",
            )

        except Exception as e:
            logger.error(f"Page content classification failed: {e}")
            return FailureContext(
                failure_type=FailureType.NETWORK_ERROR,
                confidence=0.5,
                details={"classification_error": str(e)},
                recovery_strategy="retry",
            )

    def _check_selectors(self, driver, selectors: list) -> float:
        """Check if any of the selectors are present on the page."""
        try:
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return 0.9  # High confidence for selector match
                except:
                    continue
            return 0.0
        except Exception:
            return 0.0

    def _calculate_text_match_confidence(self, text: str, patterns: list) -> float:
        """Calculate confidence score based on text pattern matching."""
        if not patterns:
            return 0.0

        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1

        return min(matches / len(patterns), 1.0) if patterns else 0.0

    def _check_status_code(self, status_code: int, failure_type: FailureType) -> float:
        """Check if status code matches expected failure type."""
        status_mappings = {
            FailureType.PAGE_NOT_FOUND: [404],
            FailureType.ACCESS_DENIED: [403, 401],
            FailureType.RATE_LIMITED: [429],
            FailureType.NETWORK_ERROR: [500, 502, 503, 504],
        }

        if failure_type in status_mappings:
            if status_code in status_mappings[failure_type]:
                return 0.95  # Very high confidence for status code match

        return 0.0