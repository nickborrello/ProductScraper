# Deployment Guide

This guide covers the deployment procedures for ProductScraper scrapers to the Apify platform.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Scripts](#deployment-scripts)
- [Manual Deployment](#manual-deployment)
- [Post-Deployment Validation](#post-deployment-validation)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

### Platform Requirements

1. **Apify Account**
   - Valid Apify account with billing enabled
   - Sufficient credits for deployment and testing
   - API token with appropriate permissions

2. **Local Environment**
   - Python 3.8+ with all dependencies
   - Apify CLI installed: `npm install -g apify-cli`
   - Valid scraper structure (see testing guide)

3. **Configuration**
   ```json
   {
     "apify_api_token": "your-apify-api-token",
     "apify_base_url": "https://api.apify.com/v2"
   }
   ```

### Pre-Deployment Checklist

- [ ] All scrapers pass local testing
- [ ] Data quality score > 90% for all scrapers
- [ ] Platform testing successful
- [ ] API token configured and tested
- [ ] Sufficient Apify credits available
- [ ] Backup of current production actors (if applicable)

## Deployment Scripts

### Automated Deployment Script

The `scripts/deploy_scrapers.py` script provides automated deployment:

```python
#!/usr/bin/env python3
"""
Automated scraper deployment script for Apify platform.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.apify_platform_client import ApifyPlatformClient
from src.core.settings_manager import settings


async def deploy_scraper(scraper_name: str, client: ApifyPlatformClient) -> Dict[str, Any]:
    """Deploy a single scraper to Apify platform."""
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / scraper_name

    print(f"🚀 Deploying {scraper_name}...")

    # Build deployment command
    import subprocess
    result = subprocess.run([
        "apify", "push", str(scraper_dir)
    ], capture_output=True, text=True, cwd=scraper_dir)

    if result.returncode != 0:
        return {
            "success": False,
            "scraper": scraper_name,
            "error": result.stderr
        }

    # Extract actor ID from output
    actor_id = None
    for line in result.stdout.split('\n'):
        if 'Actor ID:' in line:
            actor_id = line.split('Actor ID:')[1].strip()
            break

    return {
        "success": True,
        "scraper": scraper_name,
        "actor_id": actor_id
    }


async def deploy_all_scrapers() -> Dict[str, Any]:
    """Deploy all available scrapers."""
    async with ApifyPlatformClient() as client:
        from src.core.platform_testing_integration import PlatformScraperIntegrationTester
        tester = PlatformScraperIntegrationTester()
        scrapers = tester.get_available_scrapers()

        results = {
            "total": len(scrapers),
            "successful": 0,
            "failed": 0,
            "deployments": {}
        }

        for scraper in scrapers:
            result = await deploy_scraper(scraper, client)
            results["deployments"][scraper] = result

            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1

        return results


async def main():
    """Main deployment function."""
    print("🚀 Starting ProductScraper deployment...")

    # Pre-deployment validation
    print("🔍 Running pre-deployment validation...")
    from platform_test_scrapers import test_all_scrapers
    from src.core.platform_testing_client import TestingMode

    validation_passed = await test_all_scrapers(TestingMode.LOCAL, verbose=False)
    if not validation_passed:
        print("❌ Pre-deployment validation failed. Fix issues before deploying.")
        return 1

    # Deploy all scrapers
    results = await deploy_all_scrapers()

    print(f"\n📊 Deployment Results:")
    print(f"Total Scrapers: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")

    if results['failed'] > 0:
        print(f"\n❌ Failed Deployments:")
        for scraper, result in results['deployments'].items():
            if not result['success']:
                print(f"  • {scraper}: {result['error']}")

    success = results['failed'] == 0
    if success:
        print(f"\n✅ All scrapers deployed successfully!")
    else:
        print(f"\n⚠️  Some deployments failed. Check errors above.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

### Usage

```bash
# Deploy all scrapers
python scripts/deploy_scrapers.py

# Deploy specific scraper
python scripts/deploy_scrapers.py --scraper amazon

# Dry run (validate without deploying)
python scripts/deploy_scrapers.py --dry-run
```

### Deployment Validation Script

```python
#!/usr/bin/env python3
"""
Post-deployment validation script.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from platform_test_scrapers import test_all_scrapers
from src.core.platform_testing_client import TestingMode


async def validate_deployment():
    """Validate deployed scrapers on platform."""
    print("🔍 Validating deployment...")

    # Test all scrapers on platform
    success = await test_all_scrapers(TestingMode.PLATFORM, verbose=True)

    if success:
        print("✅ Deployment validation successful!")
        return 0
    else:
        print("❌ Deployment validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(validate_deployment()))
```

## Manual Deployment

### Using Apify CLI

1. **Navigate to Scraper Directory**
   ```bash
   cd src/scrapers/amazon
   ```

2. **Login to Apify**
   ```bash
   apify login
   ```

3. **Deploy Scraper**
   ```bash
   apify push
   ```

4. **Verify Deployment**
   ```bash
   apify actors ls
   ```

### Using Apify Console

1. **Access Apify Console**
   - Go to https://console.apify.com/
   - Sign in to your account

2. **Create New Actor**
   - Click "Create new" → "Blank actor"
   - Set actor name (e.g., "amazon-scraper")

3. **Upload Source Code**
   - Upload scraper directory as ZIP
   - Or use GitHub integration

4. **Configure Actor**
   - Set input/output schemas
   - Configure build settings
   - Set environment variables

5. **Build and Test**
   - Build the actor
   - Test with sample input
   - Verify output format

## Post-Deployment Validation

### Automated Validation

```bash
# Run platform validation
python scripts/validate_deployment.py

# Test specific scraper
python platform_test_scrapers.py --scraper amazon --platform

# Test all scrapers
python platform_test_scrapers.py --all --platform
```

### Manual Validation

1. **Check Actor Status**
   ```bash
   apify actors ls
   ```

2. **Test Actor Run**
   ```bash
   apify call <actor-id> --input '{"skus": ["TEST-SKU"]}'
   ```

3. **Verify Output**
   - Check dataset creation
   - Validate data format
   - Confirm field coverage

### Validation Checklist

- [ ] All actors deployed successfully
- [ ] Platform testing passes for all scrapers
- [ ] Data quality scores maintained
- [ ] API responses within acceptable time limits
- [ ] No authentication or permission errors
- [ ] Dataset creation and access working

## Rollback Procedures

### Automated Rollback

```python
#!/usr/bin/env python3
"""
Rollback script for failed deployments.
"""

import asyncio
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.apify_platform_client import ApifyPlatformClient


async def rollback_deployment(failed_scrapers: List[str]):
    """Rollback failed scraper deployments."""
    async with ApifyPlatformClient() as client:
        for scraper in failed_scrapers:
            print(f"🔄 Rolling back {scraper}...")

            # Delete failed actor version
            # Implementation depends on specific rollback strategy

            print(f"✅ Rolled back {scraper}")


async def main():
    """Main rollback function."""
    # Get failed scrapers from deployment results
    # Implementation would read from deployment log

    failed_scrapers = ["amazon", "bradley"]  # Example
    await rollback_deployment(failed_scrapers)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

### Manual Rollback

1. **Identify Failed Deployment**
   - Check deployment logs
   - Identify problematic actors

2. **Revert to Previous Version**
   ```bash
   apify push --version-tag previous
   ```

3. **Delete Failed Version**
   ```bash
   apify actors rm <actor-id> --version <failed-version>
   ```

4. **Restore Configuration**
   - Restore backed up configurations
   - Revert environment variables

## Monitoring and Maintenance

### Health Checks

```python
#!/usr/bin/env python3
"""
Health check script for deployed scrapers.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.apify_platform_client import ApifyPlatformClient


async def health_check():
    """Perform health checks on all deployed scrapers."""
    async with ApifyPlatformClient() as client:
        # Check actor status
        # Test basic functionality
        # Monitor performance metrics

        print("✅ Health check completed")


if __name__ == "__main__":
    sys.exit(asyncio.run(health_check()))
```

### Performance Monitoring

1. **Execution Times**
   - Monitor average run times
   - Set up alerts for timeouts

2. **Success Rates**
   - Track successful vs failed runs
   - Monitor error patterns

3. **Resource Usage**
   - Monitor memory and CPU usage
   - Track API call volumes

### Maintenance Tasks

#### Regular Updates
- Update dependencies quarterly
- Review and update test data
- Monitor platform API changes

#### Performance Optimization
- Profile scraper performance
- Optimize network requests
- Implement caching where appropriate

#### Security Updates
- Monitor for security vulnerabilities
- Update base images regularly
- Review access permissions

### Alert Configuration

Set up alerts for:
- Deployment failures
- Performance degradation
- High error rates
- Resource exhaustion
- Security incidents

### Backup and Recovery

1. **Code Backup**
   - Maintain version control
   - Tag stable releases

2. **Configuration Backup**
   - Backup actor configurations
   - Document environment settings

3. **Data Backup**
   - Backup test datasets
   - Archive successful runs

## Troubleshooting Deployment Issues

### Common Issues

**Build Failures**
```
ERROR: Build failed
```
- Check dependency versions
- Validate Dockerfile syntax
- Review build logs

**Authentication Errors**
```
ERROR: Authentication failed
```
- Verify API token validity
- Check token permissions
- Confirm account status

**Timeout Errors**
```
ERROR: Build timeout
```
- Optimize build process
- Reduce dependencies
- Increase timeout limits

**Resource Limits**
```
ERROR: Memory limit exceeded
```
- Optimize memory usage
- Reduce concurrent operations
- Upgrade Apify plan

### Debug Steps

1. **Check Logs**
   ```bash
   apify builds ls
   apify builds log <build-id>
   ```

2. **Local Testing**
   ```bash
   python platform_test_scrapers.py --scraper <scraper> --validate
   ```

3. **Incremental Deployment**
   - Deploy one scraper at a time
   - Test each deployment individually

4. **Environment Isolation**
   - Test in staging environment first
   - Use separate accounts for testing