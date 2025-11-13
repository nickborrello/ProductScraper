"""Bradley Caldwell Product Scraper Actor"""

from __future__ import annotations

import asyncio
import os
import random
import re
import sys
import time
from typing import Any

from apify import Actor
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


# Bradley Caldwell scraper configuration
HEADLESS = False  # Set to False for debugging and manual inspection
DEBUG_MODE = False  # Set to True to pause for manual inspection during scraping
ENABLE_DEVTOOLS = DEBUG_MODE  # Automatically enable DevTools when in debug mode
DEVTOOLS_PORT = 9222  # Port for Chrome DevTools remote debugging
TEST_SKU = "791611038437"  # Bradley Caldwell SKU that previously had empty brand


def create_driver(proxy_url=None) -> webdriver.Chrome:
    """Create Chrome driver with enhanced anti-detection measures and proxy support."""
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # Dynamic viewport to avoid detection
    width = random.randint(1024, 1920)
    height = random.randint(768, 1080)
    options.add_argument(f"--window-size={width},{height}")

    # Rotate user agents
    try:
        ua = UserAgent()
        user_agent = ua.random
    except:
        # Fallback user agent if fake-useragent fails
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    options.add_argument(f'--user-agent={user_agent}')

    # Enable Chrome DevTools remote debugging if configured
    if ENABLE_DEVTOOLS:
        options.add_argument(f"--remote-debugging-port={DEVTOOLS_PORT}")
        options.add_argument("--remote-debugging-address=0.0.0.0")
        Actor.log.info(f"🔧 DevTools enabled on port {DEVTOOLS_PORT}")

    # Proxy support - use provided proxy or get from proxy manager
    effective_proxy = proxy_url or proxy_manager.get_proxy_url()
    if effective_proxy:
        options.add_argument(f'--proxy-server={effective_proxy}')
        Actor.log.info(f"🌐 Using proxy: {effective_proxy}")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


class RateLimiter:
    """Smart rate limiter with randomized delays."""

    def __init__(self, min_delay=1, max_delay=5):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0

    async def wait(self):
        """Wait for appropriate delay before next request."""
        elapsed = time.time() - self.last_request
        delay = max(self.min_delay, random.uniform(self.min_delay, self.max_delay))
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self.last_request = time.time()


class BrowserSession:
    """Manages browser session with automatic rotation."""

    def __init__(self):
        self.driver = None
        self.created_at = time.time()
        self.request_count = 0

    def get_driver(self):
        """Get current driver, rotating if necessary."""
        if not self.driver or self.should_rotate():
            self.rotate_session()
        return self.driver

    def should_rotate(self):
        """Check if session should be rotated."""
        # Rotate every 10 requests or after 5 minutes
        return (self.request_count >= 10 or
                time.time() - self.created_at > 300)

    def rotate_session(self):
        """Create new browser session."""
        if self.driver:
            monitoring.record_session_rotated()
            self.driver.quit()
        self.driver = create_driver()
        monitoring.record_session_created()
        self.created_at = time.time()
        self.request_count = 0

    def increment_counter(self):
        """Increment request counter."""
        self.request_count += 1

    def cleanup(self):
        """Clean up browser session."""
        if self.driver:
            self.driver.quit()
            self.driver = None


class DataValidator:
    """Validates scraped product data for completeness and quality."""

    @staticmethod
    def validate_sku(sku: str) -> bool:
        """Validate SKU format."""
        if not sku or not isinstance(sku, str):
            return False
        # Amazon ASINs are 10 characters, alphanumeric
        if len(sku) == 10 and sku.isalnum():
            return True
        # Allow other formats but ensure not empty
        return len(sku.strip()) > 0

    @staticmethod
    def validate_product_data(product: dict[str, Any] | None) -> dict[str, Any]:
        """Validate and clean product data."""
        if not product:
            return {"valid": False, "errors": ["No product data"], "data": None}

        errors = []
        cleaned_data = {}

        # Validate SKU
        if not DataValidator.validate_sku(product.get("SKU", "")):
            errors.append("Invalid or missing SKU")
        else:
            cleaned_data["SKU"] = product["SKU"].strip()

        # Validate Name
        name = product.get("Name", "").strip()
        if not name or name == "N/A":
            errors.append("Missing product name")
        else:
            cleaned_data["Name"] = name

        # Validate Brand (optional but should be meaningful)
        brand = product.get("Brand", "").strip()
        if brand and brand not in ["Unknown", "N/A"]:
            cleaned_data["Brand"] = brand
        elif not brand:
            cleaned_data["Brand"] = "Unknown"

        # Validate Images
        images = product.get("Image URLs", [])
        if not isinstance(images, list):
            errors.append("Image URLs should be a list")
        elif len(images) == 0:
            errors.append("No product images found")
        else:
            # Validate image URLs
            valid_images = []
            for img_url in images:
                if isinstance(img_url, str) and img_url.startswith("http") and "bradleycaldwell.com" in img_url:
                    valid_images.append(img_url)
            if len(valid_images) == 0:
                errors.append("No valid Bradley Caldwell image URLs found")
            else:
                cleaned_data["Image URLs"] = valid_images[:5]  # Limit to 5 images

        # Validate Weight
        weight = product.get("Weight", "").strip()
        if not weight or weight == "N/A":
            errors.append("Missing product weight")
        else:
            # Validate weight format (should be numeric)
            try:
                float(weight)
                cleaned_data["Weight"] = weight
            except ValueError:
                errors.append(f"Invalid weight format: {weight}")

        # Check data completeness score
        total_fields = 4  # SKU, Name, Brand, Images, Weight
        completed_fields = len(cleaned_data)
        completeness_score = completed_fields / total_fields

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "data": cleaned_data if cleaned_data else None,
            "completeness_score": completeness_score,
            "quality_score": DataValidator._calculate_quality_score(cleaned_data)
        }

    @staticmethod
    def _calculate_quality_score(data: dict[str, Any]) -> float:
        """Calculate data quality score (0.0 to 1.0)."""
        if not data:
            return 0.0

        score = 0.0
        max_score = 0.0

        # SKU quality (required)
        if "SKU" in data:
            score += 1.0
        max_score += 1.0

        # Name quality (required, bonus for length)
        if "Name" in data:
            name = data["Name"]
            score += min(1.0, len(name) / 50)  # Bonus for descriptive names
        max_score += 1.0

        # Brand quality (optional)
        if "Brand" in data and data["Brand"] not in ["Unknown", "N/A"]:
            score += 1.0
        max_score += 0.5  # Optional field, lower weight

        # Images quality (required, bonus for multiple images)
        if "Image URLs" in data:
            images = data["Image URLs"]
            score += min(1.0, len(images) / 3)  # Bonus for multiple images
        max_score += 1.0

        # Weight quality (required)
        if "Weight" in data:
            score += 1.0
        max_score += 1.0

        return score / max_score if max_score > 0 else 0.0


