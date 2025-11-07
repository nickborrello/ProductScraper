"""
Product Classification Module
Handles product classification (Category, Product Type, Product On Pages) using interactive UI.
Separates business logic from basic product editing (product_editor.py).
"""

import os
import sqlite3
import time
import pandas as pd
import re
import sys
from pathlib import Path

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QFrame, QCheckBox, QMessageBox,
    QSplitter, QProgressBar, QSizePolicy, QGridLayout
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

# Import local options
try:
    from .shopsite_constants import SHOPSITE_PAGES
except ImportError:
    # Handle case when run as standalone script
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shopsite_constants_path = os.path.join(current_dir, 'shopsite_constants.py')
    if os.path.exists(shopsite_constants_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("shopsite_constants", shopsite_constants_path)
        shopsite_constants_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shopsite_constants_module)
        SHOPSITE_PAGES = shopsite_constants_module.SHOPSITE_PAGES
    else:
        # Fallback if file doesn't exist
        SHOPSITE_PAGES = []

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "databases" / "products.db"

# Cache for facet options to avoid repeated database queries
_facet_cache = {
    'category_product_types': None,
    'product_on_pages_options': None,
    'cache_timestamp': None
}
CACHE_DURATION_SECONDS = 300  # 5 minutes

def clear_facet_cache():
    """Clear the facet options cache, forcing fresh database queries on next access."""
    global _facet_cache
    _facet_cache = {
        'category_product_types': None,
        'product_on_pages_options': None,
        'cache_timestamp': None
    }

