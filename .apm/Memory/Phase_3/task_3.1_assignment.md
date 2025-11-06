# Task 3.1: Implement Error Handling and User Feedback

**Assigned to:** Agent_GUI

## Objective
To make the application more robust and user-friendly by providing clear feedback for errors and intuitive help for UI elements.

## Expected Output
An updated GUI where exceptions from background tasks are shown in a dialog box, and all buttons have helpful tooltips.

## Guidance
This task focuses on improving the user experience for non-technical users, which was a core requirement.

- Connect the `error` signal from the `WorkerSignals` class to a new slot in `MainWindow` (e.g., `on_worker_error`).
- In the `on_worker_error` slot, use `QMessageBox.critical()` to display a user-friendly error message, including the exception details passed by the signal.
- For each `QPushButton` in the main window, use the `setTooltip()` method to add a descriptive sentence explaining what the button does (e.g., "Select an Excel file to start scraping products.").

## `gui.py` Content

```python
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
)

# Conditional import for core logic
try:
    from main import run_scraping, run_discontinued_check, run_db_refresh, run_scraper_tests
except ImportError as e:
    print(f"Error importing from main: {e}")
    # Provide dummy functions if the import fails, so the GUI can still load.
    def run_scraping(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Scraping logic not found.")
        print("Error: Scraping logic not found.")
    def run_discontinued_check(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Discontinued check logic not found.")
        print("Error: Discontinued check logic not found.")
    def run_db_refresh(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: DB refresh logic not found.")
        print("Error: DB refresh logic not found.")
    def run_scraper_tests(*args, **kwargs):
        log_callback = kwargs.get("log_callback")
        if log_callback:
            log_callback("Error: Scraper test logic not found.")
        print("Error: Scraper test logic not found.")


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class Worker(QThread):
    """
    Worker thread for executing long-running tasks.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add callbacks to kwargs for the target function
        self.kwargs["progress_callback"] = self.signals.progress
        self.kwargs["log_callback"] = self.signals.log.emit

    def run(self):
        """
        Execute the worker's target function.
        """
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Product Scraper")
        self.worker = None

        # Create widgets
        self.start_scraping_button = QPushButton("Start Scraping")
        self.check_discontinued_button = QPushButton("Check Discontinued")
        self.refresh_database_button = QPushButton("Refresh Database")
        self.run_tests_button = QPushButton("Run Tests")
        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.progress_bar = QProgressBar()

        # Group buttons for easy enabling/disabling
        self.buttons = [
            self.start_scraping_button,
            self.check_discontinued_button,
            self.refresh_database_button,
            self.run_tests_button,
        ]

        # Set up the layout
        layout = QVBoxLayout()
        for button in self.buttons:
            layout.addWidget(button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output_area)

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Connect signals
        self.start_scraping_button.clicked.connect(self.start_scraping)
        self.check_discontinued_button.clicked.connect(self.start_discontinued_check)
        self.refresh_database_button.clicked.connect(self.start_db_refresh)
        self.run_tests_button.clicked.connect(self.start_scraper_tests)

    def _set_buttons_enabled(self, enabled):
        """Enable or disable all action buttons."""
        for button in self.buttons:
            button.setEnabled(enabled)

    def _run_worker(self, fn, *args, **kwargs):
        """Generic method to run a function in the worker thread."""
        self.log_output_area.clear()
        self.progress_bar.setValue(0)
        self._set_buttons_enabled(False)

        self.worker = Worker(fn, *args, **kwargs)
        self.worker.signals.log.connect(self.log_message)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.error.connect(self.handle_error)
        self.worker.signals.finished.connect(self.worker_finished)
        self.worker.start()

    def start_scraping(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;Text Files (*.txt)",
        )
        if file_path:
            self._run_worker(run_scraping, file_path)

    def start_discontinued_check(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File for Discontinued Check",
            "",
            "Excel Files (*.xlsx *.xls);;Text Files (*.txt)",
        )
        if file_path:
            self._run_worker(run_discontinued_check, file_path)

    def start_db_refresh(self):
        """Starts the database refresh process."""
        self._run_worker(run_db_refresh)

    def start_scraper_tests(self):
        """Starts the scraper test process."""
        self._run_worker(run_scraper_tests, run_integration=True)

    def log_message(self, message):
        self.log_output_area.append(message)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def handle_error(self, error_tuple):
        err_type, err_val, err_tb = error_tuple
        self.log_message(f"❌ An error occurred: {err_val}")
        self.log_message(f"Traceback:\n{err_tb}")
        self.worker_finished(is_error=True)

    def worker_finished(self, is_error=False):
        if not is_error:
            self.progress_bar.setValue(100)
        self._set_buttons_enabled(True)
        self.worker = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```