class CircuitBreaker:
    """Circuit breaker pattern for handling persistent failures."""

    def __init__(self, failure_threshold=5, recovery_timeout=300, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                Actor.log.info("🔄 Circuit breaker: Attempting reset (HALF_OPEN)")
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self):
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful operation."""
        if self.state == "HALF_OPEN":
            self._reset()
            Actor.log.info("✅ Circuit breaker: Reset successful (CLOSED)")
        self.failure_count = 0

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            Actor.log.error(f"🚫 Circuit breaker: OPEN after {self.failure_count} failures")

    def _reset(self):
        """Reset circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class Monitoring:
    """Comprehensive monitoring and observability for the scraper."""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "blocked_requests": 0,
            "circuit_breaker_trips": 0,
            "response_times": [],
            "error_counts": {},
            "validation_stats": {
                "total_validations": 0,
                "passed_validations": 0,
                "failed_validations": 0,
                "quality_scores": []
            },
            "session_stats": {
                "sessions_created": 0,
                "sessions_rotated": 0,
                "avg_session_lifetime": 0
            },
            "rate_limiting_stats": {
                "delays_applied": 0,
                "avg_delay": 0,
                "total_delay_time": 0
            }
        }
        self.current_session_start = time.time()

    def record_request_start(self, sku: str):
        """Record the start of a scraping request."""
        self.metrics["total_requests"] += 1
        Actor.log.info(f"📊 Request {self.metrics['total_requests']}: Started scraping SKU {sku}")

    def record_request_success(self, sku: str, response_time: float, data_quality: float = 0.0):
        """Record a successful request."""
        self.metrics["successful_requests"] += 1
        self.metrics["response_times"].append(response_time)
        if data_quality > 0:
            self.metrics["validation_stats"]["quality_scores"].append(data_quality)

        Actor.log.info(".2f"
                      ".2f")

    def record_request_failure(self, sku: str, error_type: str, response_time: float = 0):
        """Record a failed request."""
        self.metrics["failed_requests"] += 1
        self.metrics["error_counts"][error_type] = self.metrics["error_counts"].get(error_type, 0) + 1
        if response_time > 0:
            self.metrics["response_times"].append(response_time)

        Actor.log.warning(f"❌ Request failed: SKU {sku} - {error_type}")

    def record_blocking_detected(self, sku: str):
        """Record when blocking is detected."""
        self.metrics["blocked_requests"] += 1
        Actor.log.warning(f"🚫 Blocking detected: SKU {sku}")

    def record_circuit_breaker_trip(self):
        """Record when circuit breaker trips."""
        self.metrics["circuit_breaker_trips"] += 1
        Actor.log.error(f"🔄 Circuit breaker tripped (trip #{self.metrics['circuit_breaker_trips']})")

    def record_validation_result(self, passed: bool, quality_score: float = 0.0):
        """Record data validation results."""
        self.metrics["validation_stats"]["total_validations"] += 1
        if passed:
            self.metrics["validation_stats"]["passed_validations"] += 1
        else:
            self.metrics["validation_stats"]["failed_validations"] += 1

        if quality_score > 0:
            self.metrics["validation_stats"]["quality_scores"].append(quality_score)

    def record_session_created(self):
        """Record when a new browser session is created."""
        self.metrics["session_stats"]["sessions_created"] += 1
        self.current_session_start = time.time()
        Actor.log.info(f"🌐 Browser session created (total: {self.metrics['session_stats']['sessions_created']})")

    def record_session_rotated(self):
        """Record when a browser session is rotated."""
        self.metrics["session_stats"]["sessions_rotated"] += 1
        session_lifetime = time.time() - self.current_session_start

        # Update average session lifetime
        total_sessions = self.metrics["session_stats"]["sessions_created"]
        current_avg = self.metrics["session_stats"]["avg_session_lifetime"]
        self.metrics["session_stats"]["avg_session_lifetime"] = (
            (current_avg * (total_sessions - 1)) + session_lifetime
        ) / total_sessions

        Actor.log.info(".1f"
                      ".1f")

    def record_rate_limit_delay(self, delay: float):
        """Record rate limiting delays."""
        self.metrics["rate_limiting_stats"]["delays_applied"] += 1
        self.metrics["rate_limiting_stats"]["total_delay_time"] += delay

        # Update average delay
        total_delays = self.metrics["rate_limiting_stats"]["delays_applied"]
        self.metrics["rate_limiting_stats"]["avg_delay"] = (
            self.metrics["rate_limiting_stats"]["total_delay_time"] / total_delays
        )

    def get_summary_report(self) -> dict:
        """Generate a comprehensive summary report."""
        runtime = time.time() - self.start_time

        # Calculate rates
        success_rate = (self.metrics["successful_requests"] / self.metrics["total_requests"]) * 100 if self.metrics["total_requests"] > 0 else 0
        block_rate = (self.metrics["blocked_requests"] / self.metrics["total_requests"]) * 100 if self.metrics["total_requests"] > 0 else 0
        validation_pass_rate = (self.metrics["validation_stats"]["passed_validations"] / self.metrics["validation_stats"]["total_validations"]) * 100 if self.metrics["validation_stats"]["total_validations"] > 0 else 0

        # Calculate averages
        avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        avg_quality_score = sum(self.metrics["validation_stats"]["quality_scores"]) / len(self.metrics["validation_stats"]["quality_scores"]) if self.metrics["validation_stats"]["quality_scores"] else 0

        # Throughput
        throughput = self.metrics["total_requests"] / runtime if runtime > 0 else 0

        return {
            "runtime_seconds": runtime,
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "blocked_requests": self.metrics["blocked_requests"],
            "success_rate_percent": success_rate,
            "block_rate_percent": block_rate,
            "circuit_breaker_trips": self.metrics["circuit_breaker_trips"],
            "average_response_time": avg_response_time,
            "throughput_requests_per_second": throughput,
            "validation_stats": {
                "total_validations": self.metrics["validation_stats"]["total_validations"],
                "passed_validations": self.metrics["validation_stats"]["passed_validations"],
                "failed_validations": self.metrics["validation_stats"]["failed_validations"],
                "pass_rate_percent": validation_pass_rate,
                "average_quality_score": avg_quality_score
            },
            "session_stats": self.metrics["session_stats"],
            "rate_limiting_stats": self.metrics["rate_limiting_stats"],
            "top_errors": sorted(self.metrics["error_counts"].items(), key=lambda x: x[1], reverse=True)[:5]
        }

    def log_final_report(self):
        """Log a comprehensive final report."""
        report = self.get_summary_report()

        Actor.log.info("📊 === SCRAPER FINAL REPORT ===")
        Actor.log.info(f"⏱️ Runtime: {report['runtime_seconds']:.1f} seconds")
        Actor.log.info(f"📈 Total Requests: {report['total_requests']}")
        Actor.log.info(f"✅ Successful: {report['successful_requests']}")
        Actor.log.info(f"❌ Failed: {report['failed_requests']}")
        Actor.log.info(f"🚫 Blocked: {report['blocked_requests']}")
        Actor.log.info(f"📊 Success Rate: {report['success_rate_percent']:.1f}%")
        Actor.log.info(f"🚫 Block Rate: {report['block_rate_percent']:.1f}%")
        Actor.log.info(f"� Circuit Breaker Trips: {report['circuit_breaker_trips']}")
        Actor.log.info(f"⏱️ Avg Response Time: {report['average_response_time']:.2f}s")
        Actor.log.info(f"⚡ Throughput: {report['throughput_requests_per_second']:.2f} req/s")
        # Validation stats
        vstats = report["validation_stats"]
        Actor.log.info("🔍 Data Validation Summary:")
        Actor.log.info(f"  - Total Validations: {vstats['total_validations']}")
        Actor.log.info(f"  - Passed: {vstats['passed_validations']} ({vstats['pass_rate_percent']:.1f}%)")
        Actor.log.info(f"  - Average Quality Score: {vstats['average_quality_score']:.2f}")
        # Session stats
        sstats = report["session_stats"]
        Actor.log.info("🌐 Session Management:")
        Actor.log.info(f"  - Sessions Created: {sstats['sessions_created']}")
        Actor.log.info(f"  - Sessions Rotated: {sstats['sessions_rotated']}")
        Actor.log.info(f"  - Avg Session Lifetime: {sstats['avg_session_lifetime']:.1f}s")
        # Rate limiting stats
        rstats = report["rate_limiting_stats"]
        Actor.log.info("⏱️ Rate Limiting:")
        Actor.log.info(f"  - Delays Applied: {rstats['delays_applied']}")
        Actor.log.info(f"  - Average Delay: {rstats['avg_delay']:.2f}s")

        # CAPTCHA stats
        cstats = captcha_detector.get_captcha_stats()
        Actor.log.info("🚨 CAPTCHA Statistics:")
        Actor.log.info(f"  - Total CAPTCHA Events: {cstats['total_captcha_events']}")
        Actor.log.info(f"  - Manual Interventions Required: {cstats['manual_interventions_required']}")
        Actor.log.info(f"  - CAPTCHA Success Rate: {cstats['captcha_success_rate']:.2f}")

        if cstats["recent_events"]:
            Actor.log.info("  - Recent CAPTCHA Events:")
            for event in cstats["recent_events"][-3:]:  # Show last 3
                Actor.log.info(f"    • {event['type']} at {time.strftime('%H:%M:%S', time.localtime(event['timestamp']))}")

        Actor.log.info("📊 === END REPORT ===")


