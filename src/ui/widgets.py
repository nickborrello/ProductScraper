"""
This module contains shared custom widgets and utility classes for the UI.
"""

import asyncio
import inspect
import traceback
from datetime import datetime

from PyQt6.QtCore import QEventLoop, QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QGroupBox, QPushButton, QTextEdit, QVBoxLayout


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    status = pyqtSignal(str)
    metrics = pyqtSignal(dict)
    request_editor_sync = pyqtSignal(
        list, object, str
    )  # products_list, result_container, editor_type
    request_confirmation_sync = pyqtSignal(str, str, object)  # title, text, result_container


class Worker(QThread):
    """
    Worker thread for executing long-running tasks without blocking the GUI.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False

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
        result_container = {"result": None, "done": False}
        self.signals.request_confirmation_sync.emit(title, text, result_container)

        loop = QEventLoop()
        timer = QTimer()

        def check_done():
            if result_container["done"]:
                loop.quit()

        timer.timeout.connect(check_done)
        timer.start(100)
        loop.exec()
        timer.stop()

        return result_container["result"]

    def _request_editor_sync(self, products_list, editor_type="product"):
        """Request editor on main thread and wait for result."""
        result_container = {"result": None, "done": False}
        self.signals.request_editor_sync.emit(products_list, result_container, editor_type)

        loop = QEventLoop()
        timer = QTimer()

        def check_done():
            if result_container["done"]:
                loop.quit()

        timer.timeout.connect(check_done)
        timer.start(100)
        loop.exec()
        timer.stop()

        return result_container["result"]

    def run(self):
        """Execute the worker's target function."""
        had_error = False
        try:
            if inspect.iscoroutinefunction(self.fn):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.fn(*self.args, **self.kwargs))
                finally:
                    loop.close()
            else:
                result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            had_error = True
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        else:
            if not self._is_cancelled:
                self.signals.result.emit(result)
        finally:
            if not had_error:
                self.signals.finished.emit()


class LogViewer(QTextEdit):
    """Professional log viewer with color-coded messages."""

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
        """Add a timestamped, color-coded log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.LOG_COLORS.get(level, "#ffffff")
        icon = self.LOG_ICONS.get(level, "•")

        formatted = f'<span style="color: {color}"><b>[{timestamp}]</b> {icon} {message}</span>'
        self.append(formatted)

        if self.auto_scroll:
            self.moveCursor(QTextCursor.MoveOperation.End)

    def clear_logs(self):
        """Clear all log entries."""
        self.clear()
        self.log("Logs cleared", "INFO")


class ActionCard(QGroupBox):
    """A styled action card widget for organized UI sections."""

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
        """Add a styled button to the card."""
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
