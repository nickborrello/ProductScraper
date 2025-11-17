"""
Product Classification Module
Handles product classification (Category, Product Type, Product On Pages) using interactive UI.
Separates business logic from basic product editing (product_editor.py).
"""

import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Check if GUI is available (for headless CI environments)
GUI_AVAILABLE = True
# Check for CI/test environments
is_ci = (
    os.environ.get("CI") == "true"
    or os.environ.get("GITHUB_ACTIONS") == "true"
    or "pytest" in os.environ.get("_", "")
)

# Check if we're running under pytest by inspecting the call stack
import inspect

is_pytest = any("pytest" in str(frame) for frame in inspect.stack())
if is_pytest:
    is_ci = True

# On Unix-like systems, also check for missing DISPLAY
if os.name != "nt":  # Not Windows
    is_ci = is_ci or os.environ.get("DISPLAY", "") == ""

if TYPE_CHECKING:
    # Type checking imports for PyQt6
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                                 QMessageBox, QPushButton, QScrollArea,
                                 QSplitter, QVBoxLayout, QWidget)

if is_ci:
    GUI_AVAILABLE = False
    print("Warning: Running in CI/test environment, disabling GUI")
else:
    try:
        # PyQt6 imports
        from PyQt6.QtCore import Qt, pyqtSignal
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import (QApplication, QCheckBox, QFrame,
                                     QGridLayout, QHBoxLayout, QLabel,
                                     QLineEdit, QMainWindow, QMessageBox,
                                     QPushButton, QScrollArea, QSplitter,
                                     QVBoxLayout, QWidget)
    except ImportError as e:
        # GUI not available (headless environment)
        GUI_AVAILABLE = False
        print(f"⚠️ PyQt6 GUI not available (headless environment): {e}")

# Import product pages from manager (which loads from JSON) - moved inside function to avoid relative import issues when run directly
# from .manager import PRODUCT_PAGES


