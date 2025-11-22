from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QSpinBox, QComboBox, QFormLayout, QGroupBox, QTabWidget,
    QMessageBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt
from src.core.settings_manager import settings

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("Settings")
        header.setProperty("class", "h1")
        layout.addWidget(header)

        # Scroll Area for settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # Tab Widget
        self.tabs = QTabWidget()
        
        self.create_credentials_tab()
        self.create_shopsite_tab()
        self.create_application_tab()
        
        content_layout.addWidget(self.tabs)
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 Save Settings")
        self.btn_save.setProperty("class", "primary")
        self.btn_save.clicked.connect(self.save_settings)
        
        self.btn_reset = QPushButton("🔄 Reset to Defaults")
        self.btn_reset.clicked.connect(self.reset_to_defaults)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)

    def create_credentials_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # PetFood
        group = QGroupBox("PetFood Credentials")
        form = QFormLayout()
        self.petfood_user = QLineEdit()
        self.petfood_pass = QLineEdit()
        self.petfood_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.petfood_user)
        form.addRow("Password:", self.petfood_pass)
        group.setLayout(form)
        layout.addWidget(group)

        # Phillips
        group = QGroupBox("Phillips Credentials")
        form = QFormLayout()
        self.phillips_user = QLineEdit()
        self.phillips_pass = QLineEdit()
        self.phillips_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.phillips_user)
        form.addRow("Password:", self.phillips_pass)
        group.setLayout(form)
        layout.addWidget(group)

        # Orgill
        group = QGroupBox("Orgill Credentials")
        form = QFormLayout()
        self.orgill_user = QLineEdit()
        self.orgill_pass = QLineEdit()
        self.orgill_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.orgill_user)
        form.addRow("Password:", self.orgill_pass)
        group.setLayout(form)
        layout.addWidget(group)

        layout.addStretch()
        self.tabs.addTab(tab, "🔐 Credentials")

    def create_shopsite_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # OAuth
        group = QGroupBox("ShopSite OAuth2")
        form = QFormLayout()
        self.ss_client_id = QLineEdit()
        self.ss_secret = QLineEdit()
        self.ss_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.ss_auth_code = QLineEdit()
        self.ss_auth_code.setEchoMode(QLineEdit.EchoMode.Password)
        self.ss_auth_url = QLineEdit()
        
        form.addRow("Client ID:", self.ss_client_id)
        form.addRow("Secret Key:", self.ss_secret)
        form.addRow("Auth Code:", self.ss_auth_code)
        form.addRow("Auth URL:", self.ss_auth_url)
        group.setLayout(form)
        layout.addWidget(group)

        # Legacy Login
        group = QGroupBox("Alternative Login")
        form = QFormLayout()
        self.ss_user = QLineEdit()
        self.ss_pass = QLineEdit()
        self.ss_pass.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.ss_user)
        form.addRow("Password:", self.ss_pass)
        group.setLayout(form)
        layout.addWidget(group)

        layout.addStretch()
        self.tabs.addTab(tab, "🏪 ShopSite")

    def create_application_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Database
        group = QGroupBox("Database")
        form = QFormLayout()
        
        db_layout = QHBoxLayout()
        self.db_path = QLineEdit()
        self.btn_browse_db = QPushButton("📂")
        self.btn_browse_db.setFixedWidth(40)
        self.btn_browse_db.clicked.connect(self.browse_db)
        db_layout.addWidget(self.db_path)
        db_layout.addWidget(self.btn_browse_db)
        
        form.addRow("Database Path:", db_layout)
        group.setLayout(form)
        layout.addWidget(group)

        # Scraper Settings
        group = QGroupBox("Scraper Engine")
        form = QFormLayout()
        
        self.chk_headless = QCheckBox("Run Headless (Hidden Browser)")
        self.chk_debug = QCheckBox("Debug Mode (Show Browser)")
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 300)
        self.spin_timeout.setSuffix(" sec")
        
        form.addRow(self.chk_headless)
        form.addRow(self.chk_debug)
        form.addRow("Timeout:", self.spin_timeout)
        group.setLayout(form)
        layout.addWidget(group)

        # AI Settings
        group = QGroupBox("AI Classification")
        form = QFormLayout()
        
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_method = QComboBox()
        self.ai_method.addItems(["llm", "local_llm", "fuzzy"])
        self.ai_model = QLineEdit()
        
        form.addRow("OpenRouter Key:", self.ai_key)
        form.addRow("Method:", self.ai_method)
        form.addRow("Model:", self.ai_model)
        group.setLayout(form)
        layout.addWidget(group)

        layout.addStretch()
        self.tabs.addTab(tab, "⚙️ Application")

    def load_settings(self):
        s = settings.get_all()
        
        # Credentials
        self.petfood_user.setText(s.get("petfood_username", ""))
        self.petfood_pass.setText(s.get("petfood_password", ""))
        self.phillips_user.setText(s.get("phillips_username", ""))
        self.phillips_pass.setText(s.get("phillips_password", ""))
        self.orgill_user.setText(s.get("orgill_username", ""))
        self.orgill_pass.setText(s.get("orgill_password", ""))
        
        # ShopSite
        self.ss_client_id.setText(s.get("shopsite_client_id", ""))
        self.ss_secret.setText(s.get("shopsite_secret_key", ""))
        self.ss_auth_code.setText(s.get("shopsite_authorization_code", ""))
        self.ss_auth_url.setText(s.get("shopsite_auth_url", ""))
        self.ss_user.setText(s.get("shopsite_username", ""))
        self.ss_pass.setText(s.get("shopsite_password", ""))
        
        # App
        self.db_path.setText(s.get("database_path", ""))
        self.chk_headless.setChecked(s.get("selenium_headless", True))
        self.chk_debug.setChecked(s.get("debug_mode", False))
        self.spin_timeout.setValue(s.get("selenium_timeout", 30))
        
        # AI
        self.ai_key.setText(s.get("openrouter_api_key", ""))
        self.ai_method.setCurrentText(s.get("classification_method", "llm"))
        self.ai_model.setText(s.get("ollama_model", "llama3.2"))

    def save_settings(self):
        try:
            # Credentials
            settings.set("petfood_username", self.petfood_user.text())
            settings.set("petfood_password", self.petfood_pass.text())
            settings.set("phillips_username", self.phillips_user.text())
            settings.set("phillips_password", self.phillips_pass.text())
            settings.set("orgill_username", self.orgill_user.text())
            settings.set("orgill_password", self.orgill_pass.text())
            
            # ShopSite
            settings.set("shopsite_client_id", self.ss_client_id.text())
            settings.set("shopsite_secret_key", self.ss_secret.text())
            settings.set("shopsite_authorization_code", self.ss_auth_code.text())
            settings.set("shopsite_auth_url", self.ss_auth_url.text())
            settings.set("shopsite_username", self.ss_user.text())
            settings.set("shopsite_password", self.ss_pass.text())
            
            # App
            settings.set("database_path", self.db_path.text())
            settings.set("selenium_headless", self.chk_headless.isChecked())
            settings.set("debug_mode", self.chk_debug.isChecked())
            settings.set("selenium_timeout", self.spin_timeout.value())
            
            # AI
            settings.set("openrouter_api_key", self.ai_key.text())
            settings.set("classification_method", self.ai_method.currentText())
            settings.set("ollama_model", self.ai_model.text())
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def reset_to_defaults(self):
        if QMessageBox.question(self, "Confirm Reset", "Reset all settings to defaults?") == QMessageBox.StandardButton.Yes:
            settings.reset_to_defaults()
            self.load_settings()

    def browse_db(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select Database", self.db_path.text(), "SQLite DB (*.db)")
        if path:
            self.db_path.setText(path)
