from PyQt6.QtWidgets import QApplication

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

    /* Custom Button Styles */
    QPushButton[class="success"] {{
        background-color: {SUCCESS_COLOR};
        color: white;
        border: none;
    }}
    QPushButton[class="success"]:hover {{
        background-color: #45a049;
    }}
    QPushButton[class="success"]:pressed {{
        background-color: #3d8b40;
    }}
    QPushButton[class="primary"] {{
        background-color: {ACCENT_COLOR};
        color: white;
        border: none;
    }}
    QPushButton[class="primary"]:hover {{
        background-color: #1976D2;
    }}
    QPushButton[class="primary"]:pressed {{
        background-color: #1565C0;
    }}
    QPushButton[class="danger"] {{
        background-color: {ERROR_COLOR};
        color: white;
        border: none;
    }}
    QPushButton[class="danger"]:hover {{
        background-color: #c82333;
    }}
    QPushButton[class="danger"]:pressed {{
        background-color: #bd2130;
    }}
    QPushButton[class="secondary"] {{
        background-color: #6c757d;
        color: white;
        border: none;
    }}
    QPushButton[class="secondary"]:hover {{
        background-color: #5a6268;
    }}
    QPushButton[class="secondary"]:pressed {{
        background-color: #545b62;
    }}

    /* Custom Label Styles */
    QLabel[class="page-label"] {{
        font-weight: bold;
        font-size: 14px;
    }}
"""


def apply_dark_theme(app: QApplication):
    """Apply a global dark theme to the application."""
    app.setStyleSheet(STYLESHEET)
