#!/usr/bin/env python3
"""
Ollama Installation and Setup Script for ProductScraper

This script helps install and configure Ollama for local LLM classification.
"""

import os
import sys
import platform
import subprocess
import requests
from pathlib import Path

def run_command(command, shell=False):
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def download_file(url, destination):
    """Download a file from URL to destination."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def install_ollama_windows():
    """Install Ollama on Windows."""
    print("🐧 Installing Ollama on Windows...")

    # Download the installer
    installer_url = "https://ollama.com/download/OllamaSetup.exe"
    installer_path = Path.home() / "Downloads" / "OllamaSetup.exe"

    print(f"📥 Downloading Ollama installer to {installer_path}...")
    if not download_file(installer_url, installer_path):
        return False

    print("✅ Download complete!")
    print(f"🔧 Please run the installer: {installer_path}")
    print("   After installation, run 'ollama serve' in a terminal")
    print("   Then pull a model with: ollama pull llama3.2")

    return True

def install_ollama_linux():
    """Install Ollama on Linux."""
    print("🐧 Installing Ollama on Linux...")

    success, stdout, stderr = run_command("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
    if success:
        print("✅ Ollama installed successfully!")
        print("🔧 Starting Ollama service...")
        run_command(["systemctl", "--user", "start", "ollama"])
        return True
    else:
        print(f"❌ Installation failed: {stderr}")
        return False

def install_ollama_macos():
    """Install Ollama on macOS."""
    print("🍎 Installing Ollama on macOS...")

    # Download the installer
    installer_url = "https://ollama.com/download/Ollama.dmg"
    installer_path = Path.home() / "Downloads" / "Ollama.dmg"

    print(f"📥 Downloading Ollama installer to {installer_path}...")
    if not download_file(installer_url, installer_path):
        return False

    print("✅ Download complete!")
    print(f"🔧 Please open and install: {installer_path}")
    print("   After installation, Ollama should start automatically")

    return True

def check_ollama_installation():
    """Check if Ollama is installed and running."""
    print("🔍 Checking Ollama installation...")

    success, stdout, stderr = run_command(["ollama", "--version"])
    if not success:
        print("❌ Ollama is not installed or not in PATH")
        return False

    print(f"✅ Ollama is installed: {stdout.strip()}")

    # Check if Ollama is running
    try:
        import ollama
        ollama.list()
        print("✅ Ollama service is running")
        return True
    except Exception as e:
        print(f"⚠️ Ollama service is not running: {e}")
        print("   Try running: ollama serve")
        return False

def pull_default_model():
    """Pull the default model (llama3.2)."""
    print("📥 Pulling default model (llama3.2)...")

    success, stdout, stderr = run_command(["ollama", "pull", "llama3.2"])
    if success:
        print("✅ Model llama3.2 downloaded successfully!")
        return True
    else:
        print(f"❌ Failed to pull model: {stderr}")
        return False

def main():
    """Main installation function."""
    print("🚀 ProductScraper Ollama Setup")
    print("=" * 40)

    system = platform.system().lower()

    # Check if already installed
    if check_ollama_installation():
        print("🎉 Ollama is already installed and running!")
        if input("Pull default model (llama3.2)? [y/N]: ").lower().startswith('y'):
            pull_default_model()
        return

    # Install based on platform
    if system == "windows":
        if install_ollama_windows():
            print("\n📋 Next steps:")
            print("1. Run the downloaded installer")
            print("2. Start Ollama: ollama serve")
            print("3. Pull a model: ollama pull llama3.2")
            print("4. Test in ProductScraper by selecting 'local_llm' classification method")

    elif system == "linux":
        if install_ollama_linux():
            pull_default_model()
            print("\n📋 Next steps:")
            print("1. Test in ProductScraper by selecting 'local_llm' classification method")

    elif system == "darwin":  # macOS
        if install_ollama_macos():
            print("\n📋 Next steps:")
            print("1. Run the downloaded installer")
            print("2. Ollama should start automatically")
            print("3. Pull a model: ollama pull llama3.2")
            print("4. Test in ProductScraper by selecting 'local_llm' classification method")

    else:
        print(f"❌ Unsupported platform: {system}")
        print("Please visit https://ollama.com/download for manual installation")

    print("\n📖 For more information, visit: https://ollama.com")
    print("🔧 To use in ProductScraper: Set classification method to 'local_llm' in settings")

if __name__ == "__main__":
    main()