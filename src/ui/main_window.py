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

import os
from pathlib import Path

# Conditional import for core logic to ensure GUI is runnable even if main fails.
# Check scraper system preference
from src.core.settings_manager import settings
scraper_system = settings.get("scraper_system", "new")

try:
    if scraper_system == "legacy":
        print("🔄 GUI using legacy archived scraper system...")
        from src.scrapers_archive.main import (
            run_scraping,
            run_db_refresh,
            run_shopsite_xml_download,
            run_shopsite_publish
        )
        # DEPRECATION WARNING: Using legacy system
        import warnings
        warnings.warn(
            "GUI is configured to use the deprecated archived scraper system. "
            "Consider switching to the new modular scraper system in settings. "
            "See docs/SCRAPER_MIGRATION_GUIDE.md for migration instructions.",
            DeprecationWarning,
            stacklevel=2
        )
    else:
        print("🚀 GUI using new modular scraper system...")
        from src.scrapers.main import run_scraping
        # Import legacy functions for backward compatibility
        from src.scrapers_archive.main import (
            run_db_refresh,
            run_shopsite_xml_download,
            run_shopsite_publish
        )

    from src.utils.run_scraper import (
        run_scraper_tests,
        run_scraper_integration_tests,
    )
except ImportError as e:
    print(f"Error importing scraper functions: {e}")

    # Provide dummy functions if the import fails, so the GUI can still load.
    def run_scraping(*args, **kwargs):
        """Dummy function for scraping if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: Scraping logic not found.")
            else:
                log_callback("Error: Scraping logic not found.")

    def run_db_refresh(*args, **kwargs):
        """Dummy function for DB refresh if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: DB refresh logic not found.")
            else:
                log_callback("Error: DB refresh logic not found.")

    def run_scraper_tests(*args, **kwargs) -> bool:
        """Dummy function for scraper tests if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: Scraper test logic not found.")
            else:
                log_callback("Error: Scraper test logic not found.")
        return False

    def run_scraper_integration_tests(*args, **kwargs):
        """Dummy function for scraper integration tests if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: Scraper integration test logic not found.")
            else:
                log_callback("Error: Scraper integration test logic not found.")
        return False
    def run_shopsite_xml_download(*args, **kwargs):
        """Dummy function for ShopSite XML download if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: ShopSite XML download logic not found.")
            else:
                log_callback("Error: ShopSite XML download logic not found.")
    def run_shopsite_publish(*args, **kwargs):
        """Dummy function for ShopSite publish if import fails."""
        log_callback = kwargs.get("log_callback")
        if log_callback:
            if hasattr(log_callback, 'emit'):
                log_callback.emit("Error: ShopSite publish logic not found.")
            else:
                log_callback("Error: ShopSite publish logic not found.")


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:
    - finished: No data
    - error: tuple (exctype, value, traceback.format_exc())
    - result: object
    - progress: int
    - log: str
    - status: str (status message update)
    - metrics: dict (execution metrics like elapsed time, processed count, etc.)
    - request_editor_sync: list (products), object (result container), str (editor type)
    - request_confirmation_sync: str (title), str (text), object (result container)
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    status = pyqtSignal(str)
    metrics = pyqtSignal(dict)
    request_editor_sync = pyqtSignal(list, object, str)  # products_list, result_container, editor_type
    request_confirmation_sync = pyqtSignal(str, str, object) # title, text, result_container


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
        self._is_cancelled = False

        # Inject progress and log callbacks into the target function's kwargs
        # Pass signal objects directly - run_scraper.py expects objects with .emit()
        self.kwargs["progress_callback"] = self.signals.progress
        self.kwargs["log_callback"] = self.signals.log
        self.kwargs["status_callback"] = self.signals.status
        self.kwargs["metrics_callback"] = self.signals.metrics
        self.kwargs["editor_callback"] = self._request_editor_sync
        self.kwargs["confirmation_callback"] = self._request_confirmation_sync

    def cancel(self):
        """Cancel the running task"""
        self._is_cancelled = True
        self.requestInterruption()
        self.quit()

    def _request_confirmation_sync(self, title, text):
        """Request a confirmation dialog on the main thread and wait for the result."""
        from PyQt6.QtCore import QEventLoop
        result_container = {"result": None, "done": False}
        self.signals.request_confirmation_sync.emit(title, text, result_container)
        
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(lambda: result_container["done"] and loop.quit())
        timer.start(100)
        loop.exec()
        timer.stop()
        
        return result_container["result"]

    def _request_editor_sync(self, products_list, editor_type='product'):
        """Request editor on main thread and wait for result (synchronous from worker's perspective)"""
        from PyQt6.QtCore import QEventLoop

        # Create container for result
        result_container = {"result": None, "done": False}

        # Emit signal to main thread with products and result container
        self.signals.request_editor_sync.emit(products_list, result_container, editor_type)

        # Wait for main thread to complete
        loop = QEventLoop()

        # Poll until done
        from PyQt6.QtCore import QTimer

        def check_done():
            if result_container["done"]:
                loop.quit()

        timer = QTimer()
        timer.timeout.connect(check_done)
        timer.start(100)  # Check every 100ms

        loop.exec()  # Block until done
        timer.stop()

        return result_container["result"]

    def run(self):
        """
        Execute the worker's target function and emit signals.

        Supports both synchronous and asynchronous functions.
        For async functions, creates a new event loop in the thread.
        Emits 'error' on exception, 'result' on success, and 'finished'
        once the execution is complete.
        """
        import asyncio
        import inspect

        try:
            if inspect.iscoroutinefunction(self.fn):
                # Async function: create new event loop in this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.fn(*self.args, **self.kwargs))
                finally:
                    loop.close()
            else:
                # Synchronous function
                result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            # Emit error signal with exception details
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        else:
            # Emit result signal with the function's return value
            if not self._is_cancelled:
                self.signals.result.emit(result)
        finally:
            # Emit finished signal regardless of outcome
            self.signals.finished.emit()


class LogViewer(QTextEdit):
    """Professional log viewer with color-coded messages and filtering"""

    LOG_COLORS = {
        "DEBUG": "#888888",
        "INFO": "#2196F3",
        "SUCCESS": "#4CAF50",
        "WARNING": "#FF9800",
        "ERROR": "#F44336",
    }

    LOG_ICONS = {
        "DEBUG": "🔧",
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
    }

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.auto_scroll = True
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 4px;
            }
        """
        )

    def log(self, message, level="INFO"):
        """Add a timestamped, color-coded log entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.LOG_COLORS.get(level, "#000000")
        icon = self.LOG_ICONS.get(level, "•")

        formatted = (
            f'<span style="color: {color}"><b>[{timestamp}]</b> {icon} {message}</span>'
        )
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
        self.setStyleSheet(
            """
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
        """
        )

        self._layout = QVBoxLayout()
        self._layout.setSpacing(8)
        self.setLayout(self._layout)

    def add_button(self, text, callback, tooltip="", icon=""):
        """Add a styled button to the card"""
        button = QPushButton(f"{icon} {text}" if icon else text)
        button.setMinimumHeight(40)
        button.setToolTip(tooltip)
        button.setStyleSheet(
            """
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
        """
        )
        button.clicked.connect(callback)
        self._layout.addWidget(button)
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
        
        # Apply the global dark theme.
        try:
            from src.ui.styling import STYLESHEET
            self.setStyleSheet(STYLESHEET)
        except (ImportError, ModuleNotFoundError):
            print("CRITICAL: Could not import stylesheet. UI will be unstyled.")
            # Fallback to a very basic theme if the import fails
            self.setStyleSheet("QMainWindow { background-color: #1e1e1e; color: #ffffff; }")

        # Initial status
        self.log_message("Application started successfully", "SUCCESS")
        self.update_database_stats()

    def create_menu_bar(self):
        """Create the menu bar with all application menus"""
        menubar = self.menuBar()
        if menubar is None:
            return

        # File Menu
        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return

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
        if db_menu is None:
            return

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

        publish_shopsite_action = QAction("🚀 Publish to ShopSite", self)
        publish_shopsite_action.triggered.connect(self.start_shopsite_publish)
        db_menu.addAction(publish_shopsite_action)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")
        if tools_menu is None:
            return

        classify_action = QAction("🏷️ Classify Excel File", self)
        classify_action.triggered.connect(self.classify_excel_file)
        tools_menu.addAction(classify_action)

        tests_action = QAction("🧪 Run Scraper Tests", self)
        tests_action.triggered.connect(self.start_scraper_tests)
        tools_menu.addAction(tests_action)

        # View Menu
        view_menu = menubar.addMenu("&View")
        if view_menu is None:
            return

        view_menu.addSeparator()

        clear_logs_action = QAction("🗑️ Clear Logs", self)
        clear_logs_action.setShortcut("Ctrl+L")
        clear_logs_action.triggered.connect(self.clear_logs)
        view_menu.addAction(clear_logs_action)

        # Settings Menu
        settings_menu = menubar.addMenu("&Settings")
        if settings_menu is None:
            return

        settings_action = QAction("⚙️ Settings", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        if help_menu is None:
            return

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
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """
        )

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
            "▶️",
        )
        self.cancel_scraping_btn = scraping_card.add_button(
            "Cancel Scraping",
            self.cancel_scraping,
            "Cancel the currently running scraping operation",
            "⏹️",
        )
        self.cancel_scraping_btn.setEnabled(False)  # Disabled by default
        layout.addWidget(scraping_card)

        # Database Operations Card
        database_card = ActionCard("Database Operations", "💾")
        self.refresh_db_btn = database_card.add_button(
            "Refresh from XML",
            self.start_db_refresh,
            "Update database from ShopSite XML file",
            "🔄",
        )
        self.download_xml_btn = database_card.add_button(
            "Download XML",
            self.start_xml_download,
            "Download latest XML from ShopSite",
            "⬇️",
        )
        self.publish_shopsite_btn = database_card.add_button(
            "Publish to ShopSite",
            self.start_shopsite_publish,
            "Publish changes to ShopSite website",
            "🚀",
        )
        self.view_products_btn = database_card.add_button(
            "View/Edit Products",
            self.open_product_viewer,
            "Browse and edit products in database",
            "👁️",
        )
        self.db_stats_btn = database_card.add_button(
            "Database Statistics",
            self.show_database_statistics,
            "View database statistics and metrics",
            "📊",
        )
        layout.addWidget(database_card)

        # Tools Card
        tools_card = ActionCard("Tools", "🛠️")
        self.classify_btn = tools_card.add_button(
            "Classify Excel File",
            self.classify_excel_file,
            "Classify products in an Excel file",
            "🏷️",
        )
        self.run_tests_btn = tools_card.add_button(
            "Run Tests", self.start_scraper_tests, "Run automated scraper tests", "🧪"
        )
        self.add_scraper_btn = tools_card.add_button(
            "Add New Scraper",
            self.add_new_scraper,
            "Create a new scraper configuration",
            "➕",
        )
        self.manage_scrapers_btn = tools_card.add_button(
            "Manage Scrapers",
            self.manage_scrapers,
            "View and edit existing scraper configurations",
            "⚙️",
        )
        self.scraper_builder_btn = tools_card.add_button(
            "Scraper Builder",
            self.open_scraper_builder,
            "Build new scrapers with AI-assisted selector generation",
            "🤖",
        )
        layout.addWidget(tools_card)

        # Store buttons for enabling/disabling
        self.action_buttons = [
            self.start_scraping_btn,
            self.refresh_db_btn,
            self.download_xml_btn,
            self.publish_shopsite_btn,
            self.view_products_btn,
            self.db_stats_btn,
            self.classify_btn,
            self.run_tests_btn,
            self.add_scraper_btn,
            self.manage_scrapers_btn,
            self.scraper_builder_btn,
        ]

        # Cancel button is handled separately - enabled when worker is running
        self.cancel_scraping_btn.setEnabled(False)

        layout.addStretch()
        scroll_area.setWidget(container)
        return scroll_area

    def cancel_scraping(self):
        """Cancel the currently running scraping operation"""
        if self.worker and self.worker.isRunning():
            self.log_message("⏹️ Cancelling scraping operation...", "WARNING")
            self.worker.cancel()
            self.update_status("Cancelling...", "working")
        else:
            self.log_message("No active scraping operation to cancel", "INFO")

    def create_right_panel(self):
        """Create the right panel with status and logs"""
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # Status card
        status_card = QGroupBox("📊 Status")
        status_card.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 0px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4CAF50;
            }
        """
        )
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

        # Execution metrics labels
        self.elapsed_label = QLabel("⏱️ Elapsed: 00:00:00")
        self.elapsed_label.setFont(QFont("Arial", 9))
        self.elapsed_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.elapsed_label)

        self.processed_label = QLabel("📦 Processed: 0/0")
        self.processed_label.setFont(QFont("Arial", 9))
        self.processed_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.processed_label)

        self.current_op_label = QLabel("🔄 Current: Idle")
        self.current_op_label.setFont(QFont("Arial", 9))
        self.current_op_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.current_op_label)

        self.eta_label = QLabel("⏳ ETA: --")
        self.eta_label.setFont(QFont("Arial", 9))
        self.eta_label.setStyleSheet("color: #ffffff;")
        status_layout.addWidget(self.eta_label)

        status_card.setLayout(status_layout)
        layout.addWidget(status_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
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
        """
        )
        layout.addWidget(self.progress_bar)

        # Log viewer
        log_card = QGroupBox("📋 Activity Log")
        log_card.setStyleSheet(
            """
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
        """
        )
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
            lambda state: setattr(
                self.log_viewer, "auto_scroll", state == Qt.CheckState.Checked.value
            )
        )
        log_controls.addWidget(auto_scroll_cb)

        log_layout.addLayout(log_controls)
        log_card.setLayout(log_layout)
        layout.addWidget(log_card, 1)  # Give log viewer most space

        return container

    def create_status_bar(self):
        """Create the status bar at the bottom"""
        status_bar = self.statusBar()
        if status_bar is None:
            return
        status_bar.showMessage("Ready")

        # Add database info to status bar
        self.status_db_label = QLabel("Database: Loading...")
        self.status_db_label.setStyleSheet("color: #ffffff;")
        status_bar.addPermanentWidget(self.status_db_label)

    def _set_buttons_enabled(self, enabled):
        """Enable or disable all action buttons to prevent concurrent runs"""
        for button in self.action_buttons:
            button.setEnabled(enabled)

    def _run_worker(self, fn, *args, **kwargs):
        """Generic method to run a function in the worker thread"""
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)
        self.cancel_scraping_btn.setEnabled(True)  # Enable cancel button when worker starts
        self.update_status("Running...", "working")
        
        # Reset metrics labels
        self.elapsed_label.setText("⏱️ Elapsed: 00:00:00")
        self.processed_label.setText("📦 Processed: 0/0")
        self.current_op_label.setText("🔄 Current: Starting...")
        self.eta_label.setText("⏳ ETA: --")

        # Create and configure the worker thread
        self.worker = Worker(fn, *args, **kwargs)

        # Connect worker signals to the appropriate slots in the main window
        self.worker.signals.log.connect(self.log_message)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.status.connect(self.update_status)
        self.worker.signals.metrics.connect(self.update_metrics)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.finished.connect(self.worker_finished)
        self.worker.signals.request_editor_sync.connect(
            self.open_editor_on_main_thread_sync
        )
        self.worker.signals.request_confirmation_sync.connect(
            self.open_confirmation_on_main_thread_sync
        )

        # Start the worker thread
        self.worker.start()

    def open_confirmation_on_main_thread_sync(self, title, text, result_container):
        """Show a confirmation dialog on the main thread and capture the result."""
        reply = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        result_container["result"] = (reply == QMessageBox.StandardButton.Yes)
        result_container["done"] = True

    def open_editor_on_main_thread_sync(self, products_list, result_container, editor_type):
        """Open a specified editor on the main GUI thread (synchronous)."""
        if editor_type == 'product':
            from src.ui.product_editor import edit_products_in_batch as editor_func
            log_msg = "product editor"
        elif editor_type == 'classification':
            from src.core.classification.ui import edit_classification_in_batch as editor_func
            log_msg = "classification editor"
        else:
            self.log_message(f"❌ Unknown editor type requested: {editor_type}", "ERROR")
            result_container["result"] = None
            result_container["done"] = True
            return

        self.log_message(f"📝 Opening {log_msg} for {len(products_list)} products...", "INFO")

        try:
            # Open editor - this runs on the main thread so it's safe
            edited_products = editor_func(products_list)

            if edited_products:
                self.log_message(
                    f"✅ User edited {len(edited_products)} products", "SUCCESS"
                )
                result_container["result"] = edited_products
            else:
                self.log_message("❌ User cancelled editing", "WARNING")
                result_container["result"] = None

        except Exception as e:
            self.log_message(f"❌ Error opening {log_msg}: {e}", "ERROR")
            import traceback

            traceback.print_exc()
            result_container["result"] = None

        # Mark as done so worker thread can continue
        result_container["done"] = True

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
            self.log_message(
                f"Starting scraping for: {os.path.basename(file_path)} on sites: {', '.join(selected_sites)}",
                "INFO",
            )
            self._run_worker(
                run_scraping,
                file_path,
                interactive=False,
                selected_sites=selected_sites,
            )

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

    def start_shopsite_publish(self):
        """Publish changes to ShopSite"""
        self.last_operation = "ShopSite Publish"
        self.log_message("Publishing changes to ShopSite...", "INFO")
        self._run_worker(run_shopsite_publish)

    def open_product_viewer(self):
        """Open the product viewer window"""
        try:
            self.log_message("Opening product viewer...", "INFO")
            import subprocess
            
            # Construct path relative to this file's location
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            viewer_path = os.path.join(project_root, "src", "ui", "product_viewer.py")

            subprocess.Popen([sys.executable, viewer_path])
            self.log_message("Product viewer launched", "SUCCESS")
        except Exception as e:
            self.log_message(f"Failed to open product viewer: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open product viewer:\n{e}")

    def open_settings(self):
        """Open the settings dialog"""
        try:
            from src.ui.settings_dialog import SettingsDialog

            dialog = SettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.log_message("Settings updated", "SUCCESS")
                # Update database stats in case database path changed
                self.update_database_stats()
        except Exception as e:
            self.log_message(f"Failed to open settings: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open settings:\n{e}")

    def show_database_statistics(self):
        """Show database statistics dialog"""
        try:
            from src.core.database.queries import ProductDatabase

            db = ProductDatabase()
            db.connect()

            stats = {
                "Total Products": f"{db.get_product_count():,}",
                "Available Fields": len(db.get_sample_fields()),
            }

            db.disconnect()

            msg = "Database Statistics:\n\n"
            for key, value in stats.items():
                msg += f"{key}: {value}\n"

            QMessageBox.information(self, "Database Statistics", msg)
            self.log_message("Displayed database statistics", "INFO")

        except Exception as e:
            self.log_message(f"Failed to get database statistics: {e}", "ERROR")
            QMessageBox.critical(
                self, "Error", f"Failed to get database statistics:\n{e}"
            )

    def classify_excel_file(self):
        """Classify products in an Excel file"""
        file_path = self.select_excel_file()
        if file_path:
            self.last_operation = "Classification"
            self.log_message(
                f"Starting classification for: {os.path.basename(file_path)}", "INFO"
            )
            self._run_worker(self.run_classification_worker, file_path)

    def run_classification_worker(
        self,
        file_path,
        log_callback=None,
        progress_callback=None,
        status_callback=None,
        editor_callback=None,
        metrics_callback=None,
    ):
        """Worker function to run classification"""
        import pandas as pd
        from src.core.classification.ui import edit_classification_in_batch
        from src.core.classification.manager import classify_products_batch

        # Determine log function
        if log_callback is None:
            log = print
        elif hasattr(log_callback, 'emit'):
            # If it's a Qt signal object, use emit method
            log = log_callback.emit
        else:
            # If it's already a callable (like emit method or function), use it directly
            log = log_callback

        try:
            log("Loading Excel file...")
            if progress_callback: progress_callback.emit(10)

            # Load the original DataFrame, keeping all original data
            df = pd.read_excel(file_path, dtype=str).fillna('')
            log(f"Loaded {len(df)} rows from Excel file")

            if df.empty:
                log("Excel file is empty")
                return

            # Check for required columns for classification
            required_cols = ["SKU", "Name"]
            if not all(col in df.columns for col in required_cols):
                missing_cols = [col for col in required_cols if col not in df.columns]
                log(f"Missing required columns for classification: {missing_cols}")
                return

            if progress_callback: progress_callback.emit(20)

            # Create a temporary list of dicts for the classification functions
            products_for_classification = df.rename(columns={
                "Product Field 16": "Brand",
                "Product Field 11": "Special Order",
                "Product Field 32": "Product Cross Sell",
                "ProductDisabled": "Product Disabled"
            }).to_dict('records')
            log(f"Converted {len(products_for_classification)} products for classification")

            if progress_callback: progress_callback.emit(40)

            # --- Classification Process ---
            from src.core.settings_manager import SettingsManager
            settings = SettingsManager()
            classification_method = settings.get("classification_method", "llm")
            
            log(f"Running automatic classification using {classification_method} method...")
            classified_products = classify_products_batch(
                products_for_classification, method=classification_method
            )
            log("Automatic classification complete")

            if progress_callback: progress_callback.emit(60)

            log("Opening manual classification editor...")
            if editor_callback:
                edited_products = editor_callback(classified_products, editor_type='classification')
            else:
                log("Editor callback not available, skipping manual edit.", "WARNING")
                edited_products = classified_products # Proceed with auto-classified data

            if edited_products is None:
                log("Classification cancelled by user. No file will be saved.")
                return

            log("Manual classification complete")
            if progress_callback: progress_callback.emit(80)
            # --- End of Classification Process ---

            # Create a DataFrame from the results
            results_df = pd.DataFrame(edited_products)

            # Set SKU as the index on both DataFrames to join the data
            df = df.set_index('SKU')
            results_df = results_df.set_index('SKU')

            # Define the mapping from classification results to final Excel columns
            column_mapping = {
                "Category": "Product Field 24",
                "Product Type": "Product Field 25",
                "Product On Pages": "Product On Pages"
            }
            
            results_to_update = results_df.rename(columns=column_mapping)
            df.update(results_to_update)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df['Last Edited'] = timestamp
            df.reset_index(inplace=True)

            # --- Save back to Excel ---
            save_path = Path(file_path)
            if save_path.suffix.lower() == ".xls":
                save_path = save_path.with_suffix(".xlsx")
                log(f"Original was .xls, saving as .xlsx to preserve features: {save_path.name}")

            df.to_excel(save_path, index=False)
            log(f"Saved {len(df)} classified products back to: {save_path}")
            log("Classification complete!")

            if progress_callback: progress_callback.emit(100)

        except Exception as e:
            log(f"Error during classification: {e}")
            import traceback
            log(traceback.format_exc())
            raise

    def get_available_sites(self):
        """Get list of available scraping sites"""
        from src.core.settings_manager import settings
        scraper_system = settings.get("scraper_system", "new")

        try:
            if scraper_system == "legacy":
                from src.scrapers_archive.master import discover_scrapers
                # DEPRECATION WARNING: Using legacy system
                import warnings
                warnings.warn(
                    "Using discover_scrapers from src.scrapers_archive.master which is deprecated. "
                    "Please migrate to the new modular scraper system. "
                    "See docs/SCRAPER_MIGRATION_GUIDE.md for migration instructions.",
                    DeprecationWarning,
                    stacklevel=2
                )
                scraping_options, _ = discover_scrapers()
                return list(scraping_options.keys())
            else:
                from src.scrapers.main import get_available_scrapers
                return get_available_scrapers()
        except Exception as e:
            self.log_message(f"Error getting available sites: {e}", "ERROR")
            return []

    def select_sites_dialog(self, available_sites):
        """Show dialog to select which sites to scrape"""
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QLabel,
            QCheckBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Scraping Sites")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)

        layout = QVBoxLayout(dialog)

        label = QLabel("Select the websites to scrape from:")
        layout.addWidget(label)

        # List widget with checkboxes
        list_widget = QListWidget()
        list_widget.setStyleSheet(
            """
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3e3e3e;
            }
            QListWidget::item {
                color: #ffffff;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: #ffffff;
            }
            QListWidget::indicator {
                width: 13px;
                height: 13px;
                border: 1px solid #888888;
                background-color: #2d2d2d;
            }
            QListWidget::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #ffffff;
            }
            QListWidget::indicator:unchecked {
                background-color: #2d2d2d;
                border: 1px solid #888888;
            }
        """
        )
        for site in available_sites:
            item = QListWidgetItem(site)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)  # Default to checked
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        # Select All / Deselect All buttons
        buttons_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(
            lambda: self._set_all_sites_checked(list_widget, True)
        )
        buttons_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(
            lambda: self._set_all_sites_checked(list_widget, False)
        )
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
                if item is not None and item.checkState() == Qt.CheckState.Checked:
                    selected_sites.append(item.text())
            return selected_sites
        else:
            return []

    def _set_all_sites_checked(self, list_widget, checked):
        """Set all sites checked or unchecked"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item is not None:
                item.setCheckState(state)

    def select_excel_file(self):
        """Open file dialog to select Excel file"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            os.path.join(project_root, "src", "data", "spreadsheets"),
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        return file_path

    def start_scraper_tests(self):
        """Start scraper integration test process - tests all scrapers with known working products"""
        self.last_operation = "Scraper Tests"
        self.log_message("Starting scraper integration tests (testing all scrapers with known working products)...", "INFO")
        self._run_worker(run_scraper_integration_tests)

    def add_new_scraper(self):
        """Open dialog to add a new scraper configuration"""
        try:
            from src.ui.scraper_management_dialog import AddScraperDialog
            dialog = AddScraperDialog(self)
            dialog.exec()
        except Exception as e:
            self.log_message(f"Failed to open add scraper dialog: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open add scraper dialog:\n{e}")

    def manage_scrapers(self):
        """Open dialog to manage existing scraper configurations"""
        try:
            from src.ui.scraper_management_dialog import ScraperManagementDialog
            dialog = ScraperManagementDialog(self)
            dialog.exec()
        except Exception as e:
            self.log_message(f"Failed to open scraper management dialog: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open scraper management dialog:\n{e}")

    def open_scraper_builder(self):
        """Open the scraper builder dialog"""
        try:
            from src.ui.scraper_builder_dialog import ScraperBuilderDialog
            dialog = ScraperBuilderDialog(self)
            dialog.exec()
        except Exception as e:
            self.log_message(f"Failed to open scraper builder dialog: {e}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to open scraper builder dialog:\n{e}")

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
        elif (
            message.startswith("🔧")
            or message.startswith("💾")
            or message.startswith("🚀")
        ):
            level = "INFO"
            message = message[2:].strip()

        self.log_viewer.log(message, level)

        # Also update status bar for important messages
        if level in ["ERROR", "SUCCESS"]:
            status_bar = self.statusBar()
            if status_bar is not None:
                status_bar.showMessage(message, 5000)

    def update_progress(self, value):
        """Update the progress bar value"""
        self.progress_bar.setValue(value)
        
    def update_metrics(self, metrics_dict):
        """Update execution metrics labels"""
        elapsed = metrics_dict.get('elapsed', '00:00:00')
        processed = metrics_dict.get('processed', '0/0')
        current_op = metrics_dict.get('current_op', 'Idle')
        eta = metrics_dict.get('eta', '--')

        self.elapsed_label.setText(f"⏱️ Elapsed: {elapsed}")
        self.processed_label.setText(f"📦 Processed: {processed}")
        self.current_op_label.setText(f"🔄 Current: {current_op}")
        self.eta_label.setText(f"⏳ ETA: {eta}")
    def update_status(self, message, status_type="ready"):
        """Update the status indicator"""
        colors = {"ready": "#4CAF50", "working": "#FF9800", "error": "#F44336"}
        icons = {"ready": "●", "working": "⟳", "error": "✖"}

        color = colors.get(status_type, "#4CAF50")
        icon = icons.get(status_type, "●")

        self.status_label.setText(f"{icon} {message}")
        self.status_label.setStyleSheet(f"color: {color};")

    def update_database_stats(self):
        """Update database statistics in the UI"""
        try:
            from src.core.database.queries import ProductDatabase

            db = ProductDatabase()
            db.connect()
            self.db_product_count = db.get_product_count()
            db.disconnect()

            self.db_status_label.setText(
                f"🗄️ Database: {self.db_product_count:,} products"
            )
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
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log_viewer.clear_logs()

    def export_logs(self):
        """Export logs to a text file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"ProductScraper_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
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
        if self.worker and self.worker._is_cancelled:
            # Operation was cancelled
            self.log_message(f"{self.last_operation} was cancelled by user", "WARNING")
            self.update_status("Cancelled", "ready")
            self.last_operation_label.setText(
                f"📋 Last Operation: {self.last_operation} (Cancelled)"
            )
        elif not is_error:
            self.progress_bar.setValue(100)
            self.log_message(f"{self.last_operation} completed successfully", "SUCCESS")
            self.update_status("Ready", "ready")
            self.last_operation_label.setText(
                f"📋 Last Operation: {self.last_operation} (Success)"
            )

            # Update database stats after operations that might change it
            if self.last_operation in ["Database Refresh", "XML Download", "Scraping"]:
                QTimer.singleShot(1000, self.update_database_stats)
        else:
            self.update_status("Ready", "ready")
            self.last_operation_label.setText(
                f"📋 Last Operation: {self.last_operation} (Failed)"
            )

        self._set_buttons_enabled(True)
        self.cancel_scraping_btn.setEnabled(False)  # Disable cancel button when worker finishes
        self.worker = None
