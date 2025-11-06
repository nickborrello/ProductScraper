# ProductScraper GUI – Implementation Plan

**Memory Strategy:** [Determined during Memory Root Creation phase]
**Last Modification:** Initial plan creation.
**Project Overview:** To create a PyQt6-based desktop GUI for the ProductScraper tool, replacing the existing CLI to make it accessible for non-technical users. The application will provide a user-friendly interface for scraping, running tests, and managing the database, while ensuring the UI remains responsive during long-running operations.

## Phase 1: Foundation & Scaffolding

### Task 1.1 – Create Main Application Window and UI Skeleton │ Agent_GUI
- **Objective:** To establish the foundational structure of the GUI application by creating the main window and laying out all necessary UI widgets as static placeholders.
- **Output:** A new `gui.py` file that, when run, displays a non-functional desktop window containing all the visual elements required for the MVP.
- **Guidance:** Use standard PyQt6 widgets and a `QVBoxLayout` for a simple, clean presentation. The focus is purely on the visual structure, not functionality.

- Create a new file named `gui.py` and define a `MainWindow` class that inherits from `QMainWindow`.
- Inside `MainWindow`, add `QPushButton` widgets for each core action: "Start Scraping," "Check Discontinued," "Refresh Database," and "Run Tests." Also, add a non-editable `QTextEdit` for logging output and a `QProgressBar` to show task progress.
- Create a central widget and use a `QVBoxLayout` to arrange the buttons, progress bar, and text area in a clean, vertical sequence.
- In a `if __name__ == "__main__":` block, instantiate the `QApplication` and the `MainWindow`, show the window, and start the application's event loop.

### Task 1.2 – Refactor Core Logic from `main.py` for GUI Consumption │ Agent_Core
- **Objective:** To decouple the core business logic from the command-line interface in `main.py`, making it importable and callable from the new GUI.
- **Output:** A modified `main.py` file where the primary functionalities are encapsulated within distinct functions, and the existing CLI behavior is preserved.
- **Guidance:** The goal is to isolate logic, not to change its behavior. The refactored functions should accept parameters like file paths directly, rather than parsing `sys.argv`.

1. **Analyze Logic:** Carefully read through `main.py` to identify the specific code blocks responsible for each major operation (e.g., the scraping process, the discontinued check, database refresh, and running tests).
2. **Encapsulate Functions:** For each identified block, create a new, well-named function (e.g., `run_scraping(file_path)`, `run_discontinued_check()`). Move the relevant logic into this function and modify it to accept arguments instead of relying on CLI parsing.
3. **Preserve CLI Entrypoint:** Update the `if __name__ == "__main__":` block to parse command-line arguments as before, but now have it call the newly created functions. This ensures the script remains fully functional as a CLI tool.

### Task 1.3 – Implement a Reusable Worker Thread Class │ Agent_GUI
- **Objective:** To create a generic, reusable `QThread` worker that can execute any long-running function in the background to prevent the GUI from freezing.
- **Output:** A `Worker` class within `gui.py` (or a new `utils.py`) that can be instantiated with a target function and emits signals for completion, errors, and progress.
- **Guidance:** Depends on: Task 1.1 Output. This class is the cornerstone of the application's responsiveness. It should be designed to be generic and handle exceptions gracefully by emitting an error signal.

- Define a `WorkerSignals` class inheriting from `QObject` to hold the custom signals: `finished` (no arguments), `error` (tuple argument for exception info), and `progress` (int argument for percentage).
- Define a `Worker` class inheriting from `QThread`. Its `__init__` method should accept a function and its `*args` and `**kwargs`.
- In the `Worker` class, implement the `run()` method. Inside `run()`, wrap the execution of the target function in a `try...except` block. On success, emit `finished`. On failure, emit the `error` signal with the exception details.
- The worker's `run()` method should be able to call functions that periodically yield progress updates, which are then emitted via the `progress` signal.
