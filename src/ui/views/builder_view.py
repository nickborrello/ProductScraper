import json
import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.scrapers.models.config import ScraperConfig
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.ui.scraper_builder_dialog import ScraperBuilderDialog
from src.ui.scraper_management_dialog import EditScraperDialog


class InfoCard(QFrame):
    """A simple styled information card."""

    def __init__(self, title: str, content: str | list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setStyleSheet("""
            InfoCard {
                background-color: #252525;
                border: 1px solid #333333;
                border-radius: 5px;
            }
            QLabel.title {
                font-weight: bold;
                color: #3B8ED0;
                font-size: 14px;
            }
            QLabel.label {
                color: #B0B0B0;
                font-weight: bold;
            }
            QLabel.value {
                color: #E0E0E0;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "title")
        layout.addWidget(title_lbl)

        # Content
        if isinstance(content, str):
            content_lbl = QLabel(content)
            content_lbl.setProperty("class", "value")
            content_lbl.setWordWrap(True)
            layout.addWidget(content_lbl)
        elif isinstance(content, list):
            # Grid of label-value pairs
            grid = QFormLayout()
            grid.setSpacing(5)
            for label, value in content:
                l_widget = QLabel(f"{label}:")
                l_widget.setProperty("class", "label")
                v_widget = QLabel(str(value))
                v_widget.setProperty("class", "value")
                v_widget.setWordWrap(True)
                grid.addRow(l_widget, v_widget)
            layout.addLayout(grid)


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

        # Scroll area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container for cards
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setSpacing(15)
        self.details_layout.setContentsMargins(5, 5, 5, 5)
        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.details_container)
        layout.addWidget(scroll)

        # Show initial placeholder
        self.show_placeholder()

        return panel

    def show_placeholder(self):
        """Show the placeholder text in the details panel."""
        self.clear_details()
        placeholder = QLabel("Select a scraper to view its configuration details.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-size: 14px; margin-top: 50px;")
        self.details_layout.addWidget(placeholder)

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
            # Show placeholder
            self.show_placeholder()

    def clear_details(self):
        """Clear the details container."""
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

    def show_scraper_details(self, scraper_name):
        """Show details for the selected scraper as cards."""
        if scraper_name not in self.scraper_configs:
            self.clear_details()
            error_lbl = QLabel(f"Configuration for '{scraper_name}' could not be loaded.")
            error_lbl.setStyleSheet("color: red;")
            self.details_layout.addWidget(error_lbl)
            return

        config_data = self.scraper_configs[scraper_name]
        config: ScraperConfig = config_data["config"]
        file_path = config_data["file_path"]

        self.clear_details()

        # 1. General Info Card
        general_info = [
            ("File", str(file_path.name)),
            ("Base URL", config.base_url),
            ("Timeout", f"{config.timeout}s"),
            ("Retries", str(config.retries)),
        ]
        self.details_layout.addWidget(InfoCard("General Settings", general_info))

        # 2. Selectors Card
        selectors_info = []
        for sel in config.selectors:
            info = f"'{sel.selector}'"
            if sel.attribute:
                info += f" → {sel.attribute}"
            if sel.multiple:
                info += " [Multi]"
            selectors_info.append((sel.name, info))

        if not selectors_info:
            selectors_info = [("None", "No selectors defined")]

        self.details_layout.addWidget(
            InfoCard(f"Selectors ({len(config.selectors)})", selectors_info)
        )

        # 3. Workflows Card
        workflows_info = []
        for i, step in enumerate(config.workflows, 1):
            # Format params nicely
            param_str = json.dumps(step.params)
            if len(param_str) > 50:
                param_str = param_str[:47] + "..."
            workflows_info.append((f"Step {i} ({step.action.upper()})", param_str))

        if not workflows_info:
            workflows_info = [("None", "No workflow steps defined")]

        self.details_layout.addWidget(
            InfoCard(f"Workflow Steps ({len(config.workflows)})", workflows_info)
        )

        # 4. Login Card (if exists)
        if config.login:
            login_info = [
                ("URL", config.login.url),
                ("User Field", config.login.username_field),
                ("Pass Field", config.login.password_field),
                ("Submit Btn", config.login.submit_button),
            ]
            self.details_layout.addWidget(InfoCard("Login Configuration", login_info))

        self.details_layout.addStretch()

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
            self.show_scraper_details(scraper_name)  # Refresh details view

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
                    self.show_placeholder()
                else:
                    QMessageBox.warning(self, "Error", f"Scraper '{scraper_name}' not found.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete scraper: {e!s}")
