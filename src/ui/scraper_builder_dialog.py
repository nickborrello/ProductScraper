"""
Scraper Builder Dialog - AI-assisted scraper creation.

This dialog provides a simple interface for building scrapers with AI assistance
for CSS selector generation, testing, and YAML configuration creation.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, cast, TYPE_CHECKING
from urllib.parse import urlparse
import yaml

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QCheckBox,
    QComboBox,
    QTabWidget,
    QDialogButtonBox,
    QWidget,
    QWizard,
    QWizardPage,
)

from src.scrapers.selector_storage import SelectorManager
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.scrapers.models.config import ScraperConfig, SelectorConfig, WorkflowStep
from src.ui.visual_selector_picker import VisualSelectorPicker
from src.ui.styling import STYLESHEET

if TYPE_CHECKING:
    from src.core.classification.llm_classifier import LLMProductClassifier

try:
    from src.core.classification.llm_classifier import get_llm_classifier  # type: ignore
except ImportError:
    def get_llm_classifier(model_name=None, product_taxonomy=None, product_pages=None) -> Optional['LLMProductClassifier']:  # type: ignore
        return None


# Helper functions for wizard data management
def set_wizard_data(key: str, value):
    """Set wizard data (to be called from wizard pages)."""
    # This will be set on the wizard instance
    pass

def get_wizard_data(key: str, default=None):
    """Get wizard data (to be called from wizard pages)."""
    # This will be accessed from the wizard instance
    return default


class UrlInputPage(QWizardPage):
    """First page: URL input and page loading."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 1: Enter URL")
        self.setSubTitle("Enter the URL of the product page you want to scrape")
        self.setup_ui()

    @property
    def typed_wizard(self) -> 'ScraperBuilderDialog':
        """Get the wizard cast to the correct type."""
        return cast('ScraperBuilderDialog', self.wizard())

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Product Page URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/product/123")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Load button
        self.load_btn = QPushButton("🔗 Load Page")
        self.load_btn.clicked.connect(self.load_page)
        layout.addWidget(self.load_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Page content preview
        content_group = QGroupBox("Page Content Preview")
        content_layout = QVBoxLayout(content_group)

        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setFont(QFont("Consolas", 9))
        self.content_preview.setPlainText("Load a page to see its content...")
        content_layout.addWidget(self.content_preview)

        layout.addWidget(content_group)

        # Register fields
        self.registerField("url*", self.url_input)

    def load_page(self):
        """Load the page content using HTTP request."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL first.")
            return

        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_input.setText(url)

        self.load_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start loading in background
        self.load_thread = PageLoadThread(url)
        self.load_thread.finished.connect(self.on_page_loaded)
        self.load_thread.error.connect(self.on_load_error)
        self.load_thread.start()

    def on_page_loaded(self, content: str):
        """Handle successful page loading."""
        self.load_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Store content for next steps
        self.typed_wizard.set_wizard_data('page_content', content)

        # Show preview (first 2000 chars)
        preview = content[:2000]
        if len(content) > 2000:
            preview += "\n\n[... content truncated ...]"
        self.content_preview.setPlainText(preview)

        # Enable next button
        self.completeChanged.emit()

    def on_load_error(self, error_msg: str):
        """Handle page loading error."""
        self.load_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Failed to load page: {error_msg}")

    def isComplete(self):
        """Check if page is complete."""
        return (
            super().isComplete() and
            self.typed_wizard.get_wizard_data('page_content') is not None
        )


class SelectorGenerationPage(QWizardPage):
    """Second page: Selector generation with AI and visual picker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 2: Generate Selectors")
        self.setSubTitle("Use AI analysis or visually select elements to generate CSS selectors")
        self.setup_ui()

    @property
    def typed_wizard(self) -> 'ScraperBuilderDialog':
        """Get the wizard cast to the correct type."""
        return cast('ScraperBuilderDialog', self.wizard())

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Tab widget for different selector generation methods
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # AI Generation Tab
        self.setup_ai_tab()

        # Visual Picker Tab
        self.setup_visual_tab()

        # Selectors table (shared between tabs)
        selectors_group = QGroupBox("Generated Selectors")
        selectors_layout = QVBoxLayout(selectors_group)

        self.selectors_table = QTableWidget()
        self.selectors_table.setColumnCount(4)
        self.selectors_table.setHorizontalHeaderLabels(["Field", "Selector", "Attribute", "Source"])
        self.selectors_table.horizontalHeader().setStretchLastSection(True)  # type: ignore
        self.selectors_table.setAlternatingRowColors(True)
        selectors_layout.addWidget(self.selectors_table)

        # Clear selectors button
        clear_layout = QHBoxLayout()
        clear_layout.addStretch()
        self.clear_selectors_btn = QPushButton("🗑️ Clear All")
        self.clear_selectors_btn.clicked.connect(self.clear_all_selectors)
        clear_layout.addWidget(self.clear_selectors_btn)
        selectors_layout.addLayout(clear_layout)

        layout.addWidget(selectors_group)

        # Manual selector addition
        manual_group = QGroupBox("Add Manual Selector")
        manual_layout = QHBoxLayout(manual_group)

        self.field_combo = QComboBox()
        self.field_combo.addItems([
            "product_name", "price", "description", "image_urls",
            "sku", "brand", "availability", "rating", "specifications"
        ])
        manual_layout.addWidget(QLabel("Field:"))
        manual_layout.addWidget(self.field_combo)

        self.selector_input = QLineEdit()
        self.selector_input.setPlaceholderText(".product-title")
        manual_layout.addWidget(QLabel("Selector:"))
        manual_layout.addWidget(self.selector_input)

        self.attr_combo = QComboBox()
        self.attr_combo.addItems(["text", "src", "href", "content", "value", "alt"])
        manual_layout.addWidget(QLabel("Attribute:"))
        manual_layout.addWidget(self.attr_combo)

        self.add_selector_btn = QPushButton("➕ Add")
        self.add_selector_btn.clicked.connect(self.add_manual_selector)
        manual_layout.addWidget(self.add_selector_btn)

        layout.addWidget(manual_group)

    def setup_ai_tab(self):
        """Setup the AI generation tab."""
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)

        # Generate button
        self.generate_btn = QPushButton("🤖 Generate Selectors with AI")
        self.generate_btn.clicked.connect(self.generate_selectors)
        ai_layout.addWidget(self.generate_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        ai_layout.addWidget(self.progress_bar)

        self.tab_widget.addTab(ai_widget, "🤖 AI Generation")

    def setup_visual_tab(self):
        """Setup the visual picker tab."""
        visual_widget = QWidget()
        visual_layout = QVBoxLayout(visual_widget)

        # Visual selector picker
        self.visual_picker = VisualSelectorPicker()
        self.visual_picker.selector_selected.connect(self.on_visual_selector_selected)
        self.visual_picker.page_loaded.connect(self.on_visual_page_loaded)

        # Set URL from previous page if available
        try:
            url = self.typed_wizard.field("url")
            if url:
                self.visual_picker.set_url(url)
        except:
            pass

        visual_layout.addWidget(self.visual_picker)

        self.tab_widget.addTab(visual_widget, "🎯 Visual Picker")

    def generate_selectors(self):
        """Generate selectors using AI."""
        page_content = self.typed_wizard.get_wizard_data('page_content')
        if not page_content:
            QMessageBox.warning(self, "Error", "No page content available. Please go back and load a page first.")
            return

        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Start AI generation in background
        self.ai_thread = SelectorGenerationThread(page_content)
        self.ai_thread.finished.connect(self.on_selectors_generated)
        self.ai_thread.error.connect(self.on_generation_error)
        self.ai_thread.start()

    def on_selectors_generated(self, selectors: Dict[str, Dict[str, Any]]):
        """Handle successful selector generation."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Store selectors with source information
        for field_name, selector_info in list(selectors.items()):
            if not isinstance(selector_info, dict):
                selectors[field_name] = {}
                selector_info = selectors[field_name]
            selector_info['source'] = 'ai'
        self.typed_wizard.set_wizard_data('suggested_selectors', selectors)

        # Populate table
        self.selectors_table.setRowCount(len(selectors))
        for row, (field_name, selector_info) in enumerate(selectors.items()):
            # Field name
            field_item = QTableWidgetItem(field_name)
            field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.selectors_table.setItem(row, 0, field_item)

            # Selector
            selector_item = QTableWidgetItem(selector_info.get('selector', ''))
            self.selectors_table.setItem(row, 1, selector_item)

            # Attribute
            attr_item = QTableWidgetItem(selector_info.get('attribute', 'text'))
            self.selectors_table.setItem(row, 2, attr_item)

            # Source
            source_item = QTableWidgetItem("🤖 AI")
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.selectors_table.setItem(row, 3, source_item)

        # Enable next button
        self.completeChanged.emit()

    def on_generation_error(self, error_msg: str):
        """Handle selector generation error."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Failed to generate selectors: {error_msg}")

    def add_manual_selector(self):
        """Add a manual selector to the table."""
        field = self.field_combo.currentText()
        selector = self.selector_input.text().strip()
        attribute = self.attr_combo.currentText()

        if not selector:
            QMessageBox.warning(self, "Error", "Please enter a selector.")
            return

        # Add to table
        row_count = self.selectors_table.rowCount()
        self.selectors_table.insertRow(row_count)

        field_item = QTableWidgetItem(field)
        field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.selectors_table.setItem(row_count, 0, field_item)

        selector_item = QTableWidgetItem(selector)
        self.selectors_table.setItem(row_count, 1, selector_item)

        attr_item = QTableWidgetItem(attribute)
        self.selectors_table.setItem(row_count, 2, attr_item)

        source_item = QTableWidgetItem("📝 Manual")
        source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.selectors_table.setItem(row_count, 3, source_item)

        # Clear inputs
        self.selector_input.clear()

        # Update wizard data
        suggested_selectors = self.typed_wizard.get_wizard_data('suggested_selectors', {}) or {}
        suggested_selectors[field] = {
            'selector': selector,
            'attribute': attribute,
            'source': 'manual'
        }
        self.typed_wizard.set_wizard_data('suggested_selectors', suggested_selectors)

        self.completeChanged.emit()

    def get_selectors(self) -> Dict[str, Dict[str, Any]]:
        """Get all selectors from the table."""
        selectors = {}
        for row in range(self.selectors_table.rowCount()):
            field_item = self.selectors_table.item(row, 0)
            selector_item = self.selectors_table.item(row, 1)
            attr_item = self.selectors_table.item(row, 2)

            if field_item and selector_item and attr_item:
                field = field_item.text()
                selector = selector_item.text()
                attribute = attr_item.text()

                if selector.strip():
                    selectors[field] = {
                        'selector': selector,
                        'attribute': attribute
                    }

        return selectors

    def on_visual_selector_selected(self, selector: str, attribute: str, field_name: str):
        """Handle selector selection from visual picker."""
        # Add to table
        row_count = self.selectors_table.rowCount()
        self.selectors_table.insertRow(row_count)

        field_item = QTableWidgetItem(field_name)
        field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.selectors_table.setItem(row_count, 0, field_item)

        selector_item = QTableWidgetItem(selector)
        self.selectors_table.setItem(row_count, 1, selector_item)

        attr_item = QTableWidgetItem(attribute)
        self.selectors_table.setItem(row_count, 2, attr_item)

        source_item = QTableWidgetItem("🎯 Visual")
        source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.selectors_table.setItem(row_count, 3, source_item)

        # Update wizard data
        suggested_selectors = self.typed_wizard.get_wizard_data('suggested_selectors', {}) or {}
        suggested_selectors[field_name] = {
            'selector': selector,
            'attribute': attribute,
            'source': 'visual'
        }
        self.typed_wizard.set_wizard_data('suggested_selectors', suggested_selectors)

        self.completeChanged.emit()

    def on_visual_page_loaded(self):
        """Handle page load in visual picker."""
        # Could update status or enable buttons here
        pass

    def clear_all_selectors(self):
        """Clear all selectors from the table."""
        self.selectors_table.setRowCount(0)
        self.typed_wizard.set_wizard_data('suggested_selectors', {})
        self.completeChanged.emit()

    def isComplete(self):
        """Check if page is complete."""
        suggested_selectors = self.typed_wizard.get_wizard_data('suggested_selectors', {}) or {}
        return (
            super().isComplete() and
            len(suggested_selectors) > 0
        )


