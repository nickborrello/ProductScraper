#!/usr/bin/env python3
"""
ProductScraper - Professional Product Management System
Main entry point for the desktop application.
"""

import sys
import os

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from scripts.run_gui import MainWindow


def main():
    """Launch the ProductScraper GUI application"""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("ProductScraper")
    app.setOrganizationName("BayStatePet")
    app.setOrganizationDomain("baystatepet.com")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
