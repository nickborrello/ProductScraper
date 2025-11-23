import json
import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.scrapers.models.config import ScraperConfig, SelectorConfig, WorkflowStep
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


class WorkflowStepCard(QFrame):
    """A visual card representing a workflow step."""

    edit_clicked = pyqtSignal(object)  # Emits self
    delete_clicked = pyqtSignal(object)  # Emits self

    def __init__(self, step: WorkflowStep, index: int, parent=None):
        super().__init__(parent)
        self.step = step
        self.index = index
        self.setProperty("class", "card")  # Use style class if defined
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            WorkflowStepCard {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-bottom: 5px;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Action Name (Left)
        action_label = QLabel(f"<b>{self.step.action.upper()}</b>")
        action_label.setFixedWidth(120)
        layout.addWidget(action_label)

        # Parameters (Middle)
        params_str = json.dumps(self.step.params)
        # Truncate if too long
        if len(params_str) > 60:
            params_str = params_str[:57] + "..."

        params_label = QLabel(params_str)
        params_label.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(params_label, 1)  # Stretch to fill space

        # Buttons (Right)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        edit_btn = QPushButton("✏️")
        edit_btn.setFixedSize(30, 30)
        edit_btn.setToolTip("Edit Step")
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self))
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setToolTip("Delete Step")
        delete_btn.setProperty("class", "danger")  # if supported
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self))
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)


