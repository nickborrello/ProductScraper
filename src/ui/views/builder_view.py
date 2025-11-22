import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.scrapers.models.config import ScraperConfig
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.ui.scraper_builder_dialog import ScraperBuilderDialog
from src.ui.scraper_management_dialog import EditScraperDialog


class BuilderView(QWidget):
    """View for building and managing scrapers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = ScraperConfigParser()
        self.scrapers_dir = Path("src/scrapers/configs")
        self.scrapers_dir.mkdir(exist_ok=True)

        self.setup_ui()
        self.load_scrapers()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Scraper list
        left_panel = self.create_scraper_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - Scraper details
        right_panel = self.create_details_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        # Bottom buttons
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("➕ Build New Scraper (AI)")
        self.add_btn.setProperty("class", "primary")
        self.add_btn.clicked.connect(self.build_scraper)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected_scraper)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.clicked.connect(self.delete_selected_scraper)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_scrapers)
        buttons_layout.addWidget(self.refresh_btn)

        layout.addLayout(buttons_layout)

    def create_scraper_list_panel(self):
        """Create the scraper list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Available Scrapers")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        # Scraper list
        self.scraper_list = QListWidget()
        self.scraper_list.itemSelectionChanged.connect(self.on_scraper_selected)
        self.scraper_list.itemDoubleClicked.connect(self.edit_selected_scraper)
        layout.addWidget(self.scraper_list)

        # Status label
        self.status_label = QLabel("No scrapers loaded")
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(self.status_label)

        return panel

    def create_details_panel(self):
        """Create the scraper details panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Scraper Details")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.details_text)

        # Placeholder text
        self.details_text.setPlainText("Select a scraper to view its configuration details.")

        return panel

    def load_scrapers(self):
        """Load all scraper configurations."""
        self.scraper_list.clear()
        self.scraper_configs: dict[str, dict[str, Any]] = {}

        try:
            # Find all YAML files in configs directory
            config_files = list(self.scrapers_dir.glob("*.yaml"))

            if not config_files:
                self.status_label.setText(
                    "No scraper configurations found. Click 'Build New Scraper' to create one."
                )
                self.details_text.setPlainText(
                    "No scrapers available. Create your first scraper configuration."
                )
                return

            for config_file in config_files:
                try:
                    config = self.parser.load_from_file(config_file)
                    self.scraper_configs[config.name] = {
                        "config": config,
                        "file_path": config_file,
                    }

                    # Add to list
                    item = QListWidgetItem(f"📄 {config.name}")
                    item.setToolTip(
                        f"Base URL: {config.base_url}\nTimeout: {config.timeout}s\n"
                        f"Retries: {config.retries}"
                    )
                    self.scraper_list.addItem(item)

                except Exception as e:
                    # Add error item
                    item = QListWidgetItem(f"❌ {config_file.stem} (Error: {e!s})")
                    item.setToolTip(f"Failed to load: {e!s}")
                    self.scraper_list.addItem(item)

            count = len(self.scraper_configs)
            self.status_label.setText(
                f"Loaded {count} scraper configuration{'s' if count != 1 else ''}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load scrapers: {e!s}")
            self.status_label.setText("Error loading scrapers")

    def on_scraper_selected(self):
        """Handle scraper selection change."""
        selected_items = self.scraper_list.selectedItems()
        has_selection = len(selected_items) > 0

        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

        if has_selection:
            scraper_name = selected_items[0].text().replace("📄 ", "").replace("❌ ", "")
            self.show_scraper_details(scraper_name)
        else:
            self.details_text.setPlainText("Select a scraper to view its configuration details.")

    def show_scraper_details(self, scraper_name):
        """Show details for the selected scraper."""
        if scraper_name not in self.scraper_configs:
            self.details_text.setPlainText(
                f"Configuration for '{scraper_name}' could not be loaded."
            )
            return

        config_data = self.scraper_configs[scraper_name]
        config: ScraperConfig = config_data["config"]
        file_path = config_data["file_path"]

        # Build details text
        separator = "=" * 50
        details = f"""
Scraper Configuration: {config.name}
{separator}

📁 File: {file_path}
🌐 Base URL: {config.base_url}
⏱️  Timeout: {config.timeout} seconds
🔄 Retries: {config.retries}

📋 Selectors ({len(config.selectors)}):
"""

        for selector in config.selectors:
            details += f"  • {selector.name}: '{selector.selector}'"
            if selector.attribute:
                details += f" → {selector.attribute}"
            if selector.multiple:
                details += " (multiple)"
            details += "\n"

        details += f"\n⚙️ Workflows ({len(config.workflows)}):\n"
        for i, workflow in enumerate(config.workflows, 1):
            details += f"  {i}. {workflow.action}: {workflow.params}\n"

        if config.login is not None:
            details += "\n🔐 Login Configuration:\n"
            details += f"  URL: {config.login.url}\n"
            details += f"  Username field: {config.login.username_field}\n"
            details += f"  Password field: {config.login.password_field}\n"
            details += f"  Submit button: {config.login.submit_button}\n"
            if config.login.success_indicator:
                details += f"  Success indicator: {config.login.success_indicator}\n"

        self.details_text.setPlainText(details)

    def build_scraper(self):
        """Open the AI Scraper Builder Wizard."""
        dialog = ScraperBuilderDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_scrapers()  # Refresh the list

    def edit_selected_scraper(self):
        """Edit the selected scraper."""
        selected_items = self.scraper_list.selectedItems()
        if not selected_items:
            return

        scraper_name = selected_items[0].text().replace("📄 ", "").replace("❌ ", "")
        if scraper_name not in self.scraper_configs:
            QMessageBox.warning(
                self,
                "Error",
                f"Cannot edit '{scraper_name}': configuration not loaded.",
            )
            return

        config_data = self.scraper_configs[scraper_name]
        dialog = EditScraperDialog(config_data["config"], config_data["file_path"], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_scrapers()  # Refresh the list

    def delete_selected_scraper(self):
        """Delete the selected scraper."""
        selected_items = self.scraper_list.selectedItems()
        if not selected_items:
            return

        scraper_name = selected_items[0].text().replace("📄 ", "").replace("❌ ", "")

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the scraper '{scraper_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if scraper_name in self.scraper_configs:
                    file_path = self.scraper_configs[scraper_name]["file_path"]
                    os.remove(file_path)
                    QMessageBox.information(
                        self, "Success", f"Scraper '{scraper_name}' has been deleted."
                    )
                    self.load_scrapers()  # Refresh the list
                else:
                    QMessageBox.warning(self, "Error", f"Scraper '{scraper_name}' not found.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete scraper: {e!s}")