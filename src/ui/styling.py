# src/ui/styling.py

import traceback
from datetime import datetime

from PyQt6.QtCore import QEventLoop, QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QApplication, QGroupBox, QPushButton, QTextEdit, QVBoxLayout

# Professional color palette
DARK_BACKGROUND = "#1e1e1e"
LIGHT_BACKGROUND = "#2d2d2d"
BORDER_COLOR = "#3e3e3e"
ACCENT_COLOR = "#2196F3"
SUCCESS_COLOR = "#4CAF50"
WARNING_COLOR = "#FF9800"
ERROR_COLOR = "#F44336"
TEXT_COLOR = "#ffffff"
MUTED_TEXT_COLOR = "#888888"

STYLESHEET = f"""
    QWidget {{
        background-color: {DARK_BACKGROUND};
        color: {TEXT_COLOR};
        font-family: Arial;
    }}
    QMainWindow, QDialog {{
        background-color: {DARK_BACKGROUND};
    }}
    QMenuBar {{
        background-color: {LIGHT_BACKGROUND};
        color: {TEXT_COLOR};
    }}
    QMenuBar::item:selected {{
        background-color: {ACCENT_COLOR};
    }}
    QMenu {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
    }}
    QMenu::item:selected {{
        background-color: {ACCENT_COLOR};
    }}
    QPushButton {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        padding: 8px;
        font-weight: normal;
        color: {TEXT_COLOR};
    }}
    QPushButton:hover {{
        background-color: #3d3d3d;
        border: 1px solid {ACCENT_COLOR};
    }}
    QPushButton:pressed {{
        background-color: #1a1a1a;
    }}
    QPushButton:disabled {{
        background-color: #1a1a1a;
        color: #666666;
    }}
    QCheckBox {{
        color: {TEXT_COLOR};
        spacing: 5px;
    }}
    QCheckBox::indicator {{
        border: 1px solid {BORDER_COLOR};
        background-color: {LIGHT_BACKGROUND};
        width: 15px;
        height: 15px;
        border-radius: 3px;
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {ACCENT_COLOR};
    }}
    QCheckBox::indicator:checked {{
        background-color: {SUCCESS_COLOR};
        border: 1px solid {SUCCESS_COLOR};
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iNyIgdmlld0JveD0iMCAwIDEwIDciIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMy41TDQuMDggNi41TDkgMSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
    }}
    QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        padding: 4px;
    }}
    QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {ACCENT_COLOR};
    }}
    QHeaderView::section {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        padding: 4px;
    }}
    QTableView {{
        gridline-color: {BORDER_COLOR};
    }}
    QFrame {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        border-radius: 5px;
    }}
    QGroupBox {{
        font-weight: bold;
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
        margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }}
    QTableWidget {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        gridline-color: {BORDER_COLOR};
    }}
    QTableWidget::item {{
        padding: 5px;
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    QTableWidget::item:selected {{
        background-color: {ACCENT_COLOR};
        color: {TEXT_COLOR};
    }}
    QTabWidget::pane {{
        border-top: 1px solid {BORDER_COLOR};
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background-color: {DARK_BACKGROUND};
        color: {MUTED_TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-bottom: none;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:hover {{
        background-color: {LIGHT_BACKGROUND};
        color: {TEXT_COLOR};
    }}
    QTabBar::tab:selected {{
        background-color: {LIGHT_BACKGROUND};
        color: {TEXT_COLOR};
        border: 1px solid {BORDER_COLOR};
        border-bottom: 2px solid {ACCENT_COLOR};
    }}
    QSpinBox, QDoubleSpinBox {{
        padding-right: 15px; /* make room for the arrows */
    }}
    QSpinBox::up-button, QSpinBox::down-button, 
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
        width: 18px;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-position: top right;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-position: bottom right;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjQiPjxwYXRoIGQ9Ik00IDAgTDAgNEg4WiIgZmlsbD0iI2ZmZiIvPjwvc3ZnPg==);
        width: 8px;
        height: 4px;
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjQiPjxwYXRoIGQ9Ik00IDRMMCAwSDhaIiBmaWxsPSIjZmZmIi8+PC9zdmc+);
        width: 8px;
        height: 4px;
    }}
    QProgressBar {{
        border: 2px solid {BORDER_COLOR};
        border-radius: 5px;
        text-align: center;
        height: 25px;
        background-color: {LIGHT_BACKGROUND};
        color: {TEXT_COLOR};
    }}
    QProgressBar::chunk {{
        background-color: {SUCCESS_COLOR};
        border-radius: 3px;
    }}
    QScrollBar:vertical {{
        border: none;
        background: {DARK_BACKGROUND};
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_COLOR};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        border: none;
        background: {DARK_BACKGROUND};
        height: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER_COLOR};
        min-width: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QListWidget {{
        background-color: {LIGHT_BACKGROUND};
        border: 1px solid {BORDER_COLOR};
    }}
    QListWidget::item {{
        padding: 3px 5px;
    }}
    QListWidget::item:selected {{
        background-color: {SUCCESS_COLOR};
    }}
    QListWidget::indicator {{
        width: 15px;
        height: 15px;
        border-radius: 3px;
    }}
    QListWidget::indicator:unchecked {{
        border: 1px solid {MUTED_TEXT_COLOR};
        background-color: {LIGHT_BACKGROUND};
    }}
    QListWidget::indicator:checked {{
        border: 1px solid {SUCCESS_COLOR};
        background-color: {SUCCESS_COLOR};
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iNyIgdmlld0JveD0iMCAwIDEwIDciIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMy41TDQuMDggNi41TDkgMSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
    }}
"""


