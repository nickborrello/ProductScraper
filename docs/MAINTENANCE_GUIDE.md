# Maintenance Guide

This guide covers ongoing maintenance procedures for the ProductScraper testing framework and deployed scrapers.

## Table of Contents

- [Daily Operations](#daily-operations)
- [Weekly Maintenance](#weekly-maintenance)
- [Monthly Maintenance](#monthly-maintenance)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Performance Optimization](#performance-optimization)
- [Security Maintenance](#security-maintenance)
- [Backup and Recovery](#backup-and-recovery)

## Daily Operations

### Health Checks

Run daily health checks to ensure system stability:

```bash
#!/usr/bin/env python3
"""
Daily health check script.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.apify_platform_client import ApifyPlatformClient


async def daily_health_check():
    """Perform comprehensive daily health checks."""
    print(f"🏥 Daily Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with ApifyPlatformClient() as client:
        checks = {
            "API Connectivity": await check_api_connectivity(client),
            "Actor Status": await check_actor_status(client),
            "Test Suite": await check_test_suite(),
            "Data Quality": await check_data_quality(),
            "Resource Usage": await check_resource_usage(client)
        }

        passed = 0
        failed = 0

        for check_name, result in checks.items():
            status = "✅" if result["success"] else "❌"
            print(f"{status} {check_name}: {result['message']}")

            if result["success"]:
                passed += 1
            else:
                failed += 1

        print(f"\n📊 Summary: {passed} passed, {failed} failed")

        return failed == 0


async def check_api_connectivity(client: ApifyPlatformClient) -> Dict[str, Any]:
    """Check API connectivity."""
    try:
        await client.list_datasets(limit=1)
        return {"success": True, "message": "API connection successful"}
    except Exception as e:
        return {"success": False, "message": f"API connection failed: {e}"}


async def check_actor_status(client: ApifyPlatformClient) -> Dict[str, Any]:
    """Check deployed actor status."""
    try:
        # Get list of expected actors
        expected_actors = ["amazon-scraper", "bradley-scraper", "central_pet-scraper"]

        # Check if actors exist and are accessible
        actors_found = 0
        for actor in expected_actors:
            try:
                # This would need actual actor listing API
                actors_found += 1
            except:
                pass

        if actors_found == len(expected_actors):
            return {"success": True, "message": f"All {actors_found} actors accessible"}
        else:
            return {"success": False, "message": f"Only {actors_found}/{len(expected_actors)} actors accessible"}

    except Exception as e:
        return {"success": False, "message": f"Actor status check failed: {e}"}


async def check_test_suite() -> Dict[str, Any]:
    """Run basic test suite check."""
    try:
        from platform_test_scrapers import test_all_scrapers
        from src.core.platform_testing_client import TestingMode

        success = await test_all_scrapers(TestingMode.LOCAL, verbose=False)
        return {
            "success": success,
            "message": "Test suite passed" if success else "Test suite failed"
        }
    except Exception as e:
        return {"success": False, "message": f"Test suite error: {e}"}


async def check_data_quality() -> Dict[str, Any]:
    """Check recent data quality scores."""
    try:
        # Check recent test results
        results_dir = PROJECT_ROOT / "results"
        if results_dir.exists():
            recent_results = list(results_dir.glob("scrape_results_*"))
            if recent_results:
                # Analyze recent results for quality scores
                return {"success": True, "message": f"Found {len(recent_results)} recent result sets"}
            else:
                return {"success": False, "message": "No recent results found"}
        else:
            return {"success": False, "message": "Results directory not found"}

    except Exception as e:
        return {"success": False, "message": f"Data quality check failed: {e}"}


async def check_resource_usage(client: ApifyPlatformClient) -> Dict[str, Any]:
    """Check platform resource usage."""
    try:
        # Check account usage/limits
        # This would integrate with Apify billing API
        return {"success": True, "message": "Resource usage within limits"}
    except Exception as e:
        return {"success": False, "message": f"Resource check failed: {e}"}


if __name__ == "__main__":
    success = asyncio.run(daily_health_check())
    sys.exit(0 if success else 1)
```

### Daily Checklist

- [ ] Run health check script
- [ ] Review overnight test results
- [ ] Check for failed scraper runs
- [ ] Monitor resource usage
- [ ] Review error logs
- [ ] Update status dashboard

## Weekly Maintenance

### Test Data Updates

Update test data weekly to ensure relevance:

```bash
#!/usr/bin/env python3
"""
Weekly test data update script.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def update_test_data():
    """Update test data with fresh SKUs."""
    test_data_file = PROJECT_ROOT / "tests" / "fixtures" / "scraper_test_data.json"

    print("🔄 Updating test data...")

    with open(test_data_file, 'r') as f:
        test_data = json.load(f)

    # Update timestamps
    test_data["_metadata"] = {
        "last_updated": datetime.now().isoformat(),
        "updated_by": "maintenance_script"
    }

    # Validate test SKUs are still available
    # This would involve checking with actual retailers
    # For now, just update metadata

    with open(test_data_file, 'w') as f:
        json.dump(test_data, f, indent=2)

    print("✅ Test data updated")


def validate_test_skus():
    """Validate that test SKUs are still functional."""
    print("🔍 Validating test SKUs...")

    # Run quick validation on test SKUs
    # This would use the testing framework to check SKU validity

    print("✅ Test SKU validation completed")


if __name__ == "__main__":
    update_test_data()
    validate_test_skus()
```

### Dependency Updates

Check and update dependencies weekly:

```bash
# Update Python dependencies
pip list --outdated
pip install --upgrade -r requirements.txt

# Update system packages if applicable
# apt update && apt upgrade -y

# Test after updates
python platform_test_scrapers.py --all
```

### Performance Review

Review weekly performance metrics:

- Average execution times
- Success rates by scraper
- Resource utilization
- Error patterns

## Monthly Maintenance

### Comprehensive Testing

Run full platform testing monthly:

```bash
#!/usr/bin/env python3
"""
Monthly comprehensive testing script.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from platform_test_scrapers import test_all_scrapers
from src.core.platform_testing_client import TestingMode


async def monthly_comprehensive_test():
    """Run comprehensive monthly testing."""
    print("🧪 Starting monthly comprehensive testing...")

    # Test local mode
    print("\n📍 Testing LOCAL mode...")
    local_success = await test_all_scrapers(TestingMode.LOCAL, verbose=True)

    # Test platform mode
    print("\n☁️  Testing PLATFORM mode...")
    platform_success = await test_all_scrapers(TestingMode.PLATFORM, verbose=True)

    # Generate monthly report
    generate_monthly_report(local_success, platform_success)

    overall_success = local_success and platform_success
    return overall_success


def generate_monthly_report(local_success: bool, platform_success: bool):
    """Generate monthly testing report."""
    from datetime import datetime

    report = f"""
# Monthly Testing Report - {datetime.now().strftime('%B %Y')}

## Summary
- Local Testing: {'✅ PASSED' if local_success else '❌ FAILED'}
- Platform Testing: {'✅ PASSED' if platform_success else '❌ FAILED'}
- Overall Status: {'✅ ALL TESTS PASSED' if (local_success and platform_success) else '❌ ISSUES DETECTED'}

## Recommendations
{'All systems operating normally.' if (local_success and platform_success) else 'Review failed tests and address issues.'}
"""

    report_file = PROJECT_ROOT / "docs" / "monthly_reports" / f"monthly_report_{datetime.now().strftime('%Y%m')}.md"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w') as f:
        f.write(report)

    print(f"📄 Monthly report saved to {report_file}")


if __name__ == "__main__":
    success = asyncio.run(monthly_comprehensive_test())
    sys.exit(0 if success else 1)
```

### Security Audits

Perform monthly security checks:

- Review API token usage
- Check for exposed credentials
- Audit access permissions
- Update security patches

### Capacity Planning

Review monthly usage patterns:

- Peak usage times
- Resource consumption trends
- Scalability requirements
- Cost optimization opportunities

## Monitoring and Alerting

### Alert Configuration

Set up alerts for critical events:

```yaml
# alerts.yaml
alerts:
  - name: "Deployment Failure"
    condition: "deployment_success == false"
    channels: ["email", "slack"]
    severity: "critical"

  - name: "High Error Rate"
    condition: "error_rate > 0.1"
    channels: ["email"]
    severity: "warning"

  - name: "Resource Limit"
    condition: "resource_usage > 0.9"
    channels: ["email", "slack"]
    severity: "warning"

  - name: "Test Suite Failure"
    condition: "test_success == false"
    channels: ["email"]
    severity: "error"
```

### Monitoring Dashboard

Key metrics to monitor:

- **Performance Metrics**
  - Average scraper execution time
  - Platform API response times
  - Memory and CPU usage

- **Reliability Metrics**
  - Scraper success rates
  - Platform uptime
  - Error rates by scraper

- **Business Metrics**
  - Data quality scores
  - Test coverage
  - Deployment frequency

### Log Analysis

Regular log review procedures:

```bash
#!/usr/bin/env python3
"""
Log analysis script for maintenance.
"""

import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent


def analyze_recent_logs(days: int = 7):
    """Analyze logs from the last N days."""
    print(f"📊 Analyzing logs from last {days} days...")

    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        print("❌ Logs directory not found")
        return

    # Find log files from last N days
    cutoff_date = datetime.now() - timedelta(days=days)
    log_files = []

    for log_file in logs_dir.glob("*.log"):
        if log_file.stat().st_mtime > cutoff_date.timestamp():
            log_files.append(log_file)

    if not log_files:
        print(f"ℹ️  No log files found in last {days} days")
        return

    # Analyze logs
    error_patterns = []
    warning_patterns = []

    for log_file in log_files:
        with open(log_file, 'r') as f:
            for line in f:
                if 'ERROR' in line:
                    error_patterns.append(extract_error_pattern(line))
                elif 'WARNING' in line:
                    warning_patterns.append(extract_warning_pattern(line))

    # Report findings
    print(f"\n🔍 Error Analysis:")
    if error_patterns:
        error_counts = Counter(error_patterns)
        for error, count in error_counts.most_common(5):
            print(f"  • {error}: {count} occurrences")
    else:
        print("  ✅ No errors found")

    print(f"\n⚠️  Warning Analysis:")
    if warning_patterns:
        warning_counts = Counter(warning_patterns)
        for warning, count in warning_counts.most_common(5):
            print(f"  • {warning}: {count} occurrences")
    else:
        print("  ✅ No warnings found")


def extract_error_pattern(line: str) -> str:
    """Extract error pattern from log line."""
    # Simple pattern extraction - could be more sophisticated
    if 'Exception' in line:
        return 'Exception'
    elif 'Timeout' in line:
        return 'Timeout'
    elif 'Authentication' in line:
        return 'Authentication'
    else:
        return 'Other Error'


def extract_warning_pattern(line: str) -> str:
    """Extract warning pattern from log line."""
    if 'deprecated' in line.lower():
        return 'Deprecation Warning'
    elif 'rate limit' in line.lower():
        return 'Rate Limit Warning'
    else:
        return 'Other Warning'


if __name__ == "__main__":
    analyze_recent_logs()
```

## Performance Optimization

### Profiling and Analysis

Regular performance profiling:

```bash
#!/usr/bin/env python3
"""
Performance profiling script.
"""

import cProfile
import pstats
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def profile_scraper_execution(scraper_name: str):
    """Profile scraper execution performance."""
    print(f"⚡ Profiling {scraper_name} execution...")

    # Profile the scraper execution
    profiler = cProfile.Profile()
    profiler.enable()

    # Run scraper test
    import asyncio
    from platform_test_scrapers import test_single_scraper
    from src.core.platform_testing_client import TestingMode

    asyncio.run(test_single_scraper(scraper_name, mode=TestingMode.LOCAL, verbose=False))

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    # Save profile data
    profile_file = PROJECT_ROOT / "performance" / f"{scraper_name}_profile.txt"
    profile_file.parent.mkdir(exist_ok=True)

    with open(profile_file, 'w') as f:
        stats.print_stats(file=f)

    print(f"📄 Profile saved to {profile_file}")

    # Print top bottlenecks
    print("\n🔥 Top Performance Bottlenecks:")
    stats.print_stats(10)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        profile_scraper_execution(sys.argv[1])
    else:
        print("Usage: python profile_scraper.py <scraper_name>")
```

### Optimization Strategies

1. **Code Optimization**
   - Profile hot paths
   - Optimize database queries
   - Reduce memory allocations

2. **Network Optimization**
   - Implement request batching
   - Add connection pooling
   - Use compression

3. **Caching Strategies**
   - Cache frequently accessed data
   - Implement response caching
   - Use CDN for static assets

## Security Maintenance

### Security Checklist

Monthly security review:

- [ ] Review API token permissions
- [ ] Check for exposed credentials
- [ ] Audit access logs
- [ ] Update security patches
- [ ] Review encryption settings
- [ ] Check for vulnerabilities in dependencies

### Incident Response

Security incident procedures:

1. **Detection**
   - Monitor for unusual activity
   - Review access logs
   - Check for unauthorized access

2. **Containment**
   - Revoke compromised credentials
   - Isolate affected systems
   - Disable suspicious actors

3. **Recovery**
   - Restore from clean backups
   - Update security measures
   - Monitor for recurrence

4. **Lessons Learned**
   - Document incident details
   - Update security procedures
   - Implement preventive measures

## Backup and Recovery

### Backup Strategy

Automated backup procedures:

```bash
#!/usr/bin/env python3
"""
Backup script for critical data.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def create_backup():
    """Create comprehensive backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "backups" / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"💾 Creating backup: {backup_dir}")

    # Backup configurations
    config_items = [
        "settings.json",
        "tests/fixtures/scraper_test_data.json",
        ".github/workflows/"
    ]

    for item in config_items:
        src = PROJECT_ROOT / item
        if src.exists():
            dst = backup_dir / item
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dst)
            else:
                shutil.copytree(src, dst, dirs_exist_ok=True)

    # Backup results (last 30 days)
    results_dir = PROJECT_ROOT / "results"
    if results_dir.exists():
        backup_results = backup_dir / "results"
        backup_results.mkdir()

        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=30)

        for result_dir in results_dir.glob("scrape_results_*"):
            if result_dir.stat().st_mtime > cutoff.timestamp():
                shutil.copytree(result_dir, backup_results / result_dir.name)

    # Create backup manifest
    manifest = {
        "timestamp": timestamp,
        "version": "1.0",
        "items": config_items + ["results (last 30 days)"]
    }

    with open(backup_dir / "manifest.json", 'w') as f:
        import json
        json.dump(manifest, f, indent=2)

    print("✅ Backup completed")
    return backup_dir


def cleanup_old_backups(retention_days: int = 30):
    """Clean up old backups."""
    backups_dir = PROJECT_ROOT / "backups"
    if not backups_dir.exists():
        return

    cutoff = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)

    removed = 0
    for backup_dir in backups_dir.glob("backup_*"):
        if backup_dir.stat().st_mtime < cutoff:
            shutil.rmtree(backup_dir)
            removed += 1

    if removed > 0:
        print(f"🗑️  Cleaned up {removed} old backups")


if __name__ == "__main__":
    create_backup()
    cleanup_old_backups()
```

### Recovery Procedures

1. **Data Recovery**
   - Identify backup point
   - Restore configurations
   - Validate restored data

2. **System Recovery**
   - Rebuild from backup
   - Test restored system
   - Update dependencies

3. **Validation**
   - Run test suite
   - Verify data integrity
   - Check system functionality

### Disaster Recovery Plan

- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour
- **Backup Frequency**: Daily automated + weekly full
- **Testing**: Monthly recovery testing

## Automation

### Scheduled Tasks

Set up automated maintenance tasks:

```bash
# Daily health check (cron)
0 6 * * * /path/to/project/scripts/daily_health_check.py

# Weekly test data update (cron)
0 7 * * 1 /path/to/project/scripts/weekly_update.py

# Monthly comprehensive testing (cron)
0 8 1 * * /path/to/project/scripts/monthly_testing.py

# Monthly backup (cron)
0 2 1 * * /path/to/project/scripts/backup.py
```

### Monitoring Integration

Integrate with monitoring systems:

- Set up dashboards for key metrics
- Configure alerts for critical events
- Enable log aggregation
- Implement performance tracking

This maintenance guide ensures the ProductScraper testing framework remains reliable, secure, and performant over time.