def get_facet_options_from_db(force_refresh=False):
    """
    Query facet options directly from the database with caching.

    Args:
        force_refresh: If True, bypass cache and query database

    Returns:
        Tuple of (category_product_types_dict, product_on_pages_list)
    """
    import time

    # Check cache validity
    current_time = time.time()
    cache_valid = (
        _facet_cache['cache_timestamp'] is not None and
        (current_time - _facet_cache['cache_timestamp']) < CACHE_DURATION_SECONDS and
        not force_refresh
    )

    if cache_valid and _facet_cache['category_product_types'] is not None:
        print(f"DEBUG: Using cached facet options (age: {current_time - _facet_cache['cache_timestamp']:.1f}s)")
        return _facet_cache['category_product_types'], _facet_cache['product_on_pages_options']

    print(f"DEBUG: Querying database for category/product type options (cache {'expired' if _facet_cache['cache_timestamp'] else 'empty'} or force_refresh={force_refresh})")

    # Cache miss or expired - query database
    if not DB_PATH.exists():
        # Fallback defaults if database doesn't exist
        default_categories = {
            "Dog Food": ["Dry Dog Food", "Wet Dog Food", "Raw Dog Food", "Dog Treats"],
            "Cat Food": ["Dry Cat Food", "Wet Cat Food", "Raw Cat Food", "Cat Treats"],
            "Bird Supplies": ["Bird Food", "Bird Cages", "Bird Toys", "Bird Healthcare"],
            "Small Pet Food": ["Rabbit Food", "Guinea Pig Food", "Hamster Food", "Rat Food"],
            "Farm Animal Supplies": ["Chicken Feed", "Goat Feed", "Sheep Feed", "Pig Feed"],
            "Pet Toys": ["Dog Toys", "Cat Toys", "Bird Toys", "Small Pet Toys"],
            "Pet Healthcare": ["Dog Medications", "Cat Medications", "Bird Medications", "Small Pet Medications"],
            "Pet Grooming": ["Dog Shampoos", "Cat Shampoos", "Pet Brushes", "Pet Clippers"],
            "Pet Beds": ["Dog Beds", "Cat Beds", "Small Pet Beds"],
            "Pet Bowls": ["Dog Bowls", "Cat Bowls", "Bird Bowls", "Small Pet Bowls"],
            "Hardware": ["Tools", "Fasteners", "Plumbing", "Electrical", "HVAC"],
            "Lawn & Garden": ["Seeds", "Fertilizer", "Tools", "Plants"],
            "Farm Supplies": ["Fencing", "Feeders", "Equipment", "Animal Health"],
            "Home & Kitchen": ["Cleaning", "Storage", "Appliances", "Decor"],
            "Automotive": ["Parts", "Tools", "Maintenance", "Accessories"]
        }
        default_pages = sorted(list(SHOPSITE_PAGES), key=str.lower)
        _facet_cache.update({
            'category_product_types': default_categories,
            'product_on_pages_options': default_pages,
            'cache_timestamp': current_time
        })
        return default_categories, default_pages

    conn = sqlite3.connect(DB_PATH)
    try:
        # Check if there are any products with facet data
        cursor = conn.execute("""
            SELECT COUNT(*) FROM products
            WHERE Category IS NOT NULL OR Product_Type IS NOT NULL
        """)
        classified_count = cursor.fetchone()[0]

        if classified_count == 0:
            # No products with facet data, return minimal defaults
            default_categories = {
                "Dog Food": ["Dry Dog Food", "Wet Dog Food", "Raw Dog Food", "Dog Treats"],
                "Cat Food": ["Dry Cat Food", "Wet Cat Food", "Raw Cat Food", "Cat Treats"],
                "Bird Supplies": ["Bird Food", "Bird Cages", "Bird Toys", "Bird Healthcare"],
                "Small Pet Food": ["Rabbit Food", "Guinea Pig Food", "Hamster Food", "Rat Food"],
                "Farm Animal Supplies": ["Chicken Feed", "Goat Feed", "Sheep Feed", "Pig Feed"],
                "Pet Toys": ["Dog Toys", "Cat Toys", "Bird Toys", "Small Pet Toys"],
                "Pet Healthcare": ["Dog Medications", "Cat Medications", "Bird Medications", "Small Pet Medications"],
                "Pet Grooming": ["Dog Shampoos", "Cat Shampoos", "Pet Brushes", "Pet Clippers"],
                "Pet Beds": ["Dog Beds", "Cat Beds", "Small Pet Beds"],
                "Pet Bowls": ["Dog Bowls", "Cat Bowls", "Bird Bowls", "Small Pet Bowls"],
                "Hardware": ["Tools", "Fasteners", "Plumbing", "Electrical", "HVAC"],
                "Lawn & Garden": ["Seeds", "Fertilizer", "Tools", "Plants"],
                "Farm Supplies": ["Fencing", "Feeders", "Equipment", "Animal Health"],
                "Home & Kitchen": ["Cleaning", "Storage", "Appliances", "Decor"],
                "Automotive": ["Parts", "Tools", "Maintenance", "Accessories"]
            }
            default_pages = [
                "##FaceBook Store",
                "##FaceBook Store",
                "##orderstatus mod",
                "#BLOG",
                "#Bay State Pet & Garden Supply",
                "#Contact-Thank-You-BSPGS",
                "#Military Discount",
                "#Photos",
                "#Services",
                "#Upcoming-Events-BSPGS",
                "#Video-BSPGS",
                "About: Bay State Pet & Garden Supply",
                "Apparel",
                "Baby Chicks",
                "Barn Supplies Buckets & Feeders",
                "Barn Supplies Farm Gates & Fencing",
                "Barn Supplies Shop All",
                "Barn Supplies Tools & Equipment",
                "Bay State Country Gift Shop",
                "Beekeeping",
                "Black Friday Specials",
                "Boots",
                "Brand - Blue Buffalo",
                "Brand - Blue Seal",
                "Brand - Fromm",
                "Brand - Instinct",
                "Brand - Jonathan Green",
                "Brand - Orijen",
                "Brand - Pro Plan",
                "Brand - Purina",
                "Brand - Science Diet",
                "Brand - Stella & Chewys",
                "Brand - Taste Of The Wild",
                "Brands",
                "Cage Bird Cages & Accessories",
                "Caged Bird Canary & Finch",
                "Caged Bird Cockatiel",
                "Caged Bird Food",
                "Caged Bird Food & Supplies Shop All",
                "Caged Bird Healthcare",
                "Caged Bird Litter & Nesting",
                "Caged Bird Parakeet",
                "Caged Bird Parrot",
                "Caged Bird Pigeon",
                "Caged Bird Toys",
                "Caged Bird Treats",
                "Career Opportunities",
                "Cat Beds & Carriers",
                "Cat Bowls & Feeders",
                "Cat Flea & Tick",
                "Cat Food Dry",
                "Cat Food Raw",
                "Cat Food Shop All",
                "Cat Food Wet",
                "Cat Grooming",
                "Cat Healthcare",
                "Cat Leashes Collars & Harnesses",
                "Cat Litter & Litter Boxes",
                "Cat Supplies Shop All",
                "Cat Toys & Scratchers",
                "Cat Treats",
                "Chick Chat",
                "Chicken Breeds",
                "Contact Us",
                "Curbside Pick-up",
                "Delivery Services",
                "Dog Beds",
                "Dog Bowls & Feeders",
                "Dog Cleanup",
                "Dog Clothing & Accessories",
                "Dog Crates & Carriers",
                "Dog Dental Treats",
                "Dog Flea & Tick",
                "Dog Food Dry",
                "Dog Food Raw",
                "Dog Food Shop All",
                "Dog Food Wet",
                "Dog Grooming",
                "Dog Healthcare",
                "Dog Leashes Collars & Harnesses",
                "Dog Supplies Shop All",
                "Dog Toys",
                "Dog Treats Biscuits Cookies & Crunchy Treats",
                "Dog Treats Bones Bully Sticks & Natural Chews",
                "Dog Treats Shop All",
                "Dog Treats Soft & Chewy",
                "Employment Opportunities",
                "Example - Brand - Acana",
                "Example - Brand - American Journey",
                "Example - Brand - Frisco",
                "Example - Brand - Hills",
                "Example - Brand - Kong",
                "Example - Brand - NexGard",
                "Example - Brand - Nutro",
                "Example - Brand - Purina",
                "Example - Brand - Royal Canin",
                "Example - Brand - The Disney Collection",
                "Example - Brands",
                "Example Content #1",
                "Example Content #2 Example Content #2 Example Content #2 Example Content #2",
                "Farm Animal Chicken & Poultry",
                "Farm Animal Cow",
                "Farm Animal Llama & Alpaca",
                "Farm Animal Pig",
                "Farm Animal Sheep & Goat",
                "Farm Animal Shop All",
                "Featured Brand - Purina",
                "Featured Products",
                "Fencing & Gates",
                "Fish Food Betta",
                "Fish Food Goldfish",
                "Fish Food Koi & Pond Fish",
                "Fish Food Shop All",
                "Fish Food Tropical",
                "Fish Pond Supplies",
                "Fish Supplies Shop All",
                "Fish Tanks & Accessories",
                "Fish Water Treatments & Test Kits",
                "Flowers & Plants",
                "Food Candy & Refreshments",
                "Gardening Tools & Supplies",
                "Gloves",
                "Grills & Accessories",
                "Hardware",
                "Hay",
                "Hay Testing",
                "Heating",
                "Home Shop All",
                "Horse Dewormers",
                "Horse Feed",
                "Horse Feed & Treats Shop All",
                "Horse First Aid",
                "Horse Fly Control",
                "Horse Grooming",
                "Horse Health & Wellness Shop All",
                "Horse Treats",
                "Horse Vitamins & Supplements",
                "Jerky Dog Treats",
                "Kyle - Test",
                "Landscape Professionals",
                "Landscape Services",
                "Lawn & Garden Shop All",
                "Lawn Care",
                "Lawn Care Q&A 2025",
                "Lawn Equipment Rental",
                "Mulch & Loam",
                "Open House",
                "Pest Control",
                "Pest Control & Animal Repellents",
                "Plants",
                "Privacy/Security",
                "Propane Filling Station",
                "Redbarn Canned Dog Food",
                "Reptile Bearded Dragon",
                "Reptile Bedding & Substrate",
                "Reptile Food & Supplies Shop All",
                "Reptile Food & Treats",
                "Reptile Frog",
                "Reptile Heating & Lighting",
                "Reptile Lizard",
                "Reptile Snake",
                "Reptile Tanks & Accessories",
                "Reptile Turtle",
                "Return Merchandise Request Form",
                "Return Request Received",
                "Returns",
                "Search results",
                "Seasonal Products",
                "Seeds & Seed Starting",
                "Shavings & Bedding",
                "Shipping",
                "Shop By Brand",
                "Small Pet Bedding & Litter",
                "Small Pet Food",
                "Small Pet Food & Supplies Shop All",
                "Small Pet Grooming & Health",
                "Small Pet Guinea Pig",
                "Small Pet Habitats & Accessories",
                "Small Pet Hamster",
                "Small Pet Hay",
                "Small Pet Mouse & Rat",
                "Small Pet Rabbit",
                "Small Pet Toys & Chews",
                "Small Pet Treats",
                "Snow Plowing",
                "Soap Lotion & Sanitizer",
                "Soy Candles & Melts",
                "Special Offers",
                "Terms & Conditions",
                "Thank you!",
                "Thank you!",
                "The Christmas Shop",
                "Wild Bird Baths",
                "Wild Bird Feeders",
                "Wild Bird Food Shop All",
                "Wild Bird Hangers Poles & Baffles",
                "Wild Bird Houses",
                "Wild Bird Seed & Seed Mixes",
                "Wild Bird Suet & Mealworm",
                "Wild Bird Supplies Shop All",
                "Wildlife Deer Food",
                "Wildlife Squirrel Food",
                "Winter Supplies",
                "Wood Pellets"
            ]
            _facet_cache.update({
                'category_product_types': default_categories,
                'product_on_pages_options': default_pages,
                'cache_timestamp': current_time
            })
            return default_categories, default_pages

        # Get category to product types mapping
        cursor = conn.execute("""
            SELECT Category, Product_Type
            FROM products
            WHERE Category IS NOT NULL AND Product_Type IS NOT NULL
        """)

        category_types = {}
        for row in cursor.fetchall():
            category_str, product_type_str = row
            if category_str and product_type_str:
                categories = [c.strip().title() for c in str(category_str).split('|') if c.strip()]
                product_types = [pt.strip().title() for pt in str(product_type_str).split('|') if pt.strip()]

                for category in categories:
                    if category not in category_types:
                        category_types[category] = set()
                    category_types[category].update(product_types)

        # Convert sets to sorted lists
        CATEGORY_PRODUCT_TYPES = {cat: sorted(list(set(types)), key=str.lower)
                                for cat, types in category_types.items()}

        # Get product on pages options - use static file instead of parsing from database
        PRODUCT_ON_PAGES_OPTIONS = sorted(list(SHOPSITE_PAGES), key=str.lower)

        # Update cache
        _facet_cache.update({
            'category_product_types': CATEGORY_PRODUCT_TYPES,
            'product_on_pages_options': PRODUCT_ON_PAGES_OPTIONS,
            'cache_timestamp': current_time
        })

        return CATEGORY_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS

    except Exception as e:
        print(f"DEBUG: Database query failed in get_facet_options_from_db: {e}")
        # Database query failed, return comprehensive fallback defaults
        default_categories = {
            "Dog Food": ["Dry Dog Food", "Wet Dog Food", "Raw Dog Food", "Dog Treats"],
            "Cat Food": ["Dry Cat Food", "Wet Cat Food", "Raw Cat Food", "Cat Treats"],
            "Bird Supplies": ["Bird Food", "Bird Cages", "Bird Toys", "Bird Healthcare"],
            "Small Pet Food": ["Rabbit Food", "Guinea Pig Food", "Hamster Food", "Rat Food"],
            "Farm Animal Supplies": ["Chicken Feed", "Goat Feed", "Sheep Feed", "Pig Feed"],
            "Pet Toys": ["Dog Toys", "Cat Toys", "Bird Toys", "Small Pet Toys"],
            "Pet Healthcare": ["Dog Medications", "Cat Medications", "Bird Medications", "Small Pet Medications"],
            "Pet Grooming": ["Dog Shampoos", "Cat Shampoos", "Pet Brushes", "Pet Clippers"],
            "Pet Beds": ["Dog Beds", "Cat Beds", "Small Pet Beds"],
            "Pet Bowls": ["Dog Bowls", "Cat Bowls", "Bird Bowls", "Small Pet Bowls"],
            "Hardware": ["Tools", "Fasteners", "Plumbing", "Electrical", "HVAC"],
            "Lawn & Garden": ["Seeds", "Fertilizer", "Tools", "Plants"],
            "Farm Supplies": ["Fencing", "Feeders", "Equipment", "Animal Health"],
            "Home & Kitchen": ["Cleaning", "Storage", "Appliances", "Decor"],
            "Automotive": ["Parts", "Tools", "Maintenance", "Accessories"]
        }
        default_pages = sorted(list(SHOPSITE_PAGES), key=str.lower)
        _facet_cache.update({
            'category_product_types': default_categories,
            'product_on_pages_options': default_pages,
            'cache_timestamp': current_time
        })
        return default_categories, default_pages

    finally:
        conn.close()


