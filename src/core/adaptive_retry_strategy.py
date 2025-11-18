"""
Adaptive Retry Strategy for Intelligent Scraping Operations

Provides dynamic retry configuration based on failure history and patterns.
Learns from past failures to optimize scraping efficiency and success rates.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque

from src.core.failure_classifier import FailureType

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Different retry strategies for various failure types."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE_RETRY = "immediate_retry"
    EXTENDED_WAIT = "extended_wait"
    SESSION_ROTATION = "session_rotation"
    CAPTCHA_SOLVE = "captcha_solve"


@dataclass
class FailureRecord:
    """Record of a single failure occurrence."""

    timestamp: float
    failure_type: FailureType
    site_name: str
    action: str
    retry_count: int
    context: Dict[str, Any]
    success_after_retry: bool = False
    final_success: bool = False


@dataclass
class FailurePattern:
    """Aggregated failure pattern for analysis."""

    failure_type: FailureType
    site_name: str
    total_occurrences: int
    recent_occurrences: int  # Last 24 hours
    success_rate: float  # Success rate after retries
    average_retry_count: float
    last_occurrence: float
    peak_failure_hour: Optional[int] = None
    consecutive_failures: int = 0


@dataclass
class AdaptiveRetryConfig:
    """Adaptive retry configuration for a specific failure scenario."""

    max_retries: int
    base_delay: float
    max_delay: float
    backoff_multiplier: float
    strategy: RetryStrategy
    timeout_multiplier: float = 1.0
    session_rotation_threshold: int = 5
    captcha_retry_limit: int = 3


class AdaptiveRetryStrategy:
    """
    Adaptive retry strategy that learns from failure patterns to optimize scraping operations.

    Tracks failure history per site and failure type, analyzes patterns, and generates
    intelligent retry configurations that adapt to site behavior.
    """

    def __init__(self, history_file: Optional[str] = None, max_history_size: int = 10000):
        """
        Initialize the adaptive retry strategy.

        Args:
            history_file: Path to persist failure history across sessions
            max_history_size: Maximum number of failure records to keep in memory
        """
        self.history_file = Path(history_file) if history_file else None
        self.max_history_size = max_history_size

        # In-memory failure history
        self.failure_history: List[FailureRecord] = []
        self.failure_patterns: Dict[Tuple[str, FailureType], FailurePattern] = {}

        # Load persisted history if available
        self._load_history()

        # Default retry configurations for different failure types
        self.default_configs = {
            FailureType.CAPTCHA_DETECTED: AdaptiveRetryConfig(
                max_retries=3,
                base_delay=5.0,
                max_delay=60.0,
                backoff_multiplier=2.0,
                strategy=RetryStrategy.CAPTCHA_SOLVE,
                captcha_retry_limit=3,
            ),
            FailureType.RATE_LIMITED: AdaptiveRetryConfig(
                max_retries=5,
                base_delay=10.0,
                max_delay=300.0,
                backoff_multiplier=2.0,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            ),
            FailureType.LOGIN_FAILED: AdaptiveRetryConfig(
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0,
                backoff_multiplier=1.5,
                strategy=RetryStrategy.EXTENDED_WAIT,
                session_rotation_threshold=2,
            ),
            FailureType.ACCESS_DENIED: AdaptiveRetryConfig(
                max_retries=3,
                base_delay=15.0,
                max_delay=120.0,
                backoff_multiplier=2.0,
                strategy=RetryStrategy.SESSION_ROTATION,
                session_rotation_threshold=1,
            ),
            FailureType.NETWORK_ERROR: AdaptiveRetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                backoff_multiplier=1.5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            ),
            FailureType.ELEMENT_MISSING: AdaptiveRetryConfig(
                max_retries=2,
                base_delay=0.5,
                max_delay=5.0,
                backoff_multiplier=1.2,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                timeout_multiplier=1.5,
            ),
            FailureType.PAGE_NOT_FOUND: AdaptiveRetryConfig(
                max_retries=1,
                base_delay=0.0,
                max_delay=0.0,
                backoff_multiplier=1.0,
                strategy=RetryStrategy.IMMEDIATE_RETRY,
            ),
            FailureType.NO_RESULTS: AdaptiveRetryConfig(
                max_retries=1,
                base_delay=0.0,
                max_delay=0.0,
                backoff_multiplier=1.0,
                strategy=RetryStrategy.IMMEDIATE_RETRY,
            ),
        }

    def record_failure(
        self,
        failure_type: FailureType,
        site_name: str,
        action: str,
        retry_count: int,
        context: Dict[str, Any],
        success_after_retry: bool = False,
        final_success: bool = False,
    ) -> None:
        """
        Record a failure occurrence for learning and analysis.

        Args:
            failure_type: Type of failure that occurred
            site_name: Name of the site where failure occurred
            action: Action that was being performed
            retry_count: Number of retries attempted
            context: Additional context information
            success_after_retry: Whether operation succeeded after retries
            final_success: Whether operation ultimately succeeded
        """
        record = FailureRecord(
            timestamp=time.time(),
            failure_type=failure_type,
            site_name=site_name,
            action=action,
            retry_count=retry_count,
            context=context,
            success_after_retry=success_after_retry,
            final_success=final_success,
        )

        # Add to history
        self.failure_history.append(record)

        # Maintain history size limit
        if len(self.failure_history) > self.max_history_size:
            self.failure_history.pop(0)

        # Update patterns
        self._update_patterns(record)

        # Persist history
        self._save_history()

        logger.debug(
            f"Recorded failure: {failure_type.value} on {site_name} during {action} "
            f"(retry_count: {retry_count}, success: {final_success})"
        )

    def get_adaptive_config(
        self,
        failure_type: FailureType,
        site_name: str,
        current_retry_count: int = 0
    ) -> AdaptiveRetryConfig:
        """
        Generate adaptive retry configuration based on failure history.

        Args:
            failure_type: Type of failure being handled
            site_name: Site where failure occurred
            current_retry_count: Current number of retries attempted

        Returns:
            AdaptiveRetryConfig with optimized retry parameters
        """
        # Start with default configuration
        config = self.default_configs.get(failure_type, self._get_fallback_config())

        # Get failure pattern for this site/failure combination
        pattern_key = (site_name, failure_type)
        pattern = self.failure_patterns.get(pattern_key)

        if pattern:
            # Adapt configuration based on pattern analysis
            config = self._adapt_config_from_pattern(config, pattern, current_retry_count)

        return config

    def analyze_failure_patterns(self, site_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze failure patterns for insights and optimization.

        Args:
            site_name: Optional site name to filter analysis

        Returns:
            Dictionary with pattern analysis results
        """
        patterns_to_analyze = self.failure_patterns

        if site_name:
            patterns_to_analyze = {
                k: v for k, v in self.failure_patterns.items() if k[0] == site_name
            }

        analysis = {
            "total_failures": len(self.failure_history),
            "patterns": {},
            "insights": [],
        }

        for (site, failure_type), pattern in patterns_to_analyze.items():
            pattern_analysis = self._analyze_pattern(pattern)
            analysis["patterns"][f"{site}_{failure_type.value}"] = pattern_analysis

            # Generate insights
            insights = self._generate_insights(pattern, pattern_analysis)
            analysis["insights"].extend(insights)

        return analysis

    def _update_patterns(self, record: FailureRecord) -> None:
        """Update failure patterns based on new failure record."""
        key = (record.site_name, record.failure_type)
        current_time = time.time()

        if key not in self.failure_patterns:
            self.failure_patterns[key] = FailurePattern(
                failure_type=record.failure_type,
                site_name=record.site_name,
                total_occurrences=0,
                recent_occurrences=0,
                success_rate=0.0,
                average_retry_count=0.0,
                last_occurrence=current_time,
            )

        pattern = self.failure_patterns[key]

        # Update counters
        pattern.total_occurrences += 1
        pattern.last_occurrence = current_time

        # Count recent occurrences (last 24 hours)
        recent_threshold = current_time - (24 * 60 * 60)
        pattern.recent_occurrences = sum(
            1 for r in self.failure_history
            if r.site_name == record.site_name
            and r.failure_type == record.failure_type
            and r.timestamp > recent_threshold
        )

        # Update success rate and retry statistics
        successful_retries = [
            r for r in self.failure_history
            if r.site_name == record.site_name
            and r.failure_type == record.failure_type
            and (r.success_after_retry or r.final_success)
        ]

        if pattern.total_occurrences > 0:
            pattern.success_rate = len(successful_retries) / pattern.total_occurrences

        # Update average retry count
        all_retries = [
            r.retry_count for r in self.failure_history
            if r.site_name == record.site_name and r.failure_type == record.failure_type
        ]
        if all_retries:
            pattern.average_retry_count = sum(all_retries) / len(all_retries)

        # Update consecutive failures
        if record.final_success:
            pattern.consecutive_failures = 0
        else:
            pattern.consecutive_failures += 1

        # Analyze peak failure hours
        failure_hours = [
            time.localtime(r.timestamp).tm_hour
            for r in self.failure_history
            if r.site_name == record.site_name and r.failure_type == record.failure_type
        ]
        if failure_hours:
            hour_counts = defaultdict(int)
            for hour in failure_hours:
                hour_counts[hour] += 1
            pattern.peak_failure_hour = max(hour_counts.keys(), key=lambda h: hour_counts[h])

    def _adapt_config_from_pattern(
        self,
        config: AdaptiveRetryConfig,
        pattern: FailurePattern,
        current_retry_count: int
    ) -> AdaptiveRetryConfig:
        """Adapt retry configuration based on failure pattern analysis."""
        adapted_config = AdaptiveRetryConfig(**asdict(config))

        # Increase max retries for frequently failing sites
        if pattern.recent_occurrences > 10:
            adapted_config.max_retries = min(config.max_retries + 2, 10)

        # Adjust delays based on success rate
        if pattern.success_rate < 0.3:  # Low success rate
            adapted_config.base_delay *= 1.5
            adapted_config.max_delay *= 2.0
            adapted_config.backoff_multiplier *= 1.2
        elif pattern.success_rate > 0.8:  # High success rate
            adapted_config.base_delay *= 0.8
            adapted_config.max_delay *= 0.9

        # Increase timeout multiplier for element missing failures
        if pattern.failure_type == FailureType.ELEMENT_MISSING:
            adapted_config.timeout_multiplier = min(
                config.timeout_multiplier + 0.2, 3.0
            )

        # Lower session rotation threshold for access denied failures
        if pattern.failure_type == FailureType.ACCESS_DENIED and pattern.consecutive_failures > 2:
            adapted_config.session_rotation_threshold = max(
                config.session_rotation_threshold - 1, 1
            )

        # Adjust for peak failure hours
        current_hour = time.localtime().tm_hour
        if (pattern.peak_failure_hour is not None and
            abs(current_hour - pattern.peak_failure_hour) <= 2):
            adapted_config.base_delay *= 1.3  # Increase delay during peak hours

        return adapted_config

    def _analyze_pattern(self, pattern: FailurePattern) -> Dict[str, Any]:
        """Analyze a single failure pattern for insights."""
        return {
            "total_occurrences": pattern.total_occurrences,
            "recent_occurrences": pattern.recent_occurrences,
            "success_rate": pattern.success_rate,
            "average_retry_count": pattern.average_retry_count,
            "consecutive_failures": pattern.consecutive_failures,
            "peak_failure_hour": pattern.peak_failure_hour,
            "last_occurrence_hours_ago": (time.time() - pattern.last_occurrence) / 3600,
            "failure_frequency_per_hour": pattern.recent_occurrences / 24,
        }

    def _generate_insights(
        self,
        pattern: FailurePattern,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable insights from pattern analysis."""
        insights = []

        if analysis["failure_frequency_per_hour"] > 1.0:
            insights.append(
                f"High failure frequency for {pattern.failure_type.value} on {pattern.site_name}: "
                f"{analysis['failure_frequency_per_hour']:.1f} failures/hour"
            )

        if analysis["success_rate"] < 0.5:
            insights.append(
                f"Low success rate for {pattern.failure_type.value} on {pattern.site_name}: "
                f"{analysis['success_rate']:.1%}"
            )

        if analysis["consecutive_failures"] > 3:
            insights.append(
                f"Consecutive failures for {pattern.failure_type.value} on {pattern.site_name}: "
                f"{analysis['consecutive_failures']} failures in a row"
            )

        if analysis["average_retry_count"] > 2.0:
            insights.append(
                f"High retry count needed for {pattern.failure_type.value} on {pattern.site_name}: "
                f"{analysis['average_retry_count']:.1f} average retries"
            )

        return insights

    def _get_fallback_config(self) -> AdaptiveRetryConfig:
        """Get fallback retry configuration for unknown failure types."""
        return AdaptiveRetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        )

    def _load_history(self) -> None:
        """Load failure history from persistent storage."""
        if not self.history_file or not self.history_file.exists():
            return

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)

            # Reconstruct failure records
            for record_data in data.get("failure_history", []):
                # Convert string back to enum
                if 'failure_type' in record_data:
                    record_data['failure_type'] = FailureType(record_data['failure_type'])
                record = FailureRecord(**record_data)
                self.failure_history.append(record)
                self._update_patterns(record)

            logger.info(f"Loaded {len(self.failure_history)} failure records from {self.history_file}")

        except Exception as e:
            logger.warning(f"Failed to load failure history: {e}")

    def _save_history(self) -> None:
        """Save failure history to persistent storage."""
        if not self.history_file:
            return

        try:
            # Ensure directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert records to dictionaries with enum handling
            def serialize_record(record):
                data = asdict(record)
                # Convert enum to string
                data['failure_type'] = record.failure_type.value
                return data

            data = {
                "failure_history": [serialize_record(record) for record in self.failure_history[-1000:]],  # Keep last 1000
                "timestamp": time.time(),
            }

            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save failure history: {e}")

    def calculate_delay(
        self,
        config: AdaptiveRetryConfig,
        retry_count: int
    ) -> float:
        """
        Calculate delay for a specific retry attempt.

        Args:
            config: Retry configuration
            retry_count: Current retry count (0-based)

        Returns:
            Delay in seconds
        """
        if config.strategy == RetryStrategy.IMMEDIATE_RETRY:
            return 0.0

        elif config.strategy == RetryStrategy.FIXED_DELAY:
            return config.base_delay

        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            return config.base_delay * (retry_count + 1)

        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** retry_count)
            return min(delay, config.max_delay)

        elif config.strategy == RetryStrategy.EXTENDED_WAIT:
            # Longer initial wait, then exponential
            if retry_count == 0:
                return config.base_delay * 3
            delay = config.base_delay * (config.backoff_multiplier ** retry_count)
            return min(delay, config.max_delay)

        else:
            # Default to exponential backoff
            delay = config.base_delay * (config.backoff_multiplier ** retry_count)
            return min(delay, config.max_delay)