def apply_dark_theme(app: QApplication):
    """Apply a global dark theme to the application."""
    app.setStyleSheet(STYLESHEET)


class LogViewer(QTextEdit):
    """Professional log viewer with color-coded messages and filtering"""

    LOG_COLORS = {
        "DEBUG": MUTED_TEXT_COLOR,
        "INFO": ACCENT_COLOR,
        "SUCCESS": SUCCESS_COLOR,
        "WARNING": WARNING_COLOR,
        "ERROR": ERROR_COLOR,
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
        # The global stylesheet will cover this, but we can keep it for standalone use.
        self.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {DARK_BACKGROUND};
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                padding: 4px;
            }}
        """
        )

    def log(self, message, level="INFO"):
        """Add a timestamped, color-coded log entry"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.LOG_COLORS.get(level, TEXT_COLOR)
        icon = self.LOG_ICONS.get(level, "•")

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
        self.setTitle("{icon} {title}" if icon else title)
        self.setStyleSheet(
            f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: {DARK_BACKGROUND};
                color: {TEXT_COLOR};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {TEXT_COLOR};
            }}
        """
        )

        self._layout = QVBoxLayout()
        self._layout.setSpacing(8)
        self.setLayout(self._layout)

    def add_button(self, text, callback, tooltip="", icon=""):
        """Add a styled button to the card"""
        button = QPushButton("{icon} {text}" if icon else text)
        button.setMinimumHeight(40)
        button.setToolTip(tooltip)
        # The global stylesheet for QPushButton is good enough, but ActionCard buttons are special.
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {LIGHT_BACKGROUND};
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px;
                text-align: left;
                font-weight: normal;
                color: {TEXT_COLOR};
            }}
            QPushButton:hover {{
                background-color: #3d3d3d;
                border: 1px solid {ACCENT_COLOR};
            }}
            QPushButton:pressed {{
                background-color: #1a1a1a;
            }}
            QPushButton:disabled {{
                background-color: #1a1a1a;
                color: #666666;
            }}
        """
        )
        button.clicked.connect(callback)
        self._layout.addWidget(button)
        return button


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:
    - finished: No data
    - error: tuple (exctype, value, traceback.format_exc())
    - result: object
    - progress: int
    - log: str
    - request_editor_sync: list (products to edit - blocks until editor closes)
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    request_editor_sync = pyqtSignal(list, object)  # products_list, result_container


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
        self.kwargs["editor_callback"] = self._request_editor_sync  # Inject sync editor callback

    def _request_editor_sync(self, products_list):
        """Request editor on main thread and wait for result (synchronous from worker's perspective)"""

        # Create container for result
        result_container = {"result": None, "done": False}

        # Emit signal to main thread with products and result container
        self.signals.request_editor_sync.emit(products_list, result_container)

        # Wait for main thread to complete
        loop = QEventLoop()

        # Poll until done
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
