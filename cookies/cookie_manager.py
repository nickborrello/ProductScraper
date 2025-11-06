# Cookie management utilities for scrapers

import os
import pickle
import glob
from pathlib import Path

def list_cookie_files():
    """List all cookie files in the cookies directory."""
    cookie_dir = Path("cookies")
    if not cookie_dir.exists():
        print("❌ Cookies directory does not exist")
        return []

    cookie_files = list(cookie_dir.glob("*.pkl"))
    if not cookie_files:
        print("📁 No cookie files found")
        return []

    print("🍪 Found cookie files:")
    for cookie_file in cookie_files:
        size = cookie_file.stat().st_size
        print(f"  • {cookie_file.name} ({size} bytes)")
    return cookie_files

def clear_cookies(site=None):
    """Clear cookie files. If site is specified, only clear that site's cookies."""
    cookie_dir = Path("cookies")
    if not cookie_dir.exists():
        print("❌ Cookies directory does not exist")
        return

    if site:
        cookie_file = cookie_dir / f"{site.lower()}_cookies.pkl"
        if cookie_file.exists():
            cookie_file.unlink()
            print(f"🗑️ Cleared cookies for {site}")
        else:
            print(f"❌ No cookie file found for {site}")
    else:
        cookie_files = list(cookie_dir.glob("*.pkl"))
        for cookie_file in cookie_files:
            cookie_file.unlink()
        print(f"🗑️ Cleared all {len(cookie_files)} cookie files")

def show_cookie_info(site):
    """Show information about a site's cookie file."""
    cookie_file = Path("cookies") / f"{site.lower()}_cookies.pkl"
    if not cookie_file.exists():
        print(f"❌ No cookie file found for {site}")
        return

    try:
        with open(cookie_file, "rb") as f:
            cookies = pickle.load(f)

        print(f"🍪 Cookie info for {site}:")
        print(f"  • File: {cookie_file}")
        print(f"  • Size: {cookie_file.stat().st_size} bytes")
        print(f"  • Number of cookies: {len(cookies)}")

        domains = set()
        for cookie in cookies:
            domains.add(cookie.get('domain', 'unknown'))

        print(f"  • Domains: {', '.join(sorted(domains))}")

    except Exception as e:
        print(f"❌ Error reading cookie file: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cookie_manager.py <command> [site]")
        print("Commands:")
        print("  list              - List all cookie files")
        print("  clear [site]      - Clear cookies (all or for specific site)")
        print("  info <site>       - Show info about site's cookies")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_cookie_files()
    elif command == "clear":
        site = sys.argv[2] if len(sys.argv) > 2 else None
        clear_cookies(site)
    elif command == "info":
        if len(sys.argv) < 3:
            print("❌ Please specify a site for info command")
            sys.exit(1)
        show_cookie_info(sys.argv[2])
    else:
        print(f"❌ Unknown command: {command}")