#!/usr/bin/env python3
"""
DevTools setup utility for ProductScraper.
Helps configure Chrome DevTools integration with Selenium scrapers.
"""

import json
import os
import sys
from pathlib import Path

def update_mcp_config(connect_to_selenium=True):
    """Update MCP configuration to connect to Selenium or launch standalone."""
    mcp_config_path = Path(".vscode/mcp.json")

    if connect_to_selenium:
        config = {
            "servers": {
                "chrome-devtools": {
                    "command": "npx",
                    "args": ["-y", "chrome-devtools-mcp@latest", "--browserUrl=http://127.0.0.1:9222"]
                }
            }
        }
        print("✅ MCP configured to connect to Selenium Chrome instance (port 9222)")
    else:
        config = {
            "servers": {
                "chrome-devtools": {
                    "command": "npx",
                    "args": ["-y", "chrome-devtools-mcp@latest"]
                }
            }
        }
        print("✅ MCP configured for standalone Chrome instance")

    with open(mcp_config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print("🔄 Restart VS Code to apply MCP configuration changes")

def enable_devtools_in_scraper(scraper_file, enable=True):
    """Enable or disable devtools in a scraper file."""
    scraper_path = Path(scraper_file)

    if not scraper_path.exists():
        print(f"❌ Scraper file not found: {scraper_file}")
        return

    content = scraper_path.read_text(encoding='utf-8')

    if enable:
        # Change ENABLE_DEVTOOLS = False to True
        if "ENABLE_DEVTOOLS = False" in content:
            content = content.replace("ENABLE_DEVTOOLS = False", "ENABLE_DEVTOOLS = True")
            print(f"✅ Enabled DevTools in {scraper_file}")
        else:
            print(f"ℹ️ DevTools already enabled in {scraper_file}")
    else:
        # Change ENABLE_DEVTOOLS = True to False
        if "ENABLE_DEVTOOLS = True" in content:
            content = content.replace("ENABLE_DEVTOOLS = True", "ENABLE_DEVTOOLS = False")
            print(f"✅ Disabled DevTools in {scraper_file}")
        else:
            print(f"ℹ️ DevTools already disabled in {scraper_file}")

    scraper_path.write_text(content, encoding='utf-8')

def main():
    if len(sys.argv) < 2:
        print("Usage: python devtools_setup.py <command>")
        print("Commands:")
        print("  connect-selenium    - Configure MCP to connect to Selenium Chrome")
        print("  standalone          - Configure MCP for standalone Chrome")
        print("  enable-devtools     - Enable DevTools in coastal.py scraper")
        print("  disable-devtools    - Disable DevTools in coastal.py scraper")
        return

    command = sys.argv[1]

    if command == "connect-selenium":
        update_mcp_config(connect_to_selenium=True)
    elif command == "standalone":
        update_mcp_config(connect_to_selenium=False)
    elif command == "enable-devtools":
        enable_devtools_in_scraper("src/scrapers/coastal.py", enable=True)
    elif command == "disable-devtools":
        enable_devtools_in_scraper("src/scrapers/coastal.py", enable=False)
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()