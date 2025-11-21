import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
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
from src.ui.styling import STYLESHEET


class ScraperManagementDialog(QDialog):
    """Dialog for managing scraper configurations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scraper Management")
        self.setMinimumSize(1000, 700)
        self.parser = ScraperConfigParser()
        self.scrapers_dir = Path("src/scrapers/configs")
        self.scrapers_dir.mkdir(exist_ok=True)

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()
        self.load_scrapers()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Scraper Management")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Scraper list
        left_panel = self.create_scraper_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - Scraper details
        right_panel = self.create_details_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

        # Bottom buttons
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("+ Add New Scraper")
        self.add_btn.clicked.connect(self.add_scraper)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected_scraper)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected_scraper)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_scrapers)
        buttons_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("❌ Close")
        self.close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

    def create_scraper_list_panel(self):
        """Create the scraper list panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

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

        # Header
        header = QLabel("Scraper Details")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 9))
        # Dark theme styling is handled by global stylesheet
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
                    "No scraper configurations found. Click 'Add New Scraper' to create one."
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
        details = f"""Scraper Configuration: {config.name}
{"=" * 50}

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

    def add_scraper(self):
        """Open dialog to add a new scraper."""
        dialog = AddScraperDialog(self)
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


class AddScraperDialog(QDialog):
    """Dialog for creating a new scraper configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Scraper")
        self.setMinimumSize(600, 400)
        self.parser = ScraperConfigParser()

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Create New Scraper Configuration")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Create a new scraper configuration. You can start with the sample configuration "
            "and modify it, or create one from scratch."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888888;")
        layout.addWidget(instructions)

        # Options
        options_layout = QVBoxLayout()

        self.from_sample_btn = QPushButton("📋 Start from Sample Configuration")
        self.from_sample_btn.setMinimumHeight(40)
        self.from_sample_btn.clicked.connect(self.create_from_sample)
        options_layout.addWidget(self.from_sample_btn)

        self.from_scratch_btn = QPushButton("✏️ Create from Scratch")
        self.from_scratch_btn.setMinimumHeight(40)
        self.from_scratch_btn.clicked.connect(self.create_from_scratch)
        options_layout.addWidget(self.from_scratch_btn)

        layout.addLayout(options_layout)
        layout.addStretch()

        # Bottom buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def create_from_sample(self):
        """Create a new scraper from the sample configuration."""
        try:
            # Load sample config
            sample_path = Path("src/scrapers/config/sample_config.yaml")
            sample_config = self.parser.load_from_file(sample_path)

            # Ask for new name
            new_name, ok = QInputDialog.getText(
                self,
                "Scraper Name",
                "Enter a name for the new scraper:",
                text=sample_config.name + " Copy",
            )

            if not ok or not new_name.strip():
                return

            # Update config with new name
            sample_config.name = new_name.strip()

            # Ask for filename
            filename = f"{new_name.lower().replace(' ', '_')}.yaml"
            file_path = Path("src/scrapers/configs") / filename

            # Save the new config
            self.parser.save_to_file(sample_config, file_path)

            QMessageBox.information(
                self,
                "Success",
                f"New scraper '{new_name}' has been created!\n\nFile: {file_path}",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create scraper from sample: {e!s}")

    def create_from_scratch(self):
        """Create a new scraper from scratch."""
        # For now, just create from sample but with empty fields
        try:
            # Create minimal config
            config = ScraperConfig(
                name="New Scraper",
                base_url="https://example.com",
                selectors=[],
                workflows=[],
                login=None,
                timeout=30,
                retries=3,
                anti_detection=None,
                http_status=None,
                validation=None,
                test_skus=None,
            )

            # Ask for name
            name, ok = QInputDialog.getText(
                self,
                "Scraper Name",
                "Enter a name for the new scraper:",
                text="New Scraper",
            )

            if not ok or not name.strip():
                return

            config.name = name.strip()

            # Save
            filename = f"{name.lower().replace(' ', '_')}.yaml"
            file_path = Path("src/scrapers/configs") / filename
            self.parser.save_to_file(config, file_path)

            QMessageBox.information(
                self,
                "Success",
                f"New scraper '{name}' has been created!\n\nFile: {file_path}\n\n"
                "You can now edit it to add selectors and workflows.",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create scraper: {e!s}")


class EditScraperDialog(QDialog):
    """Dialog for editing an existing scraper configuration."""

    def __init__(self, config: ScraperConfig, file_path, parent=None):
        super().__init__(parent)
        self.config = config
        self.file_path = file_path
        self.parser = ScraperConfigParser()

        self.setWindowTitle(f"Edit Scraper: {config.name}")
        self.setMinimumSize(800, 600)

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"Edit Scraper: {self.config.name}")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # YAML Editor
        editor_group = QGroupBox("Configuration (YAML)")
        editor_layout = QVBoxLayout(editor_group)

        self.yaml_editor = QTextEdit()
        self.yaml_editor.setFont(QFont("Consolas", 10))
        # Dark theme styling is handled by global stylesheet

        # Load current config as YAML
        try:
            yaml_content = yaml.safe_dump(
                self.config.model_dump(), default_flow_style=False, sort_keys=False
            )
            self.yaml_editor.setPlainText(yaml_content)
        except Exception as e:
            self.yaml_editor.setPlainText(f"Error loading YAML: {e!s}")

        editor_layout.addWidget(self.yaml_editor)
        layout.addWidget(editor_group)

        # Bottom buttons
        buttons_layout = QHBoxLayout()

        self.validate_btn = QPushButton("✅ Validate")
        self.validate_btn.clicked.connect(self.validate_config)
        buttons_layout.addWidget(self.validate_btn)

        buttons_layout.addStretch()

        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        buttons_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

    def validate_config(self):
        """Validate the current YAML configuration."""
        try:
            yaml_text = self.yaml_editor.toPlainText()
            config = self.parser.load_from_string(yaml_text)
            QMessageBox.information(
                self,
                "Validation Success",
                "✅ Configuration is valid!\n\n"
                f"Scraper: {config.name}\n"
                f"Base URL: {config.base_url}\n"
                f"Selectors: {len(config.selectors)}\n"
                f"Workflows: {len(config.workflows)}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Validation Error", f"❌ Configuration is invalid:\n\n{e!s}")

    def save_changes(self):
        """Save the changes to the configuration file."""
        try:
            yaml_text = self.yaml_editor.toPlainText()
            config = self.parser.load_from_string(yaml_text)

            # Save to file
            self.parser.save_to_file(config, self.file_path)

            QMessageBox.information(
                self,
                "Success",
                f"✅ Scraper '{config.name}' has been updated successfully!",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"❌ Failed to save configuration:\n\n{e!s}")
