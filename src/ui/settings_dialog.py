"""
Settings Dialog for ProductScraper
Provides a GUI for configuring application settings.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QTextEdit,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from src.core.settings_manager import settings


class SettingsDialog(QDialog):
    """Settings dialog for configuring ProductScraper."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProductScraper Settings")
        self.setMinimumSize(700, 600)
        self.setModal(True)

        # Load current settings
        self.current_settings = settings.get_all()

        self.create_ui()
        self.load_settings()

        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3e3e3e;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #4CAF50;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                border: 1px solid #ffffff;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
            }
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #4CAF50;
            }
            QSpinBox:focus {
                border: 1px solid #2196F3;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #3d3d3d;
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4a4a4a;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #4CAF50;
            }
            QComboBox:focus {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggM0w2IDUgMiA5IiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                selection-background-color: #4CAF50;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #2196F3;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QPushButton[text="💾 Save"] {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
            }
            QPushButton[text="💾 Save"]:hover {
                background-color: #45a049;
                border: 1px solid #45a049;
            }
            QPushButton[text="❌ Cancel"] {
                background-color: #F44336;
                border: 1px solid #F44336;
            }
            QPushButton[text="❌ Cancel"]:hover {
                background-color: #d32f2f;
                border: 1px solid #d32f2f;
            }
            QTabWidget::pane {
                border: 1px solid #3e3e3e;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #2196F3;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
            }
            QMessageBox {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QFileDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)

    def create_ui(self):
        """Create the settings dialog UI."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Create tabs
        self.create_credentials_tab()
        self.create_shopsite_tab()
        self.create_application_tab()

        layout.addWidget(self.tab_widget)

        # Buttons
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        buttons_layout.addWidget(save_btn)

        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        buttons_layout.addWidget(reset_btn)

        buttons_layout.addStretch()

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def create_credentials_tab(self):
        """Create the scraper credentials tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # PetFood credentials
        petfood_group = QGroupBox("PetFood Credentials")
        petfood_layout = QFormLayout()

        self.petfood_username = QLineEdit()
        self.petfood_username.setPlaceholderText("Enter PetFood username")
        petfood_layout.addRow("Username:", self.petfood_username)

        self.petfood_password = QLineEdit()
        self.petfood_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.petfood_password.setPlaceholderText("Enter PetFood password")
        petfood_layout.addRow("Password:", self.petfood_password)

        petfood_group.setLayout(petfood_layout)
        layout.addWidget(petfood_group)

        # Phillips credentials
        phillips_group = QGroupBox("Phillips Credentials")
        phillips_layout = QFormLayout()

        self.phillips_username = QLineEdit()
        self.phillips_username.setPlaceholderText("Enter Phillips username")
        phillips_layout.addRow("Username:", self.phillips_username)

        self.phillips_password = QLineEdit()
        self.phillips_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.phillips_password.setPlaceholderText("Enter Phillips password")
        phillips_layout.addRow("Password:", self.phillips_password)

        phillips_group.setLayout(phillips_layout)
        layout.addWidget(phillips_group)

        # Orgill credentials
        orgill_group = QGroupBox("Orgill Credentials")
        orgill_layout = QFormLayout()

        self.orgill_username = QLineEdit()
        self.orgill_username.setPlaceholderText("Enter Orgill username")
        orgill_layout.addRow("Username:", self.orgill_username)

        self.orgill_password = QLineEdit()
        self.orgill_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.orgill_password.setPlaceholderText("Enter Orgill password")
        orgill_layout.addRow("Password:", self.orgill_password)

        orgill_group.setLayout(orgill_layout)
        layout.addWidget(orgill_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "🔐 Scraper Credentials")

    def create_shopsite_tab(self):
        """Create the ShopSite API credentials tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # OAuth2 credentials
        oauth_group = QGroupBox("ShopSite OAuth2 Credentials")
        oauth_layout = QFormLayout()

        self.shopsite_client_id = QLineEdit()
        self.shopsite_client_id.setPlaceholderText("Enter ShopSite Client ID")
        oauth_layout.addRow("Client ID:", self.shopsite_client_id)

        self.shopsite_secret_key = QLineEdit()
        self.shopsite_secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.shopsite_secret_key.setPlaceholderText("Enter ShopSite Secret Key")
        oauth_layout.addRow("Secret Key:", self.shopsite_secret_key)

        self.shopsite_auth_code = QLineEdit()
        self.shopsite_auth_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.shopsite_auth_code.setPlaceholderText("Enter ShopSite Authorization Code")
        oauth_layout.addRow("Auth Code:", self.shopsite_auth_code)

        self.shopsite_auth_url = QLineEdit()
        self.shopsite_auth_url.setPlaceholderText("https://yourstore.shopsite.com/xml/")
        oauth_layout.addRow("Auth URL:", self.shopsite_auth_url)

        oauth_group.setLayout(oauth_layout)
        layout.addWidget(oauth_group)

        # Alternative login credentials
        login_group = QGroupBox("Alternative Login Credentials")
        login_layout = QFormLayout()

        self.shopsite_username = QLineEdit()
        self.shopsite_username.setPlaceholderText("Enter ShopSite username")
        login_layout.addRow("Username:", self.shopsite_username)

        self.shopsite_password = QLineEdit()
        self.shopsite_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.shopsite_password.setPlaceholderText("Enter ShopSite password")
        login_layout.addRow("Password:", self.shopsite_password)

        login_group.setLayout(login_layout)
        layout.addWidget(login_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "🏪 ShopSite API")

    def create_application_tab(self):
        """Create the application settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Database settings
        db_group = QGroupBox("Database Settings")
        db_layout = QFormLayout()

        db_path_layout = QHBoxLayout()
        self.database_path = QLineEdit()
        self.database_path.setPlaceholderText("data/databases/products.db")
        db_path_layout.addWidget(self.database_path)

        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self.browse_database_path)
        db_path_layout.addWidget(browse_btn)

        db_layout.addRow("Database Path:", db_path_layout)
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # Selenium settings
        selenium_group = QGroupBox("Selenium Settings")
        selenium_layout = QFormLayout()

        self.selenium_headless = QCheckBox("Run in headless mode")
        self.selenium_headless.setChecked(True)
        selenium_layout.addRow(self.selenium_headless)

        self.selenium_timeout = QSpinBox()
        self.selenium_timeout.setRange(10, 300)
        self.selenium_timeout.setValue(30)
        self.selenium_timeout.setSuffix(" seconds")
        selenium_layout.addRow("Timeout:", self.selenium_timeout)

        selenium_group.setLayout(selenium_layout)
        layout.addWidget(selenium_group)

        # UI settings
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout()

        self.debug_mode = QCheckBox("Enable debug mode")
        ui_layout.addRow(self.debug_mode)

        self.auto_scroll_logs = QCheckBox("Auto-scroll logs")
        self.auto_scroll_logs.setChecked(True)
        ui_layout.addRow(self.auto_scroll_logs)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # AI/ML settings
        ai_group = QGroupBox("AI/ML Settings")
        ai_layout = QFormLayout()

        self.openrouter_api_key = QLineEdit()
        self.openrouter_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_api_key.setPlaceholderText(
            "Enter OpenRouter API key for LLM classification"
        )
        ai_layout.addRow("OpenRouter API Key:", self.openrouter_api_key)

        # Classification method dropdown
        from PyQt6.QtWidgets import QComboBox

        self.classification_method = QComboBox()
        self.classification_method.addItems(["llm", "local_llm", "fuzzy"])
        self.classification_method.setToolTip(
            "llm: OpenRouter API only\nlocal_llm: Local Ollama (no API key)\nfuzzy: fuzzy matching only"
        )
        ai_layout.addRow("Classification Method:", self.classification_method)

        self.ollama_model = QLineEdit()
        self.ollama_model.setText("llama3.2")
        self.ollama_model.setPlaceholderText("Enter Ollama model name (e.g., llama3.2, gemma3)")
        ai_layout.addRow("Ollama Model:", self.ollama_model)

        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "⚙️ Application")

    def load_settings(self):
        """Load current settings into the UI."""
        # Credentials
        self.petfood_username.setText(self.current_settings.get("petfood_username", ""))
        self.petfood_password.setText(self.current_settings.get("petfood_password", ""))
        self.phillips_username.setText(
            self.current_settings.get("phillips_username", "")
        )
        self.phillips_password.setText(
            self.current_settings.get("phillips_password", "")
        )
        self.orgill_username.setText(self.current_settings.get("orgill_username", ""))
        self.orgill_password.setText(self.current_settings.get("orgill_password", ""))

        # ShopSite
        self.shopsite_client_id.setText(
            self.current_settings.get("shopsite_client_id", "")
        )
        self.shopsite_secret_key.setText(
            self.current_settings.get("shopsite_secret_key", "")
        )
        self.shopsite_auth_code.setText(
            self.current_settings.get("shopsite_authorization_code", "")
        )
        self.shopsite_auth_url.setText(
            self.current_settings.get("shopsite_auth_url", "")
        )
        self.shopsite_username.setText(
            self.current_settings.get("shopsite_username", "")
        )
        self.shopsite_password.setText(
            self.current_settings.get("shopsite_password", "")
        )

        # Application
        self.database_path.setText(self.current_settings.get("database_path", ""))
        self.selenium_headless.setChecked(
            self.current_settings.get("selenium_headless", True)
        )
        self.selenium_timeout.setValue(
            self.current_settings.get("selenium_timeout", 30)
        )
        self.debug_mode.setChecked(self.current_settings.get("debug_mode", False))
        self.auto_scroll_logs.setChecked(
            self.current_settings.get("auto_scroll_logs", True)
        )

        # AI/ML
        self.openrouter_api_key.setText(self.current_settings.get("openrouter_api_key", ""))
        method = self.current_settings.get("classification_method", "llm")
        index = self.classification_method.findText(method)
        if index >= 0:
            self.classification_method.setCurrentIndex(index)
        self.ollama_model.setText(self.current_settings.get("ollama_model", "llama3.2"))

    def save_settings(self):
        """Save settings from UI to settings manager."""
        try:
            # Credentials
            settings.set("petfood_username", self.petfood_username.text().strip())
            settings.set("petfood_password", self.petfood_password.text().strip())
            settings.set("phillips_username", self.phillips_username.text().strip())
            settings.set("phillips_password", self.phillips_password.text().strip())
            settings.set("orgill_username", self.orgill_username.text().strip())
            settings.set("orgill_password", self.orgill_password.text().strip())

            # ShopSite
            settings.set("shopsite_client_id", self.shopsite_client_id.text().strip())
            settings.set("shopsite_secret_key", self.shopsite_secret_key.text().strip())
            settings.set(
                "shopsite_authorization_code", self.shopsite_auth_code.text().strip()
            )
            settings.set("shopsite_auth_url", self.shopsite_auth_url.text().strip())
            settings.set("shopsite_username", self.shopsite_username.text().strip())
            settings.set("shopsite_password", self.shopsite_password.text().strip())

            # Application
            settings.set("database_path", self.database_path.text().strip())
            settings.set("selenium_headless", self.selenium_headless.isChecked())
            settings.set("selenium_timeout", self.selenium_timeout.value())
            settings.set("debug_mode", self.debug_mode.isChecked())
            settings.set("auto_scroll_logs", self.auto_scroll_logs.isChecked())

            # AI/ML
            settings.set("openrouter_api_key", self.openrouter_api_key.text().strip())
            settings.set(
                "classification_method", self.classification_method.currentText()
            )
            settings.set("ollama_model", self.ollama_model.text().strip())

            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\n\nThis will clear all your configured credentials.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            settings.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(self, "Success", "Settings reset to defaults.")

    def browse_database_path(self):
        """Browse for database file location."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database Location",
            self.database_path.text() or "data/databases/products.db",
            "SQLite Database (*.db);;All Files (*)",
        )
        if file_path:
            self.database_path.setText(file_path)