# Global monitoring instance
monitoring = Monitoring()


class ProxyManager:
    """Manages proxy rotation for anti-blocking."""

    def __init__(self):
        self.current_proxy = None
        self.proxy_list = []
        self.proxy_index = 0
        self.failures = {}
        self.last_rotation = 0
        self.rotation_interval = 30  # Rotate proxy every 30 seconds

    def initialize_apify_proxy(self):
        """Initialize Apify proxy configuration."""
        try:
            # Check if running on Apify platform
            apify_proxy_url = os.getenv('APIFY_PROXY_URL')
            if apify_proxy_url:
                Actor.log.info("🌐 Using Apify proxy infrastructure")
                # Apify provides proxy URL that handles rotation automatically
                self.current_proxy = apify_proxy_url
                return True
            else:
                Actor.log.info("🌐 No Apify proxy detected, using direct connection")
                return False
        except Exception as e:
            Actor.log.warning(f"⚠️ Failed to initialize Apify proxy: {e}")
            return False

    def get_proxy_url(self) -> str | None:
        """Get current proxy URL, rotating if necessary."""
        # Check if we should rotate based on time
        if time.time() - self.last_rotation > self.rotation_interval:
            self.rotate_proxy()

        return self.current_proxy

    def rotate_proxy(self):
        """Rotate to next proxy in list or request new one."""
        self.last_rotation = time.time()

        # If using Apify proxy, it handles rotation automatically
        if os.getenv('APIFY_PROXY_URL'):
            Actor.log.info("🔄 Apify proxy rotation handled automatically")
            return

        # For local testing or custom proxy lists
        if self.proxy_list:
            self.proxy_index = (self.proxy_index + 1) % len(self.proxy_list)
            self.current_proxy = self.proxy_list[self.proxy_index]
            Actor.log.info(f"🔄 Rotated to proxy: {self.current_proxy}")
        else:
            Actor.log.info("🔄 No proxy list available, using direct connection")

    def mark_proxy_failure(self, proxy_url: str):
        """Mark a proxy as failed."""
        if proxy_url:
            self.failures[proxy_url] = self.failures.get(proxy_url, 0) + 1
            Actor.log.warning(f"❌ Proxy failure recorded: {proxy_url} (failures: {self.failures[proxy_url]})")

            # If proxy has too many failures, rotate immediately
            if self.failures[proxy_url] >= 3:
                Actor.log.error(f"🚫 Proxy {proxy_url} has {self.failures[proxy_url]} failures, rotating...")
                self.rotate_proxy()

    def add_custom_proxy(self, proxy_url: str):
        """Add a custom proxy to the rotation list."""
        if proxy_url not in self.proxy_list:
            self.proxy_list.append(proxy_url)
            Actor.log.info(f"➕ Added custom proxy: {proxy_url}")

    def get_proxy_stats(self) -> dict:
        """Get proxy usage statistics."""
        return {
            "current_proxy": self.current_proxy,
            "total_proxies": len(self.proxy_list),
            "proxy_failures": self.failures.copy(),
            "last_rotation": self.last_rotation,
            "using_apify_proxy": bool(os.getenv('APIFY_PROXY_URL'))
        }


# Global proxy manager instance
proxy_manager = ProxyManager()


