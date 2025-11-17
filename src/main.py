import sys
import os
import argparse
from PyQt6.QtWidgets import QApplication

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    parser = argparse.ArgumentParser(description="ProductScraper")
    parser.add_argument(
        "--run",
        type=str,
        help="Run a specific part of the application",
        choices=["gui", "scraper"],
    )
    parser.add_argument(
        "--file", type=str, help="Path to the Excel file to be processed by the scraper"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for scrapers (sets HEADLESS=False and DEBUG_MODE=True)",
    )
    args = parser.parse_args()

    # Set debug environment variables if --debug is used
    if args.debug:
        os.environ["HEADLESS"] = "False"
        os.environ["DEBUG_MODE"] = "True"

    if args.run == "gui":
        from src.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    elif args.run == "scraper":
        from src.core.settings_manager import settings

        # Check which scraper system to use
        scraper_system = settings.get("scraper_system", "new")

        if scraper_system == "legacy":
            print("🔄 Using legacy archived scraper system...")
            from src.scrapers.main import run_scraping
        else:
            print("🚀 Using new modular scraper system...")
            from src.scrapers.main import run_scraping

        if args.file:
            run_scraping(args.file)
        else:
            print("Please provide a file path using the --file argument.")
    else:
        # Default to GUI if no argument is provided
        from src.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
