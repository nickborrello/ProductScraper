from PyQt6.QtWidgets import QApplication

# Professional Modern Dark Theme Palette
DARK_BG = "#121212"  # Main background (very dark gray/black)
SIDEBAR_BG = "#1E1E1E"  # Sidebar background
CARD_BG = "#252525"  # Card/Container background
BORDER_COLOR = "#333333"  # Subtle borders
PRIMARY_COLOR = "#3B8ED0"  # Primary Action Blue
ACCENT_COLOR = "#64B5F6"  # Lighter Blue for accents
TEXT_PRIMARY = "#FFFFFF"  # Main text
TEXT_SECONDARY = "#B0B0B0"  # Subtitles/Labels
SUCCESS_COLOR = "#4CAF50"  # Green
WARNING_COLOR = "#FF9800"  # Orange
ERROR_COLOR = "#EF5350"  # Red
HOVER_COLOR = "#333333"  # Hover state for list items/buttons

STYLESHEET = f"""
    /* Global Reset */
    QWidget {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 14px;
    }}

    /* Main Window */
    QMainWindow {{
        background-color: {DARK_BG};
    }}

    /* Sidebar */
    QWidget#sidebar {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid {BORDER_COLOR};
    }}
    
    /* Sidebar Buttons */
    QPushButton.sidebar-btn {{
        background-color: transparent;
        border: none;
        color: {TEXT_SECONDARY};
        text-align: left;
        padding: 12px 20px;
        font-size: 15px;
        border-left: 3px solid transparent;
    }}
    QPushButton.sidebar-btn:hover {{
        background-color: {HOVER_COLOR};
        color: {TEXT_PRIMARY};
    }}
    QPushButton.sidebar-btn:checked {{
        background-color: {HOVER_COLOR};
        color: {ACCENT_COLOR};
        border-left: 3px solid {ACCENT_COLOR};
        font-weight: bold;
    }}

    /* Content Area */
    QWidget#content_area {{
        background-color: {DARK_BG};
    }}

    /* Cards / Containers */
    QFrame.card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
    }}
    
    /* Headings */
    QLabel.h1 {{
        font-size: 24px;
        font-weight: bold;
        color: {TEXT_PRIMARY};
        margin-bottom: 10px;
    }}
    QLabel.h2 {{
        font-size: 18px;
        font-weight: bold;
        color: {TEXT_PRIMARY};
        margin-bottom: 5px;
    }}
    QLabel.subtitle {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 8px 16px;
        color: {TEXT_PRIMARY};
    }}
    QPushButton:hover {{
        background-color: {HOVER_COLOR};
        border-color: {ACCENT_COLOR};
    }}
    QPushButton:pressed {{
        background-color: {BORDER_COLOR};
    }}
    QPushButton:disabled {{
        background-color: {SIDEBAR_BG};
        color: #555555;
        border-color: {BORDER_COLOR};
    }}

    /* Primary Button */
    QPushButton.primary {{
        background-color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        color: white;
        font-weight: bold;
    }}
    QPushButton.primary:hover {{
        background-color: {ACCENT_COLOR};
        border-color: {ACCENT_COLOR};
    }}

    /* Danger Button */
    QPushButton.danger {{
        background-color: transparent;
        border: 1px solid {ERROR_COLOR};
        color: {ERROR_COLOR};
    }}
    QPushButton.danger:hover {{
        background-color: {ERROR_COLOR};
        color: white;
    }}

    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {SIDEBAR_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        padding: 8px;
        color: {TEXT_PRIMARY};
        selection-background-color: {PRIMARY_COLOR};
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border: 1px solid {ACCENT_COLOR};
    }}

    /* Tables */
    QTableWidget {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        gridline-color: {BORDER_COLOR};
        selection-background-color: #1976D2; /* Stronger Blue */
        selection-color: #FFFFFF;
    }}
    QTableWidget::item:selected {{
        background-color: #1976D2;
        color: #FFFFFF;
        border: 1px solid {ACCENT_COLOR}; /* Add border for extra visibility */
    }}
    QTableWidget::item:hover {{
        background-color: {HOVER_COLOR};
    }}
    QHeaderView::section {{
        background-color: {SIDEBAR_BG};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {BORDER_COLOR};
        border-right: 1px solid {BORDER_COLOR};
        font-weight: bold;
    }}
    QTableWidget::item {{
        padding: 5px;
    }}
    
    /* Buttons inside tables (Actions) */
    QTableWidget QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-weight: bold;
    }}
    QTableWidget QPushButton:hover {{
        background-color: {ACCENT_COLOR};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: {SIDEBAR_BG};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_COLOR};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {ACCENT_COLOR};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Progress Bar */
    QProgressBar {{
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        text-align: center;
        background-color: {SIDEBAR_BG};
    }}
    QProgressBar::chunk {{
        background-color: {SUCCESS_COLOR};
        border-radius: 3px;
    }}

    /* Checkboxes */
    QCheckBox {{
        spacing: 8px;
        color: {TEXT_PRIMARY};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {BORDER_COLOR};
        border-radius: 3px;
        background-color: {SIDEBAR_BG};
    }}
    QCheckBox::indicator:unchecked:hover {{
        border: 1px solid {ACCENT_COLOR};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {ACCENT_COLOR};
        border-color: {ACCENT_COLOR};
    }}
"""


def apply_dark_theme(app: QApplication):
    """Apply a global dark theme to the application."""
    app.setStyleSheet(STYLESHEET)
