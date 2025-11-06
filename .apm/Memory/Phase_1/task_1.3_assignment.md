# Task 1.3: Implement a Reusable Worker Thread Class

**Assigned to:** Agent_GUI

## Objective
To create a generic, reusable `QThread` worker that can execute any long-running function in the background to prevent the GUI from freezing.

## Expected Output
A `Worker` class within `gui.py` (or a new `utils.py`) that can be instantiated with a target function and emits signals for completion, errors, and progress.

## Guidance
This class is the cornerstone of the application's responsiveness. It should be designed to be generic and handle exceptions gracefully by emitting an error signal.

- Define a `WorkerSignals` class inheriting from `QObject` to hold the custom signals: `finished` (no arguments), `error` (tuple argument for exception info), and `progress` (int argument for percentage).
- Define a `Worker` class inheriting from `QThread`. Its `__init__` method should accept a function and its `*args` and `**kwargs`.
- In the `Worker` class, implement the `run()` method. Inside `run()`, wrap the execution of the target function in a `try...except` block. On success, emit `finished`. On failure, emit the `error` signal with the exception details.
- The worker's `run()` method should be able to call functions that periodically yield progress updates, which are then emitted via the `progress` signal.

## `gui.py` Content

```python
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Product Scraper")

        # Create widgets
        self.start_scraping_button = QPushButton("Start Scraping")
        self.check_discontinued_button = QPushButton("Check Discontinued")
        self.refresh_database_button = QPushButton("Refresh Database")
        self.run_tests_button = QPushButton("Run Tests")
        self.log_output_area = QTextEdit()
        self.log_output_area.setReadOnly(True)
        self.progress_bar = QProgressBar()

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.start_scraping_button)
        layout.addWidget(self.check_discontinued_button)
        layout.addWidget(self.refresh_database_button)
        layout.addWidget(self.run_tests_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output_area)

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```
