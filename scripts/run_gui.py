import sys
import traceback
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

# Ensure project root is on sys.path so we can import from scripts
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Conditional import for core logic to ensure GUI is runnable even if main fails.
try:
    from scripts.run_scraper import run_scraping, run_discontinued_check, run_db_refresh, run_scraper_tests
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


class MainWindow(QMainWindow):
    """
    The main application window for the Product Scraper GUI.

    Sets up the UI layout, connects button clicks to worker functions,
    and handles signals from the worker thread.
    """
    def __init__(self):
        """Initializes the main window, widgets, and signal connections."""
        super().__init__()

        self.setWindowTitle("Product Scraper")
        self.worker = None  # To hold the reference to the running worker

        # --- Create widgets ---
        self.start_scraping_button = QPushButton("Start Scraping")
        self.start_scraping_button.setToolTip("Select an Excel file to start scraping products.")
        self.check_discontinued_button = QPushButton("Check Discontinued")
        self.check_discontinued_button.setToolTip("Select an Excel file to check for discontinued products.")
        self.refresh_database_button = QPushButton("Refresh Database")
        self.refresh_database_button.setToolTip("Refresh the internal database with the latest product information.")
        self.run_tests_button = QPushButton("Run Tests")
        self.run_tests_button.setToolTip("Run automated tests for the scrapers.")
        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.progress_bar = QProgressBar()

        # Group buttons for easy enabling/disabling during worker execution
        self.buttons = [
            self.start_scraping_button,
            self.check_discontinued_button,
            self.refresh_database_button,
            self.run_tests_button,
        ]

        # --- Set up the layout ---
        layout = QVBoxLayout()
        for button in self.buttons:
            layout.addWidget(button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output_area)

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- Connect signals to slots ---
        self.start_scraping_button.clicked.connect(self.start_scraping)
        self.check_discontinued_button.clicked.connect(self.start_discontinued_check)
        self.refresh_database_button.clicked.connect(self.start_db_refresh)
        self.run_tests_button.clicked.connect(self.start_scraper_tests)

    def _set_buttons_enabled(self, enabled):
        """Enable or disable all action buttons to prevent concurrent runs."""
        for button in self.buttons:
            button.setEnabled(enabled)

    def _run_worker(self, fn, *args, **kwargs):
        """Generic method to run a function in the worker thread."""
        self.log_output_area.clear()
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)

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
        """Opens a file dialog and starts the scraping process if a file is selected."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if file_path:
            self._run_worker(run_scraping, file_path, interactive=False)

    def start_discontinued_check(self):
        """Opens a file dialog and starts the discontinued check process."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File for Discontinued Check",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )
        if file_path:
            self._run_worker(run_discontinued_check, file_path)

    def start_db_refresh(self):
        """Starts the database refresh process."""
        self._run_worker(run_db_refresh)

    def start_scraper_tests(self):
        """Starts the scraper test process with integration tests enabled."""
        self._run_worker(run_scraper_tests, run_integration=True)

    def log_message(self, message):
        """Appends a message to the log output area."""
        self.log_output_area.append(message)

    def update_progress(self, value):
        """Updates the progress bar's value."""
        self.progress_bar.setValue(value)

    def handle_error(self, error_tuple):
        """Handles errors emitted from the worker thread."""
        err_type, err_val, err_tb = error_tuple
        self.log_message(f"❌ An error occurred: {err_val}")
        self.log_message(f"Traceback:\n{err_tb}")

        # Show a critical error message box to the user
        QMessageBox.critical(
            self,
            "An Error Occurred",
            f"An unexpected error occurred:\n\n{err_val}\n\nSee the log for more details.",
        )
        self.worker_finished(is_error=True)

    def worker_finished(self, is_error=False):
        """Called when the worker thread is finished."""
        if not is_error:
            self.progress_bar.setValue(100)
        self._set_buttons_enabled(True)
        self.worker = None # Release the worker reference

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())