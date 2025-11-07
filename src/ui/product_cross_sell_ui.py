"""
Product Cross-Sell Module
Handles cross-sell recommendations using interactive UI.
"""

import os
import sqlite3
from pathlib import Path

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QFrame, QCheckBox, QMessageBox,
    QSplitter, QProgressBar, QSizePolicy, QGridLayout, QGroupBox
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtGui import QPixmap, QPainter, QFont
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QPalette, QColor

# Import non-UI logic
from src.core.classification.cross_sell_logic import (
    get_facet_options_from_db,
    query_cross_sell_candidates,
    get_first_image_url
)

CROSS_SELL_FIELD = "Product Cross Sell"
MAX_CROSS_SELLS = 4
# Database path - Adjusted for the new location: UI/product_cross_sell_ui.py
# It needs to go up two levels (UI, ProductScraper) and then into data
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "databases" / "products.db"


def assign_cross_sells_batch(products_list):
    """
    Assign cross-sell recommendations to multiple products using the interactive PyQt6 UI.
    Always uses the UI, even for a single product.
    Args:
        products_list: List of product_info dictionaries
    Returns:
        List of product_info dictionaries with cross-sells assigned
    """
    print(f"🔗 Cross-Sell Assignment (UI): Processing {len(products_list)} products...")
    
    # Always use the interactive batch UI
    results = edit_cross_sells_in_batch(products_list)
    print(f"\033[92m✅ Cross-sell assignment (UI) complete! Processed {len(results)} products\033[0m\n")
    return results


def assign_cross_sells_single(product_info):
    """
    Assign cross-sell recommendations to a single product using the interactive PyQt6 UI.
    Treated as a batch of one.
    Args:
        product_info: Dict with product details
    Returns:
        Dict: Product_info with cross-sells assigned
    """
    batch = [product_info]
    results = assign_cross_sells_batch(batch)
    return results[0]


class MultiSelectWidget(QWidget):
    """PyQt6 widget for multi-select functionality with search and checkboxes."""

    selection_changed = pyqtSignal()

    def __init__(self, label, all_options, current_selections=None, parent=None):
        super().__init__(parent)
        self.label = label
        self.all_options = list(all_options)
        self.current_options = list(all_options)
        self.selected_items = set(current_selections or [])
        self.checkboxes = {}
        self.setup_ui()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Available options section with search
        available_layout = QHBoxLayout()
        available_label = QLabel(f"Available {self.label}:")
        available_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        available_label.setStyleSheet("color: #ffffff;")
        available_layout.addWidget(available_label)

        self.search_edit = QLineEdit()
        self.search_edit.setFont(QFont("Arial", 12))
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_options)
        available_layout.addWidget(self.search_edit)

        available_layout.addStretch()
        layout.addLayout(available_layout)

        self.available_scroll = QScrollArea()
        self.available_scroll.setWidgetResizable(True)
        self.available_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.available_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
            }
        """)

        available_widget = QWidget()
        self.available_layout = QVBoxLayout(available_widget)
        self.available_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.available_scroll.setWidget(available_widget)
        layout.addWidget(self.available_scroll)

        # Selected options section
        selected_label = QLabel(f"Selected {self.label}:")
        selected_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        selected_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(selected_label)

        self.selected_scroll = QScrollArea()
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.selected_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
            }
        """)

        selected_widget = QWidget()
        self.selected_layout = QVBoxLayout(selected_widget)
        self.selected_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.selected_scroll.setWidget(selected_widget)
        layout.addWidget(self.selected_scroll)

        self.update_display()

    def filter_options(self):
        query = self.search_edit.text().lower().strip()
        if not query:
            self.current_options = self.all_options[:]
        else:
            self.current_options = [opt for opt in self.all_options if query in opt.lower()]
        self.update_display()

    def update_display(self):
        # Clear existing checkboxes
        for checkbox in self.checkboxes.values():
            checkbox.setParent(None)
        self.checkboxes.clear()

        # Available options
        for option in self.current_options:
            if option not in self.selected_items:
                checkbox = QCheckBox(option)
                checkbox.stateChanged.connect(lambda state, opt=option: self.on_available_changed(opt, state))
                self.available_layout.addWidget(checkbox)
                self.checkboxes[option] = checkbox

        # Selected options
        for option in sorted(self.selected_items, key=str.lower):
            checkbox = QCheckBox(option)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, opt=option: self.on_selected_changed(opt, state))
            self.selected_layout.addWidget(checkbox)
            self.checkboxes[option] = checkbox

    def on_available_changed(self, option, state):
        if state == 2:  # Checked
            self.selected_items.add(option)
            self.selection_changed.emit()
        self.update_display()

    def on_selected_changed(self, option, state):
        if state == 0:  # Unchecked
            self.selected_items.discard(option)
            self.selection_changed.emit()
        self.update_display()

    def get_selected(self):
        return list(self.selected_items)

    def refresh_options(self, new_options):
        self.all_options = list(new_options)
        self.current_options = list(new_options)
        # Keep only selected items that are still in the new options
        self.selected_items = self.selected_items.intersection(set(new_options))
        self.update_display()

    def set_selected(self, selections):
        self.selected_items = set(selections)
        self.update_display()