def get_facet_options_from_db(force_refresh=False):
    """
    Load facet options from JSON files instead of database.

    Args:
        force_refresh: Ignored (kept for compatibility)

    Returns:
        Tuple of (category_product_types_dict, product_on_pages_list)
    """
    try:
        # Load taxonomy from JSON via taxonomy manager
        from .taxonomy_manager import get_product_taxonomy

        category_product_types = get_product_taxonomy()

        # Load product pages from JSON via manager
        from .manager import get_product_pages

        product_on_pages_options = get_product_pages()

        return category_product_types, product_on_pages_options

    except (ImportError, ModuleNotFoundError) as e:
        # Handle relative import failures when run directly
        print(
            f"⚠️ Relative import failed (running standalone), using fallback defaults: {e}"
        )
        # Fallback defaults if JSON files don't exist or are corrupted
        default_categories = {
            "Dog Food": ["Dry Dog Food", "Wet Dog Food", "Raw Dog Food", "Dog Treats"],
            "Cat Food": ["Dry Cat Food", "Wet Cat Food", "Raw Cat Food", "Cat Treats"],
            "Bird Supplies": [
                "Bird Food",
                "Bird Cages",
                "Bird Toys",
                "Bird Healthcare",
            ],
            "Small Pet Food": [
                "Rabbit Food",
                "Guinea Pig Food",
                "Hamster Food",
                "Rat Food",
            ],
            "Farm Animal Supplies": [
                "Chicken Feed",
                "Goat Feed",
                "Sheep Feed",
                "Pig Feed",
            ],
            "Pet Toys": ["Dog Toys", "Cat Toys", "Bird Toys", "Small Pet Toys"],
            "Pet Healthcare": [
                "Dog Medications",
                "Cat Medications",
                "Bird Medications",
                "Small Pet Medications",
            ],
            "Pet Grooming": [
                "Dog Shampoos",
                "Cat Shampoos",
                "Pet Brushes",
                "Pet Clippers",
            ],
            "Pet Beds": ["Dog Beds", "Cat Beds", "Small Pet Beds"],
            "Pet Bowls": ["Dog Bowls", "Cat Bowls", "Bird Bowls", "Small Pet Bowls"],
            "Hardware": ["Tools", "Fasteners", "Plumbing", "Electrical", "HVAC"],
            "Lawn & Garden": ["Seeds", "Fertilizer", "Tools", "Plants"],
            "Farm Supplies": ["Fencing", "Feeders", "Equipment", "Animal Health"],
            "Home & Kitchen": ["Cleaning", "Storage", "Appliances", "Decor"],
            "Automotive": ["Parts", "Tools", "Maintenance", "Accessories"],
        }
        default_pages = [
            "Dog Food Shop All",
            "Cat Food Shop All",
            "Bird Supplies Shop All",
            "Small Pet Food Shop All",
            "Farm Animal Supplies Shop All",
            "Pet Toys Shop All",
            "Pet Healthcare Shop All",
            "Pet Grooming Shop All",
            "Pet Beds Shop All",
            "Pet Bowls Shop All",
            "Hardware Shop All",
            "Lawn & Garden Shop All",
            "Farm Supplies Shop All",
            "Home & Kitchen Shop All",
            "Automotive Shop All",
        ]
        return default_categories, default_pages
    except Exception as e:
        print(f"⚠️ Error loading facet options from JSON: {e}")
        # Fallback defaults if JSON files don't exist or are corrupted
        default_categories = {
            "Dog Food": ["Dry Dog Food", "Wet Dog Food", "Raw Dog Food", "Dog Treats"],
            "Cat Food": ["Dry Cat Food", "Wet Cat Food", "Raw Cat Food", "Cat Treats"],
            "Bird Supplies": [
                "Bird Food",
                "Bird Cages",
                "Bird Toys",
                "Bird Healthcare",
            ],
            "Small Pet Food": [
                "Rabbit Food",
                "Guinea Pig Food",
                "Hamster Food",
                "Rat Food",
            ],
            "Farm Animal Supplies": [
                "Chicken Feed",
                "Goat Feed",
                "Sheep Feed",
                "Pig Feed",
            ],
            "Pet Toys": ["Dog Toys", "Cat Toys", "Bird Toys", "Small Pet Toys"],
            "Pet Healthcare": [
                "Dog Medications",
                "Cat Medications",
                "Bird Medications",
                "Small Pet Medications",
            ],
            "Pet Grooming": [
                "Dog Shampoos",
                "Cat Shampoos",
                "Pet Brushes",
                "Pet Clippers",
            ],
            "Pet Beds": ["Dog Beds", "Cat Beds", "Small Pet Beds"],
            "Pet Bowls": ["Dog Bowls", "Cat Bowls", "Bird Bowls", "Small Pet Bowls"],
            "Hardware": ["Tools", "Fasteners", "Plumbing", "Electrical", "HVAC"],
            "Lawn & Garden": ["Seeds", "Fertilizer", "Tools", "Plants"],
            "Farm Supplies": ["Fencing", "Feeders", "Equipment", "Animal Health"],
            "Home & Kitchen": ["Cleaning", "Storage", "Appliances", "Decor"],
            "Automotive": ["Parts", "Tools", "Maintenance", "Accessories"],
        }
        default_pages = [
            "Dog Food Shop All",
            "Cat Food Shop All",
            "Bird Supplies Shop All",
            "Small Pet Food Shop All",
            "Farm Animal Supplies Shop All",
            "Pet Toys Shop All",
            "Pet Healthcare Shop All",
            "Pet Grooming Shop All",
            "Pet Beds Shop All",
            "Pet Bowls Shop All",
            "Hardware Shop All",
            "Lawn & Garden Shop All",
            "Farm Supplies Shop All",
            "Home & Kitchen Shop All",
            "Automotive Shop All",
        ]
        return default_categories, default_pages


def clear_facet_cache():
    """
    Clear the facet options cache (dummy function for compatibility).
    In the new JSON-based system, there's no cache to clear.
    """
    pass  # No-op since we don't cache in the JSON system


def assign_classification_batch(products_list):
    """
    Assign classification (Category, Product Type, Product On Pages) to multiple products using the interactive batch UI.
    Always uses the UI, even for a single product.
    Args:
        products_list: List of product_info dictionaries
    Returns:
        List of product_info dictionaries with classifications assigned
    """
    print(
        f"🏷️ Classification Assignment (UI): Processing {len(products_list)} products..."
    )
    # Always use the interactive batch UI
    results = edit_classification_in_batch(products_list)
    print(
        f"\033[92m✅ Classification assignment (UI) complete! Processed {len(results)} products\033[0m\n"
    )
    return results


