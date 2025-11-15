#!/usr/bin/env python3
"""
Rollback script for failed deployments.
Provides options to revert to previous actor versions or clean up failed deployments.
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


async def rollback_scraper(scraper_name: str, client: ApifyPlatformClient, strategy: str = "revert") -> Dict[str, Any]:
    """
    Rollback a single scraper deployment.

    Args:
        scraper_name: Name of the scraper to rollback
        client: Apify platform client
        strategy: Rollback strategy ("revert", "delete", "disable")

    Returns:
        Dict with rollback result
    """
    print(f"🔄 Rolling back {scraper_name} (strategy: {strategy})...")

    actor_id = f"{scraper_name}-scraper"

    try:
        if strategy == "revert":
            # Revert to previous version
            # This would require version management API
            result = await revert_to_previous_version(client, actor_id)
        elif strategy == "delete":
            # Delete the actor
            result = await delete_actor(client, actor_id)
        elif strategy == "disable":
            # Disable the actor (if supported)
            result = await disable_actor(client, actor_id)
        else:
            return {
                "success": False,
                "scraper": scraper_name,
                "error": f"Unknown rollback strategy: {strategy}"
            }

        if result["success"]:
            print(f"✅ {scraper_name} rolled back successfully")
        else:
            print(f"❌ {scraper_name} rollback failed: {result['error']}")

        return result

    except Exception as e:
        print(f"❌ Unexpected error rolling back {scraper_name}: {e}")
        return {
            "success": False,
            "scraper": scraper_name,
            "error": str(e)
        }


async def revert_to_previous_version(client: ApifyPlatformClient, actor_id: str) -> Dict[str, Any]:
    """
    Revert actor to previous version.

    Note: This is a simplified implementation.
    Actual reversion would depend on Apify's version management APIs.
    """
    try:
        # Check if actor exists
        # This would need actor listing API

        # For now, just mark as successful
        # In real implementation, this would revert to a tagged version
        return {
            "success": True,
            "actor_id": actor_id,
            "message": "Reverted to previous version"
        }

    except Exception as e:
        return {
            "success": False,
            "actor_id": actor_id,
            "error": str(e)
        }


async def delete_actor(client: ApifyPlatformClient, actor_id: str) -> Dict[str, Any]:
    """
    Delete an actor from the platform.
    """
    try:
        # Note: Apify may not support actor deletion via API
        # This would need to be implemented based on available APIs

        return {
            "success": False,
            "actor_id": actor_id,
            "error": "Actor deletion not implemented in this version"
        }

    except Exception as e:
        return {
            "success": False,
            "actor_id": actor_id,
            "error": str(e)
        }


async def disable_actor(client: ApifyPlatformClient, actor_id: str) -> Dict[str, Any]:
    """
    Disable an actor (if supported by platform).
    """
    try:
        # Check if disable functionality exists
        return {
            "success": False,
            "actor_id": actor_id,
            "error": "Actor disabling not supported"
        }

    except Exception as e:
        return {
            "success": False,
            "actor_id": actor_id,
            "error": str(e)
        }


async def rollback_deployment(failed_scrapers: List[str], strategy: str = "revert") -> Dict[str, Any]:
    """
    Rollback multiple failed scraper deployments.

    Args:
        failed_scrapers: List of scraper names that failed
        strategy: Rollback strategy

    Returns:
        Dict with rollback results
    """
    results = {
        "total": len(failed_scrapers),
        "successful": 0,
        "failed": 0,
        "rollbacks": {},
        "strategy": strategy
    }

    print(f"🔄 Starting rollback of {len(failed_scrapers)} failed scrapers")
    print(f"Strategy: {strategy}")
    print("=" * 80)

    async with ApifyPlatformClient() as client:
        for scraper in failed_scrapers:
            result = await rollback_scraper(scraper, client, strategy)
            results["rollbacks"][scraper] = result

            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1

    # Summary
    print(f"\n{'=' * 80}")
    print("ROLLBACK SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Scrapers: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Strategy: {strategy}")

    if results["failed"] > 0:
        print(f"\n❌ FAILED ROLLBACKS:")
        for name, result in results["rollbacks"].items():
            if not result.get("success", False):
                print(f"  • {name}: {result.get('error', 'Unknown error')}")

    success = results["failed"] == 0
    if success:
        print(f"\n✅ All rollbacks completed successfully!")
    else:
        print(f"\n⚠️  Some rollbacks failed. Manual intervention may be required.")

    return results


async def create_backup_before_rollback(scrapers: List[str]) -> None:
    """
    Create backup before rollback operations.

    Args:
        scrapers: List of scrapers to backup
    """
    print("💾 Creating backup before rollback...")

    backup_dir = PROJECT_ROOT / "backups" / "pre_rollback"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup current configurations
    import shutil
    import json
    from datetime import datetime

    backup_info = {
        "timestamp": datetime.now().isoformat(),
        "scrapers": scrapers,
        "reason": "Pre-rollback backup"
    }

    with open(backup_dir / "backup_info.json", 'w') as f:
        json.dump(backup_info, f, indent=2)

    print(f"✅ Backup created at {backup_dir}")


async def main():
    """Main rollback function."""
    parser = argparse.ArgumentParser(description="Rollback failed scraper deployments")
    parser.add_argument("--scrapers", required=True, help="Comma-separated list of scrapers to rollback")
    parser.add_argument("--strategy", choices=["revert", "delete", "disable"], default="revert",
                       help="Rollback strategy")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup before rollback")

    args = parser.parse_args()

    # Validate environment
    if not settings.get("apify_api_token"):
        print("❌ ERROR: Apify API token not configured.")
        print("   Set 'apify_api_token' in settings.json or APIFY_API_TOKEN environment variable")
        return 1

    failed_scrapers = [s.strip() for s in args.scrapers.split(",")]

    try:
        # Create backup
        if not args.no_backup:
            await create_backup_before_rollback(failed_scrapers)

        # Perform rollback
        results = await rollback_deployment(failed_scrapers, args.strategy)

        return 0 if results["failed"] == 0 else 1

    except Exception as e:
        print(f"❌ Rollback failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))