def assign_classification_batch(products_list):
    """
    Assign classification (Category, Product Type, Product On Pages) to multiple products using the interactive batch UI.
    Always uses the UI, even for a single product.
    Args:
        products_list: List of product_info dictionaries
    Returns:
        List of product_info dictionaries with classifications assigned
    """
    print(f"🏷️ Classification Assignment (UI): Processing {len(products_list)} products...")
    # Always use the interactive batch UI
    results = edit_classification_in_batch(products_list)
    print(f"\033[92m✅ Classification assignment (UI) complete! Processed {len(results)} products\033[0m\n")
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

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search section
        search_layout = QHBoxLayout()
        search_label = QLabel(f"Search {self.label}:")
        search_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        search_label.setStyleSheet("color: #ffffff;")
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setFont(QFont("Arial", 12))
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
        search_layout.addWidget(self.search_edit)

        search_layout.addStretch()
        layout.addLayout(search_layout)

        # Available options section
        available_label = QLabel(f"Available {self.label}:")
        available_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        available_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(available_label)

        self.available_scroll = QScrollArea()
        self.available_scroll.setWidgetResizable(True)
        self.available_scroll.setMinimumHeight(200)
        self.available_scroll.setMaximumHeight(300)
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
        self.selected_scroll.setMinimumHeight(200)
        self.selected_scroll.setMaximumHeight(300)
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
                checkbox.setChecked(False)
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