class SelectorTestingPage(QWizardPage):
    """Third page: Selector testing and validation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 3: Test Selectors")
        self.setSubTitle("Test and validate the CSS selectors against the loaded page")
        self.setup_ui()

    @property
    def typed_wizard(self) -> 'ScraperBuilderDialog':
        """Get the wizard cast to the correct type."""
        return cast('ScraperBuilderDialog', self.wizard())

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Test all button
        self.test_all_btn = QPushButton("🧪 Test All Selectors")
        self.test_all_btn.clicked.connect(self.test_all_selectors)
        layout.addWidget(self.test_all_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results table
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Field", "Selector", "Status", "Extracted Value"])
        self.results_table.horizontalHeader().setStretchLastSection(True)  # type: ignore
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group)

        # Summary
        self.summary_label = QLabel("Run tests to see results...")
        layout.addWidget(self.summary_label)

    def initializePage(self):
        """Initialize page with selectors from previous page."""
        prev_page = self.typed_wizard.page(1)  # Selector generation page
        if isinstance(prev_page, SelectorGenerationPage):
            selectors = prev_page.get_selectors()
            self.populate_results_table(selectors)

    def populate_results_table(self, selectors: Dict[str, Dict[str, Any]]):
        """Populate the results table with selectors."""
        self.results_table.setRowCount(len(selectors))
        for row, (field_name, selector_info) in enumerate(selectors.items()):
            # Field name
            field_item = QTableWidgetItem(field_name)
            field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 0, field_item)

            # Selector
            selector_item = QTableWidgetItem(selector_info.get('selector', ''))
            selector_item.setFlags(selector_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 1, selector_item)

            # Status
            status_item = QTableWidgetItem("Not tested")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 2, status_item)

            # Value
            value_item = QTableWidgetItem("")
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 3, value_item)

    def test_all_selectors(self):
        """Test all selectors against the page content."""
        page_content = self.typed_wizard.get_wizard_data('page_content')
        if not page_content:
            QMessageBox.warning(self, "Error", "No page content available for testing.")
            return

        self.test_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.results_table.rowCount())

        # Start testing in background
        selectors = self.get_selectors_from_table()
        self.test_thread = SelectorTestingThread(
            page_content,
            selectors
        )
        self.test_thread.progress.connect(self.update_progress)
        self.test_thread.result.connect(self.on_test_result)
        self.test_thread.finished.connect(self.on_testing_finished)
        self.test_thread.start()

    def get_selectors_from_table(self) -> Dict[str, Dict[str, Any]]:
        """Get selectors from the results table."""
        selectors = {}
        for row in range(self.results_table.rowCount()):
            field_item = self.results_table.item(row, 0)
            selector_item = self.results_table.item(row, 1)

            if field_item and selector_item:
                field = field_item.text()
                selector = selector_item.text()
                if selector.strip():
                    selectors[field] = {'selector': selector}
        return selectors

    def update_progress(self, row: int, status: str, value: str):
        """Update progress for a specific row."""
        if row < self.results_table.rowCount():
            # Status
            status_item = self.results_table.item(row, 2)
            if status_item:
                status_item.setText(status)
                # Color code status
                if status == "✅ Success":
                    status_item.setBackground(Qt.GlobalColor.green)
                elif status == "❌ Failed":
                    status_item.setBackground(Qt.GlobalColor.red)
                elif status == "⚠️ Warning":
                    status_item.setBackground(Qt.GlobalColor.yellow)

            # Value
            value_item = self.results_table.item(row, 3)
            if value_item:
                value_item.setText(value[:100])  # Truncate long values

        self.progress_bar.setValue(row + 1)

    def on_test_result(self, row: int, success: bool, extracted_value: str):
        """Handle individual test result."""
        status = "✅ Success" if success else "❌ Failed"
        self.update_progress(row, status, extracted_value)

    def on_testing_finished(self, results: Dict[str, Any]):
        """Handle completion of all tests."""
        self.test_all_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Update summary
        total = len(results)
        successful = sum(1 for r in results.values() if r.get('success', False))
        self.summary_label.setText(
            f"Testing complete: {successful}/{total} selectors successful"
        )

        # Store results for next page
        self.typed_wizard.test_results = results

        # Enable next button
        self.completeChanged.emit()

    def isComplete(self):
        """Check if page is complete."""
        return (
            super().isComplete() and
            hasattr(self.typed_wizard, 'test_results')
        )


class ConfigurationSavingPage(QWizardPage):
    """Fourth page: Save configuration as YAML."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Step 4: Save Configuration")
        self.setSubTitle("Review and save your scraper configuration")
        self.setup_ui()

    @property
    def typed_wizard(self) -> 'ScraperBuilderDialog':
        """Get the wizard cast to the correct type."""
        return cast('ScraperBuilderDialog', self.wizard())

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Configuration name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Scraper Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("My Product Scraper")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # YAML preview
        yaml_group = QGroupBox("YAML Configuration Preview")
        yaml_layout = QVBoxLayout(yaml_group)

        self.yaml_preview = QTextEdit()
        self.yaml_preview.setReadOnly(True)
        self.yaml_preview.setFont(QFont("Consolas", 9))
        yaml_layout.addWidget(self.yaml_preview)

        layout.addWidget(yaml_group)

        # Save options
        options_layout = QHBoxLayout()

        self.save_to_storage_cb = QCheckBox("Save selectors to storage for learning")
        self.save_to_storage_cb.setChecked(True)
        options_layout.addWidget(self.save_to_storage_cb)

        self.create_workflow_cb = QCheckBox("Create basic workflow")
        self.create_workflow_cb.setChecked(True)
        options_layout.addWidget(self.create_workflow_cb)

        layout.addLayout(options_layout)

        # Save button
        self.save_btn = QPushButton("💾 Save Configuration")
        self.save_btn.clicked.connect(self.save_configuration)
        layout.addWidget(self.save_btn)

        # Register fields
        self.registerField("scraper_name*", self.name_input)

    def initializePage(self):
        """Initialize page with data from previous pages."""
        # Generate YAML preview
        self.generate_yaml_preview()

    def generate_yaml_preview(self):
        """Generate YAML preview from collected data."""
        try:
            # Get data from wizard
            url = self.typed_wizard.field("url")
            scraper_name = self.name_input.text().strip() or "Generated Scraper"

            # Parse domain from URL
            domain = urlparse(url).netloc.replace('www.', '')

            # Get successful selectors from test results
            selectors = []
            if self.typed_wizard.test_results:
                for field_name, result in self.typed_wizard.test_results.items():
                    if result.get('success', False):
                        selector_info = result.get('selector_info', {})
                        selector_config = SelectorConfig(
                            name=field_name,
                            selector=selector_info.get('selector', ''),
                            attribute=selector_info.get('attribute', 'text'),
                            multiple=field_name.endswith('s')  # Plural fields are multiple
                        )
                        selectors.append(selector_config)

            # Create basic workflow
            workflows = []
            if self.create_workflow_cb.isChecked():
                workflows = [
                    WorkflowStep(
                        action="navigate",
                        params={"url": url}
                    ),
                    WorkflowStep(
                        action="wait",
                        params={"selector": "body", "timeout": 5}
                    ),
                    WorkflowStep(
                        action="extract",
                        params={"fields": [s.name for s in selectors]}
                    )
                ]

            # Create config
            config = ScraperConfig(
                name=scraper_name,
                base_url=f"https://{domain}",
                selectors=selectors,
                workflows=workflows,
                login=None,
                timeout=30,
                retries=3,
                anti_detection=None
            )

            # Convert to YAML
            import yaml
            yaml_content = yaml.safe_dump(
                config.model_dump(),
                default_flow_style=False,
                sort_keys=False
            )

            self.yaml_preview.setPlainText(yaml_content)

        except Exception as e:
            self.yaml_preview.setPlainText(f"Error generating YAML: {str(e)}")

    def save_configuration(self):
        """Save the configuration to file and storage."""
        try:
            scraper_name = self.name_input.text().strip()
            if not scraper_name:
                QMessageBox.warning(self, "Error", "Please enter a scraper name.")
                return

            # Generate YAML content
            yaml_content = self.yaml_preview.toPlainText()

            # Parse config
            parser = ScraperConfigParser()
            config = parser.load_from_string(yaml_content)

            # Save to file
            configs_dir = Path("src/scrapers/configs")
            configs_dir.mkdir(exist_ok=True)
            filename = f"{scraper_name.lower().replace(' ', '_')}.yaml"
            config_file = configs_dir / filename

            parser.save_to_file(config, config_file)

            # Save selectors to storage for learning
            if self.save_to_storage_cb.isChecked():
                self.save_selectors_to_storage(config)

            QMessageBox.information(
                self,
                "Success",
                f"Scraper configuration saved successfully!\n\n"
                f"File: {config_file}\n"
                f"Selectors: {len(config.selectors)}\n"
                f"Workflows: {len(config.workflows)}"
            )

            # Mark wizard as complete
            self.typed_wizard.config_saved = True
            self.completeChanged.emit()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def save_selectors_to_storage(self, config: ScraperConfig):
        """Save successful selectors to storage for learning."""
        try:
            manager = SelectorManager()
            domain = urlparse(config.base_url).netloc

            for selector in config.selectors:
                # Only save if we have test results indicating success
                if self.typed_wizard.test_results:
                    test_result = self.typed_wizard.test_results.get(selector.name, {})
                    if test_result.get('success', False):
                        manager.learn_selector(
                            domain=domain,
                            field_name=selector.name,
                            selector=selector.selector,
                            success=True
                        )

        except Exception as e:
            print(f"Warning: Failed to save selectors to storage: {e}")

    def isComplete(self):
        """Check if page is complete."""
        return (
            super().isComplete() and
            self.typed_wizard.config_saved
        )


