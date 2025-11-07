import sys
import traceback
from datetime import datetime
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QTextCursor, QIcon, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QLabel,
    QFrame,
    QSplitter,
    QGroupBox,
    QScrollArea,
    QMenuBar,
    QMenu,
    QStatusBar,
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QCheckBox,
    QComboBox,
)

# Ensure project root is on sys.path so we can import from scripts
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Conditional import for core logic to ensure GUI is runnable even if main fails.
try:
    from scripts.run_scraper import (
        run_scraping, 
        run_discontinued_check, 
        run_db_refresh, 
        run_scraper_tests,
        run_shopsite_xml_download
    )
except ImportError as e:
    print(f"Error importing from main: {e}")
    # Provide dummy functions if the import fails, so the GUI can still load.
    def run_scraping(*args, **kwargs):
        """Dummy function for scraping if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Scraping logic not found.")
        print("Error: Scraping logic not found.")
    def run_discontinued_check(*args, **kwargs):
        """Dummy function for discontinued check if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Discontinued check logic not found.")
        print("Error: Discontinued check logic not found.")
    def run_db_refresh(*args, **kwargs):
        """Dummy function for DB refresh if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: DB refresh logic not found.")
        print("Error: DB refresh logic not found.")
    def run_scraper_tests(*args, **kwargs):
        """Dummy function for scraper tests if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Scraper test logic not found.")
        print("Error: Scraper test logic not found.")
    def run_shopsite_xml_download(*args, **kwargs):
        """Dummy function for XML download if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: XML download logic not found.")
        print("Error: XML download logic not found.")


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:
    - finished: No data
    - error: tuple (exctype, value, traceback.format_exc())
    - result: object
    - progress: int
    - log: str
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class Worker(QThread):
    """
    Worker thread for executing long-running tasks without blocking the GUI.

    Inherits from QThread and uses a signal-based system to communicate
    with the main thread.

    Args:
        fn (function): The function to execute in the worker thread.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Inject progress and log callbacks into the target function's kwargs
        self.kwargs["progress_callback"] = self.signals.progress
        self.kwargs["log_callback"] = self.signals.log.emit

    def run(self):
        """
        Execute the worker's target function and emit signals.

        Emits 'error' on exception, 'result' on success, and 'finished'
        once the execution is complete.
        """
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            # Emit error signal with exception details
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        else:
            # Emit result signal with the function's return value
            self.signals.result.emit(result)
        finally:
            # Emit finished signal regardless of outcome
            self.signals.finished.emit()


class LogViewer(QTextEdit):
    """Professional log viewer with color-coded messages and filtering"""
    
    LOG_COLORS = {
        'DEBUG': '#888888',
        'INFO': '#2196F3',
        'SUCCESS': '#4CAF50',
        'WARNING': '#FF9800',
        'ERROR': '#F44336',
    }
    
    LOG_ICONS = {
        'DEBUG': '🔧',
        'INFO': 'ℹ️',
        'SUCCESS': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
    }
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.auto_scroll = True
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
    def log(self, message, level='INFO'):
        """Add a timestamped, color-coded log entry"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color = self.LOG_COLORS.get(level, '#000000')
        icon = self.LOG_ICONS.get(level, '•')
        
        formatted = f'<span style="color: {color}"><b>[{timestamp}]</b> {icon} {message}</span>'
        self.append(formatted)
        
        if self.auto_scroll:
            self.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_logs(self):
        """Clear all log entries"""
        self.clear()
        self.log("Logs cleared", "INFO")


class ActionCard(QGroupBox):
    """A styled action card widget for organized UI sections"""
    
    def __init__(self, title, icon=""):
        super().__init__()
        self.setTitle(f"{icon} {title}" if icon else title)
        self.setStyleSheet("""
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
        """)
        
        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.setLayout(self.layout)
    
    def add_button(self, text, callback, tooltip="", icon=""):
        """Add a styled button to the card"""
        button = QPushButton(f"{icon} {text}" if icon else text)
        button.setMinimumHeight(40)
        button.setToolTip(tooltip)
        button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px;
                text-align: left;
                font-weight: normal;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #2196F3;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
            }
        """)
        button.clicked.connect(callback)
        self.layout.addWidget(button)
        return button