class ClassificationEditorWindow(QMainWindow):
    """PyQt6 main window for batch classification editing."""

    finished = pyqtSignal()  # Signal emitted when window closes

    def __init__(self, products_list, category_options, all_product_types, product_on_pages_options, category_product_types):
        super().__init__()
        self.products_list = products_list
        self.category_options = category_options
        self.all_product_types = all_product_types
        self.product_on_pages_options = product_on_pages_options
        self.category_product_types = category_product_types
        self.current_index = 0
        self.multi_select_widgets = {}

        # Apply dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
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
                padding: 6px;
                font-size: 12px;
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

        # Network manager for image downloading
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_image_download_finished)

        self.setup_ui()
        self.load_product_into_ui(0)

    def on_image_download_finished(self, reply):
        """Handle the completion of image download."""
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                # Download successful
                image_data = reply.readAll()
                
                # Create pixmap from downloaded data
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    # Scale image to fit the display area while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        self.image_display.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    self.image_display.setPixmap(scaled_pixmap)
                    self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.image_display.setStyleSheet("")  # Clear any text styling
                else:
                    self.image_display.setText("Failed to decode image")
                    self.image_display.setStyleSheet("""
                        QLabel {
                            background-color: #f8d7da;
                            border: 1px solid #f5c6cb;
                            border-radius: 5px;
                            color: #721c24;
                            font-size: 12px;
                            text-align: center;
                        }
                    """)
            else:
                # Download failed
                error_msg = reply.errorString()
                print(f"Image download failed: {error_msg}")
                self.image_display.setText("Failed to load image")
                self.image_display.setStyleSheet("""
                    QLabel {
                        background-color: #f8d7da;
                        border: 1px solid #f5c6cb;
                        border-radius: 5px;
                        color: #721c24;
                        font-size: 12px;
                        text-align: center;
                    }
                """)
        except Exception as e:
            print(f"Error processing downloaded image: {e}")
            self.image_display.setText("Error displaying image")
            self.image_display.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 5px;
                    color: #721c24;
                    font-size: 12px;
                    text-align: center;
                }
            """)
        finally:
            reply.deleteLater()

    def setup_ui(self):
        self.setWindowTitle(f"Batch Classification Editor - Professional Edition - {len(self.products_list)} Products")

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter - product info on left, classification on right
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(main_splitter)

        # Left side - Product Information Panel
        self.setup_product_info_panel(main_splitter)

        # Right side - Classification Panel
        self.setup_classification_panel(main_splitter)

        # Set splitter proportions (25% product info, 75% classification)
        main_splitter.setSizes([300, 1000])

        # Navigation bar at bottom
        self.setup_navigation_bar(central_widget.layout())

    def setup_product_info_panel(self, parent_splitter):
        """Setup the product information panel on the left side."""
        # Product Information Card
        info_card = QGroupBox("📦 Product Information")
        info_card.setStyleSheet("""
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
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(15, 15, 15, 15)

        # Product header
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #343a40;
                border: 1px solid #495057;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)

        # Product title
        self.product_name_label = QLabel("")
        self.product_name_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.product_name_label.setStyleSheet("color: #ffffff; margin: 5px;")
        self.product_name_label.setWordWrap(True)
        self.product_name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(self.product_name_label)

        # SKU
        self.product_sku_label = QLabel("")
        self.product_sku_label.setFont(QFont("Arial", 12, QFont.Weight.Normal, True))
        self.product_sku_label.setStyleSheet("color: #cccccc; margin: 5px;")
        self.product_sku_label.setWordWrap(True)
        self.product_sku_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(self.product_sku_label)

        info_layout.addWidget(header_frame)

        # Product details grid
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.Shape.Box)
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        details_layout = QVBoxLayout(details_frame)

        # Create a grid for product details
        details_grid = QWidget()
        grid_layout = QGridLayout(details_grid)

        # Labels for product details
        labels = [
            ("Brand:", "brand"),
            ("Price:", "price"),
            ("Weight:", "weight"),
            ("Images:", "images")
        ]

        self.detail_labels = {}
        for i, (label_text, key) in enumerate(labels):
            # Label
            label = QLabel(label_text)
            label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            label.setStyleSheet("color: #ffffff;")
            grid_layout.addWidget(label, i, 0, Qt.AlignmentFlag.AlignTop)

            # Value
            value_label = QLabel("")
            value_label.setFont(QFont("Arial", 11))
            value_label.setStyleSheet("color: #cccccc;")
            value_label.setWordWrap(True)
            value_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            grid_layout.addWidget(value_label, i, 1)
            self.detail_labels[key] = value_label

        details_layout.addWidget(details_grid)
        info_layout.addWidget(details_frame)

        # Product image display
        image_frame = QFrame()
        image_frame.setFrameStyle(QFrame.Shape.Box)
        image_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        image_layout = QVBoxLayout(image_frame)

        image_label = QLabel("Product Image:")
        image_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        image_label.setStyleSheet("color: #ffffff;")
        image_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        image_layout.addWidget(image_label)

        # Placeholder for image
        self.image_display = QLabel("No image available")
        self.image_display.setFixedSize(280, 280)
        self.image_display.setStyleSheet("""
            QLabel {
                background-color: #343a40;
                border: 2px dashed #6c757d;
                border-radius: 5px;
                color: #adb5bd;
                font-size: 12px;
            }
        """)
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_display)

        info_layout.addWidget(image_frame)

        # Add stretch to push everything to top
        info_layout.addStretch()

        parent_splitter.addWidget(info_card)

    def setup_classification_panel(self, parent_splitter):
        """Setup the classification panel on the right side."""
        # Classification Card
        classification_card = QGroupBox("🏷️ Product Classification")
        classification_card.setStyleSheet("""
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
        classification_layout = QVBoxLayout(classification_card)
        classification_layout.setContentsMargins(15, 15, 15, 15)

        # Classification selection area - horizontal splitter for three columns
        selection_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Category section
        category_frame = QGroupBox("📁 Category")
        category_frame.setStyleSheet("""
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
        category_layout = QVBoxLayout(category_frame)
        category_layout.setContentsMargins(10, 10, 10, 10)

        self.category_multi_select = MultiSelectWidget("Category", self.category_options)
        self.category_multi_select.selection_changed.connect(self.on_category_changed)
        category_layout.addWidget(self.category_multi_select)
        selection_splitter.addWidget(category_frame)

        # Product Type section
        type_frame = QGroupBox("🏷️ Product Type")
        type_frame.setStyleSheet("""
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
        type_layout = QVBoxLayout(type_frame)
        type_layout.setContentsMargins(10, 10, 10, 10)

        self.type_multi_select = MultiSelectWidget("Product Type", self.all_product_types)
        type_layout.addWidget(self.type_multi_select)
        selection_splitter.addWidget(type_frame)

        # Product On Pages section
        pages_frame = QGroupBox("📄 Product On Pages")
        pages_frame.setStyleSheet("""
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
        pages_layout = QVBoxLayout(pages_frame)
        pages_layout.setContentsMargins(10, 10, 10, 10)

        self.pages_multi_select = MultiSelectWidget("Product On Pages", self.product_on_pages_options)
        pages_layout.addWidget(self.pages_multi_select)
        selection_splitter.addWidget(pages_frame)

        # Set equal widths for the three sections
        selection_splitter.setSizes([333, 333, 334])
        classification_layout.addWidget(selection_splitter)

        self.multi_select_widgets = {
            "Category": self.category_multi_select,
            "Product Type": self.type_multi_select,
            "Product On Pages": self.pages_multi_select
        }

        parent_splitter.addWidget(classification_card)

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

        self.product_count_label = QLabel("")
        self.product_count_label.setFont(QFont("Arial", 10))
        self.product_count_label.setStyleSheet("color: #cccccc;")
        progress_layout.addWidget(self.product_count_label)

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

    def normalize_selections(self, selections, available_options):
        """Normalize selections from string or list format, handling comma/pipe separators."""
        if isinstance(selections, str):
            # Split on comma or pipe, strip whitespace, and normalize casing
            selections = [s.strip().title() for s in re.split(r'[|,]', selections) if s.strip()]
        elif not isinstance(selections, list):
            selections = []
        else:
            # If it's already a list, normalize casing
            selections = [s.title() if isinstance(s, str) else str(s) for s in selections]

        # Filter to only available options
        return [s for s in selections if s in available_options]

    def load_product_into_ui(self, idx):
        """Load product data into the classification UI."""
        product = self.products_list[idx]

        # Update product header
        name = product.get('Name', 'Unknown Product')
        sku = product.get('SKU', 'Unknown')
        self.product_name_label.setText(name)
        self.product_sku_label.setText(f"SKU: {sku}")

        # Update product details
        self.detail_labels['brand'].setText(product.get('Brand', 'N/A'))  # Brand
        self.detail_labels['price'].setText(product.get('Price', 'N/A'))
        self.detail_labels['weight'].setText(product.get('Weight', 'N/A'))

        # Handle images
        images_text = product.get('Images') or product.get('Image URLs', '')
        if images_text:
            image_urls = [url.strip() for url in images_text.split(',') if url.strip()]
            self.detail_labels['images'].setText(f"{len(image_urls)} image(s) available")
            # Try to load the first image
            self.load_product_image(image_urls[0] if image_urls else None)
        else:
            self.detail_labels['images'].setText("No images")
            self.load_product_image(None)

        # Update progress
        self.progress_label.setText(f"Product {idx + 1} of {len(self.products_list)}")
        self.product_count_label.setText(f"Classifying: {name[:50]}...")

        # Get current selections from product data
        category_list = self.normalize_selections(product.get('Category', ''), self.category_options)
        product_type_list = self.normalize_selections(product.get('Product Type', ''), self.all_product_types)
        pages_list = self.normalize_selections(product.get('Product On Pages', ''), self.product_on_pages_options)

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
                # Clear previous image
                self.image_display.clear()
                self.image_display.setText("Loading image...")
                self.image_display.setStyleSheet("""
                    QLabel {
                        background-color: #e9ecef;
                        border: 1px solid #adb5bd;
                        border-radius: 5px;
                        color: #495057;
                        font-size: 12px;
                        text-align: center;
                    }
                """)
                
                # Create network request
                request = QNetworkRequest(QUrl(image_url))
                request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, 
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                
                # Start download
                self.network_manager.get(request)
                
            except Exception as e:
                print(f"Error initiating image download: {e}")
                self.image_display.setText("Failed to load image")
                self.image_display.setStyleSheet("""
                    QLabel {
                        background-color: #f8d7da;
                        border: 1px solid #f5c6cb;
                        border-radius: 5px;
                        color: #721c24;
                        font-size: 12px;
                        text-align: center;
                    }
                """)
        else:
            self.image_display.setText("No image available")
            self.image_display.setStyleSheet("""
                QLabel {
                    background-color: #e9ecef;
                    border: 2px dashed #adb5bd;
                    border-radius: 5px;
                    color: #6c757d;
                    font-size: 12px;
                    text-align: center;
                }
            """)

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
        product['Category'] = '|'.join(self.category_multi_select.get_selected())
        product['Product Type'] = '|'.join(self.type_multi_select.get_selected())
        product['Product On Pages'] = '|'.join(self.pages_multi_select.get_selected())

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
        print(f"🤖 Products with auto-classifications only: {len(self.products_list) - (self.current_index + 1)}")
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


def edit_classification_in_batch(products_list):
    """
    Interactive batch editor for product classification fields (Category, Product Type, Product On Pages).
    Similar to cross-sell editor but focused on classification selection.
    Returns updated products_list with selected classifications.
    """
    # Import facet options from database and local pages
    CATEGORY_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS = get_facet_options_from_db()

    # For consolidated products, augment available options with any categories/types/pages found in scraped data
    # that aren't already in the database
    if products_list and any("_consolidated_data" in p for p in products_list):
        print("EDITOR DEBUG: Found consolidated products, augmenting facet options with scraped data...")

        # Collect all unique options from consolidated data
        additional_categories = set()
        additional_product_types = set()
        additional_pages = set()

        for product in products_list:
            if "_consolidated_data" in product:
                consolidated = product["_consolidated_data"]

                # Add categories from consolidated data
                if "category_options" in consolidated:
                    additional_categories.update(cat.title() for cat in consolidated["category_options"] if cat)

                # Add product types from consolidated data
                if "product_type_options" in consolidated:
                    additional_product_types.update(pt.title() for pt in consolidated["product_type_options"] if pt)

                # Add pages from consolidated data
                if "product_on_pages_options" in consolidated:
                    additional_pages.update(page.title() for page in consolidated["product_on_pages_options"] if page)

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
                    print(f"EDITOR DEBUG: Added product type '{ptype}' to category '{generic_cat}'")

        # Add new pages to PRODUCT_ON_PAGES_OPTIONS
        for page in additional_pages:
            if page not in PRODUCT_ON_PAGES_OPTIONS:
                PRODUCT_ON_PAGES_OPTIONS.append(page)
                print(f"EDITOR DEBUG: Added page from scraped data: {page}")

    # Extract categories and all product types
    CATEGORY_OPTIONS = sorted(CATEGORY_PRODUCT_TYPES.keys(), key=str.lower)
    ALL_PRODUCT_TYPES = sorted(set(
        ptype for types in CATEGORY_PRODUCT_TYPES.values() for ptype in types
    ), key=str.lower)

    # Create the application and main window
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    # If QApplication already exists, just reuse it (don't recreate)

    window = ClassificationEditorWindow(products_list, CATEGORY_OPTIONS, ALL_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS, CATEGORY_PRODUCT_TYPES)
    window.showMaximized()

    # Use QEventLoop to wait for window closure (works with existing QApplication)
    from PyQt6.QtCore import QEventLoop
    loop = QEventLoop()
    window.finished.connect(loop.quit)
    loop.exec()

    # Return the updated products list
    return window.get_products_list()


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
            "Price": "$29.99",
            "Weight": "30 LB",
            "Category": "Dog Food|Pet Supplies",
            "Product Type": "Dry Dog Food|Premium Dog Food",
            "Product On Pages": "Dog Food Shop All|Premium Products",
            "Images": "https://www.baystatepet.com/media//open-farm/resized/open-farm-grass-fed-beef-rustic-stew-wet-dog-food_medium.jpg"
        },
        {
            "SKU": "DEMO002",
            "Name": "Cat Toy Bundle",
            "Brand": "DemoBrand",
            "Price": "$15.99",
            "Weight": "2 LB",
            "Category": "Cat Supplies",
            "Product Type": "Cat Toys",
            "Product On Pages": "Cat Supplies Shop All",
            "Images": "https://www.baystatepet.com/media//open-farm/resized/open-farm-grass-fed-beef-rustic-stew-wet-dog-food_medium.jpg"
        },
        {
            "SKU": "DEMO003",
            "Name": "Unclassified Bird Seed",
            "Brand": "DemoBrand",
            "Price": "$12.99",
            "Weight": "5 LB",
            "Category": "",  # Empty - should show no preselection
            "Product Type": "",
            "Product On Pages": "",
            "Images": "https://www.baystatepet.com/media//open-farm/resized/open-farm-grass-fed-beef-rustic-stew-wet-dog-food_medium.jpg"
        }
    ]

    print("Launching classification UI demo with pre-filled data...")
    print("DEMO001 should show 'Dog Food' and 'Pet Supplies' pre-selected in Category")
    print("DEMO001 should show 'Dry Dog Food' and 'Premium Dog Food' pre-selected in Product Type")
    print("DEMO001 should show 'Dog Food Shop All' and 'Premium Products' pre-selected in Pages")
    print("DEMO002 should show 'Cat Supplies' pre-selected in Category")
    print("DEMO003 should show no pre-selections (empty checkboxes)")
    print()

    # Get facet options
    CATEGORY_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS = get_facet_options_from_db()
    CATEGORY_OPTIONS = sorted(CATEGORY_PRODUCT_TYPES.keys(), key=str.lower)
    ALL_PRODUCT_TYPES = sorted(set(
        ptype for types in CATEGORY_PRODUCT_TYPES.values() for ptype in types
    ), key=str.lower)

    # Create and show the demo window
    app = QApplication(sys.argv)
    window = ClassificationEditorWindow(demo_products, CATEGORY_OPTIONS, ALL_PRODUCT_TYPES, PRODUCT_ON_PAGES_OPTIONS, CATEGORY_PRODUCT_TYPES)
    window.showMaximized()

    # Start the event loop (standalone mode)
    app.exec()

    results = window.get_products_list()

    print("\nDemo complete. Results:")
    for prod in results:
        print(f"{prod['SKU']}: Category='{prod.get('Category', '')}', Type='{prod.get('Product Type', '')}', Pages='{prod.get('Product On Pages', '')}'")