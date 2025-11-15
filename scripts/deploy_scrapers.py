#!/usr/bin/env python3
"""
Automated scraper deployment script for Apify platform.
Deploys all available scrapers and validates deployment.
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.apify_platform_client import ApifyPlatformClient
from src.core.settings_manager import settings


async def deploy_scraper(scraper_name: str, client: ApifyPlatformClient, dry_run: bool = False) -> Dict[str, Any]:
    """
    Deploy a single scraper to Apify platform.

    Args:
        scraper_name: Name of the scraper to deploy
        client: Apify platform client
        dry_run: If True, only validate without deploying

    Returns:
        Dict with deployment result
    """
    scraper_dir = PROJECT_ROOT / "src" / "scrapers" / scraper_name

    print(f"🚀 {'[DRY RUN] ' if dry_run else ''}Deploying {scraper_name}...")

    # Validate scraper structure
    required_files = [
        "src/__main__.py",
        "src/main.py",
        ".actor/actor.json",
        ".actor/input_schema.json",
        ".actor/output_schema.json",
        ".actor/dataset_schema.json",
        "requirements.txt",
        "Dockerfile"
    ]

    missing_files = []
    for file_path in required_files:
        if not (scraper_dir / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        return {
            "success": False,
            "scraper": scraper_name,
            "error": f"Missing required files: {', '.join(missing_files)}"
        }

    if dry_run:
        return {
            "success": True,
            "scraper": scraper_name,
            "actor_id": f"{scraper_name}-scraper",
            "message": "Structure validation passed"
        }

    # Deploy using Apify CLI
    import subprocess
    result = subprocess.run([
        "apify", "push", str(scraper_dir)
    ], capture_output=True, text=True, cwd=scraper_dir)

    if result.returncode != 0:
        return {
            "success": False,
            "scraper": scraper_name,
            "error": result.stderr.strip()
        }

    # Extract actor ID from output
    actor_id = None
    for line in result.stdout.split('\n'):
        if 'Actor ID:' in line:
            actor_id = line.split('Actor ID:')[1].strip()
            break

    if not actor_id:
        return {
            "success": False,
            "scraper": scraper_name,
            "error": "Could not extract actor ID from deployment output"
        }

    return {
        "success": True,
        "scraper": scraper_name,
        "actor_id": actor_id
    }


async def deploy_all_scrapers(dry_run: bool = False, skip_failing: bool = False) -> Dict[str, Any]:
    """
    Deploy all available scrapers.

    Args:
        dry_run: If True, only validate without deploying
        skip_failing: If True, continue with other scrapers if one fails

    Returns:
        Dict with deployment results
    """
    from src.core.platform_testing_integration import PlatformScraperIntegrationTester

    tester = PlatformScraperIntegrationTester()
    scrapers = tester.get_available_scrapers()

    results = {
        "total": len(scrapers),
        "successful": 0,
        "failed": 0,
        "deployments": {},
        "dry_run": dry_run
    }

    print(f"🚀 Starting {'DRY RUN ' if dry_run else ''}deployment of {len(scrapers)} scrapers")
    print(f"Scrapers: {', '.join(scrapers)}")
    print("=" * 80)

    async with ApifyPlatformClient() as client:
        for scraper in scrapers:
            try:
                result = await deploy_scraper(scraper, client, dry_run)
                results["deployments"][scraper] = result

                if result["success"]:
                    results["successful"] += 1
                    print(f"✅ {scraper}: {result.get('actor_id', 'OK')}")
                else:
                    results["failed"] += 1
                    print(f"❌ {scraper}: {result['error']}")

                if not skip_failing and not result["success"]:
                    print(f"❌ Stopping deployment due to failure in {scraper}")
                    break

            except Exception as e:
                print(f"❌ Unexpected error deploying {scraper}: {e}")
                results["deployments"][scraper] = {
                    "success": False,
                    "scraper": scraper,
                    "error": str(e)
                }
                results["failed"] += 1

                if not skip_failing:
                    break

    # Summary
    print(f"\n{'=' * 80}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Scrapers: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")

    if results["failed"] > 0:
        print(f"\n❌ FAILED DEPLOYMENTS:")
        for name, result in results["deployments"].items():
            if not result.get("success", False):
                print(f"  • {name}: {result.get('error', 'Unknown error')}")

    success = results["failed"] == 0
    if success:
        print(f"\n🎉 All scrapers deployed successfully!")
    else:
        print(f"\n⚠️  Some deployments failed. Check errors above.")

    return results


async def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy ProductScraper scrapers to Apify platform")
    parser.add_argument("--dry-run", action="store_true", help="Validate structure without deploying")
    parser.add_argument("--skip-failing", action="store_true", help="Continue deployment even if some scrapers fail")
    parser.add_argument("--scraper", help="Deploy specific scraper only")

    args = parser.parse_args()

    # Validate environment
    if not settings.get("apify_api_token"):
        print("❌ ERROR: Apify API token not configured.")
        print("   Set 'apify_api_token' in settings.json or APIFY_API_TOKEN environment variable")
        return 1

    try:
        if args.scraper:
            async with ApifyPlatformClient() as client:
                result = await deploy_scraper(args.scraper, client, args.dry_run)
                if result["success"]:
                    print(f"✅ {args.scraper} deployed successfully!")
                    return 0
                else:
                    print(f"❌ {args.scraper} deployment failed: {result['error']}")
                    return 1
        else:
            results = await deploy_all_scrapers(args.dry_run, args.skip_failing)
            return 0 if results["failed"] == 0 else 1

    except Exception as e:
        print(f"❌ Deployment failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))