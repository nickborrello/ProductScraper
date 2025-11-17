"""
Visual Selector Picker Component

A QWebEngineView-based component that allows users to visually select elements
on web pages to automatically generate CSS selectors.
"""

import json
from typing import Optional, Dict, Any, Callable

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QComboBox,
    QMessageBox,
    QProgressBar,
    QSplitter
)
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEnginePage  # type: ignore
except ImportError:
    # PyQt6-WebEngine not available
    QWebEngineView = None
    QWebEnginePage = None


class VisualSelectorPicker(QWidget):
    """Visual selector picker using QWebEngineView."""

    # Signals
    selector_selected = pyqtSignal(str, str, str)  # selector, attribute, field_name
    page_loaded = pyqtSignal()
    selector_validated = pyqtSignal(str, bool, str)  # selector, is_valid, extracted_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_url = ""
        self.selection_mode = False
        self.selected_element_info = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Check if web engine is available
        if QWebEngineView is None:
            error_label = QLabel("❌ PyQt6-WebEngine is not installed.\n\n"
                               "To use the visual selector picker, install PyQt6-WebEngine:\n"
                               "pip install PyQt6-WebEngine")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(error_label)
            return

        # URL input and controls
        url_group = QGroupBox("Web Page")
        url_layout = QVBoxLayout(url_group)

        # URL input
        url_input_layout = QHBoxLayout()
        url_input_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/product")
        url_input_layout.addWidget(self.url_input)

        self.load_btn = QPushButton("🔗 Load Page")
        self.load_btn.clicked.connect(self.load_page)
        url_input_layout.addWidget(self.load_btn)

        url_layout.addLayout(url_input_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        url_layout.addWidget(self.progress_bar)

        layout.addWidget(url_group)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Web view
        web_group = QGroupBox("Web Page")
        web_layout = QVBoxLayout(web_group)

        # Selection controls
        controls_layout = QHBoxLayout()

        self.select_mode_btn = QPushButton("🎯 Start Selection")
        self.select_mode_btn.clicked.connect(self.toggle_selection_mode)
        self.select_mode_btn.setCheckable(True)
        controls_layout.addWidget(self.select_mode_btn)

        self.clear_selection_btn = QPushButton("🗑️ Clear")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        controls_layout.addWidget(self.clear_selection_btn)

        controls_layout.addStretch()
        web_layout.addLayout(controls_layout)

        # Web engine view
        self.web_view = QWebEngineView()
        self.web_view.page().loadFinished.connect(self.on_page_load_finished)
        web_layout.addWidget(self.web_view)

        splitter.addWidget(web_group)

        # Selector panel
        selector_group = QGroupBox("Selector Configuration")
        selector_layout = QVBoxLayout(selector_group)

        # Selected element info
        element_info_group = QGroupBox("Selected Element")
        element_layout = QVBoxLayout(element_info_group)

        self.element_info = QTextEdit()
        self.element_info.setReadOnly(True)
        self.element_info.setMaximumHeight(100)
        self.element_info.setFont(QFont("Consolas", 9))
        self.element_info.setPlainText("Click 'Start Selection' and click on an element in the web page...")
        element_layout.addWidget(self.element_info)

        selector_layout.addWidget(element_info_group)

        # Field selection
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.addItems([
            "product_name", "price", "description", "image_urls",
            "sku", "brand", "availability", "rating", "specifications"
        ])
        field_layout.addWidget(self.field_combo)
        selector_layout.addLayout(field_layout)

        # Attribute selection
        attr_layout = QHBoxLayout()
        attr_layout.addWidget(QLabel("Attribute:"))
        self.attr_combo = QComboBox()
        self.attr_combo.addItems(["text", "src", "href", "content", "value", "alt"])
        attr_layout.addWidget(self.attr_combo)
        selector_layout.addLayout(attr_layout)

        # Generated selector
        selector_display_layout = QHBoxLayout()
        selector_display_layout.addWidget(QLabel("Selector:"))
        self.selector_display = QLineEdit()
        self.selector_display.setReadOnly(True)
        selector_display_layout.addWidget(self.selector_display)
        selector_layout.addLayout(selector_display_layout)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.validate_btn = QPushButton("✅ Validate")
        self.validate_btn.clicked.connect(self.validate_selector)
        buttons_layout.addWidget(self.validate_btn)

        self.add_selector_btn = QPushButton("➕ Add Selector")
        self.add_selector_btn.clicked.connect(self.add_selector)
        buttons_layout.addWidget(self.add_selector_btn)

        selector_layout.addLayout(buttons_layout)

        # Validation results
        validation_group = QGroupBox("Validation Results")
        validation_layout = QVBoxLayout(validation_group)

        self.validation_result = QTextEdit()
        self.validation_result.setReadOnly(True)
        self.validation_result.setMaximumHeight(80)
        self.validation_result.setFont(QFont("Consolas", 9))
        validation_layout.addWidget(self.validation_result)

        selector_layout.addWidget(validation_group)

        splitter.addWidget(selector_group)

        # Set splitter proportions
        splitter.setSizes([600, 400])

        layout.addWidget(splitter)

    def load_page(self):
        """Load the web page in the QWebEngineView."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL.")
            return

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_input.setText(url)

        self.current_url = url
        self.load_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.web_view.load(QUrl(url))

    def on_page_load_finished(self, success: bool):
        """Handle page load completion."""
        self.load_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        if success:
            self.page_loaded.emit()
            # Inject the selection JavaScript
            self.inject_selection_script()
        else:
            QMessageBox.critical(self, "Error", "Failed to load the web page.")

    def inject_selection_script(self):
        """Inject JavaScript for element selection."""
        script = """
        // Remove existing selection overlay if any
        var existingOverlay = document.getElementById('selector-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // Create selection overlay
        var overlay = document.createElement('div');
        overlay.id = 'selector-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 255, 0.1);
            z-index: 999999;
            pointer-events: none;
            display: none;
        `;
        document.body.appendChild(overlay);

        // Selection mode variable
        window.selectionMode = false;

        // Function to generate CSS selector
        function generateSelector(element) {
            if (!element) return '';

            var path = [];
            var current = element;

            while (current && current.nodeType === Node.ELEMENT_NODE) {
                var selector = current.tagName.toLowerCase();

                if (current.id) {
                    selector += '#' + current.id;
                    path.unshift(selector);
                    break; // ID is unique, stop here
                } else if (current.className) {
                    var classes = current.className.trim().split(/\\s+/).filter(function(cls) {
                        return cls.length > 0;
                    });
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }

                // Add nth-child if needed
                var siblings = Array.from(current.parentNode ? current.parentNode.children : []);
                var index = siblings.indexOf(current);
                if (siblings.length > 1 && index >= 0) {
                    selector += ':nth-child(' + (index + 1) + ')';
                }

                path.unshift(selector);
                current = current.parentNode;

                // Limit depth to avoid overly complex selectors
                if (path.length > 5) break;
            }

            return path.join(' > ');
        }

        // Function to get element info
        function getElementInfo(element) {
            var info = {
                tagName: element.tagName.toLowerCase(),
                id: element.id || '',
                className: element.className || '',
                text: element.textContent ? element.textContent.trim().substring(0, 100) : '',
                attributes: {}
            };

            // Get common attributes
            var commonAttrs = ['src', 'href', 'alt', 'title', 'value', 'content'];
            commonAttrs.forEach(function(attr) {
                if (element.hasAttribute(attr)) {
                    info.attributes[attr] = element.getAttribute(attr);
                }
            });

            return info;
        }

        // Click handler
        document.addEventListener('click', function(e) {
            if (!window.selectionMode) return;

            e.preventDefault();
            e.stopPropagation();

            var element = e.target;
            var selector = generateSelector(element);
            var info = getElementInfo(element);

            // Highlight selected element
            if (window.lastSelected) {
                window.lastSelected.style.outline = '';
            }
            element.style.outline = '3px solid red';
            window.lastSelected = element;

            // Send info to Python
            window.qtSelectorSelected(selector, JSON.stringify(info));
        });

        // Mouseover handler for preview
        document.addEventListener('mouseover', function(e) {
            if (!window.selectionMode) return;

            var element = e.target;
            if (element.id === 'selector-overlay') return;

            element.style.outline = '2px solid blue';
            element.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
        });

        document.addEventListener('mouseout', function(e) {
            if (!window.selectionMode || e.target === window.lastSelected) return;

            var element = e.target;
            if (element.id === 'selector-overlay') return;

            element.style.outline = '';
            element.style.backgroundColor = '';
        });

        // Functions exposed to Python
        window.startSelection = function() {
            window.selectionMode = true;
            overlay.style.display = 'block';
            document.body.style.cursor = 'crosshair';
        };

        window.stopSelection = function() {
            window.selectionMode = false;
            overlay.style.display = 'none';
            document.body.style.cursor = 'default';
        };

        window.clearSelection = function() {
            if (window.lastSelected) {
                window.lastSelected.style.outline = '';
                window.lastSelected = null;
            }
        };
        """

        # Run the script
        self.web_view.page().runJavaScript(script)

        # Connect to JavaScript signals
        self.web_view.page().javaScriptConsoleMessage = self.on_js_console_message

    def on_js_console_message(self, level, message, line, source):
        """Handle JavaScript console messages."""
        print(f"JS Console: {message}")

    def toggle_selection_mode(self):
        """Toggle element selection mode."""
        if self.select_mode_btn.isChecked():
            self.start_selection_mode()
        else:
            self.stop_selection_mode()

    def start_selection_mode(self):
        """Start element selection mode."""
        script = "window.startSelection();"
        self.web_view.page().runJavaScript(script)
        self.select_mode_btn.setText("⏹️ Stop Selection")
        self.element_info.setPlainText("Click on elements in the web page to select them...")

    def stop_selection_mode(self):
        """Stop element selection mode."""
        script = "window.stopSelection();"
        self.web_view.page().runJavaScript(script)
        self.select_mode_btn.setChecked(False)
        self.select_mode_btn.setText("🎯 Start Selection")

    def clear_selection(self):
        """Clear current selection."""
        script = "window.clearSelection();"
        self.web_view.page().runJavaScript(script)
        self.element_info.setPlainText("Selection cleared. Click 'Start Selection' to begin again...")
        self.selector_display.clear()
        self.validation_result.clear()

    def validate_selector(self):
        """Validate the current selector by testing it against the page."""
        selector = self.selector_display.text().strip()
        if not selector:
            QMessageBox.warning(self, "Error", "No selector to validate.")
            return

        attribute = self.attr_combo.currentText()

        # JavaScript to test the selector
        script = f"""
        (function() {{
            try {{
                var elements = document.querySelectorAll('{selector}');
                if (elements.length === 0) {{
                    return {{success: false, message: 'No elements found'}};
                }}

                var element = elements[0];
                var value = '';

                if ('{attribute}' === 'text') {{
                    value = element.textContent ? element.textContent.trim() : '';
                }} else {{
                    value = element.getAttribute('{attribute}') || '';
                }}

                return {{
                    success: true,
                    value: value.substring(0, 200),
                    count: elements.length
                }};
            }} catch (e) {{
                return {{success: false, message: e.message}};
            }}
        }})();
        """

        def handle_result(result):
            if result.get('success'):
                value = result.get('value', '')
                count = result.get('count', 0)
                message = f"✅ Valid - Found {count} element(s)\nExtracted: {value}"
                self.validation_result.setPlainText(message)
                self.selector_validated.emit(selector, True, value)
            else:
                message = f"❌ Invalid - {result.get('message', 'Unknown error')}"
                self.validation_result.setPlainText(message)
                self.selector_validated.emit(selector, False, "")

        self.web_view.page().runJavaScript(script, handle_result)

    def add_selector(self):
        """Add the current selector to the scraper configuration."""
        selector = self.selector_display.text().strip()
        if not selector:
            QMessageBox.warning(self, "Error", "No selector to add.")
            return

        field_name = self.field_combo.currentText()
        attribute = self.attr_combo.currentText()

        self.selector_selected.emit(selector, attribute, field_name)

        # Clear for next selection
        self.clear_selection()

    def set_url(self, url: str):
        """Set the URL to load."""
        self.url_input.setText(url)
        self.load_page()

    def get_current_selector_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently selected element."""
        return self.selected_element_info


# JavaScript bridge class
class SelectorJavaScriptBridge(QWidget if QWebEnginePage is None else QWebEnginePage):  # type: ignore
    """Bridge between JavaScript and Python for selector selection."""

    selector_selected = pyqtSignal(str, dict)  # selector, element_info

    def __init__(self, parent=None):
        super().__init__(parent)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Handle JavaScript console messages."""
        if QWebEnginePage is not None:
            print(f"JS Console [{level}]: {message} (line {lineNumber})")

    # This method will be called from JavaScript
    def qtSelectorSelected(self, selector: str, element_info_json: str):
        """Handle selector selection from JavaScript."""
        try:
            element_info = json.loads(element_info_json)
            self.selector_selected.emit(selector, element_info)
        except json.JSONDecodeError:
            print(f"Failed to parse element info JSON: {element_info_json}")


# Integration helper functions
def generate_css_selector(element_info: Dict[str, Any]) -> str:
    """Generate a CSS selector from element information."""
    # This is a simplified version - the JavaScript version is more sophisticated
    tag = element_info.get('tagName', 'div')
    selector = tag

    if element_info.get('id'):
        selector = f"{tag}#{element_info['id']}"

    elif element_info.get('className'):
        classes = element_info['className'].split()
        if classes:
            selector = f"{tag}.{'.'.join(classes)}"

    return selector


def validate_selector_on_page(html_content: str, selector: str, attribute: str = 'text') -> Dict[str, Any]:
    """Validate a selector against HTML content."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        elements = soup.select(selector)
        if not elements:
            return {'valid': False, 'message': 'No elements found'}

        element = elements[0]
        if attribute == 'text':
            value = element.get_text(strip=True)
        else:
            value = element.get(attribute, '')

        return {
            'valid': True,
            'value': value,
            'count': len(elements)
        }

    except Exception as e:
        return {'valid': False, 'message': str(e)}