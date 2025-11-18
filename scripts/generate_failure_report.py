#!/usr/bin/env python3
"""
Failure Analytics Report Generator

Generates comprehensive reports from failure analytics data.
Can be run as a standalone script or imported as a module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

if TYPE_CHECKING:
    from src.core.failure_analytics import FailureAnalytics

try:
    from src.core.failure_analytics import FailureAnalytics
except ImportError:
    # Fallback for different execution contexts
    import src.core.failure_analytics as failure_analytics
    FailureAnalytics = failure_analytics.FailureAnalytics


def generate_report(
    analytics: Any,
    site_name: Optional[str] = None,
    hours: int = 24,
    output_format: str = "text"
) -> str:
    """
    Generate a failure analytics report.

    Args:
        analytics: FailureAnalytics instance
        site_name: Specific site to report on (None for all)
        hours: Time window in hours
        output_format: Output format ('text', 'json')

    Returns:
        Formatted report string
    """
    report_data = analytics.generate_report(site_name=site_name, hours=hours)

    if output_format == "json":
        return json.dumps(report_data, indent=2, default=str)

    # Text format
    lines = []
    lines.append("=" * 80)
    lines.append("FAILURE ANALYTICS REPORT")
    lines.append("=" * 80)
    lines.append(f"Period: Last {hours} hours")
    lines.append(f"Site: {site_name or 'All sites'}")
    lines.append(f"Generated: {report_data.get('generated_at', 'Unknown')}")
    lines.append("")

    lines.append("SUMMARY STATISTICS:")
    lines.append("-" * 40)
    lines.append(f"Total Failures: {report_data.get('total_failures', 0)}")
    lines.append(f"Average Retry Count: {report_data.get('avg_retry_count', 0):.2f}")
    lines.append(f"Success After Retry Rate: {report_data.get('success_after_retry_rate', 0):.1%}")
    lines.append("")

    if report_data.get('failure_counts'):
        lines.append("FAILURE TYPES:")
        lines.append("-" * 40)
        for failure_type, count in report_data['failure_counts'].items():
            lines.append(f"  {failure_type}: {count}")
        lines.append("")

    if report_data.get('site_failures') and not site_name:
        lines.append("FAILURES BY SITE:")
        lines.append("-" * 40)
        for site, count in sorted(report_data['site_failures'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {site}: {count}")
        lines.append("")

    if report_data.get('action_failures'):
        lines.append("FAILURES BY ACTION:")
        lines.append("-" * 40)
        for action, count in sorted(report_data['action_failures'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {action}: {count}")
        lines.append("")

    if report_data.get('insights'):
        lines.append("KEY INSIGHTS:")
        lines.append("-" * 40)
        for insight in report_data['insights']:
            lines.append(f"  • {insight}")
        lines.append("")

    if report_data.get('recommendations'):
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 40)
        for rec in report_data['recommendations']:
            lines.append(f"  • {rec}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def generate_health_report(analytics: Any, output_format: str = "text") -> str:
    """
    Generate a health report for all sites.

    Args:
        analytics: FailureAnalytics instance
        output_format: Output format ('text', 'json')

    Returns:
        Formatted health report string
    """
    all_metrics = analytics.get_all_site_metrics()

    if output_format == "json":
        health_data = {}
        for site, metrics in all_metrics.items():
            health_data[site] = {
                "health_score": analytics.get_health_score(site),
                "success_rate": metrics.success_rate,
                "total_requests": metrics.total_requests,
                "total_failures": metrics.total_failures,
                "recent_failures": metrics.recent_failures
            }
        return json.dumps(health_data, indent=2)

    # Text format
    lines = []
    lines.append("=" * 80)
    lines.append("SCRAPER HEALTH REPORT")
    lines.append("=" * 80)

    if not all_metrics:
        lines.append("No site metrics available.")
        return "\n".join(lines)

    # Sort by health score (worst first)
    sorted_sites = sorted(
        all_metrics.items(),
        key=lambda x: analytics.get_health_score(x[0])
    )

    lines.append("<10>")
    lines.append("-" * 80)
    lines.append("<20>")
    lines.append("")

    for site, metrics in sorted_sites:
        health_score = analytics.get_health_score(site)
        status = "🔴 CRITICAL" if health_score < 0.5 else "🟡 WARNING" if health_score < 0.8 else "🟢 HEALTHY"

        lines.append(f"Site: {site}")
        lines.append(f"  Status: {status}")
        lines.append(f"  Health Score: {health_score:.1%}")
        lines.append(f"  Success Rate: {metrics.success_rate:.1%}")
        lines.append(f"  Total Requests: {metrics.total_requests}")
        lines.append(f"  Total Failures: {metrics.total_failures}")
        lines.append(f"  Recent Failures: {metrics.recent_failures}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate failure analytics reports")
    parser.add_argument(
        "--site", "-s",
        help="Specific site to report on (default: all sites)"
    )
    parser.add_argument(
        "--hours", "-H",
        type=int,
        default=24,
        help="Time window in hours (default: 24)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Generate health report instead of failure report"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    try:
        # Initialize analytics
        analytics = FailureAnalytics()

        # Generate report
        if args.health:
            report = generate_health_report(analytics, args.format)
        else:
            report = generate_report(
                analytics,
                site_name=args.site,
                hours=args.hours,
                output_format=args.format
            )

        # Output report
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()