class EditScraperDialog(QDialog):
    """Dialog for editing an existing scraper configuration."""

    def __init__(self, config: ScraperConfig, file_path, parent=None):
        super().__init__(parent)
        self.config = config
        self.file_path = file_path
        self.parser = ScraperConfigParser()

        self.setWindowTitle(f"Edit Scraper: {config.name}")
        self.setMinimumSize(900, 700)

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # General Settings Tab
        self.tab_widget.addTab(self.create_general_tab(), "General Settings")

        # Selectors Tab
        self.tab_widget.addTab(self.create_selectors_tab(), "Selectors")

        # Workflows Tab
        self.tab_widget.addTab(self.create_workflows_tab(), "Workflows")

        # Raw YAML Tab
        self.tab_widget.addTab(self.create_yaml_tab(), "Raw YAML")

        # Bottom buttons
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setProperty("class", "primary")
        buttons_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setProperty("class", "secondary")
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

    def create_general_tab(self):
        """Create the general settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Scraper Name
        self.name_edit = QLineEdit(self.config.name)
        layout.addRow("Scraper Name:", self.name_edit)

        # Base URL
        self.url_edit = QLineEdit(self.config.base_url)
        layout.addRow("Base URL:", self.url_edit)

        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(self.config.timeout)
        self.timeout_spin.setSuffix(" seconds")
        layout.addRow("Timeout:", self.timeout_spin)

        # Retries
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(self.config.retries)
        layout.addRow("Max Retries:", self.retries_spin)

        return tab

    def create_selectors_tab(self):
        """Create the selectors management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table
        self.selectors_table = QTableWidget()
        self.selectors_table.setColumnCount(4)
        self.selectors_table.setHorizontalHeaderLabels(
            ["Name", "Selector", "Attribute", "Multiple"]
        )
        header = self.selectors_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 150)
        header.resizeSection(2, 100)
        header.resizeSection(3, 80)

        # Populate table
        for selector in self.config.selectors:
            self.add_selector_row(selector)

        layout.addWidget(self.selectors_table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_selector_btn = QPushButton("+ Add Selector")
        self.add_selector_btn.clicked.connect(lambda: self.add_selector_row())
        btn_layout.addWidget(self.add_selector_btn)

        self.remove_selector_btn = QPushButton("- Remove Selected")
        self.remove_selector_btn.clicked.connect(self.remove_selected_selector)
        btn_layout.addWidget(self.remove_selector_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return tab

    def add_selector_row(self, selector_config: SelectorConfig | None = None):
        """Add a row to the selectors table."""
        row = self.selectors_table.rowCount()
        self.selectors_table.insertRow(row)

        # Name
        name_item = QTableWidgetItem(selector_config.name if selector_config else "new_field")
        self.selectors_table.setItem(row, 0, name_item)

        # Selector
        # Handle list or string for selector
        sel_text = ""
        if selector_config:
            if isinstance(selector_config.selector, list):
                sel_text = selector_config.selector[0] if selector_config.selector else ""
            else:
                sel_text = str(selector_config.selector)

        selector_item = QTableWidgetItem(sel_text)
        self.selectors_table.setItem(row, 1, selector_item)

        # Attribute
        attr_text = (
            selector_config.attribute if selector_config and selector_config.attribute else "text"
        )
        attr_item = QTableWidgetItem(attr_text)
        self.selectors_table.setItem(row, 2, attr_item)

        # Multiple (Checkbox)
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = QCheckBox()
        if selector_config:
            checkbox.setChecked(selector_config.multiple)
        chk_layout.addWidget(checkbox)
        self.selectors_table.setCellWidget(row, 3, chk_widget)

    def remove_selected_selector(self):
        """Remove selected rows from the selectors table."""
        rows = sorted(
            set(index.row() for index in self.selectors_table.selectedIndexes()), reverse=True
        )
        for row in rows:
            self.selectors_table.removeRow(row)

    def create_workflows_tab(self):
        """Create the workflow management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Scroll Area for Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Container for the card layout
        self.workflow_container = QWidget()
        self.workflow_layout = QVBoxLayout(self.workflow_container)
        self.workflow_layout.setSpacing(10)
        self.workflow_layout.setContentsMargins(10, 10, 10, 10)
        self.workflow_layout.addStretch()  # Push cards to top

        scroll.setWidget(self.workflow_container)
        layout.addWidget(scroll)

        # Initial population
        self.refresh_workflow_list()

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_step_btn = QPushButton("+ Add Step")
        self.add_step_btn.clicked.connect(self.add_workflow_step)
        self.add_step_btn.setProperty("class", "success")
        btn_layout.addWidget(self.add_step_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return tab

    def refresh_workflow_list(self):
        """Re-render the workflow list as cards."""
        # Clear existing items (except the stretch at the end)
        # Note: takeAt(0) removes from start.
        # We need to be careful not to remove the stretch if we want to keep it,
        # or just re-add it. Re-adding is easier.

        # Clear everything
        while self.workflow_layout.count():
            item = self.workflow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-populate
        for i, step in enumerate(self.config.workflows):
            card = WorkflowStepCard(step, i)
            card.edit_clicked.connect(self.edit_workflow_step_card)
            card.delete_clicked.connect(self.delete_workflow_step_card)
            self.workflow_layout.addWidget(card)

        self.workflow_layout.addStretch()

    def add_workflow_step(self):
        """Add a new workflow step."""
        actions = [
            "navigate",
            "wait",
            "click",
            "input_text",
            "extract_single",
            "extract_multiple",
            "scroll",
        ]
        action, ok = QInputDialog.getItem(
            self, "Select Action", "Choose an action:", actions, 0, False
        )
        if ok and action:
            # Create a basic step
            params = {}
            if action == "navigate":
                params = {"url": "https://example.com"}
            elif action == "wait":
                params = {"timeout": 5}
            elif action == "click" or action == "input_text":
                params = {"selector": ""}
            elif action.startswith("extract"):
                params = {"field": "", "selector": ""}

            step = WorkflowStep(action=action, params=params)
            self.config.workflows.append(step)
            self.refresh_workflow_list()

            # Auto-open edit dialog for the new step
            self.edit_workflow_step_card(
                self.workflow_layout.itemAt(self.workflow_layout.count() - 2).widget()
            )

    def edit_workflow_step_card(self, card: WorkflowStepCard):
        """Edit the workflow step associated with the card."""
        step = card.step
        import json

        current_params = json.dumps(step.params)
        new_params_str, ok = QInputDialog.getText(
            self,
            f"Edit {step.action}",
            "Parameters (JSON):",
            QLineEdit.EchoMode.Normal,
            current_params,
        )

        if ok:
            try:
                new_params = json.loads(new_params_str)
                step.params = new_params
                self.refresh_workflow_list()  # Refresh to show updated params
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Error", "Invalid JSON format for parameters.")

    def delete_workflow_step_card(self, card: WorkflowStepCard):
        """Remove the workflow step associated with the card."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete this '{card.step.action}' step?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config.workflows.pop(card.index)
            self.refresh_workflow_list()

    def create_yaml_tab(self):
        """Create the raw YAML editor tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.yaml_editor = QTextEdit()
        self.yaml_editor.setFont(QFont("Consolas", 10))

        # Load initial YAML
        self.update_yaml_from_config()

        layout.addWidget(self.yaml_editor)

        # Add a button to update UI from YAML (bi-directional sync)
        sync_btn = QPushButton("Update UI from YAML")
        sync_btn.clicked.connect(self.update_config_from_yaml)
        layout.addWidget(sync_btn)

        return tab

    def update_yaml_from_config(self):
        """Generate YAML from current config object and set to editor."""
        try:
            # Use Pydantic's model_dump() to serialize everything, including nested models
            config_dict = self.config.model_dump()

            yaml_content = yaml.safe_dump(config_dict, default_flow_style=False, sort_keys=False)
            self.yaml_editor.setPlainText(yaml_content)
        except Exception as e:
            self.yaml_editor.setPlainText(f"Error generating YAML: {e!s}")

    def update_config_from_yaml(self):
        """Parse YAML editor content and update the config object and UI."""
        try:
            yaml_text = self.yaml_editor.toPlainText()
            new_config = self.parser.load_from_string(yaml_text)

            # Update internal config
            self.config = new_config

            # Refresh UI elements
            self.name_edit.setText(self.config.name)
            self.url_edit.setText(self.config.base_url)
            self.timeout_spin.setValue(self.config.timeout)
            self.retries_spin.setValue(self.config.retries)

            # Refresh Selectors
            self.selectors_table.setRowCount(0)
            for selector in self.config.selectors:
                self.add_selector_row(selector)

            # Refresh Workflows
            self.refresh_workflow_list()

            QMessageBox.information(self, "Success", "UI updated from YAML content.")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to parse YAML: {e}")

    def get_updated_config(self) -> ScraperConfig:
        """Construct a new ScraperConfig object from the UI state."""
        # 1. General Settings
        name = self.name_edit.text().strip()
        base_url = self.url_edit.text().strip()
        timeout = self.timeout_spin.value()
        retries = self.retries_spin.value()

        # 2. Selectors
        selectors = []
        for row in range(self.selectors_table.rowCount()):
            name_item = self.selectors_table.item(row, 0)
            sel_item = self.selectors_table.item(row, 1)
            attr_item = self.selectors_table.item(row, 2)
            chk_widget = self.selectors_table.cellWidget(row, 3)

            if name_item and sel_item:
                # Get checkbox state
                is_multiple = False
                if chk_widget:
                    # Find the checkbox inside the layout
                    checkbox = chk_widget.findChild(QCheckBox)
                    if checkbox:
                        is_multiple = checkbox.isChecked()

                selectors.append(
                    SelectorConfig(
                        name=name_item.text(),
                        selector=sel_item.text(),
                        attribute=attr_item.text() if attr_item else "text",
                        multiple=is_multiple,
                    )
                )

        # 3. Workflows - self.config.workflows is maintained live by the card actions
        workflows = self.config.workflows

        # Create new config (preserving other fields like login/anti_detection from original)
        return ScraperConfig(
            name=name,
            base_url=base_url,
            selectors=selectors,
            workflows=workflows,
            login=self.config.login,
            timeout=timeout,
            retries=retries,
            anti_detection=self.config.anti_detection,
            http_status=self.config.http_status,
            validation=self.config.validation,
            test_skus=self.config.test_skus,
            normalization=self.config.normalization,
        )

    def save_changes(self):
        """Save the changes to the configuration file."""
        try:
            # Check if user was editing raw YAML last
            if self.tab_widget.currentIndex() == 3:  # Raw YAML tab
                # Optional: prompt to sync? or just trust get_updated_config?
                # For safety, let's prioritize the UI state unless user explicitly synced.
                pass

            new_config = self.get_updated_config()

            # Save to file
            self.parser.save_to_file(new_config, self.file_path)

            QMessageBox.information(
                self,
                "Success",
                f"✅ Scraper '{new_config.name}' has been updated successfully!",
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"❌ Failed to save configuration:\n\n{e!s}")