class CaptchaDetector:
    """Advanced CAPTCHA detection and handling for Bradley Caldwell."""

    def __init__(self):
        self.captcha_patterns = {
            # Bradley Caldwell CAPTCHA indicators
            "bradley_captcha": [
                "enter the characters you see",
                "type the characters",
                "prove you are human",
                "sorry, we just need to make sure you're not a robot"
            ],
            # Common CAPTCHA element selectors
            "captcha_selectors": [
                "#captchacharacters",
                ".a-box-inner img[alt*='CAPTCHA']",
                "input[name='field-keywords'][placeholder*='Enter the characters']",
                ".captcha-image",
                "#cvf-page-content",
                ".cvf-widget-form"
            ],
            # Blocking indicators
            "blocking_indicators": [
                "to discuss automated access to bradleycaldwell",
                "your account has been temporarily restricted",
                "we need to verify that you're not a robot",
                "please solve this puzzle"
            ]
        }
        self.captcha_events = []
        self.manual_intervention_required = False

    def detect_captcha(self, driver: webdriver.Chrome) -> dict:
        """Detect various types of CAPTCHAs and blocking on the page."""
        try:
            page_text = driver.page_source.lower()
            current_url = driver.current_url.lower()

            # Check for Bradley Caldwell CAPTCHA patterns
            for pattern in self.captcha_patterns["bradley_captcha"]:
                if pattern in page_text:
                    return {
                        "detected": True,
                        "type": "bradley_captcha",
                        "pattern": pattern,
                        "confidence": 0.9,
                        "action_required": "solve_text_captcha"
                    }

            # Check for CAPTCHA form elements
            for selector in self.captcha_patterns["captcha_selectors"]:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return {
                            "detected": True,
                            "type": "bradley_form_captcha",
                            "selector": selector,
                            "confidence": 0.95,
                            "action_required": "solve_form_captcha"
                        }
                except:
                    continue

            # Check for blocking indicators
            for indicator in self.captcha_patterns["blocking_indicators"]:
                if indicator in page_text:
                    return {
                        "detected": True,
                        "type": "blocking_page",
                        "indicator": indicator,
                        "confidence": 0.85,
                        "action_required": "manual_intervention"
                    }

            # Check URL patterns that indicate blocking
            blocking_urls = ["captcha", "verify", "challenge", "blocked"]
            for url_pattern in blocking_urls:
                if url_pattern in current_url:
                    return {
                        "detected": True,
                        "type": "blocking_url",
                        "url_pattern": url_pattern,
                        "confidence": 0.8,
                        "action_required": "url_based_blocking"
                    }

            return {"detected": False, "type": None, "confidence": 0.0}

        except Exception as e:
            Actor.log.warning(f"⚠️ CAPTCHA detection error: {e}")
            return {"detected": False, "type": "detection_error", "error": str(e), "confidence": 0.0}

    def solve_text_captcha(self, driver: webdriver.Chrome) -> bool:
        """Attempt to solve text-based CAPTCHAs automatically."""
        try:
            # Look for CAPTCHA input field
            captcha_input = None
            try:
                captcha_input = driver.find_element(By.ID, "captchacharacters")
            except:
                try:
                    captcha_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='characters']")
                except:
                    Actor.log.warning("❌ Could not find CAPTCHA input field")
                    return False

            # For now, we can't automatically solve visual CAPTCHAs
            # This would require OCR or a CAPTCHA solving service
            Actor.log.info("🤖 CAPTCHA detected - manual intervention required")
            self.manual_intervention_required = True

            # Record CAPTCHA event
            self.captcha_events.append({
                "timestamp": time.time(),
                "type": "text_captcha",
                "status": "manual_intervention_required",
                "url": driver.current_url
            })

            return False  # Require manual intervention

        except Exception as e:
            Actor.log.error(f"💥 Error attempting to solve CAPTCHA: {e}")
            return False

    def solve_form_captcha(self, driver: webdriver.Chrome) -> bool:
        """Handle form-based CAPTCHAs."""
        try:
            # Check if it's a simple form that might be solvable
            Actor.log.info("📝 Form-based CAPTCHA detected")

            # For Amazon's advanced CAPTCHAs, manual intervention is usually required
            self.manual_intervention_required = True

            self.captcha_events.append({
                "timestamp": time.time(),
                "type": "form_captcha",
                "status": "manual_intervention_required",
                "url": driver.current_url
            })

            return False

        except Exception as e:
            Actor.log.error(f"💥 Error handling form CAPTCHA: {e}")
            return False

    def handle_blocking_page(self, driver: webdriver.Chrome) -> bool:
        """Handle blocking pages that require manual intervention."""
        try:
            Actor.log.warning("🚫 Blocking page detected - manual intervention required")

            self.manual_intervention_required = True

            self.captcha_events.append({
                "timestamp": time.time(),
                "type": "blocking_page",
                "status": "manual_intervention_required",
                "url": driver.current_url
            })

            return False

        except Exception as e:
            Actor.log.error(f"💥 Error handling blocking page: {e}")
            return False

    def wait_for_manual_intervention(self, driver: webdriver.Chrome, timeout: int = 300) -> bool:
        """Wait for manual intervention to complete CAPTCHA."""
        try:
            Actor.log.info(f"⏳ Waiting for manual CAPTCHA intervention (timeout: {timeout}s)")

            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if CAPTCHA is still present
                captcha_check = self.detect_captcha(driver)
                if not captcha_check["detected"]:
                    Actor.log.info("✅ CAPTCHA appears to be solved!")
                    self.manual_intervention_required = False
                    return True

                # Brief pause before checking again
                time.sleep(2)

            Actor.log.error(f"⏰ Manual intervention timeout after {timeout} seconds")
            return False

        except Exception as e:
            Actor.log.error(f"💥 Error during manual intervention wait: {e}")
            return False

    def handle_captcha(self, driver: webdriver.Chrome) -> bool:
        """Main CAPTCHA handling method."""
        try:
            detection = self.detect_captcha(driver)

            if not detection["detected"]:
                return True  # No CAPTCHA, continue normally

            Actor.log.warning(f"🚨 CAPTCHA Detected: {detection['type']} (confidence: {detection['confidence']:.2f})")

            # Record CAPTCHA event in monitoring
            monitoring.record_request_failure("captcha_detected", detection["type"])

            # Handle based on CAPTCHA type
            if detection["action_required"] == "solve_text_captcha":
                return self.solve_text_captcha(driver)
            elif detection["action_required"] == "solve_form_captcha":
                return self.solve_form_captcha(driver)
            elif detection["action_required"] == "manual_intervention":
                return self.handle_blocking_page(driver)
            else:
                Actor.log.warning(f"⚠️ Unknown CAPTCHA action required: {detection['action_required']}")
                return False

        except Exception as e:
            Actor.log.error(f"💥 CAPTCHA handling error: {e}")
            return False

    def get_captcha_stats(self) -> dict:
        """Get CAPTCHA event statistics."""
        total_events = len(self.captcha_events)
        manual_interventions = sum(1 for event in self.captcha_events
                                 if event["status"] == "manual_intervention_required")

        return {
            "total_captcha_events": total_events,
            "manual_interventions_required": manual_interventions,
            "captcha_success_rate": 0.0 if total_events == 0 else (total_events - manual_interventions) / total_events,
            "recent_events": self.captcha_events[-5:] if self.captcha_events else []
        }


# Global CAPTCHA detector instance
captcha_detector = CaptchaDetector()