class ScraperBuilderDialog(QWizard):
    """Main scraper builder wizard dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Scraper Builder")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(900, 700)

        # Apply dark theme
        self.setStyleSheet(STYLESHEET)

        # Add pages
        self.addPage(UrlInputPage())
        self.addPage(SelectorGenerationPage())
        self.addPage(SelectorTestingPage())
        self.addPage(ConfigurationSavingPage())

        # Initialize wizard data storage
        self._wizard_data = {
            'page_content': None,
            'suggested_selectors': {},
            'test_results': {},
            'config_saved': False
        }

        # Additional attributes for wizard state
        self.test_results: Optional[Dict[str, Any]] = None
        self.config_saved: bool = False

        # Set window properties
        self.setWindowModality(Qt.WindowModality.WindowModal)

    def get_wizard_data(self, key: str, default=None):
        """Get wizard data by key."""
        return self._wizard_data.get(key, default)

    def set_wizard_data(self, key: str, value):
        """Set wizard data by key."""
        self._wizard_data[key] = value


# Background worker threads

class PageLoadThread(QThread):
    """Thread for loading page content using HTTP request."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        """Load page content."""
        try:
            # Use simple HTTP request to get page content
            import requests
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse HTML and extract text content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text content
            content = soup.get_text(separator='\n', strip=True)

            self.finished.emit(content)

        except Exception as e:
            self.error.emit(str(e))


class SelectorGenerationThread(QThread):
    """Thread for AI selector generation."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, page_content: str):
        super().__init__()
        self.page_content = page_content

    def run(self):
        """Generate selectors using AI."""
        try:
            # Use OpenRouter LLM to analyze HTML and suggest selectors
            classifier = get_llm_classifier()
            if not classifier:
                self.error.emit("OpenRouter LLM classifier not available")
                return

            # Type assertion for mypy
            assert classifier is not None

            # Create prompt for selector generation
            prompt = f"""
Analyze this HTML content from a product page and suggest CSS selectors for the following specific product fields only.
Return a JSON object with field names as keys and selector objects as values.

Required fields to look for:
- product_name: Main product title/name
- brand: Product brand
- image_urls: Product images (array of image URLs)
- weight: Product weight (look for weight information, convert any ounces to pounds, format as 'X.XX lbs')

For each field, provide:
- selector: CSS selector
- attribute: HTML attribute to extract (text, src, href, etc.)

IMPORTANT:
- Only include the 4 specified fields: product_name, brand, image_urls, weight
- Ensure all selector and attribute values are non-null and valid
- For weight, if found in ounces, convert to pounds (1 oz = 0.0625 lbs) and format as 'X.XX lbs'
- Return only valid JSON with no null values
- When using contains selectors, use the proper CSS pseudo-class ':-soup-contains' instead of the deprecated ':contains' (e.g., 'div:-soup-contains("text")' instead of 'div:contains("text")')

HTML Content:
{self.page_content[:4000]}  # Limit content length

Return only valid JSON.
"""

            # Call LLM
            messages = [{"role": "user", "content": prompt}]
            response = classifier._call_openrouter(messages)

            if not response:
                self.error.emit("No response from LLM")
                return

            # Parse JSON response
            try:
                # Extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    selectors = json.loads(json_str)
                    self.finished.emit(selectors)
                else:
                    # Fallback: create basic selectors
                    self.finished.emit(self.create_fallback_selectors())
            except json.JSONDecodeError:
                # Fallback selectors
                self.finished.emit(self.create_fallback_selectors())

        except Exception as e:
            self.error.emit(str(e))

    def create_fallback_selectors(self) -> Dict[str, Dict[str, Any]]:
        """Create fallback selectors when AI fails."""
        return {
            "product_name": {
                "selector": "h1, .product-title, .product-name, [class*='title']",
                "attribute": "text"
            },
            "price": {
                "selector": ".price, [class*='price'], .cost, .amount",
                "attribute": "text"
            },
            "description": {
                "selector": ".description, [class*='description'], .details, .info",
                "attribute": "text"
            },
            "image_urls": {
                "selector": "img[src*='product'], .product-image img",
                "attribute": "src"
            }
        }


