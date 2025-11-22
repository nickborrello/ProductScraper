from PyQt6.QtWidgets import QApplication

# Modern Professional "Deep Data" Theme
# A sophisticated, high-contrast dark theme inspired by modern SaaS data tools (Linear, Vercel).
# Focuses on content hierarchy, readability, and a professional "command center" aesthetic.

# --- Color Palette Definitions ---
PRIMARY_BG = "#09090b"      # Main window background (Rich Black)
SIDEBAR_BG = "#18181b"      # Sidebar background (Zinc-900)
CARD_BG = "#27272a"         # Card/Container background (Zinc-800)
SURFACE_BG = "#3f3f46"      # Inputs, elevated surfaces (Zinc-700)

PRIMARY_COLOR = "#2563eb"   # Main Action Blue (Royal Blue)
PRIMARY_HOVER = "#3b82f6"   # Lighter Blue for hover states
SECONDARY_COLOR = "#71717a" # Secondary actions (Zinc-500)
ACCENT_COLOR = "#8b5cf6"    # Violet accent for highlights

SUCCESS_COLOR = "#10b981"   # Emerald Green
WARNING_COLOR = "#f59e0b"   # Amber Orange
ERROR_COLOR = "#ef4444"     # Rose Red

TEXT_PRIMARY = "#f4f4f5"    # Main text (Zinc-100)
TEXT_SECONDARY = "#a1a1aa"  # Secondary text/labels (Zinc-400)
TEXT_TERTIARY = "#52525b"   # Disabled/Placeholder text (Zinc-600)

BORDER_COLOR = "#3f3f46"    # Subtle borders (Zinc-700)
HOVER_COLOR = "#3f3f46"     # General hover state background