class LargeScaleTester:
    """Large-scale testing and performance benchmarking for the scraper."""

    def __init__(self):
        self.test_results = {
            "total_skus_tested": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "blocked_requests": 0,
            "captcha_events": 0,
            "average_response_time": 0,
            "peak_memory_usage": 0,
            "total_execution_time": 0,
            "throughput_skus_per_minute": 0,
            "error_rate_by_category": {},
            "performance_over_time": [],
            "resource_usage_timeline": []
        }
        self.test_start_time = None
        self.memory_baseline = None

    def start_performance_test(self, sku_list: list[str], batch_size: int = 50) -> dict:
        """Run comprehensive large-scale performance testing."""
        self.test_start_time = time.time()
        self.memory_baseline = self._get_memory_usage()

        Actor.log.info(f"Starting large-scale performance test with {len(sku_list)} SKUs")
        Actor.log.info(f"Batch size: {batch_size}, Memory baseline: {self.memory_baseline:.1f} MB")

        all_results = []
        batches = [sku_list[i:i + batch_size] for i in range(0, len(sku_list), batch_size)]

        for batch_num, batch in enumerate(batches, 1):
            Actor.log.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} SKUs)")

            batch_start_time = time.time()
            batch_results = self._test_batch(batch)
            batch_duration = time.time() - batch_start_time

            all_results.extend(batch_results)

            # Record batch performance
            batch_stats = self._analyze_batch_results(batch_results, batch_duration)
            self._record_batch_performance(batch_num, batch_stats)

            # Memory and resource monitoring
            current_memory = self._get_memory_usage()
            self.test_results["resource_usage_timeline"].append({
                "batch": batch_num,
                "memory_mb": current_memory,
                "duration_seconds": batch_duration,
                "timestamp": time.time()
            })

            Actor.log.info(f"Batch {batch_num} completed: {batch_stats['success_rate']:.1f}% success, "
                          f"{batch_duration:.1f}s, {current_memory:.1f} MB memory")

            # Progressive performance analysis
            if batch_num % 5 == 0:  # Every 5 batches
                self._log_progressive_analysis(batch_num, len(batches))

        # Final analysis
        final_report = self._generate_final_report(all_results)
        self._log_final_performance_report(final_report)

        return final_report

    def _test_batch(self, sku_batch: list[str]) -> list[dict[str, Any] | None]:
        """Test a single batch of SKUs."""
        try:
            return scrape_products(sku_batch)
        except Exception as e:
            Actor.log.error(f"💥 Batch testing error: {e}")
            return [None] * len(sku_batch)

    def _analyze_batch_results(self, results: list[dict[str, Any] | None], duration: float) -> dict:
        """Analyze results from a single batch."""
        successful = sum(1 for r in results if r is not None)
        failed = len(results) - successful

        return {
            "total_skus": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(results)) * 100 if results else 0,
            "duration_seconds": duration,
            "throughput_skus_per_minute": (len(results) / duration) * 60
        }

    def _record_batch_performance(self, batch_num: int, batch_stats: dict):
        """Record performance data for a batch."""
        self.test_results["performance_over_time"].append({
            "batch": batch_num,
            "success_rate": batch_stats["success_rate"],
            "throughput": batch_stats["throughput_skus_per_minute"],
            "duration": batch_stats["duration_seconds"],
            "timestamp": time.time()
        })

    def _log_progressive_analysis(self, current_batch: int, total_batches: int):
        """Log progressive performance analysis."""
        completed_percentage = (current_batch / total_batches) * 100

        # Calculate running averages
        recent_batches = self.test_results["performance_over_time"][-5:]  # Last 5 batches
        if recent_batches:
            avg_success_rate = sum(b["success_rate"] for b in recent_batches) / len(recent_batches)
            avg_throughput = sum(b["throughput"] for b in recent_batches) / len(recent_batches)

            Actor.log.info(f"Progressive Analysis ({completed_percentage:.1f}% complete):")
            Actor.log.info(f"  - Recent Avg Success Rate: {avg_success_rate:.1f}%")
            Actor.log.info(f"  - Recent Avg Throughput: {avg_throughput:.1f} SKUs/min")

            # Performance trend analysis
            if len(recent_batches) >= 3:
                trend = self._calculate_performance_trend(recent_batches)
                if trend["success_trend"] < -5:  # Declining success rate
                    Actor.log.warning(f"WARNING: Success rate declining: {trend['success_trend']:.1f}% trend")
                if trend["throughput_trend"] < -10:  # Declining throughput
                    Actor.log.warning(f"WARNING: Throughput declining: {trend['throughput_trend']:.1f}% trend")

    def _calculate_performance_trend(self, batches: list[dict]) -> dict:
        """Calculate performance trends from recent batches."""
        if len(batches) < 3:
            return {"success_trend": 0, "throughput_trend": 0}

        # Simple linear trend calculation
        success_rates = [b["success_rate"] for b in batches]
        throughputs = [b["throughput"] for b in batches]

        success_trend = (success_rates[-1] - success_rates[0]) / len(success_rates)
        throughput_trend = (throughputs[-1] - throughputs[0]) / len(throughputs)

        return {
            "success_trend": success_trend,
            "throughput_trend": throughput_trend
        }

    def _generate_final_report(self, all_results: list[dict[str, Any] | None]) -> dict:
        """Generate comprehensive final performance report."""
        total_execution_time = time.time() - self.test_start_time
        successful_scrapes = sum(1 for r in all_results if r is not None)
        total_skus = len(all_results)

        # Calculate final metrics
        final_report = {
            "test_summary": {
                "total_skus_tested": total_skus,
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": total_skus - successful_scrapes,
                "overall_success_rate": (successful_scrapes / total_skus) * 100 if total_skus > 0 else 0,
                "total_execution_time_seconds": total_execution_time,
                "average_throughput_skus_per_minute": (total_skus / total_execution_time) * 60 if total_execution_time > 0 else 0
            },
            "performance_analysis": {
                "peak_memory_usage_mb": max(r["memory_mb"] for r in self.test_results["resource_usage_timeline"]) if self.test_results["resource_usage_timeline"] else 0,
                "average_response_time_seconds": sum(p["duration"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"]) if self.test_results["performance_over_time"] else 0,
                "performance_stability": self._calculate_performance_stability(),
                "bottleneck_analysis": self._identify_bottlenecks()
            },
            "scalability_assessment": {
                "recommended_batch_size": self._recommend_batch_size(),
                "estimated_max_capacity": self._estimate_max_capacity(),
                "resource_efficiency_score": self._calculate_resource_efficiency()
            },
            "recommendations": self._generate_recommendations()
        }

        return final_report

    def _calculate_performance_stability(self) -> dict:
        """Calculate performance stability metrics."""
        if not self.test_results["performance_over_time"]:
            return {"stability_score": 0, "variability": 0}

        success_rates = [p["success_rate"] for p in self.test_results["performance_over_time"]]
        throughputs = [p["throughput"] for p in self.test_results["performance_over_time"]]

        success_variability = self._calculate_coefficient_of_variation(success_rates)
        throughput_variability = self._calculate_coefficient_of_variation(throughputs)

        # Stability score (0-100, higher is more stable)
        stability_score = max(0, 100 - (success_variability + throughput_variability) / 2)

        return {
            "stability_score": stability_score,
            "success_rate_variability": success_variability,
            "throughput_variability": throughput_variability
        }

    def _calculate_coefficient_of_variation(self, values: list[float]) -> float:
        """Calculate coefficient of variation (CV) for a list of values."""
        if not values or len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        return (std_dev / mean) * 100  # Percentage

    def _identify_bottlenecks(self) -> dict:
        """Identify performance bottlenecks."""
        bottlenecks = []

        # Memory bottleneck
        peak_memory = max((r["memory_mb"] for r in self.test_results["resource_usage_timeline"]), default=0)
        if peak_memory > 1000:  # Over 1GB
            bottlenecks.append("High memory usage detected")

        # Success rate bottleneck
        avg_success = sum(p["success_rate"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"]) if self.test_results["performance_over_time"] else 0
        if avg_success < 70:
            bottlenecks.append("Low success rate indicates blocking or errors")

        # Throughput bottleneck
        avg_throughput = sum(p["throughput"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"]) if self.test_results["performance_over_time"] else 0
        if avg_throughput < 10:  # Less than 10 SKUs per minute
            bottlenecks.append("Low throughput indicates performance issues")

        return {
            "identified_bottlenecks": bottlenecks,
            "severity": "high" if len(bottlenecks) > 2 else "medium" if len(bottlenecks) > 0 else "low"
        }

    def _recommend_batch_size(self) -> int:
        """Recommend optimal batch size based on testing."""
        if not self.test_results["performance_over_time"]:
            return 50  # Default

        # Analyze throughput vs stability trade-off
        throughputs = [p["throughput"] for p in self.test_results["performance_over_time"]]
        avg_throughput = sum(throughputs) / len(throughputs)

        # Recommend batch size that balances throughput and stability
        if avg_throughput > 20:
            return 100  # Larger batches for high throughput
        elif avg_throughput > 10:
            return 50   # Medium batches
        else:
            return 25   # Smaller batches for stability

    def _estimate_max_capacity(self) -> dict:
        """Estimate maximum sustainable capacity."""
        if not self.test_results["performance_over_time"]:
            return {"estimated_max_skus_per_hour": 0, "confidence": "low"}

        avg_throughput = sum(p["throughput"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"])
        max_throughput = max(p["throughput"] for p in self.test_results["performance_over_time"])

        # Estimate sustainable capacity (80% of peak)
        sustainable_throughput = max_throughput * 0.8

        return {
            "estimated_max_skus_per_hour": sustainable_throughput * 60,
            "peak_throughput_skus_per_minute": max_throughput,
            "sustainable_throughput_skus_per_minute": sustainable_throughput,
            "confidence": "high" if len(self.test_results["performance_over_time"]) > 10 else "medium"
        }

    def _calculate_resource_efficiency(self) -> float:
        """Calculate resource efficiency score (0-100)."""
        if not self.test_results["performance_over_time"] or not self.test_results["resource_usage_timeline"]:
            return 0

        # Efficiency based on throughput per memory usage
        avg_throughput = sum(p["throughput"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"])
        avg_memory = sum(r["memory_mb"] for r in self.test_results["resource_usage_timeline"]) / len(self.test_results["resource_usage_timeline"])

        # Normalize to 0-100 scale (higher is better efficiency)
        efficiency = min(100, (avg_throughput / max(avg_memory / 100, 1)) * 10)
        return efficiency

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        # Analyze performance metrics
        stability = self._calculate_performance_stability()
        if stability["stability_score"] < 70:
            recommendations.append("Consider implementing more aggressive session rotation to improve stability")

        bottlenecks = self._identify_bottlenecks()
        if bottlenecks["severity"] == "high":
            recommendations.append("Address identified bottlenecks before production deployment")

        # Memory recommendations
        peak_memory = max((r["memory_mb"] for r in self.test_results["resource_usage_timeline"]), default=0)
        if peak_memory > 800:
            recommendations.append("Monitor memory usage in production - consider resource limits")

        # Success rate recommendations
        avg_success = sum(p["success_rate"] for p in self.test_results["performance_over_time"]) / len(self.test_results["performance_over_time"]) if self.test_results["performance_over_time"] else 0
        if avg_success < 80:
            recommendations.append("Low success rate suggests need for better anti-detection measures")

        # Throughput recommendations
        capacity = self._estimate_max_capacity()
        if capacity["estimated_max_skus_per_hour"] < 500:
            recommendations.append("Consider async optimization to improve throughput")

        return recommendations if recommendations else ["Performance looks good for production deployment"]

    def _log_final_performance_report(self, report: dict):
        """Log comprehensive final performance report."""
        Actor.log.info("=== LARGE SCALE PERFORMANCE TEST RESULTS ===")

        # Summary
        summary = report["test_summary"]
        Actor.log.info("Test Summary:")
        Actor.log.info(f"  - Total SKUs Tested: {summary['total_skus_tested']}")
        Actor.log.info(f"  - Successful Scrapes: {summary['successful_scrapes']}")
        Actor.log.info(f"  - Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        Actor.log.info(f"  - Total Execution Time: {summary['total_execution_time_seconds']:.1f} seconds")
        Actor.log.info(f"  - Average Throughput: {summary['average_throughput_skus_per_minute']:.1f} SKUs/min")

        # Performance Analysis
        perf = report["performance_analysis"]
        Actor.log.info("Performance Analysis:")
        Actor.log.info(f"  - Peak Memory Usage: {perf['peak_memory_usage_mb']:.1f} MB")
        Actor.log.info(f"  - Average Response Time: {perf['average_response_time_seconds']:.1f} seconds")
        Actor.log.info(f"  - Performance Stability Score: {perf['performance_stability']['stability_score']:.1f}/100")

        bottlenecks = perf["bottleneck_analysis"]
        if bottlenecks["identified_bottlenecks"]:
            Actor.log.info("  - Identified Bottlenecks:")
            for bottleneck in bottlenecks["identified_bottlenecks"]:
                Actor.log.info(f"    • {bottleneck}")

        # Scalability Assessment
        scale = report["scalability_assessment"]
        Actor.log.info("Scalability Assessment:")
        Actor.log.info(f"  - Recommended Batch Size: {scale['recommended_batch_size']} SKUs")
        Actor.log.info(f"  - Estimated Max Capacity: {scale['estimated_max_capacity']['estimated_max_skus_per_hour']:.0f} SKUs/hour")
        Actor.log.info(f"  - Resource Efficiency Score: {scale['resource_efficiency_score']:.1f}/100")

        # Recommendations
        Actor.log.info("Recommendations:")
        for rec in report["recommendations"]:
            Actor.log.info(f"  - {rec}")

        Actor.log.info("=== END PERFORMANCE TEST RESULTS ===")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB (simplified for cross-platform)."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback if psutil not available
            return 0.0


# Global large scale tester instance
large_scale_tester = LargeScaleTester()


def clean_string(text: str) -> str:
    """Clean and normalize string."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def extract_product_data(driver: webdriver.Chrome, sku: str) -> dict[str, Any] | None:
    """Extract product data from Bradley Caldwell page."""
    product_info = {"SKU": sku}

    try:
        # Extract title
        try:
            name_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name"))
            )
            # Wait a bit for JavaScript to potentially update the content
            WebDriverWait(driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(2)  # Give extra time for dynamic content to load

            product_info['Name'] = clean_string(name_element.text)
        except TimeoutException:
            Actor.log.error(f"Product name element not found within 15s for SKU: {sku}")
            product_info['Name'] = ''  # Return empty instead of trying alternatives

        # Try multiple selectors for brand extraction with shorter timeout
        brand_found = False
        brand_selectors = [
            "//div[@class='product-brand']/a",
            "//div[contains(@class, 'product-brand')]//a",
            "//span[@class='product-brand']",
            "//div[@class='product-brand']",
            "//a[contains(@href, '/brand/')]",
            "//span[contains(@class, 'brand')]",
            "//div[contains(@class, 'brand')]"
        ]

        for selector in brand_selectors:
            try:
                brand_element = WebDriverWait(driver, 3).until(  # Reduced to 3 seconds for optional elements
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                brand_name = clean_string(brand_element.text)
                if brand_name and len(brand_name.strip()) > 0:
                    product_info['Brand'] = brand_name
                    brand_found = True
                    break
            except (TimeoutException, NoSuchElementException):
                continue

        if not brand_found:
            # Try to extract brand from product details table
            try:
                brand_table_element = WebDriverWait(driver, 3).until(  # Reduced timeout
                    EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Brand']]/td[2]"))
                )
                brand_name = clean_string(brand_table_element.text)
                if brand_name and len(brand_name.strip()) > 0:
                    product_info['Brand'] = brand_name
                    brand_found = True
            except (TimeoutException, NoSuchElementException):
                pass

        if not brand_found:
            product_info['Brand'] = ''  # Return empty if not found

        # If brand was found and is in the name, remove it
        if brand_found and product_info['Brand']:
            brand_name = product_info['Brand']
            if brand_name.lower() in product_info['Name'].lower():
                product_info['Name'] = clean_string(product_info['Name'].replace(brand_name, ''))

        # Build complete product name from base name + color/size with shorter timeouts
        # Only add color/size if we have a base name
        if product_info['Name']:
            name_parts = [product_info['Name']]

            try:
                color_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional elements
                    EC.presence_of_element_located((By.XPATH, "//span[@data-bind='text: colorDesc']"))
                )
                color_desc = clean_string(color_element.text)
                if color_desc:
                    name_parts.append(color_desc)
            except (TimeoutException, NoSuchElementException):
                pass

            try:
                size_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional elements
                    EC.presence_of_element_located((By.XPATH, "//span[@data-bind='text: sizeDesc']"))
                )
                size_desc = clean_string(size_element.text)
                if size_desc:
                    name_parts.append(size_desc)
            except (TimeoutException, NoSuchElementException):
                pass

            product_info['Name'] = ' '.join(name_parts)
        # If no base name found, leave it empty (don't include just color/size)

        # Extract weight
        try:
            weight_element = WebDriverWait(driver, 3).until(  # Reduced timeout for optional weight
                EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Weight']]/td[2]"))
            )
            weight_html = weight_element.get_attribute('innerHTML')
            if weight_html:
                match = re.search(r'(\d*\.?\d+)\s*(lbs?|kg|oz)?', weight_html, re.IGNORECASE)
                if match:
                    product_info['Weight'] = f"{match.group(1)} {match.group(2) or ''}".strip()
                else:
                    product_info['Weight'] = ''  # Return empty if not parseable
            else:
                product_info['Weight'] = ''  # Return empty if no HTML content
        except (TimeoutException, NoSuchElementException):
            product_info['Weight'] = ''  # Return empty if not found

        # Extract images from desktop and mobile carousels
        try:
            WebDriverWait(driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(1)

            image_urls = set()

            # Desktop thumbnails
            try:
                desktop_thumbs = WebDriverWait(driver, 3).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-desktop a[href*='/ccstore/v1/images']")
                )
                for el in desktop_thumbs:
                    href = el.get_attribute("href")
                    if href:
                        if href.startswith("/ccstore"):
                            href = "https://www.bradleycaldwell.com" + href
                        image_urls.add(href)
            except (TimeoutException, NoSuchElementException):
                pass

            # Mobile thumbnails
            try:
                mobile_thumbs = WebDriverWait(driver, 3).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-mobile a[href*='/ccstore/v1/images']")
                )
                for el in mobile_thumbs:
                    href = el.get_attribute("href")
                    if href:
                        if href.startswith("/ccstore"):
                            href = "https://www.bradleycaldwell.com" + href
                        image_urls.add(href)
            except (TimeoutException, NoSuchElementException):
                pass

            product_info['Image URLs'] = list(image_urls)

        except Exception as e:
            product_info['Image URLs'] = []
            Actor.log.error(f"Image fetch failed: {e}")

    except Exception as e:
        Actor.log.error(f"Error extracting data for {sku}: {e}")
        return None

    # Check for critical missing data - only discard if no images found
    critical_fields_missing = not product_info.get('Image URLs')

    if critical_fields_missing:
        return None

    return product_info


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((TimeoutException, NoSuchElementException))
)
def scrape_single_product(driver: webdriver.Chrome, sku: str) -> dict[str, Any] | None:
    """Scrape a single Bradley Caldwell product with CAPTCHA handling."""
    try:
        # Search URL for Bradley Caldwell
        search_url = f"https://www.bradleycaldwell.com/searchresults?Ntk=All|product.active%7C&Ntt=*{sku}*&Nty=1&No=0&Nrpp=12&Rdm=323&searchType=simple&type=search"

        driver.get(search_url)

        # Check for CAPTCHA immediately after loading
        if not captcha_detector.handle_captcha(driver):
            Actor.log.error(f"CAPTCHA blocking detected for SKU {sku}")
            return None

        try:
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name")),
                    EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'No products were found.')]"))
                )
            )
        except TimeoutException:
            Actor.log.error(f"Timeout: Product page failed to load within 20s for SKU: {sku}")
            return None

        # DEBUG MODE: Pause for manual inspection
        if DEBUG_MODE:
            Actor.log.info(f"🐛 DEBUG MODE: Product page loaded for SKU {sku}")
            Actor.log.info("Press Enter in the terminal to continue with data extraction...")
            input("🐛 DEBUG MODE: Inspect the product page, then press Enter to continue...")

        # Check if product was not found
        try:
            not_found = driver.find_element(By.XPATH, "//h2[contains(text(), 'No products were found.')]")
            if not_found:
                Actor.log.info(f"Product not found for SKU: {sku}")
                return None
        except NoSuchElementException:
            pass  # Product found, continue

        # Final CAPTCHA check before extraction
        if not captcha_detector.handle_captcha(driver):
            Actor.log.error(f"CAPTCHA blocking detected before extraction for SKU {sku}")
            return None

        return extract_product_data(driver, sku)

    except Exception as e:
        Actor.log.error(f"Error scraping {sku}: {e}")
        return None


async def main() -> None:
    """Main actor function."""
    async with Actor:
        # Initialize proxy manager
        proxy_manager.initialize_apify_proxy()

        # Get input - try multiple methods for local testing
        actor_input = await Actor.get_input() or {}
        Actor.log.info(f"Received input from Actor.get_input(): {actor_input}")
        
        # For local testing, also check environment variables
        if not actor_input.get('skus'):
            import os
            input_json = os.getenv('APIFY_INPUT')
            if input_json:
                import json
                try:
                    actor_input = json.loads(input_json)
                    Actor.log.info(f"Loaded input from APIFY_INPUT env var: {actor_input}")
                except json.JSONDecodeError:
                    Actor.log.warning("Failed to parse APIFY_INPUT as JSON")
        
        skus = actor_input.get('skus', [])
        
        if not skus:
            Actor.log.error("No SKUs provided in input")
            return

        Actor.log.info(f"Starting Bradley Caldwell scraping for {len(skus)} SKUs")

        # Run scraping in thread pool since Selenium is sync
        products = await asyncio.get_event_loop().run_in_executor(None, scrape_products, skus)

        # Push results
        valid_products = [p for p in products if p]
        await Actor.push_data(valid_products)
        
        Actor.log.info(f"Scraped {len(valid_products)} products successfully")


def scrape_products(skus: list[str]) -> list[dict[str, Any] | None]:
    """Scrape multiple products with session management, rate limiting, data validation, circuit breaker, and monitoring."""
    session = BrowserSession()
    rate_limiter = RateLimiter()
    circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)  # 3 failures, 60 second timeout
    products = []
    validation_stats = {"total": 0, "valid": 0, "errors": []}

    try:
        for sku in skus:
            # Record request start
            monitoring.record_request_start(sku)
            request_start_time = time.time()

            driver = session.get_driver()

            # Apply rate limiting and record delay
            delay_start = time.time()
            asyncio.run(rate_limiter.wait())
            delay_duration = time.time() - delay_start
            monitoring.record_rate_limit_delay(delay_duration)

            try:
                # Use circuit breaker for scraping
                product = circuit_breaker.call(scrape_single_product, driver, sku)
                response_time = time.time() - request_start_time

                # Validate scraped data
                validation_result = DataValidator.validate_product_data(product)
                validation_stats["total"] += 1
                monitoring.record_validation_result(validation_result["valid"], validation_result["quality_score"])

                if validation_result["valid"]:
                    validation_stats["valid"] += 1
                    products.append(validation_result["data"])
                    monitoring.record_request_success(sku, response_time, validation_result["quality_score"])
                else:
                    validation_stats["errors"].extend(validation_result["errors"])
                    products.append(None)
                    monitoring.record_request_failure(sku, "validation_failed", response_time)

            except CircuitBreakerOpenException:
                monitoring.record_circuit_breaker_trip()
                monitoring.record_request_failure(sku, "circuit_breaker_open", time.time() - request_start_time)
                products.append(None)
                validation_stats["total"] += 1
                validation_stats["errors"].append("Circuit breaker open")

            except Exception as e:
                error_msg = str(e)
                monitoring.record_request_failure(sku, error_msg, time.time() - request_start_time)
                products.append(None)
                validation_stats["total"] += 1
                validation_stats["errors"].append(f"Unexpected error: {error_msg}")

            # Track session usage
            session.increment_counter()

        # Log validation summary
        success_rate = (validation_stats["valid"] / validation_stats["total"]) * 100 if validation_stats["total"] > 0 else 0
        Actor.log.info(f"📊 Validation Summary: {validation_stats['valid']}/{validation_stats['total']} products valid ({success_rate:.1f}%)")

        if validation_stats["errors"]:
            # Log top 5 most common errors
            error_counts = {}
            for error in validation_stats["errors"]:
                error_counts[error] = error_counts.get(error, 0) + 1

            top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            Actor.log.warning("⚠️ Top validation errors:")
            for error, count in top_errors:
                Actor.log.warning(f"  - {error}: {count} occurrences")

        # Log final monitoring report
        monitoring.log_final_report()

        return products
    finally:
        session.cleanup()


# Local testing function
def main_local():
    """Run locally for testing with improved session management."""
    import json

    # Default test SKUs
    skus = [TEST_SKU]

    # Check command line arguments
    if len(sys.argv) > 1:
        try:
            input_data = json.loads(sys.argv[1])
            skus = input_data.get('skus', skus)

            # Check for large scale testing mode
            if input_data.get('large_scale_test', False):
                return run_large_scale_test(input_data)
        except json.JSONDecodeError:
            print("Invalid JSON input, using default SKUs")

    print(f"Starting local Bradley Caldwell scraping for {len(skus)} SKUs: {skus}")

    products = scrape_products(skus)
    valid_products = [p for p in products if p]

    print(f"Scraped {len(valid_products)} products successfully")
    print("Results:")
    for product in valid_products:
        print(json.dumps(product, indent=2))

    return valid_products


def run_large_scale_test(input_data: dict) -> dict:
    """Run comprehensive large-scale performance testing."""
    import json

    # Get test parameters
    sku_list = input_data.get('skus', [])
    batch_size = input_data.get('batch_size', 50)
    test_name = input_data.get('test_name', 'large_scale_test')

    if not sku_list:
        print("ERROR: No SKUs provided for large scale testing")
        return {"error": "No SKUs provided"}

    print(f"Starting Large Scale Performance Test: {test_name}")
    print(f"Testing {len(sku_list)} SKUs with batch size {batch_size}")

    # Run the performance test
    try:
        test_report = large_scale_tester.start_performance_test(sku_list, batch_size)

        # Save detailed results to file
        results_file = f"large_scale_test_results_{test_name}_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(test_report, f, indent=2)

        print(f"SUCCESS: Large scale test completed successfully!")
        print(f"Detailed results saved to: {results_file}")
        print("\nKey Results:")
        print(f"  - Overall Success Rate: {test_report['test_summary']['overall_success_rate']:.1f}%")
        print(f"  - Average Throughput: {test_report['test_summary']['average_throughput_skus_per_minute']:.1f} SKUs/min")
        print(f"  - Peak Memory Usage: {test_report['performance_analysis']['peak_memory_usage_mb']:.1f} MB")
        print(f"  - Recommended Batch Size: {test_report['scalability_assessment']['recommended_batch_size']}")

        return test_report

    except Exception as e:
        error_msg = f"Large scale test failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"error": error_msg}


if __name__ == "__main__":
    main_local()