def assign_classification_single(product_info):
    """
    Assign classification to a single product using the interactive batch UI.
    Treated as a batch of one.
    Args:
        product_info: Dict with product details
    Returns:
        Dict: Product_info with classifications assigned
    """
    batch = [product_info]
    results = assign_classification_batch(batch)
    return results[0]


if GUI_AVAILABLE:

    class MultiSelectWidget(QWidget):  # type: ignore
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

        def setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            # Search section
            search_layout = QHBoxLayout()
            search_label = QLabel(f"Search {self.label}:")
            search_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            search_layout.addWidget(search_label)

            self.search_edit = QLineEdit()
            self.search_edit.setFont(QFont("Arial", 12))
            self.search_edit.textChanged.connect(self.filter_options)
            search_layout.addWidget(self.search_edit)

            search_layout.addStretch()
            layout.addLayout(search_layout)

            # Available options section
            available_label = QLabel(f"Available {self.label}:")
            available_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(available_label)

            self.available_scroll = QScrollArea()
            self.available_scroll.setWidgetResizable(True)
            self.available_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.available_scroll.setMinimumHeight(200)
            self.available_scroll.setMaximumHeight(300)

            available_widget = QWidget()
            self.available_layout = QVBoxLayout(available_widget)
            self.available_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.available_scroll.setWidget(available_widget)
            layout.addWidget(self.available_scroll)

            # Selected options section
            selected_label = QLabel(f"Selected {self.label}:")
            selected_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(selected_label)

            self.selected_scroll = QScrollArea()
            self.selected_scroll.setWidgetResizable(True)
            self.selected_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.selected_scroll.setMinimumHeight(200)
            self.selected_scroll.setMaximumHeight(300)

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
                self.current_options = [
                    opt for opt in self.all_options if query in opt.lower()
                ]
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
                    checkbox.setChecked(False)
                    checkbox.stateChanged.connect(
                        lambda state, opt=option: self.on_available_changed(opt, state)
                    )
                    self.available_layout.addWidget(checkbox)
                    self.checkboxes[option] = checkbox

            # Selected options
            for option in sorted(self.selected_items, key=str.lower):
                checkbox = QCheckBox(option)
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(
                    lambda state, opt=option: self.on_selected_changed(opt, state)
                )
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

    from src.ui.styling import STYLESHEET

    class ClassificationEditorWindow(QMainWindow):  # type: ignore
        """PyQt6 main window for batch classification editing."""

        def __init__(
            self,
            products_list,
            category_options,
            all_product_types,
            product_on_pages_options,
            category_product_types,
        ):
            super().__init__()
            self.products_list = products_list
            self.category_options = category_options
            self.all_product_types = all_product_types
            self.product_on_pages_options = product_on_pages_options
            self.category_product_types = category_product_types
            self.current_index = 0
            self.multi_select_widgets = {}

            # Apply global dark theme
            self.setStyleSheet(STYLESHEET)

            self.setup_ui()  # type: ignore
            self.load_product_into_ui(0)  # type: ignore

    def setup_ui(self):
        self.setWindowTitle(
            f"Batch Classification Editor - {len(self.products_list)} Products"
        )
        # Launch maximized
        self.showMaximized()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter - product info on left, classification on right
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)  # type: ignore

        # Left side - Product Information Panel
        self.setup_product_info_panel(main_splitter)

        # Right side - Classification Panel
        self.setup_classification_panel(main_splitter)

        # Set splitter proportions (30% product info, 70% classification)
        main_splitter.setSizes([400, 1000])

        # Navigation bar at bottom
        self.setup_navigation_bar(central_widget.layout())

    def setup_product_info_panel(self, parent_splitter):
        """Setup the product information panel on the left side."""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)

        # Product header
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QVBoxLayout(header_frame)

        # Product title
        self.product_name_label = QLabel("")
        self.product_name_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.product_name_label.setWordWrap(True)
        header_layout.addWidget(self.product_name_label)

        # SKU
        self.product_sku_label = QLabel("")
        self.product_sku_label.setFont(QFont("Arial", 12, QFont.Weight.Normal, True))
        header_layout.addWidget(self.product_sku_label)

        info_layout.addWidget(header_frame)

        # Product details grid
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.Shape.Box)
        details_layout = QVBoxLayout(details_frame)

        # Create a grid for product details
        details_grid = QWidget()
        grid_layout = QGridLayout(details_grid)

        # Labels for product details
        labels = [
            ("Brand:", "brand"),
            ("Price:", "price"),
            ("Weight:", "weight"),
            ("Images:", "images"),
        ]

        self.detail_labels = {}
        for i, (label_text, key) in enumerate(labels):
            # Label
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            grid_layout.addWidget(label, i, 0, Qt.AlignmentFlag.AlignTop)

            # Value
            value_label = QLabel("")
            value_label.setFont(QFont("Arial", 11))
            value_label.setWordWrap(True)
            grid_layout.addWidget(value_label, i, 1)
            self.detail_labels[key] = value_label

        details_layout.addWidget(details_grid)
        info_layout.addWidget(details_frame)

        # Product image display
        image_frame = QFrame()
        image_frame.setFrameStyle(QFrame.Shape.Box)
        image_layout = QVBoxLayout(image_frame)

        image_label = QLabel("Product Image:")
        image_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        image_layout.addWidget(image_label)

        # Placeholder for image
        self.image_display = QLabel("No image available")
        self.image_display.setFixedSize(200, 200)
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_display)

        info_layout.addWidget(image_frame)

        # Add stretch to push everything to top
        info_layout.addStretch()

        parent_splitter.addWidget(info_widget)

    def setup_classification_panel(self, parent_splitter):
        """Setup the classification panel on the right side."""
        classification_widget = QWidget()
        classification_layout = QVBoxLayout(classification_widget)

        # Classification header
        class_header = QLabel("Product Classification")
        class_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        classification_layout.addWidget(class_header)

        # Classification selection area - horizontal splitter for three columns
        selection_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Category section
        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)
        category_label = QLabel("📁 Category")
        category_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        category_layout.addWidget(category_label)

        self.category_multi_select = MultiSelectWidget(
            "Category", self.category_options
        )
        self.category_multi_select.selection_changed.connect(self.on_category_changed)
        category_layout.addWidget(self.category_multi_select)
        selection_splitter.addWidget(category_widget)

        # Product Type section
        type_widget = QWidget()
        type_layout = QVBoxLayout(type_widget)
        type_label = QLabel("🏷️ Product Type")
        type_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        type_layout.addWidget(type_label)

        self.type_multi_select = MultiSelectWidget(
            "Product Type", self.all_product_types
        )
        type_layout.addWidget(self.type_multi_select)
        selection_splitter.addWidget(type_widget)

        # Product On Pages section
        pages_widget = QWidget()
        pages_layout = QVBoxLayout(pages_widget)
        pages_label = QLabel("📄 Product On Pages")
        pages_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        pages_layout.addWidget(pages_label)

        self.pages_multi_select = MultiSelectWidget(
            "Product On Pages", self.product_on_pages_options
        )
        pages_layout.addWidget(self.pages_multi_select)
        selection_splitter.addWidget(pages_widget)

        # Set equal widths for the three sections
        selection_splitter.setSizes([333, 333, 334])
        classification_layout.addWidget(selection_splitter)

        self.multi_select_widgets = {
            "Category": self.category_multi_select,
            "Product Type": self.type_multi_select,
            "Product On Pages": self.pages_multi_select,
        }

        parent_splitter.addWidget(classification_widget)

    def setup_navigation_bar(self, parent_layout):
        """Setup the navigation bar at the bottom."""
        nav_widget = QWidget()
        nav_widget.setFixedHeight(70)
        nav_widget.setStyleSheet(
            """
            QWidget {
                background-color: #343a40;
                border-top: 2px solid #495057;
            }
        """
        )

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

        self.product_count_label = QLabel("")
        self.product_count_label.setFont(QFont("Arial", 10))
        self.product_count_label.setStyleSheet("color: #adb5bd;")
        progress_layout.addWidget(self.product_count_label)

        nav_layout.addWidget(progress_widget)

        nav_layout.addStretch()

        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.cancel_button.setFixedSize(120, 45)
        self.cancel_button.setStyleSheet(
            """
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
        """
        )
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)

        self.prev_button = QPushButton("⬅️ Previous")
        self.prev_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.prev_button.setFixedSize(140, 45)
        self.prev_button.setStyleSheet(
            """
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
                background-color: #adb5bd;
                color: #6c757d;
            }
        """
        )
        self.prev_button.clicked.connect(self.go_previous)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ➡️")
        self.next_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.next_button.setFixedSize(140, 45)
        self.next_button.setStyleSheet(
            """
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
                background-color: #adb5bd;
                color: #6c757d;
            }
        """
        )
        self.next_button.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_button)

        self.finish_button = QPushButton("✅ Finish")
        self.finish_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finish_button.setFixedSize(140, 45)
        self.finish_button.setStyleSheet(
            """
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
        """
        )
        self.finish_button.clicked.connect(self.finish)
        button_layout.addWidget(self.finish_button)

        nav_layout.addLayout(button_layout)
        parent_layout.addWidget(nav_widget)

    def normalize_selections(self, selections, available_options):
        """Normalize selections from string or list format, handling comma/pipe separators."""
        if isinstance(selections, str):
            # Split on comma or pipe, strip whitespace
            selections = [s.strip() for s in re.split(r"[|,]", selections) if s.strip()]
        elif not isinstance(selections, list):
            selections = []

        # Filter to only available options
        return [s for s in selections if s in available_options]

    def load_product_into_ui(self, idx):
        """Load product data into the classification UI."""
        product = self.products_list[idx]

        # Update product header
        name = product.get("Name", "Unknown Product")
        sku = product.get("SKU", "Unknown")
        self.product_name_label.setText(name)
        self.product_sku_label.setText(f"SKU: {sku}")

        # Update product details
        self.detail_labels["brand"].setText(
            product.get("Product_Field_16", "N/A")
        )  # Brand
        self.detail_labels["price"].setText(product.get("Price", "N/A"))
        self.detail_labels["weight"].setText(product.get("Weight", "N/A"))

        # Handle images
        images_text = product.get("Images", "")
        if images_text:
            image_urls = [url.strip() for url in images_text.split(",") if url.strip()]
            self.detail_labels["images"].setText(
                f"{len(image_urls)} image(s) available"
            )
            # Try to load the first image
            self.load_product_image(image_urls[0] if image_urls else None)
        else:
            self.detail_labels["images"].setText("No images")
            self.load_product_image(None)

        # Update progress
        self.progress_label.setText(f"Product {idx + 1} of {len(self.products_list)}")
        self.product_count_label.setText(f"Classifying: {name[:50]}...")

        # Get current selections from product data
        category_list = self.normalize_selections(
            product.get("Category", ""), self.category_options
        )
        product_type_list = self.normalize_selections(
            product.get("Product Type", ""), self.all_product_types
        )
        pages_list = self.normalize_selections(
            product.get("Product On Pages", ""), self.product_on_pages_options
        )

        # Update multi-select widgets with current selections
        self.category_multi_select.selected_items = set(category_list)
        self.category_multi_select.update_display()

        # Filter product types based on selected categories
        if category_list:
            filtered_types = set()
            for cat in category_list:
                if cat in self.category_product_types:
                    filtered_types.update(self.category_product_types[cat])
            product_type_options = sorted(filtered_types, key=str.lower)
        else:
            product_type_options = self.all_product_types

        self.type_multi_select.refresh_options(product_type_options)
        self.type_multi_select.selected_items = set(product_type_list)
        self.type_multi_select.update_display()

        self.pages_multi_select.selected_items = set(pages_list)
        self.pages_multi_select.update_display()

        # Update button states
        self.prev_button.setEnabled(idx > 0)
        self.next_button.setEnabled(idx < len(self.products_list) - 1)
        self.finish_button.setEnabled(idx == len(self.products_list) - 1)

    def load_product_image(self, image_url):
        """Load and display product image."""
        if image_url:
            try:
                # For now, just show the URL since we can't easily load images in PyQt6 without additional setup
                # In a real implementation, you'd use QNetworkAccessManager or similar
                self.image_display.setText(f"Image URL:\n{image_url}")
                self.image_display.setStyleSheet(
                    """
                    QLabel {
                        background-color: #e9ecef;
                        border: 1px solid #adb5bd;
                        border-radius: 5px;
                        color: #495057;
                        font-size: 10px;
                        padding: 5px;
                        text-align: center;
                    }
                """
                )
            except Exception as e:
                self.image_display.setText("Failed to load image")
                self.image_display.setStyleSheet(
                    """
                    QLabel {
                        background-color: #f8d7da;
                        border: 1px solid #f5c6cb;
                        border-radius: 5px;
                        color: #721c24;
                        font-size: 12px;
                    }
                """
                )
        else:
            self.image_display.setText("No image available")
            self.image_display.setStyleSheet(
                """
                QLabel {
                    background-color: #e9ecef;
                    border: 2px dashed #adb5bd;
                    border-radius: 5px;
                    color: #6c757d;
                    font-size: 12px;
                }
            """
            )

    def on_category_changed(self):
        """Filter Product Types based on selected Categories."""
        selected_categories = self.category_multi_select.get_selected()
        if selected_categories:
            filtered_types = set()
            for cat in selected_categories:
                if cat in self.category_product_types:
                    filtered_types.update(self.category_product_types[cat])
            product_type_options = sorted(filtered_types, key=str.lower)
        else:
            product_type_options = self.all_product_types

        # Refresh Product Type multi-select with new options
        self.type_multi_select.refresh_options(product_type_options)

    def save_current_product(self):
        """Save current multi-select values back to product data."""
        product = self.products_list[self.current_index]

        # Save selected values
        product["Category"] = "|".join(self.category_multi_select.get_selected())
        product["Product Type"] = "|".join(self.type_multi_select.get_selected())
        product["Product On Pages"] = "|".join(self.pages_multi_select.get_selected())

    def go_previous(self):
        self.save_current_product()
        self.current_index -= 1
        self.load_product_into_ui(self.current_index)

    def go_next(self):
        self.save_current_product()
        self.current_index += 1
        self.load_product_into_ui(self.current_index)

    def finish(self):
        self.save_current_product()
        print("\n🏁 Finishing classification editor...")
        print(f"📊 Total products: {len(self.products_list)}")
        print(f"👀 Current product index: {self.current_index}")
        print(f"💾 Products reviewed: {self.current_index + 1}")
        print(
            f"🤖 Products with auto-classifications only: {len(self.products_list) - (self.current_index + 1)}"
        )
        self.close()

    def cancel(self):
        reply = QMessageBox.question(
            self,
            "Cancel",
            "Are you sure you want to cancel? All changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.products_list.clear()  # Clear to signal cancellation
            self.close()

    def get_products_list(self):
        """Return the products list (may be empty if cancelled)."""
        return self.products_list


def edit_classification_in_batch(products_list):
    """
    Interactive batch editor for product classification fields (Category, Product Type, Product On Pages).
    Focused on classification selection.
    Returns updated products_list with selected classifications.
    In headless environments, returns products unchanged.
    """
    if not GUI_AVAILABLE:
        print(
            "⚠️ GUI not available (headless environment), returning products unchanged"
        )
        return products_list

    # Import facet options only
    CATEGORY_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS = get_facet_options_from_db()

    # For consolidated products, augment available options with any categories/types/pages found in scraped data
    # that aren't already in the database
    if products_list and any("_consolidated_data" in p for p in products_list):
        print(
            "EDITOR DEBUG: Found consolidated products, augmenting facet options with scraped data..."
        )

        # Collect all unique options from consolidated data
        additional_categories = set()
        additional_product_types = set()
        additional_pages = set()

        for product in products_list:
            if "_consolidated_data" in product:
                consolidated = product["_consolidated_data"]

                # Add categories from consolidated data
                if "category_options" in consolidated:
                    additional_categories.update(consolidated["category_options"])

                # Add product types from consolidated data
                if "product_type_options" in consolidated:
                    additional_product_types.update(
                        consolidated["product_type_options"]
                    )

                # Add pages from consolidated data
                if "product_on_pages_options" in consolidated:
                    additional_pages.update(consolidated["product_on_pages_options"])

        # Add new categories to CATEGORY_PRODUCT_TYPES (with empty product type lists for now)
        for cat in additional_categories:
            if cat not in CATEGORY_PRODUCT_TYPES:
                CATEGORY_PRODUCT_TYPES[cat] = []
                print(f"EDITOR DEBUG: Added category from scraped data: {cat}")

        # Add new product types to existing categories (or create new categories if needed)
        for ptype in additional_product_types:
            # Find a suitable category for this product type, or create a generic one
            found_category = None
            for cat, types in CATEGORY_PRODUCT_TYPES.items():
                if ptype in types:
                    found_category = cat
                    break

            if not found_category:
                # Create a generic category for this product type
                generic_cat = "General Supplies"
                if generic_cat not in CATEGORY_PRODUCT_TYPES:
                    CATEGORY_PRODUCT_TYPES[generic_cat] = []
                if ptype not in CATEGORY_PRODUCT_TYPES[generic_cat]:
                    CATEGORY_PRODUCT_TYPES[generic_cat].append(ptype)
                    print(
                        f"EDITOR DEBUG: Added product type '{ptype}' to category '{generic_cat}'"
                    )

        # Add new pages to PRODUCT_ON_PAGES_OPTIONS
        for page in additional_pages:
            if page not in PRODUCT_ON_PAGES_OPTIONS:
                PRODUCT_ON_PAGES_OPTIONS.append(page)
                print(f"EDITOR DEBUG: Added page from scraped data: {page}")

    # Extract categories and all product types
    CATEGORY_OPTIONS = sorted(CATEGORY_PRODUCT_TYPES.keys(), key=str.lower)
    ALL_PRODUCT_TYPES = sorted(
        set(ptype for types in CATEGORY_PRODUCT_TYPES.values() for ptype in types),
        key=str.lower,
    )

    # Create the application and main window
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    window = ClassificationEditorWindow(
        products_list,
        CATEGORY_OPTIONS,
        ALL_PRODUCT_TYPES,
        PRODUCT_ON_PAGES_OPTIONS,
        CATEGORY_PRODUCT_TYPES,
    )
    window.show()

    # Start the event loop
    app.exec()

    # Return the updated products list
    return window.get_products_list()  # type: ignore


if __name__ == "__main__":
    # Check if running standalone classification
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--classify-excel":
        print("❌ classify_excel_file() has been moved to classify_excel.py")
        sys.exit(1)

    # Demo: Show UI with products that have pre-filled classifications to test preselection
    demo_products = [
        {
            "SKU": "DEMO001",
            "Name": "Premium Dog Food Sample",
            "Brand": "DemoBrand",
            "Category": "Dog Food|Pet Supplies",
            "Product Type": "Dry Dog Food|Premium Dog Food",
            "Product On Pages": "Dog Food Shop All|Premium Products",
        },
        {
            "SKU": "DEMO002",
            "Name": "Cat Toy Bundle",
            "Brand": "DemoBrand",
            "Category": "Cat Supplies",
            "Product Type": "Cat Toys",
            "Product On Pages": "Cat Supplies Shop All",
        },
        {
            "SKU": "DEMO003",
            "Name": "Unclassified Bird Seed",
            "Brand": "DemoBrand",
            "Category": "",  # Empty - should show no preselection
            "Product Type": "",
            "Product On Pages": "",
        },
    ]

    print("Launching classification UI demo with pre-filled data...")
    print("DEMO001 should show 'Dog Food' and 'Pet Supplies' pre-selected in Category")
    print(
        "DEMO001 should show 'Dry Dog Food' and 'Premium Dog Food' pre-selected in Product Type"
    )
    print(
        "DEMO001 should show 'Dog Food Shop All' and 'Premium Products' pre-selected in Pages"
    )
    print("DEMO002 should show 'Cat Supplies' pre-selected in Category")
    print("DEMO003 should show no pre-selections (empty checkboxes)")
    print()

    # Get facet options
    CATEGORY_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS = get_facet_options_from_db()
    CATEGORY_OPTIONS = sorted(CATEGORY_PRODUCT_TYPES.keys(), key=str.lower)
    ALL_PRODUCT_TYPES = sorted(
        set(ptype for types in CATEGORY_PRODUCT_TYPES.values() for ptype in types),
        key=str.lower,
    )

    # Create and show the demo window
    app = QApplication(sys.argv)
    window = ClassificationEditorWindow(  # type: ignore
        demo_products,
        CATEGORY_OPTIONS,
        ALL_PRODUCT_TYPES,
        PRODUCT_ON_PAGES_OPTIONS,
        CATEGORY_PRODUCT_TYPES,
    )
    window.show()

    # Start the event loop
    app.exec()

    results = window.get_products_list()  # type: ignore

    print("\nDemo complete. Results:")
    for prod in results:
        print(
            f"{prod['SKU']}: Category='{prod.get('Category', '')}', Type='{prod.get('Product Type', '')}', Pages='{prod.get('Product On Pages', '')}'"
        )