class CrossSellEditorWindow(QMainWindow):
    """PyQt6 main window for batch cross-sell editing using database filtering."""

    finished = pyqtSignal()  # Signal emitted when window closes

    def __init__(self, products_list):
        super().__init__()
        self.products_list = products_list
        self.current_index = 0
        self.selected_cross_sells = [set() for _ in products_list]
        self.current_candidates = []  # Store current candidates for selected bar

        # Apply dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                font-size: 14px;
            }
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
                border: 1px solid #2196F3;
            }
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        # Get all available options from database
        self.all_categories, self.all_product_types, self.all_pages = get_facet_options_from_db()

        # Network manager for image downloading
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_image_download_finished)

        # Image cache
        self.image_cache = {}

        self.setup_ui()
        self.load_product_into_ui(0)
        self.showMaximized()

    def on_image_download_finished(self, reply):
        """Handle the completion of image download."""
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                image_data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    # Scale image to fit the display area while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        120, 120, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # Find the label that requested this image
                    url = reply.url().toString()
                    if url in self.image_cache:
                        label = self.image_cache[url]
                        if label:
                            label.setPixmap(scaled_pixmap)
                            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                            label.setStyleSheet("")  # Clear any text styling
            else:
                print(f"Image download failed: {reply.errorString()}")
        except Exception as e:
            print(f"Error processing downloaded image: {e}")
        finally:
            reply.deleteLater()

    def setup_ui(self):
        self.setWindowTitle(f"Batch Cross-Sell Editor - Professional Edition - {len(self.products_list)} Products")
        self.setMinimumSize(1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter - filters on left, candidates on right
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        # Left side - Filter Panel
        self.setup_filter_panel(main_splitter)

        # Right side - Candidates Panel
        self.setup_candidates_panel(main_splitter)

        # Set splitter proportions (30% filters, 70% candidates)
        main_splitter.setSizes([360, 840])

        # Navigation bar at bottom
        self.setup_navigation_bar(central_widget.layout())

    def setup_filter_panel(self, parent_splitter):
        """Setup the filter panel on the left side."""
        # Filter Panel Card
        filter_card = QGroupBox("🔍 Filter Panel")
        filter_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                font-size: 14px;
            }
        """)
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setSpacing(10)
        filter_layout.setContentsMargins(15, 15, 15, 15)

        # Category filter
        category_group = QGroupBox("📁 Categories")
        category_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                margin-top: 0.5ex;
                background-color: #343a40;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        category_layout = QVBoxLayout(category_group)
        category_layout.setContentsMargins(10, 10, 10, 10)
        self.category_multi_select = MultiSelectWidget("Categories", self.all_categories)
        self.category_multi_select.selection_changed.connect(self.on_filters_changed)
        category_layout.addWidget(self.category_multi_select)
        filter_layout.addWidget(category_group)

        # Product Type filter
        type_group = QGroupBox("🏷️ Product Types")
        type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                margin-top: 0.5ex;
                background-color: #343a40;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        type_layout = QVBoxLayout(type_group)
        type_layout.setContentsMargins(10, 10, 10, 10)
        self.type_multi_select = MultiSelectWidget("Product Types", self.all_product_types)
        self.type_multi_select.selection_changed.connect(self.on_filters_changed)
        type_layout.addWidget(self.type_multi_select)
        filter_layout.addWidget(type_group)

        # Pages filter
        pages_group = QGroupBox("📄 Pages")
        pages_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                margin-top: 0.5ex;
                background-color: #343a40;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        pages_layout = QVBoxLayout(pages_group)
        pages_layout.setContentsMargins(10, 10, 10, 10)
        self.pages_multi_select = MultiSelectWidget("Pages", self.all_pages)
        self.pages_multi_select.selection_changed.connect(self.on_filters_changed)
        pages_layout.addWidget(self.pages_multi_select)
        filter_layout.addWidget(pages_group)

        # Apply filters button
        self.apply_filters_button = QPushButton("🔍 Apply Filters")
        self.apply_filters_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.apply_filters_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.apply_filters_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.apply_filters_button)

        filter_layout.addStretch()
        parent_splitter.addWidget(filter_card)

    def setup_candidates_panel(self, parent_splitter):
        """Setup the candidates panel on the right side."""
        # Candidates Panel Card
        candidates_card = QGroupBox("🔗 Cross-Sell Candidates")
        candidates_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                font-size: 14px;
            }
        """)
        candidates_layout = QVBoxLayout(candidates_card)
        candidates_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        self.candidates_header = QLabel("Cross-Sell Candidates")
        self.candidates_header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.candidates_header.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        self.candidates_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        candidates_layout.addWidget(self.candidates_header)

        # Candidates grid in scroll area
        self.candidates_scroll = QScrollArea()
        self.candidates_scroll.setWidgetResizable(True)
        self.candidates_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.candidates_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #343a40;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
            }
        """)

        self.candidates_grid_widget = QWidget()
        self.candidates_grid_layout = QGridLayout(self.candidates_grid_widget)
        self.candidates_scroll.setWidget(self.candidates_grid_widget)
        candidates_layout.addWidget(self.candidates_scroll)

        # Selected cross-sells bar
        selected_group = QGroupBox("✅ Selected Cross-Sells")
        selected_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                margin-top: 0.5ex;
                background-color: #343a40;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        selected_layout = QVBoxLayout(selected_group)
        selected_layout.setContentsMargins(10, 10, 10, 10)

        self.selected_scroll = QScrollArea()
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setMinimumHeight(200)
        self.selected_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.selected_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.selected_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.selected_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
            }
        """)

        self.selected_bar_widget = QWidget()
        self.selected_bar_layout = QHBoxLayout(self.selected_bar_widget)
        self.selected_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_bar_layout.setSpacing(8)  # Add gap between cards
        self.selected_scroll.setWidget(self.selected_bar_widget)
        selected_layout.addWidget(self.selected_scroll)

        candidates_layout.addWidget(selected_group)

        parent_splitter.addWidget(candidates_card)

    def setup_navigation_bar(self, parent_layout):
        """Setup the navigation bar at the bottom."""
        # Navigation Card
        nav_card = QGroupBox("🧭 Navigation & Actions")
        nav_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #ffffff;
                font-size: 14px;
            }
        """)
        nav_widget = QWidget()
        nav_widget.setFixedHeight(70)
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(20, 10, 20, 10)

        # Progress info
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_label = QLabel("")
        self.progress_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.progress_label.setStyleSheet("color: #ffffff;")
        progress_layout.addWidget(self.progress_label)

        self.product_info_label_bottom = QLabel("")
        self.product_info_label_bottom.setFont(QFont("Arial", 12))
        self.product_info_label_bottom.setStyleSheet("color: #cccccc;")
        self.product_info_label_bottom.setWordWrap(True)
        progress_layout.addWidget(self.product_info_label_bottom)

        nav_layout.addWidget(progress_widget)

        nav_layout.addStretch()

        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.cancel_button.setFixedSize(120, 45)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)

        self.deselect_button = QPushButton("⛔ Deselect All")
        self.deselect_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.deselect_button.setFixedSize(140, 45)
        self.deselect_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
        """)
        self.deselect_button.clicked.connect(self.deselect_all)
        button_layout.addWidget(self.deselect_button)

        self.prev_button = QPushButton("⬅️ Previous")
        self.prev_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.prev_button.setFixedSize(140, 45)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #495057;
                color: #6c757d;
            }
        """)
        self.prev_button.clicked.connect(self.go_previous)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ➡️")
        self.next_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.next_button.setFixedSize(140, 45)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #495057;
                color: #6c757d;
            }
        """)
        self.next_button.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_button)

        self.finish_button = QPushButton("✅ Finish")
        self.finish_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finish_button.setFixedSize(140, 45)
        self.finish_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.finish_button.clicked.connect(self.finish)
        button_layout.addWidget(self.finish_button)

        nav_layout.addLayout(button_layout)
        nav_card.setLayout(nav_layout)
        parent_layout.addWidget(nav_card)

    def load_product_into_ui(self, idx):
        """Load product data into the UI."""
        product = self.products_list[idx]
        sku = product.get('SKU', 'Unknown')
        name = product.get('Name', 'Unknown Product')
        
        # Update product info in bottom bar
        self.product_info_label_bottom.setText(f"{name}\nSKU: {sku}")
        
        # Set default filters to current product's values
        category_str = str(product.get('Category', '')).strip()
        type_str = str(product.get('Product Type', '')).strip()
        pages_str = str(product.get('Product On Pages', '')).strip()
        
        # Parse pipe-separated values
        default_categories = [c.strip() for c in category_str.split('|') if c.strip()] if category_str else []
        default_types = [t.strip() for t in type_str.split('|') if t.strip()] if type_str else []
        default_pages = [p.strip() for p in pages_str.split('|') if p.strip()] if pages_str else []
        
        # Set filter defaults
        self.category_multi_select.set_selected(default_categories)
        self.type_multi_select.set_selected(default_types)
        self.pages_multi_select.set_selected(default_pages)
        
        # Update progress
        self.progress_label.setText(f"Product {idx + 1} of {len(self.products_list)}")
        
        # Update button states
        self.prev_button.setEnabled(idx > 0)
        self.next_button.setEnabled(idx < len(self.products_list) - 1)
        self.finish_button.setEnabled(idx == len(self.products_list) - 1)
        
        # Load candidates with current filters
        self.apply_filters()

    def on_filters_changed(self):
        """Called when filter selections change."""
        # Could auto-apply filters here, but for now we'll require manual apply
        pass

    def apply_filters(self):
        """Apply current filters and load candidates."""
        category_filters = self.category_multi_select.get_selected()
        type_filters = self.type_multi_select.get_selected()
        page_filters = self.pages_multi_select.get_selected()
        
        current_product = self.products_list[self.current_index]
        exclude_sku = current_product.get('SKU', '')
        
        # Query database for candidates
        candidates = query_cross_sell_candidates(
            category_filters, type_filters, page_filters, 
            exclude_sku=exclude_sku, limit=50
        )
        
        # Update candidates display
        self.display_candidates(candidates)

    def display_candidates(self, candidates):
        """Display candidates in the grid."""
        self.current_candidates = candidates  # Store for selected bar
        
        # Clear existing candidates
        for i in reversed(range(self.candidates_grid_layout.count())):
            widget = self.candidates_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Clear image cache
        self.image_cache.clear()
        
        # Display candidates in grid (4 columns)
        cols = 4
        for i, candidate in enumerate(candidates):
            row = i // cols
            col = i % cols
            
            # Create candidate card
            card = self.create_candidate_card(candidate)
            self.candidates_grid_layout.addWidget(card, row, col)
        
        # Update header
        self.candidates_header.setText(f"Cross-Sell Candidates ({len(candidates)} found)")
        
        # Update selected bar
        self.update_selected_bar()

    def create_candidate_card(self, candidate):
        """Create a card widget for a candidate product."""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)
        card.setFixedSize(180, 200)
        
        sku = candidate.get('SKU', '')
        name = candidate.get('Name', '')
        images_field = candidate.get('Images', '')
        image_url = get_first_image_url(images_field)
        
        # Set border color based on selection
        is_selected = sku in self.selected_cross_sells[self.current_index]
        border_color = "#1976d2" if is_selected else "#cccccc"
        card.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {border_color};
                border-radius: 5px;
                background-color: #ffffff;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(is_selected)
        checkbox.stateChanged.connect(lambda state, s=sku: self.on_candidate_selected(s, state))
        layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Image
        image_label = QLabel()
        image_label.setFixedSize(120, 120)
        image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
            }
        """)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if image_url:
            # Load image
            request = QNetworkRequest(QUrl(image_url))
            reply = self.network_manager.get(request)
            self.image_cache[image_url] = image_label
        else:
            image_label.setText("No image")
        
        layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Name (truncated)
        display_name = name if len(name) <= 25 else name[:22] + "..."
        name_label = QLabel(display_name)
        name_label.setFont(QFont("Arial", 10))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # SKU
        sku_label = QLabel(f"SKU: {sku}")
        sku_label.setFont(QFont("Arial", 9))
        sku_label.setStyleSheet("color: #6c757d;")
        sku_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sku_label)
        
        return card

    def on_candidate_selected(self, sku, state):
        """Handle candidate selection change."""
        if state == 2:  # Checked
            if len(self.selected_cross_sells[self.current_index]) < MAX_CROSS_SELLS:
                self.selected_cross_sells[self.current_index].add(sku)
            else:
                # Prevent selection if at max - uncheck the box
                # Find the checkbox and uncheck it
                for i in range(self.candidates_grid_layout.count()):
                    card = self.candidates_grid_layout.itemAt(i).widget()
                    if card:
                        sku_label = None
                        for child in card.findChildren(QLabel):
                            if child.text().startswith("SKU: "):
                                sku_label = child
                                break
                        if sku_label and sku_label.text().replace("SKU: ", "") == sku:
                            checkbox = card.findChild(QCheckBox)
                            if checkbox:
                                checkbox.setChecked(False)
                            break
                return  # Don't proceed with updates
        else:  # Unchecked
            self.selected_cross_sells[self.current_index].discard(sku)
        
        # Update card borders
        self.update_candidate_borders()
        # Update selected bar
        self.update_selected_bar()

    def update_candidate_borders(self):
        """Update the border colors and checkbox states of candidate cards based on selection."""
        max_reached = len(self.selected_cross_sells[self.current_index]) >= MAX_CROSS_SELLS
        
        for i in range(self.candidates_grid_layout.count()):
            card = self.candidates_grid_layout.itemAt(i).widget()
            if card and hasattr(card, 'findChild'):
                checkbox = card.findChild(QCheckBox)
                sku_label = None
                for child in card.findChildren(QLabel):
                    if child.text().startswith("SKU: "):
                        sku_label = child
                        break
                
                if checkbox and sku_label:
                    sku = sku_label.text().replace("SKU: ", "")
                    is_selected = sku in self.selected_cross_sells[self.current_index]
                    
                    # Update checkbox state
                    checkbox.setChecked(is_selected)
                    # Disable checkbox if max reached and not selected
                    checkbox.setEnabled(not (max_reached and not is_selected))
                    
                    # Update border color and opacity
                    border_color = "#1976d2" if is_selected else "#cccccc"
                    opacity = "1.0" if not max_reached or is_selected else "0.4"
                    
                    card.setStyleSheet("""
                        QFrame {{
                            border: 2px solid {};
                            border-radius: 5px;
                            background-color: #ffffff;
                            opacity: {};
                        }}
                    """.format(border_color, opacity))

    def update_selected_bar(self):
        """Update the selected cross-sells bar."""
        # Clear existing items
        for i in reversed(range(self.selected_bar_layout.count())):
            widget = self.selected_bar_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Add selected items
        for sku in sorted(self.selected_cross_sells[self.current_index]):
            # Find the candidate info
            candidate_info = None
            for candidate in self.current_candidates:
                if candidate.get('SKU') == sku:
                    candidate_info = candidate
                    break
            
            if candidate_info:
                # Create a smaller card for selected item
                selected_card = QFrame()
                selected_card.setFrameStyle(QFrame.Shape.Box)
                selected_card.setFixedSize(110, 140)
                selected_card.setStyleSheet("""
                    QFrame {
                        border: 2px solid #1976d2;
                        border-radius: 3px;
                        background-color: #ffffff;
                    }
                """)
                
                layout = QVBoxLayout(selected_card)
                layout.setContentsMargins(3, 3, 3, 3)
                
                # Checkbox (checked and enabled for deselection)
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(lambda state, s=sku: self.remove_selected_cross_sell(s))
                layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
                
                # Image
                image_label = QLabel()
                image_label.setFixedSize(70, 70)
                image_label.setStyleSheet("""
                    QLabel {
                        background-color: #f8f9fa;
                        border: 1px solid #dee2e6;
                        border-radius: 2px;
                    }
                """)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                images_field = candidate_info.get('Images', '')
                image_url = get_first_image_url(images_field)
                if image_url:
                    # Load image
                    request = QNetworkRequest(QUrl(image_url))
                    reply = self.network_manager.get(request)
                    self.image_cache[image_url] = image_label
                else:
                    image_label.setText("No image")
                
                layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignCenter)
                
                # Name (truncated)
                name = candidate_info.get('Name', '')
                display_name = name if len(name) <= 15 else name[:12] + "..."
                name_label = QLabel(display_name)
                name_label.setFont(QFont("Arial", 8))
                name_label.setWordWrap(True)
                name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(name_label)
                
                # SKU
                sku_label = QLabel(f"{sku}")
                sku_label.setFont(QFont("Arial", 7))
                sku_label.setStyleSheet("color: #6c757d;")
                sku_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(sku_label)
                
                self.selected_bar_layout.addWidget(selected_card)
        
        # No stretch needed - items are centered

    def remove_selected_cross_sell(self, sku):
        """Remove a cross-sell from the selected list."""
        self.selected_cross_sells[self.current_index].discard(sku)
        self.update_candidate_borders()
        self.update_selected_bar()

    def deselect_all(self):
        """Deselect all cross-sells for current product."""
        self.selected_cross_sells[self.current_index].clear()
        self.update_candidate_borders()
        self.update_selected_bar()

    def go_previous(self):
        self.current_index -= 1
        self.load_product_into_ui(self.current_index)

    def go_next(self):
        self.current_index += 1
        self.load_product_into_ui(self.current_index)

    def finish(self):
        print("\n🏁 Finishing cross-sell editor...")
        print(f"📊 Total products: {len(self.products_list)}")
        print(f"👀 Current product index: {self.current_index}")
        print(f"💾 Products reviewed: {self.current_index + 1}")
        print(f"🤖 Products with auto-classifications only: {len(self.products_list) - (self.current_index + 1)}")
        
        # Save selections to products
        for idx, product in enumerate(self.products_list):
            product[CROSS_SELL_FIELD] = "|".join(self.selected_cross_sells[idx])
        
        self.close()
    
    def closeEvent(self, event):
        """Emit finished signal when window closes."""
        self.finished.emit()
        super().closeEvent(event)

    def cancel(self):
        reply = QMessageBox.question(
            self, 'Cancel',
            'Are you sure you want to cancel? All changes will be lost.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.products_list.clear()  # Clear to signal cancellation
            self.close()

    def get_products_list(self):
        """Return the products list (may be empty if cancelled)."""
        return self.products_list


def edit_cross_sells_in_batch(products_list):
    """
    Interactive batch editor for cross-sells using PyQt6 and database filtering.
    For each product, allows user to filter and select up to 4 cross-sell candidates.
    Returns updated products_list with selected cross-sells.
    """
    # Create the application and main window
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    window = CrossSellEditorWindow(products_list)
    window.show()

    # Use QEventLoop to wait for window closure
    from PyQt6.QtCore import QEventLoop
    loop = QEventLoop()
    window.finished.connect(loop.quit)
    loop.exec()

    # Return the updated products list
    return window.get_products_list()


if __name__ == "__main__":
    # Demo: Show UI with dummy products
    demo_products = [
        {
            "SKU": "DEMO001",
            "Name": "Premium Dog Food Sample",
            "Category": "Dog Food",
            "Product Type": "Food",
            "Product On Pages": "Dog Food Shop All"
        },
        {
            "SKU": "DEMO002", 
            "Name": "Cat Toy Bundle",
            "Category": "Cat Supplies",
            "Product Type": "Cat Toys",
            "Product On Pages": "Cat Supplies Shop All"
        },
        {
            "SKU": "DEMO003",
            "Name": "Unclassified Bird Seed",
            "Category": "",
            "Product Type": "",
            "Product On Pages": ""
        }
    ]

    print("Launching cross-sell UI demo with database filtering...")
    print("DEMO001 should show filters pre-set to 'Dog Food', 'Dry Dog Food', etc.")
    print("Use the filter controls on the left to find cross-sell candidates.")
    print("Select up to 4 cross-sell products for each item.")
    print()

    # Launch the UI
    results = edit_cross_sells_in_batch(demo_products)

    print("\nDemo complete. Results:")
    for prod in results:
        print(f"{prod['SKU']}: {prod.get('Product Cross Sell', '')}")