class SelectorTestingThread(QThread):
    """Thread for testing selectors against page content."""

    progress = pyqtSignal(int, str, str)  # row, status, value
    result = pyqtSignal(int, bool, str)  # row, success, value
    finished = pyqtSignal(dict)

    def __init__(self, page_content: str, selectors: Dict[str, Dict[str, Any]]):
        super().__init__()
        self.page_content = page_content
        self.selectors = selectors

    def run(self):
        """Test selectors against page content."""
        results = {}

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(self.page_content, 'html.parser')
        except ImportError:
            # Fallback without BeautifulSoup
            soup = None

        for row, (field_name, selector_info) in enumerate(self.selectors.items()):
            selector = selector_info.get('selector', '')
            attribute = selector_info.get('attribute', 'text')

            try:
                if soup:
                    # Use BeautifulSoup for proper parsing
                    elements = soup.select(selector)
                    if elements:
                        if attribute == 'text':
                            value = elements[0].get_text(strip=True)
                        else:
                            value = elements[0].get(attribute, '')

                        if isinstance(value, str):
                            success = bool(value.strip())
                            extracted_value = value[:200] if value else "No value found"
                        else:
                            success = bool(value)
                            extracted_value = str(value)[:200] if value else "No value found"
                    else:
                        success = False
                        extracted_value = "Selector not found"
                else:
                    # Simple regex fallback
                    success = selector in self.page_content
                    extracted_value = "Found" if success else "Not found"

                status = "✅ Success" if success else "❌ Failed"
                self.progress.emit(row, status, extracted_value)
                self.result.emit(row, success, extracted_value)

                results[field_name] = {
                    'success': success,
                    'value': extracted_value,
                    'selector_info': selector_info
                }

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.progress.emit(row, "❌ Error", error_msg)
                self.result.emit(row, False, error_msg)
                results[field_name] = {
                    'success': False,
                    'value': error_msg,
                    'selector_info': selector_info
                }

        self.finished.emit(results)