STYLESHEET = f"""
    /* --- Global Reset & Typography --- */
    QWidget {{
        background-color: {PRIMARY_BG};
        color: {TEXT_PRIMARY};
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
        font-size: 13px;
        selection-background-color: {PRIMARY_COLOR};
        selection-color: #ffffff;
    }}

    /* --- Main Window Structure --- */
    QMainWindow {{
        background-color: {PRIMARY_BG};
    }}

    /* --- Sidebar Navigation --- */
    QWidget#sidebar {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid {BORDER_COLOR};
    }}
    
    QPushButton.sidebar-btn {{
        background-color: transparent;
        border: none;
        border-radius: 6px;
        color: {TEXT_SECONDARY};
        text-align: left;
        padding: 10px 16px;
        font-weight: 500;
        margin: 2px 8px; 
    }}
    QPushButton.sidebar-btn:hover {{
        background-color: {HOVER_COLOR};
        color: {TEXT_PRIMARY};
    }}
    QPushButton.sidebar-btn:checked {{
        background-color: {HOVER_COLOR};
        color: {PRIMARY_HOVER};
        font-weight: 600;
        border-left: 3px solid {PRIMARY_COLOR}; /* Distinctive active indicator */
    }}

    /* --- Content Area & Containers --- */
    QWidget#content_area {{
        background-color: {PRIMARY_BG};
    }}

    /* Card Style - Used for grouping content */
    QFrame.card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 8px;
    }}
    
    /* --- Typography Headers --- */
    QLabel.h1 {{
        font-size: 22px;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 12px;
    }}
    QLabel.h2 {{
        font-size: 16px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        margin-bottom: 8px;
    }}
    QLabel.subtitle {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
        line-height: 1.4;
    }}
    QLabel.label {{
        font-weight: 600;
        color: {TEXT_SECONDARY};
    }}
    QLabel.value {{
        color: {TEXT_PRIMARY};
    }}

    /* --- Interactive Elements: Buttons --- */
    QPushButton {{
        background-color: {SURFACE_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: 500;
        color: {TEXT_PRIMARY};
    }}
    QPushButton:hover {{
        background-color: {HOVER_COLOR};
        border-color: {TEXT_SECONDARY};
    }}
    QPushButton:pressed {{
        background-color: {SIDEBAR_BG};
    }}
    QPushButton:disabled {{
        background-color: {SIDEBAR_BG};
        color: {TEXT_TERTIARY};
        border-color: {BORDER_COLOR};
    }}

    /* Primary Action Button */
    QPushButton.primary {{
        background-color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        color: #ffffff;
    }}
    QPushButton.primary:hover {{
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    QPushButton.primary:pressed {{
        background-color: {PRIMARY_COLOR}; /* Slightly darker/same on press */
    }}

    /* Success Button */
    QPushButton.success {{
        background-color: {SUCCESS_COLOR};
        border: 1px solid {SUCCESS_COLOR};
        color: #ffffff;
    }}
    QPushButton.success:hover {{
        background-color: #059669; /* Darker Emerald */
    }}

    /* Danger/Destructive Button */
    QPushButton.danger {{
        background-color: transparent;
        border: 1px solid {ERROR_COLOR};
        color: {ERROR_COLOR};
    }}
    QPushButton.danger:hover {{
        background-color: {ERROR_COLOR};
        color: #ffffff;
    }}

    /* --- Form Elements: Inputs --- */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        background-color: {SIDEBAR_BG}; 
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        padding: 6px;
        color: {TEXT_PRIMARY};
        selection-background-color: {PRIMARY_COLOR};
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {PRIMARY_COLOR};
        background-color: {PRIMARY_BG};
    }}
    QLineEdit::placeholder {{
        color: {TEXT_TERTIARY};
    }}

    /* Combo Box specific */
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {TEXT_SECONDARY};
        margin-right: 5px;
    }}

    /* --- Data Presentation: Tables --- */
    QTableWidget {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        gridline-color: {BORDER_COLOR};
        outline: none;
    }}
    QTableWidget::item {{
        padding: 4px 8px;
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    QTableWidget::item:selected {{
        background-color: {HOVER_COLOR};
        color: {PRIMARY_HOVER};
        border-left: 2px solid {PRIMARY_COLOR};
    }}
    QHeaderView::section {{
        background-color: {SIDEBAR_BG};
        color: {TEXT_SECONDARY};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {BORDER_COLOR};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
    }}
    
    /* Table Action Buttons */
    QTableWidget QPushButton {{
        background-color: {SURFACE_BG};
        border: none;
        border-radius: 4px;
        font-size: 11px;
        padding: 4px 8px;
        color: {TEXT_PRIMARY};
    }}
    QTableWidget QPushButton:hover {{
        background-color: {PRIMARY_COLOR};
        color: white;
    }}

    /* --- Navigation & Scrollbars --- */
    QScrollBar:vertical {{
        border: none;
        background: {PRIMARY_BG};
        width: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {SURFACE_BG};
        min-height: 30px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {SECONDARY_COLOR};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        border: none;
        background: {PRIMARY_BG};
        height: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {SURFACE_BG};
        min-width: 30px;
        border-radius: 6px;
        margin: 2px;
    }}

    /* --- Feedback: Progress Bar --- */
    QProgressBar {{
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        text-align: center;
        background-color: {SIDEBAR_BG};
        color: {TEXT_SECONDARY};
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: {PRIMARY_COLOR};
        border-radius: 3px;
    }}

    /* --- Controls: Checkboxes --- */
    QCheckBox {{
        spacing: 8px;
        color: {TEXT_PRIMARY};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {BORDER_COLOR};
        border-radius: 4px;
        background-color: {SIDEBAR_BG};
    }}
    QCheckBox::indicator:unchecked:hover {{
        border: 1px solid {TEXT_SECONDARY};
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_COLOR};
        border: 1px solid {PRIMARY_COLOR};
        /* Simple checkmark SVG could be embedded here, or rely on system style */
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {PRIMARY_HOVER};
        border-color: {PRIMARY_HOVER};
    }}
    
    /* --- Tab Widget --- */
    QTabWidget::pane {{
        border: 1px solid {BORDER_COLOR};
        background-color: {CARD_BG};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background-color: {SIDEBAR_BG};
        color: {TEXT_SECONDARY};
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {CARD_BG};
        color: {PRIMARY_COLOR};
        font-weight: bold;
        border-bottom: 2px solid {PRIMARY_COLOR};
    }}
    QTabBar::tab:hover {{
        color: {TEXT_PRIMARY};
        background-color: {HOVER_COLOR};
    }}
    
    /* --- InfoCard Specifics --- */
    /* Note: Specific styles are often inline, but we ensure global defaults help */
    QFrame.card QLabel.title {{
        color: {PRIMARY_COLOR};
    }}
"""


def apply_dark_theme(app: QApplication):
    """Apply a global dark theme to the application."""
    app.setStyleSheet(STYLESHEET)