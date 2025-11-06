# Task 3.3: Update Project Documentation

**Assigned to:** Agent_Core

## Objective
To document the new GUI for end-users and developers.

## Expected Output
An updated `README.md` file and comprehensive docstrings/comments within the new GUI code.

## Guidance
- Add a new "GUI Usage" section to the main `README.md` file. Explain the prerequisites and provide the simple command to run the application (e.g., `python gui.py`).
- Review the entire `gui.py` file and add clear, PEP 257-compliant docstrings to all new classes and methods.
- Add inline comments (`#`) to explain any parts of the GUI code that are particularly complex or non-obvious, such as the signal/slot connections or threading logic.

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
    QMessageBox,
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

        # Show a critical error message box
        QMessageBox.critical(
            self,
            "An Error Occurred",
            f"An unexpected error occurred:\n\n{err_val}\n\nSee the log for more details.",
        )
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

## `README.md` Content

```markdown
# ProductScraper - Agentic PM Integration

## 🚀 Quick Start

Your ProductScraper project is now set up with **Agentic Project Management (APM)**!

### What is APM?

APM provides AI-assisted project management tools to help organize, track, and execute development tasks efficiently.

### Available Resources

📖 **Documentation** (in `.apm/guides/`):
- `SETUP.md` - Complete installation and configuration guide
- `Implementation_Plan_Guide.md` - How to create and manage implementation plans
- `Memory_System_Guide.md` - Project memory and context management
- `Task_Assignment_Guide.md` - Breaking down and assigning tasks
- `Project_Breakdown_Guide.md` - Project analysis and breakdown strategies

📝 **Memory System** (`.apm/Memory/`):
- `Memory_Root.md` - Current project state, architecture, and priorities

📋 **Planning** (`.apm/`):
- `Implementation_Plan.md` - Track development tasks and progress

### Core Commands

```powershell
# Run the main application
python main.py

# Install dependencies
pip install -r requirements.txt
npm install

# Run tests
python -m pytest test/test_scrapers.py
```

### Project Features

✅ **Multi-Site Scraping**
- 8 active scraper modules (Amazon, Bradley Caldwell, Central Pet, etc.)
- Automated data extraction and normalization
- Excel input/output with smart column mapping

✅ **Database Management**
- SQLite database with SQLAlchemy ORM
- ShopSite XML import/export
- Product classification UI

✅ **Testing Framework**
- Unit tests for all scrapers
- Integration tests with real network calls
- Granular field validation

### Safety Reminders

⚠️ **CRITICAL: This is a production tool with live data access**

- Always test with small batches first
- Use test product SKU: `035585499741`
- Keep credentials in `.env` only
- Never commit sensitive data to git

### Next Steps

1. ✅ Environment set up and verified
2. 📖 Review `.apm/guides/SETUP.md` for detailed usage
3. 📝 Check `Memory_Root.md` for current project state
4. 🎯 Define tasks in `Implementation_Plan.md`
5. 🚀 Start developing!

---

**Setup completed:** 2025-11-06  
**APM Version:** 0.5.1  
**Python:** 3.13.3  
**Status:** ✅ Ready for development
```