class MainWindow(QMainWindow):
    """
    Professional Product Scraper GUI with modern interface.
    
    Features:
    - Organized action cards
    - Professional log viewer
    - Real-time status updates
    - Menu bar navigation
    - Responsive layout
    """
    def __init__(self):
        """Initialize the main window with professional UI"""
        super().__init__()

        self.setWindowTitle("ProductScraper - Professional Product Management")
        self.setMinimumSize(1200, 700)
        self.worker = None
        
        # Database stats
        self.db_product_count = 0
        self.last_operation = "None"
        
        # Create UI components
        self.create_menu_bar()
        self.create_central_widget()
        self.create_status_bar()
        
        # Initial status
        self.log_message("Application started successfully", "SUCCESS")
        self.update_database_stats()

    def create_menu_bar(self):
        """Create the menu bar with all application menus"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("📂 Open Excel File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_excel_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("❌ Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Database Menu
        db_menu = menubar.addMenu("&Database")
        
        view_products_action = QAction("👁️ View/Edit Products", self)
        view_products_action.triggered.connect(self.open_product_viewer)
        db_menu.addAction(view_products_action)
        
        db_stats_action = QAction("📊 Database Statistics", self)
        db_stats_action.triggered.connect(self.show_database_statistics)
        db_menu.addAction(db_stats_action)
        
        db_menu.addSeparator()
        
        refresh_db_action = QAction("🔄 Refresh from XML", self)
        refresh_db_action.triggered.connect(self.start_db_refresh)
        db_menu.addAction(refresh_db_action)
        
        download_xml_action = QAction("⬇️ Download ShopSite XML", self)
        download_xml_action.triggered.connect(self.start_xml_download)
        db_menu.addAction(download_xml_action)
        
        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        
        classify_action = QAction("🏷️ Classify Excel File", self)
        classify_action.triggered.connect(self.classify_excel_file)
        tools_menu.addAction(classify_action)
        
        tests_action = QAction("🧪 Run Scraper Tests", self)
        tests_action.triggered.connect(self.start_scraper_tests)
        tools_menu.addAction(tests_action)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        
        clear_logs_action = QAction("🗑️ Clear Logs", self)
        clear_logs_action.setShortcut("Ctrl+L")
        clear_logs_action.triggered.connect(self.clear_logs)
        view_menu.addAction(clear_logs_action)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_central_widget(self):
        """Create the main central widget with splitter layout"""
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #1e1e1e;")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Action cards
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Logs and status
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes (30% left, 70% right)
        splitter.setSizes([350, 850])
        
        main_layout.addWidget(splitter)
    
    def create_left_panel(self):
        """Create the left panel with action cards"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(300)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Scraping Operations Card
        scraping_card = ActionCard("Scraping Operations", "📦")
        self.start_scraping_btn = scraping_card.add_button(
            "Start Scraping",
            self.start_scraping,
            "Select an Excel file and start scraping product data",
            "▶️"
        )
        self.check_discontinued_btn = scraping_card.add_button(
            "Check Discontinued",
            self.start_discontinued_check,
            "Check which products have been discontinued",
            "🔍"
        )
        layout.addWidget(scraping_card)
        
        # Database Operations Card
        database_card = ActionCard("Database Operations", "💾")
        self.refresh_db_btn = database_card.add_button(
            "Refresh from XML",
            self.start_db_refresh,
            "Update database from ShopSite XML file",
            "🔄"
        )
        self.download_xml_btn = database_card.add_button(
            "Download XML",
            self.start_xml_download,
            "Download latest XML from ShopSite",
            "⬇️"
        )
        self.view_products_btn = database_card.add_button(
            "View/Edit Products",
            self.open_product_viewer,
            "Browse and edit products in database",
            "👁️"
        )
        self.db_stats_btn = database_card.add_button(
            "Database Statistics",
            self.show_database_statistics,
            "View database statistics and metrics",
            "📊"
        )
        layout.addWidget(database_card)
        
        # Tools Card
        tools_card = ActionCard("Tools", "🛠️")
        self.classify_btn = tools_card.add_button(
            "Classify Excel File",
            self.classify_excel_file,
            "Classify products in an Excel file",
            "🏷️"
        )
        self.run_tests_btn = tools_card.add_button(
            "Run Tests",
            self.start_scraper_tests,
            "Run automated scraper tests",
            "🧪"
        )
        layout.addWidget(tools_card)
        
        # Store buttons for enabling/disabling
        self.action_buttons = [
            self.start_scraping_btn,
            self.check_discontinued_btn,
            self.refresh_db_btn,
            self.download_xml_btn,
            self.view_products_btn,
            self.db_stats_btn,
            self.classify_btn,
            self.run_tests_btn,
        ]
        
        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area
    
    def create_right_panel(self):
        """Create the right panel with status and logs"""
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Status card
        status_card = QGroupBox("📊 Status")
        status_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
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
                color: #4CAF50;
            }
        """)
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("● Ready")
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #4CAF50;")
        status_layout.addWidget(self.status_label)
        
        self.db_status_label = QLabel("🗄️ Database: Checking...")
        self.db_status_label.setFont(QFont("Arial", 9))
        self.db_status_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.db_status_label)
        
        self.last_operation_label = QLabel("📋 Last Operation: None")
        self.last_operation_label.setFont(QFont("Arial", 9))
        self.last_operation_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.last_operation_label)
        
        status_card.setLayout(status_layout)
        layout.addWidget(status_card)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3e3e3e;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Log viewer
        log_card = QGroupBox("📋 Activity Log")
        log_card.setStyleSheet("""
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
        """)
        log_layout = QVBoxLayout()
        
        self.log_viewer = LogViewer()
        log_layout.addWidget(self.log_viewer)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.clear_logs)
        log_controls.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.setMaximumWidth(100)
        export_btn.clicked.connect(self.export_logs)
        log_controls.addWidget(export_btn)
        
        log_controls.addStretch()
        
        auto_scroll_cb = QCheckBox("Auto-scroll")
        auto_scroll_cb.setChecked(True)
        auto_scroll_cb.stateChanged.connect(
            lambda state: setattr(self.log_viewer, 'auto_scroll', state == Qt.CheckState.Checked.value)
        )
        log_controls.addWidget(auto_scroll_cb)
        
        log_layout.addLayout(log_controls)
        log_card.setLayout(log_layout)
        layout.addWidget(log_card, 1)  # Give log viewer most space
        
        return container
    
    def create_status_bar(self):
        """Create the status bar at the bottom"""
        self.statusBar().showMessage("Ready")
        
        # Add database info to status bar
        self.status_db_label = QLabel("Database: Loading...")
        self.status_db_label.setStyleSheet("color: #ffffff;")
        self.statusBar().addPermanentWidget(self.status_db_label)
    
    def _set_buttons_enabled(self, enabled):
        """Enable or disable all action buttons to prevent concurrent runs"""
        for button in self.action_buttons:
            button.setEnabled(enabled)

    def _run_worker(self, fn, *args, **kwargs):
        """Generic method to run a function in the worker thread"""
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)
        self.update_status("Running...", "working")

        # Create and configure the worker thread
        self.worker = Worker(fn, *args, **kwargs)

        # Connect worker signals to the appropriate slots in the main window
        self.worker.signals.log.connect(self.log_message)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.finished.connect(self.worker_finished)

        # Start the worker thread
        self.worker.start()

    def start_scraping(self):
        """Open file dialog and start scraping process"""
        file_path = self.select_excel_file()
        if file_path:
            # Get available sites
            available_sites = self.get_available_sites()
            if not available_sites:
                self.log_message("No scraping sites available", "ERROR")
                return
            
            # Show site selection dialog
            selected_sites = self.select_sites_dialog(available_sites)
            if not selected_sites:
                self.log_message("No sites selected", "WARNING")
                return
            
            self.last_operation = "Scraping"
            self.log_message(f"Starting scraping for: {os.path.basename(file_path)} on sites: {', '.join(selected_sites)}", "INFO")
            self._run_worker(run_scraping, file_path, interactive=False, selected_sites=selected_sites)

    def start_discontinued_check(self):
        """Open file dialog and start discontinued check"""
        file_path = self.select_excel_file()
        if file_path:
            self.last_operation = "Discontinued Check"
            self.log_message(f"Starting discontinued check for: {os.path.basename(file_path)}", "INFO")
            self._run_worker(run_discontinued_check, file_path)

    def start_db_refresh(self):
        """Start database refresh from XML"""
        self.last_operation = "Database Refresh"
        self.log_message("Starting database refresh from XML...", "INFO")
        self._run_worker(run_db_refresh)
    
    def start_xml_download(self):
        """Download XML from ShopSite"""
        self.last_operation = "XML Download"
        self.log_message("Downloading XML from ShopSite...", "INFO")
        self._run_worker(run_shopsite_xml_download)
    
    def open_product_viewer(self):
        """Open the product viewer window"""
        try:
            self.log_message("Opening product viewer...", "INFO")
            import subprocess
            viewer_path = os.path.join(PROJECT_ROOT, "src", "ui", "product_viewer.py")
            subprocess.Popen([sys.executable, viewer_path])
            self.log_message("Product viewer launched", "SUCCESS")
        except Exception as e:
            self.log_message(f"Failed to open product viewer: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open product viewer:\n{e}")
    
    def show_database_statistics(self):
        """Show database statistics dialog"""
        try:
            from src.core.database_queries import ProductDatabase
            db = ProductDatabase()
            db.connect()
            
            stats = {
                "Total Products": f"{db.get_product_count():,}",
                "Available Fields": len(db.get_sample_fields())
            }
            
            db.disconnect()
            
            msg = "Database Statistics:\n\n"
            for key, value in stats.items():
                msg += f"{key}: {value}\n"
            
            QMessageBox.information(self, "Database Statistics", msg)
            self.log_message("Displayed database statistics", "INFO")
            
        except Exception as e:
            self.log_message(f"Failed to get database statistics: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to get database statistics:\n{e}")
    
    def classify_excel_file(self):
        """Classify products in an Excel file"""
        file_path = self.select_excel_file()
        if file_path:
            self.last_operation = "Classification"
            self.log_message(f"Starting classification for: {os.path.basename(file_path)}", "INFO")
            self._run_worker(self.run_classification_worker, file_path)
    
    def run_classification_worker(self, file_path, log_callback=None, progress_callback=None):
        """Worker function to run classification"""
        import pandas as pd
        from src.ui.product_classify_ui import edit_classification_in_batch
        from src.core.classification.classifier import classify_products_batch
        
        log = log_callback if log_callback else print
        
        try:
            log("Loading Excel file...")
            if progress_callback:
                progress_callback.emit(10)
            
            df = pd.read_excel(file_path, dtype=str)
            log(f"Loaded {len(df)} rows from Excel file")
            
            if df.empty:
                log("Excel file is empty")
                return
            
            if progress_callback:
                progress_callback.emit(20)
            
            # Check required columns
            required_cols = ['SKU', 'Name']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                log(f"Missing required columns: {missing_cols}")
                return
            
            if progress_callback:
                progress_callback.emit(30)
            
            # Convert Excel columns to internal format
            products_list = []
            for _, row in df.iterrows():
                product = {
                    'SKU': str(row.get('SKU', '')).strip(),
                    'Name': str(row.get('Name', '')).strip(),
                    'Brand': str(row.get('Product Field 16', '')).strip(),
                    'Price': str(row.get('Price', '')).strip(),
                    'Weight': str(row.get('Weight', '')).strip(),
                    'Images': str(row.get('Images', '')).strip(),
                    'Special Order': 'yes' if str(row.get('Product Field 11', '')).strip().lower() == 'yes' else '',
                    'Category': '',
                    'Product Type': '',
                    'Product On Pages': '',
                    'Product Cross Sell': str(row.get('Product Field 32', '')).strip(),
                    'Product Disabled': 'checked' if str(row.get('ProductDisabled', '')).strip().lower() == 'checked' else 'uncheck'
                }
                products_list.append(product)
            
            log(f"Converted {len(products_list)} products to internal format")
            
            if progress_callback:
                progress_callback.emit(50)
            
            # Run automatic classification
            log("Running automatic classification...")
            products_list = classify_products_batch(products_list)
            log("Automatic classification complete")
            
            if progress_callback:
                progress_callback.emit(70)
            
            # Save back to Excel
            from datetime import datetime
            excel_data = []
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for product in products_list:
                row = {
                    'SKU': product.get('SKU', ''),
                    'Name': product.get('Name', ''),
                    'Price': product.get('Price', ''),
                    'Images': product.get('Images', ''),
                    'Weight': product.get('Weight', ''),
                    'Product Field 16': product.get('Brand', ''),
                    'Product Field 11': 'yes' if product.get('Special Order') == 'yes' else '',
                    'Product Field 24': product.get('Category', ''),
                    'Product Field 25': product.get('Product Type', ''),
                    'Product On Pages': product.get('Product On Pages', ''),
                    'Product Field 32': product.get('Product Cross Sell', ''),
                    'ProductDisabled': 'checked' if product.get('Product Disabled') == 'checked' else 'uncheck',
                    'Last Edited': timestamp
                }
                excel_data.append(row)
            
            if progress_callback:
                progress_callback.emit(90)
            
            # Save to Excel
            save_path = file_path
            if file_path.lower().endswith('.xls'):
                save_path = file_path[:-4] + '.xlsx'
                log(f"Converting to .xlsx format: {save_path}")
            
            new_df = pd.DataFrame(excel_data)
            new_df.to_excel(save_path, index=False)
            
            log(f"Saved {len(products_list)} classified products to: {save_path}")
            log("Classification complete!")
            
            if progress_callback:
                progress_callback.emit(100)
            
        except Exception as e:
            log(f"Error during classification: {e}")
            import traceback
            log(traceback.format_exc())
            raise
    
    def get_available_sites(self):
        """Get list of available scraping sites"""
        try:
            from src.scrapers.master import discover_scrapers
            scraping_options, _ = discover_scrapers()
            return list(scraping_options.keys())
        except Exception as e:
            self.log_message(f"Error getting available sites: {e}", "ERROR")
            return []
    
    def select_sites_dialog(self, available_sites):
        """Show dialog to select which sites to scrape"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Scraping Sites")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select the websites to scrape from:")
        layout.addWidget(label)
        
        # List widget with checkboxes
        list_widget = QListWidget()
        for site in available_sites:
            item = QListWidgetItem(site)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)  # Default to checked
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        
        # Select All / Deselect All buttons
        buttons_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_sites_checked(list_widget, True))
        buttons_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self._set_all_sites_checked(list_widget, False))
        buttons_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(buttons_layout)
        
        # OK/Cancel buttons
        button_box = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        button_box.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_box.addWidget(cancel_btn)
        
        layout.addLayout(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_sites = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected_sites.append(item.text())
            return selected_sites
        else:
            return []
    
    def _set_all_sites_checked(self, list_widget, checked):
        """Set all sites checked or unchecked"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(list_widget.count()):
            list_widget.item(i).setCheckState(state)

    def select_excel_file(self):
        """Open file dialog to select Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            os.path.join(PROJECT_ROOT, "data", "input"),
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        return file_path

    def start_scraper_tests(self):
        """Start scraper test process with integration tests"""
        self.last_operation = "Scraper Tests"
        self.log_message("Starting scraper tests...", "INFO")
        self._run_worker(run_scraper_tests, run_integration=True)

    def log_message(self, message, level="INFO"):
        """Add a message to the log viewer"""
        # Convert old-style emoji messages to log levels
        if message.startswith("❌"):
            level = "ERROR"
            message = message[2:].strip()
        elif message.startswith("✅"):
            level = "SUCCESS"
            message = message[2:].strip()
        elif message.startswith("⚠️"):
            level = "WARNING"
            message = message[2:].strip()
        elif message.startswith("🔧") or message.startswith("💾") or message.startswith("🚀"):
            level = "INFO"
            message = message[2:].strip()
        
        self.log_viewer.log(message, level)
        
        # Also update status bar for important messages
        if level in ["ERROR", "SUCCESS"]:
            self.statusBar().showMessage(message, 5000)

    def update_progress(self, value):
        """Update the progress bar value"""
        self.progress_bar.setValue(value)
        
    def update_status(self, message, status_type="ready"):
        """Update the status indicator"""
        colors = {
            "ready": "#4CAF50",
            "working": "#FF9800",
            "error": "#F44336"
        }
        icons = {
            "ready": "●",
            "working": "⟳",
            "error": "✖"
        }
        
        color = colors.get(status_type, "#4CAF50")
        icon = icons.get(status_type, "●")
        
        self.status_label.setText(f"{icon} {message}")
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_database_stats(self):
        """Update database statistics in the UI"""
        try:
            from src.core.database_queries import ProductDatabase
            db = ProductDatabase()
            db.connect()
            self.db_product_count = db.get_product_count()
            db.disconnect()
            
            self.db_status_label.setText(f"🗄️ Database: {self.db_product_count:,} products")
            self.status_db_label.setText(f"DB: {self.db_product_count:,} products")
            
        except Exception as e:
            self.db_status_label.setText("🗄️ Database: Not available")
            self.status_db_label.setText("DB: Not available")
    
    def clear_logs(self):
        """Clear the log viewer"""
        reply = QMessageBox.question(
            self,
            "Clear Logs",
            "Are you sure you want to clear all logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log_viewer.clear_logs()
    
    def export_logs(self):
        """Export logs to a text file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"ProductScraper_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_viewer.toPlainText())
                self.log_message(f"Logs exported to: {file_path}", "SUCCESS")
                QMessageBox.information(self, "Success", "Logs exported successfully!")
            except Exception as e:
                self.log_message(f"Failed to export logs: {e}", "ERROR")
                QMessageBox.critical(self, "Error", f"Failed to export logs:\n{e}")
    
    def show_about_dialog(self):
        """Show about dialog"""
        about_text = """
        <h2>ProductScraper</h2>
        <p><b>Professional Product Management System</b></p>
        <p>Version 2.0</p>
        <p>A comprehensive tool for scraping, managing, and organizing product data.</p>
        <p>&copy; 2025 BayStatePet</p>
        """
        QMessageBox.about(self, "About ProductScraper", about_text)

    def handle_error(self, error_tuple):
        """Handle errors emitted from the worker thread"""
        err_type, err_val, err_tb = error_tuple
        self.log_message(f"An error occurred: {err_val}", "ERROR")
        self.log_message(f"Error details: {err_tb}", "DEBUG")
        
        self.update_status("Error", "error")

        # Show error dialog with details
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("Operation Failed")
        error_dialog.setText(f"An error occurred during {self.last_operation}:")
        error_dialog.setInformativeText(str(err_val))
        error_dialog.setDetailedText(err_tb)
        error_dialog.exec()
        
        self.worker_finished(is_error=True)

    def worker_finished(self, is_error=False):
        """Called when the worker thread is finished"""
        if not is_error:
            self.progress_bar.setValue(100)
            self.log_message(f"{self.last_operation} completed successfully", "SUCCESS")
            self.update_status("Ready", "ready")
            self.last_operation_label.setText(f"📋 Last Operation: {self.last_operation} (Success)")
            
            # Update database stats after operations that might change it
            if self.last_operation in ["Database Refresh", "XML Download", "Scraping"]:
                QTimer.singleShot(1000, self.update_database_stats)
        else:
            self.update_status("Ready", "ready")
            self.last_operation_label.setText(f"📋 Last Operation: {self.last_operation} (Failed)")
        
        self._set_buttons_enabled(True)
        self.worker = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())