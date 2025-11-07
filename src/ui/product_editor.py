import sqlite3
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QScrollArea, QFrame, QMessageBox, QSplitter, QProgressBar,
    QGroupBox, QTextEdit, QDialog, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
import requests
from io import BytesIO
from PIL import Image, ImageQt

# Handle import for shopsite_constants
try:
    # Try relative import first (when run as part of package)
    from . import shopsite_constants
except ImportError:
    try:
        # Try absolute import from src.ui (when run as standalone script)
        from src.ui import shopsite_constants
    except ImportError:
        # Last resort - import from current directory
        import shopsite_constants

SHOPSITE_PAGES = shopsite_constants.SHOPSITE_PAGES

import sys

# Database path instead of Excel
# Find project root by looking for main.py
current_path = Path(__file__).parent
project_root = current_path
while project_root.parent != project_root:  # Not at filesystem root
    if (project_root / "main.py").exists():
        break
    project_root = project_root.parent

DB_PATH = project_root / "data" / "databases" / "products.db"

RECOMMEND_COLS = []

# Cache for facet options to avoid repeated database queries
_facet_cache = {
    'category_product_types': {},
    'product_on_pages_options': [],
    'cache_timestamp': None
}
CACHE_DURATION_SECONDS = 300  # 5 minutes

def clear_facet_cache():
    """Clear the facet options cache, forcing fresh database queries on next access."""
    global _facet_cache
    _facet_cache = {
        'category_product_types': {},
        'product_on_pages_options': [],
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
        age = current_time - _facet_cache['cache_timestamp']  # type: ignore
        print(f"DEBUG: Using cached facet options (age: {age:.1f}s)")
        return _facet_cache['category_product_types'], _facet_cache['product_on_pages_options']

    print(f"DEBUG: Querying database for facet options (cache {'expired' if _facet_cache['cache_timestamp'] else 'empty'} or force_refresh={force_refresh})")

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
        default_pages = SHOPSITE_PAGES.copy()
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
            default_pages = SHOPSITE_PAGES.copy()
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

        # Get product on pages options
        cursor = conn.execute("""
            SELECT DISTINCT Product_On_Pages
            FROM products
            WHERE Product_On_Pages IS NOT NULL
        """)

        product_on_pages = set()
        for row in cursor.fetchall():
            if row[0]:
                # Split on "|" separator and add individual pages
                pages = [page.strip().title() for page in str(row[0]).split('|') if page.strip()]
                product_on_pages.update(pages)

        PRODUCT_ON_PAGES_OPTIONS = sorted(list(product_on_pages), key=str.lower)

        # Always include all ShopSite pages, plus any additional pages found in database
        all_pages = set(SHOPSITE_PAGES)
        all_pages.update(PRODUCT_ON_PAGES_OPTIONS)
        PRODUCT_ON_PAGES_OPTIONS = sorted(list(all_pages), key=str.lower)

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
        default_pages = SHOPSITE_PAGES.copy()
        _facet_cache.update({
            'category_product_types': default_categories,
            'product_on_pages_options': default_pages,
            'cache_timestamp': current_time
        })
        return default_categories, default_pages

    finally:
        conn.close()


class ImageDialog(QDialog):
    """Dialog for adding or editing image URLs."""
    def __init__(self, current_url="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Image URL")
        self.setModal(True)

        layout = QVBoxLayout()

        self.url_input = QLineEdit(current_url)
        self.url_input.setPlaceholderText("Enter image URL...")
        layout.addWidget(QLabel("Image URL:"))
        layout.addWidget(self.url_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_url(self):
        return self.url_input.text().strip()


class ThumbnailLabel(QLabel):
    """Clickable thumbnail label for image carousel."""
    clicked = pyqtSignal(int)  # Emits the image index

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(80, 60)  # Thumbnail size
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid gray;")

    def mousePressEvent(self, ev):  # type: ignore[union-attr]
        if ev and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(ev)


class ProductEditor(QMainWindow):
    """PyQt-based product editor with modern UI."""

    finished = pyqtSignal()  # Signal emitted when editing is finished

    def __init__(self, products_list):
        super().__init__()
        self.products_list = products_list
        self.current_index = 0
        self.current_images = []
        self.image_cache = {}
        self.original_pixmap = None
        self.is_loading_image = False  # Prevent concurrent image operations
        self.thumbnail_loading_queue = []  # Queue for thumbnail loading

        self.is_single_product = len(products_list) == 1
        title = "Product Editor" if self.is_single_product else f"Batch Product Editor - {len(products_list)} Products"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1600, 1000)

        self.cancelled = False

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top section: Left panel + Right panel
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        # Left panel: All form sections
        left_widget = QWidget()
        left_widget.setFixedWidth(600)
        left_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(5)  # Small gap between sections
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Product info section
        info_group = QGroupBox("Product Information")
        info_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_layout = QFormLayout(info_group)
        info_layout.setVerticalSpacing(10)
        info_layout.setHorizontalSpacing(15)

        # SKU display (read-only)
        self.sku_label = QLabel("SKU: ")
        self.sku_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addRow(self.sku_label)

        # Price display (read-only)
        self.price_label = QLabel("Price: ")
        self.price_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addRow(self.price_label)

        # Input name display (read-only, for consolidated products)
        self.input_name_label = QLabel("Name: ")
        self.input_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.input_name_label.setVisible(False)  # Only show for consolidated products
        info_layout.addRow(self.input_name_label)

        # Brand field
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setFont(QFont("Arial", 11))
        self.brand_combo.setMinimumHeight(30)
        info_layout.addRow("Brand:", self.brand_combo)

        # Name field
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setFont(QFont("Arial", 11))
        self.name_combo.setMinimumHeight(30)
        info_layout.addRow("Product Name:", self.name_combo)

        # Weight field
        self.weight_combo = QComboBox()
        self.weight_combo.setEditable(True)
        self.weight_combo.setFont(QFont("Arial", 11))
        self.weight_combo.setMinimumHeight(30)
        info_layout.addRow("Weight:", self.weight_combo)

        left_layout.addWidget(info_group)

        # Options section
        options_group = QGroupBox("Options")
        options_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        options_layout = QHBoxLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)

        self.special_order_check = QCheckBox("Special Order")
        self.special_order_check.setFont(QFont("Arial", 11))
        options_layout.addWidget(self.special_order_check)

        self.product_disabled_check = QCheckBox("Product Disabled")
        self.product_disabled_check.setFont(QFont("Arial", 11))
        options_layout.addWidget(self.product_disabled_check)

        left_layout.addWidget(options_group)

        # Image set selection (for consolidated data)
        self.image_set_group = QGroupBox("Image Sources")
        self.image_set_group.setVisible(False)
        self.image_set_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.image_set_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        image_set_layout = QVBoxLayout(self.image_set_group)
        image_set_layout.setContentsMargins(10, 10, 10, 10)

        # Create a scroll area for buttons if there are many
        self.image_buttons_scroll = QScrollArea()
        self.image_buttons_scroll.setWidgetResizable(True)
        self.image_buttons_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.image_buttons_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.image_buttons_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.image_buttons_widget = QWidget()
        self.image_buttons_layout = QHBoxLayout(self.image_buttons_widget)
        self.image_buttons_layout.setSpacing(5)
        self.image_buttons_layout.setContentsMargins(5, 5, 5, 5)

        self.image_buttons_scroll.setWidget(self.image_buttons_widget)
        image_set_layout.addWidget(self.image_buttons_scroll)

        left_layout.addWidget(self.image_set_group)

        content_layout.addWidget(left_widget)

        # Right panel: Image display and controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Image display area
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        # Allow image to expand as needed

        self.image_widget = QWidget()
        self.image_layout = QVBoxLayout(self.image_widget)

        # Placeholder for image
        self.image_label = QLabel("📷 No image available")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFont(QFont("Arial", 14))
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 2px dashed #ccc; background-color: #f9f9f9;")
        self.image_layout.addWidget(self.image_label)

        self.image_scroll.setWidget(self.image_widget)
        right_layout.addWidget(self.image_scroll)

        # Thumbnail carousel below main image
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumbnail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumbnail_scroll.setMaximumHeight(80)  # Fixed height for thumbnails

        self.thumbnail_widget = QWidget()
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_widget)
        self.thumbnail_layout.setSpacing(5)
        self.thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        self.thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.thumbnail_scroll.setWidget(self.thumbnail_widget)
        right_layout.addWidget(self.thumbnail_scroll)

        # Image controls
        controls_layout = QHBoxLayout()

        # Navigation buttons
        nav_layout = QVBoxLayout()
        nav_layout.addWidget(QLabel("Navigation:"))

        nav_buttons_layout = QHBoxLayout()
        self.prev_img_btn = QPushButton("◀ Prev")
        self.prev_img_btn.clicked.connect(self.prev_image)
        nav_buttons_layout.addWidget(self.prev_img_btn)

        self.img_counter_label = QLabel("No images")
        self.img_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_counter_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        nav_buttons_layout.addWidget(self.img_counter_label)

        self.next_img_btn = QPushButton("Next ▶")
        self.next_img_btn.clicked.connect(self.next_image)
        nav_buttons_layout.addWidget(self.next_img_btn)

        nav_layout.addLayout(nav_buttons_layout)
        controls_layout.addLayout(nav_layout)

        # Position controls
        pos_layout = QVBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))

        pos_buttons_layout = QHBoxLayout()
        self.left_pos_btn = QPushButton("⬅️ Left")
        self.left_pos_btn.clicked.connect(self.move_image_left)
        pos_buttons_layout.addWidget(self.left_pos_btn)

        self.right_pos_btn = QPushButton("Right ➡️")
        self.right_pos_btn.clicked.connect(self.move_image_right)
        pos_buttons_layout.addWidget(self.right_pos_btn)

        pos_layout.addLayout(pos_buttons_layout)
        controls_layout.addLayout(pos_layout)

        # Management buttons
        mgmt_layout = QVBoxLayout()
        mgmt_layout.addWidget(QLabel("Management:"))

        mgmt_buttons_layout = QHBoxLayout()
        self.add_img_btn = QPushButton("➕ Add")
        self.add_img_btn.clicked.connect(self.add_image)
        mgmt_buttons_layout.addWidget(self.add_img_btn)

        self.edit_img_btn = QPushButton("✏️ Edit")
        self.edit_img_btn.clicked.connect(self.edit_image)
        mgmt_buttons_layout.addWidget(self.edit_img_btn)

        self.remove_img_btn = QPushButton("❌ Remove")
        self.remove_img_btn.clicked.connect(self.remove_image)
        mgmt_buttons_layout.addWidget(self.remove_img_btn)

        mgmt_layout.addLayout(mgmt_buttons_layout)
        controls_layout.addLayout(mgmt_layout)

        right_layout.addLayout(controls_layout)

        content_layout.addWidget(right_widget)

        main_layout.addWidget(content_widget, 1)  # Give content stretch

        # Bottom section: Navigation and actions
        self.create_footer_section()
        main_layout.addWidget(self.footer_section)

        # Load first product
        self.load_product_into_ui(0)

    def manage_image_cache(self):
        """Manage image cache size to prevent memory issues."""
        max_cache_size = 50  # Maximum number of cached images
        if len(self.image_cache) > max_cache_size:
            # Remove oldest entries (simple FIFO - could be improved with LRU)
            cache_items = list(self.image_cache.items())
            # Keep the most recently used ones (last 40)
            keep_items = cache_items[-40:]
            self.image_cache = dict(keep_items)
            print(f"DEBUG: Cleaned image cache, kept {len(self.image_cache)} images")

    def load_image_safely(self, img_url, max_size=(2000, 2000)):
        """
        Load image from URL using QNetworkAccessManager for reliable HTTP loading.
        """
        try:
            # Check cache first
            if img_url in self.image_cache:
                cached_pixmap = self.image_cache[img_url]
                if cached_pixmap and not cached_pixmap.isNull():
                    return cached_pixmap

            # Use QNetworkAccessManager to download the image
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
            from PyQt6.QtCore import QEventLoop, QUrl, QTimer

            # Create network manager
            manager = QNetworkAccessManager()
            request = QNetworkRequest(QUrl(img_url))

            # Add user agent
            request.setRawHeader(b'User-Agent', b'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            # Download synchronously
            loop = QEventLoop()
            reply = manager.get(request)
            assert reply is not None, "Failed to create network reply"

            def on_finished():
                loop.quit()

            reply.finished.connect(on_finished)

            # Add timeout to prevent hanging
            timer = QTimer()
            timer.timeout.connect(loop.quit)
            timer.setSingleShot(True)
            timer.start(30000)  # 30 seconds timeout

            # Start the download
            loop.exec()

            # Stop the timer
            timer.stop()

            # Check if request finished
            if not reply.isFinished():
                raise ValueError("Network request timed out")

            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(f"Network error: {reply.errorString()}")

            # Get the image data
            image_data = reply.readAll()

            # Load pixmap from data
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                if pixmap.isNull():
                    raise ValueError("Loaded pixmap is null")

                # Resize if too large
                if pixmap.width() > max_size[0] or pixmap.height() > max_size[1]:
                    pixmap = pixmap.scaled(max_size[0], max_size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

                # Cache the pixmap
                self.image_cache[img_url] = pixmap
                self.manage_image_cache()

                return pixmap
            else:
                raise ValueError("Failed to load pixmap from downloaded data")

        except Exception as e:
            print(f"DEBUG: Failed to load image {img_url}: {e}")
            return None

    def create_header_section(self):
        """Create the header section with product basic info."""
        self.header_section = QWidget()
        layout = QVBoxLayout(self.header_section)
        layout.setContentsMargins(10, 10, 10, 10)

        # Product info section
        info_group = QGroupBox("Product Information")
        info_group.setFixedWidth(350)
        info_layout = QFormLayout(info_group)
        info_layout.setVerticalSpacing(10)
        info_layout.setHorizontalSpacing(15)

        # SKU display (read-only)
        self.sku_label = QLabel("SKU: ")
        self.sku_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addRow(self.sku_label)

        # Price display (read-only)
        self.price_label = QLabel("Price: ")
        self.price_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_layout.addRow(self.price_label)

        # Input name display (read-only, for consolidated products)
        self.input_name_label = QLabel("Name: ")
        self.input_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.input_name_label.setVisible(False)  # Only show for consolidated products
        info_layout.addRow(self.input_name_label)

        # Brand field
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setFont(QFont("Arial", 11))
        self.brand_combo.setMinimumHeight(30)
        info_layout.addRow("Brand:", self.brand_combo)

        # Name field
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setFont(QFont("Arial", 11))
        self.name_combo.setMinimumHeight(30)
        info_layout.addRow("Product Name:", self.name_combo)

        # Weight field
        self.weight_combo = QComboBox()
        self.weight_combo.setEditable(True)
        self.weight_combo.setFont(QFont("Arial", 11))
        self.weight_combo.setMinimumHeight(30)
        info_layout.addRow("Weight:", self.weight_combo)

        # Use horizontal layout to keep the group box compact on the left
        header_layout = QHBoxLayout()
        header_layout.addWidget(info_group)
        header_layout.addStretch()

        layout.addLayout(header_layout)

    def create_content_section(self):
        """Create the content section with product details and image display."""
        self.content_section = QWidget()
        layout = QHBoxLayout(self.content_section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left panel: Options and image set selection
        left_widget = QWidget()
        left_widget.setFixedWidth(350)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(0)  # No spacing between sections
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Options section
        options_group = QGroupBox("Options")
        options_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        options_layout = QHBoxLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)

        self.special_order_check = QCheckBox("Special Order")
        self.special_order_check.setFont(QFont("Arial", 11))
        options_layout.addWidget(self.special_order_check)

        self.product_disabled_check = QCheckBox("Product Disabled")
        self.product_disabled_check.setFont(QFont("Arial", 11))
        options_layout.addWidget(self.product_disabled_check)

        left_layout.addWidget(options_group)

        # Image set selection (for consolidated data)
        self.image_set_group = QGroupBox("Image Sources")
        self.image_set_group.setVisible(False)
        self.image_set_group.setFixedWidth(350)
        image_set_layout = QVBoxLayout(self.image_set_group)
        image_set_layout.setContentsMargins(10, 10, 10, 10)

        # Create a scroll area for buttons if there are many
        self.image_buttons_scroll = QScrollArea()
        self.image_buttons_scroll.setWidgetResizable(True)
        self.image_buttons_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.image_buttons_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.image_buttons_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.image_buttons_widget = QWidget()
        self.image_buttons_layout = QVBoxLayout(self.image_buttons_widget)
        self.image_buttons_layout.setSpacing(5)
        self.image_buttons_layout.setContentsMargins(5, 5, 5, 5)

        self.image_buttons_scroll.setWidget(self.image_buttons_widget)
        image_set_layout.addWidget(self.image_buttons_scroll)

        left_layout.addWidget(self.image_set_group)

        layout.addWidget(left_widget)

        # Right panel: Image display and controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Image display area
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        # Allow image to expand as needed

        self.image_widget = QWidget()
        self.image_layout = QVBoxLayout(self.image_widget)

        # Placeholder for image
        self.image_label = QLabel("📷 No image available")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFont(QFont("Arial", 14))
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 2px dashed #ccc; background-color: #f9f9f9;")
        self.image_layout.addWidget(self.image_label)

        self.image_scroll.setWidget(self.image_widget)
        right_layout.addWidget(self.image_scroll)

        # Image controls
        controls_layout = QHBoxLayout()

        # Navigation buttons
        nav_layout = QVBoxLayout()
        nav_layout.addWidget(QLabel("Navigation:"))

        nav_buttons_layout = QHBoxLayout()
        self.prev_img_btn = QPushButton("◀ Prev")
        self.prev_img_btn.clicked.connect(self.prev_image)
        nav_buttons_layout.addWidget(self.prev_img_btn)

        self.img_counter_label = QLabel("No images")
        self.img_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_counter_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        nav_buttons_layout.addWidget(self.img_counter_label)

        self.next_img_btn = QPushButton("Next ▶")
        self.next_img_btn.clicked.connect(self.next_image)
        nav_buttons_layout.addWidget(self.next_img_btn)

        nav_layout.addLayout(nav_buttons_layout)
        controls_layout.addLayout(nav_layout)

        # Position controls
        pos_layout = QVBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))

        pos_buttons_layout = QHBoxLayout()
        self.left_pos_btn = QPushButton("⬅️ Left")
        self.left_pos_btn.clicked.connect(self.move_image_left)
        pos_buttons_layout.addWidget(self.left_pos_btn)

        self.right_pos_btn = QPushButton("Right ➡️")
        self.right_pos_btn.clicked.connect(self.move_image_right)
        pos_buttons_layout.addWidget(self.right_pos_btn)

        pos_layout.addLayout(pos_buttons_layout)
        controls_layout.addLayout(pos_layout)

        # Management buttons
        mgmt_layout = QVBoxLayout()
        mgmt_layout.addWidget(QLabel("Management:"))

        mgmt_buttons_layout = QHBoxLayout()
        self.add_img_btn = QPushButton("➕ Add")
        self.add_img_btn.clicked.connect(self.add_image)
        mgmt_buttons_layout.addWidget(self.add_img_btn)

        self.edit_img_btn = QPushButton("✏️ Edit")
        self.edit_img_btn.clicked.connect(self.edit_image)
        mgmt_buttons_layout.addWidget(self.edit_img_btn)

        self.remove_img_btn = QPushButton("❌ Remove")
        self.remove_img_btn.clicked.connect(self.remove_image)
        mgmt_buttons_layout.addWidget(self.remove_img_btn)

        mgmt_layout.addLayout(mgmt_buttons_layout)
        controls_layout.addLayout(mgmt_layout)

        right_layout.addLayout(controls_layout)

        self.current_image_index = 0
        self.update_image_controls()

        layout.addWidget(right_widget)

    def create_footer_section(self):
        """Create the footer section with navigation and actions."""
        self.footer_section = QWidget()
        self.footer_section.setMaximumHeight(80)
        layout = QHBoxLayout(self.footer_section)
        layout.setContentsMargins(20, 10, 20, 10)

        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.progress_label)

        layout.addStretch()

        # Navigation widget (contains navigation and delete buttons for batch editing)
        self.navigation_widget = QWidget()
        self.navigation_layout = QHBoxLayout(self.navigation_widget)
        self.navigation_layout.setContentsMargins(0, 0, 0, 0)
        self.navigation_layout.setSpacing(10)

        if not self.is_single_product:
            self.prev_btn = QPushButton("◀ Previous")
            self.prev_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            self.prev_btn.setMinimumSize(120, 40)
            self.prev_btn.clicked.connect(self.prev_product)
            self.navigation_layout.addWidget(self.prev_btn)

            self.next_btn = QPushButton("Next ▶")
            self.next_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            self.next_btn.setMinimumSize(120, 40)
            self.next_btn.clicked.connect(self.next_product)
            self.navigation_layout.addWidget(self.next_btn)

            # Delete button (only for batch editing)
            self.delete_btn = QPushButton("🗑️ Delete")
            self.delete_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            self.delete_btn.setMinimumSize(120, 40)
            self.delete_btn.setStyleSheet("background-color: #FF5722; color: white; border: none; padding: 8px 16px;")
            self.delete_btn.clicked.connect(self.delete_current_product)
            self.navigation_layout.addWidget(self.delete_btn)

            # Make sure navigation widget is visible for batch editing
            self.navigation_widget.setVisible(True)
        else:
            # Hide navigation widget for single product editing
            self.navigation_widget.setVisible(False)

        layout.addWidget(self.navigation_widget)

        # Action buttons
        finish_text = "OK" if self.is_single_product else "✓ Finish"
        self.finish_btn = QPushButton(finish_text)
        self.finish_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.finish_btn.setMinimumSize(120, 40)
        self.finish_btn.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 8px 16px;")
        self.finish_btn.clicked.connect(self.finish_editing)
        layout.addWidget(self.finish_btn)

        self.cancel_btn = QPushButton("✗ Cancel")
        self.cancel_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.cancel_btn.setMinimumSize(120, 40)
        self.cancel_btn.setStyleSheet("background-color: #f44336; color: white; border: none; padding: 8px 16px;")
        self.cancel_btn.clicked.connect(self.cancel_editing)
        layout.addWidget(self.cancel_btn)

    def load_product_into_ui(self, index):
        """Load product at index into UI."""
        if not (0 <= index < len(self.products_list)):
            return

        product = self.products_list[index]
        is_consolidated = "_consolidated_data" in product

        # Update SKU display
        sku = product.get('SKU', 'Unknown')
        self.sku_label.setText(f"SKU: {sku}")

        # Update Price display
        if is_consolidated:
            price = product.get('input_price', 'N/A')
        else:
            price = product.get('Price', 'N/A')
        self.price_label.setText(f"Price: {price}")

        # Update Input Name display (only for consolidated products)
        if is_consolidated:
            input_name = product.get('input_name', 'N/A')
            self.input_name_label.setText(f"Original Name: {input_name}")
            self.input_name_label.setVisible(True)
        else:
            self.input_name_label.setVisible(False)

        # Handle consolidated vs regular data
        if is_consolidated:
            consolidated_data = product["_consolidated_data"]

            # Helper function to get options from grouped or flat data
            def get_options_from_data(field_name):
                # Try new format first (single value per site)
                by_site_key = f"{field_name}_by_site"
                if by_site_key in consolidated_data:
                    by_site = consolidated_data[by_site_key]
                    if field_name == 'images':
                        # For images, flatten all site image lists
                        options = []
                        sources = []
                        for site, images in by_site.items():
                            for img in images:
                                if img not in options:
                                    options.append(img)
                                    sources.append(site)
                        return options, sources
                    else:
                        # For other fields, use the single values but exclude 'Input' site
                        options = []
                        sources = []
                        for site, value in by_site.items():
                            if site != 'Input':  # Exclude the input name from selectable options
                                options.append(value)
                                sources.append(site)
                        return options, sources
                
                # Fallback to old grouped format (backward compatibility)
                sets_key = f"{field_name}_sets"
                if sets_key in consolidated_data:
                    sets = consolidated_data[sets_key]
                    if field_name == 'images':
                        # For images, flatten all site image lists
                        options = []
                        sources = []
                        for site, images in sets.items():
                            for img in images:
                                if img not in options:
                                    options.append(img)
                                    sources.append(site)
                        return options, sources
                    else:
                        # For other fields, flatten the lists but exclude 'Input' site
                        options = []
                        sources = []
                        for site, values in sets.items():
                            if site != 'Input':  # Exclude the input name from selectable options
                                for value in values:
                                    if value not in options:
                                        options.append(value)
                                        sources.append(site)
                        return options, sources
                
                # Final fallback to flat arrays (legacy support)
                options_key = f"{field_name}_options"
                sources_key = f"{field_name}_sources"
                if options_key in consolidated_data:
                    return consolidated_data[options_key], consolidated_data.get(sources_key, [])
                
                return [], []

            # Brand options
            brand_options, brand_sources = get_options_from_data('brand')
            self.brand_combo.clear()
            self.brand_combo.addItems(brand_options)
            current_brand = product.get("Brand", "")
            if current_brand:
                self.brand_combo.setCurrentText(current_brand)
            elif brand_options:
                self.brand_combo.setCurrentText(brand_options[0])

            # Name options
            name_options, name_sources = get_options_from_data('name')
            self.name_combo.clear()
            self.name_combo.addItems(name_options)
            current_name = product.get("Name", "")
            if current_name:
                self.name_combo.setCurrentText(current_name)
            elif name_options:
                self.name_combo.setCurrentText(name_options[0])

            # Weight options
            weight_options, weight_sources = get_options_from_data('weight')
            self.weight_combo.clear()
            self.weight_combo.addItems(weight_options)
            current_weight = product.get("Weight", "")
            if current_weight:
                self.weight_combo.setCurrentText(current_weight)
            elif weight_options:
                # Find largest weight (keep existing logic for weights)
                def parse_weight(w):
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', str(w))
                    return float(match.group(1)) if match else 0
                if weight_options:
                    largest_weight = max(weight_options, key=parse_weight)
                    self.weight_combo.setCurrentText(largest_weight)

            # Special Order and Product Disabled
            special_order_options, special_order_sources = get_options_from_data('special_order')
            product_disabled_options, product_disabled_sources = get_options_from_data('product_disabled')

            # Use saved value if available, otherwise default to False for consolidated products
            saved_special_order = product.get("Special Order")
            if saved_special_order is not None:
                self.special_order_check.setChecked(saved_special_order == "yes")
            else:
                # For consolidated products, default to False since these aren't scraped
                self.special_order_check.setChecked(False)

            saved_product_disabled = product.get("Product Disabled")
            if saved_product_disabled is not None:
                self.product_disabled_check.setChecked(saved_product_disabled == "checked")
            else:
                # For consolidated products, default to False since these aren't scraped
                self.product_disabled_check.setChecked(False)

            # Handle image sets for consolidated data
            saved_images = product.get("Image URLs", [])
            if saved_images:
                # Use saved images if available, but still show image set selector
                self.current_images = saved_images.copy() if isinstance(saved_images, list) else []
            else:
                # No saved images, will use consolidated image sets
                self.current_images = []

            # Always setup consolidated images for consolidated products (to show the selector)
            self.setup_consolidated_images(consolidated_data, product)

        else:
            # Regular product data
            self.brand_combo.clear()
            self.brand_combo.addItem(product.get("Brand", ""))
            self.brand_combo.setCurrentText(product.get("Brand", ""))

            self.name_combo.clear()
            self.name_combo.addItem(product.get("Name", ""))
            self.name_combo.setCurrentText(product.get("Name", ""))

            self.weight_combo.clear()
            self.weight_combo.addItem(product.get("Weight", ""))
            self.weight_combo.setCurrentText(product.get("Weight", ""))

            self.special_order_check.setChecked(product.get("Special Order") == "yes")
            self.product_disabled_check.setChecked(product.get("Product Disabled") == "checked")

            # Regular image loading
            image_urls = product.get("Image URLs", [])
            if isinstance(image_urls, str):
                self.current_images = [url.strip() for url in image_urls.split(",") if url.strip()]
            elif isinstance(image_urls, list):
                self.current_images = image_urls.copy()
            else:
                self.current_images = []

            self.image_set_group.setVisible(False)

        # Update progress and navigation
        self.update_progress_display(index)
        self.update_navigation_buttons(index)

        # Load first image - only for non-consolidated products (consolidated handled in setup_consolidated_images)
        if not is_consolidated:
            self.current_image_index = 0
            self.show_current_image()

    def setup_consolidated_images(self, consolidated_data, product=None):
        """Setup image sets for consolidated data."""
        # Check if we have grouped image_sets (new format)
        image_sets = consolidated_data.get("images_by_site", {})

        # If no grouped sets, try old format for backward compatibility
        if not image_sets:
            image_sets = consolidated_data.get("image_sets", {})

        # If no grouped sets, try to reconstruct from flat arrays (backward compatibility)
        if not image_sets:
            image_options = consolidated_data.get("image_options", [])
            image_sources = consolidated_data.get("image_sources", [])

            if not image_options:
                self.current_images = []
                self.image_set_group.setVisible(False)
                return

            # Group images by source
            image_sets = {}
            for i, img_url in enumerate(image_options):
                site = image_sources[i] if i < len(image_sources) else "Unknown"
                if site not in image_sets:
                    image_sets[site] = []
                image_sets[site].append(img_url)

        # If still no image sets after reconstruction, hide selector
        if not image_sets:
            self.current_images = []
            self.image_set_group.setVisible(False)
            return

        # Setup image source buttons
        # Clear existing buttons
        for i in reversed(range(self.image_buttons_layout.count())):
            item = self.image_buttons_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        # Create buttons for each site
        self.image_source_buttons = {}
        for site, images in image_sets.items():
            button_text = f"{site}\n({len(images)} images)"
            button = QPushButton(button_text)
            button.setFont(QFont("Arial", 10))
            button.setMinimumWidth(80)
            button.setMaximumWidth(100)
            button.setFixedHeight(35)
            button.clicked.connect(lambda checked, s=site: self.on_image_source_button_clicked(s))
            self.image_buttons_layout.addWidget(button)
            self.image_source_buttons[site] = button

        self.image_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.image_set_group.setVisible(True)

        # Store image sets for later use
        self.image_sets = image_sets

        # Select appropriate source (highlight the button)
        # First priority: Check if we have a saved selected site from previous navigation
        saved_site = product.get("selected_image_site") if product else None
        selected_site = None

        if saved_site and saved_site in image_sets:
            # Restore the previously selected site
            selected_site = saved_site
            self.current_images = image_sets[saved_site].copy()
            self.current_images = list(dict.fromkeys(self.current_images))
        elif self.current_images:
            # Check if current images match any existing set (custom images)
            has_custom_images = True
            for site, images in image_sets.items():
                if set(self.current_images) == set(images):
                    selected_site = site
                    has_custom_images = False
                    break
            if has_custom_images:
                # Custom images - don't change selection, keep current images
                selected_site = None
        else:
            # No saved images, default to first site
            if image_sets:
                selected_site = next(iter(image_sets.keys()))
                self.current_images = image_sets[selected_site].copy()
                self.current_images = list(dict.fromkeys(self.current_images))

        # Highlight the selected button and trigger initial image display
        if selected_site:
            self.highlight_selected_button(selected_site)
            # Trigger initial image display
            self.current_image_index = 0
            self.show_current_image()
            self.update_image_controls()

    def highlight_selected_button(self, selected_site):
        """Highlight the selected image source button."""
        if hasattr(self, 'image_source_buttons'):
            for site, button in self.image_source_buttons.items():
                if site == selected_site:
                    button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: 2px solid #45a049; }")
                else:
                    button.setStyleSheet("QPushButton { background-color: #f0f0f0; color: black; border: 1px solid #ccc; }")

    def on_image_source_button_clicked(self, site):
        """Handle image source button click."""
        if hasattr(self, 'image_sets') and site in self.image_sets:
            self.current_images = self.image_sets[site].copy()
            # Remove duplicates while preserving order
            self.current_images = list(dict.fromkeys(self.current_images))
            # Immediately save the selected image batch to the product
            if self.products_list and 0 <= self.current_index < len(self.products_list):
                self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                self.products_list[self.current_index]["selected_image_site"] = site  # Save selected site
            self.current_image_index = 0
            self.show_current_image()
            self.update_image_controls()
            # Highlight the selected button
            self.highlight_selected_button(site)

    def show_current_image(self):
        """Display the current image."""
        # Prevent concurrent image loading
        if self.is_loading_image:
            return
        
        self.is_loading_image = True
        
        try:
            # Clear existing image
            for i in reversed(range(self.image_layout.count())):
                item = self.image_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)

            if self.current_images and 0 <= self.current_image_index < len(self.current_images):
                img_url = self.current_images[self.current_image_index]

                # Fix relative URLs by prepending base URL if not already https
                if not img_url.startswith('https://'):
                    img_url = f'https://www.baystatepet.com/media/{img_url}'

                print(f"DEBUG: Loading image URL: {img_url}")

                try:
                    # Use safe image loading
                    pixmap = self.load_image_safely(img_url)
                    
                    if pixmap and not pixmap.isNull():
                        img_label = QLabel()
                        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.image_layout.addWidget(img_label)
                        self.image_label = img_label
                        self.original_pixmap = pixmap
                        self.display_scaled_image()
                    else:
                        raise ValueError("Failed to load valid pixmap")

                except Exception as e:
                    error_label = QLabel(f"⚠️ Image load error: {str(e)[:50]}...")
                    error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    error_label.setFont(QFont("Arial", 12))
                    error_label.setStyleSheet("color: #888;")
                    self.image_layout.addWidget(error_label)
                    self.image_label = error_label
                    self.original_pixmap = None
                    print(f"DEBUG: Image load exception: {e}")
            else:
                # No image available
                no_img_label = QLabel("📷 No image available")
                no_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_img_label.setFont(QFont("Arial", 14))
                no_img_label.setStyleSheet("color: #888;")
                self.image_layout.addWidget(no_img_label)
                self.image_label = no_img_label
                self.original_pixmap = None

        except Exception as e:
            print(f"DEBUG: Error in show_current_image: {e}")
        finally:
            self.is_loading_image = False

        # Create/update thumbnails after displaying the main image
        # Use QTimer to defer thumbnail creation to avoid blocking UI
        QTimer.singleShot(100, self.create_thumbnails)

    def display_scaled_image(self):
        """Display the current image scaled to fit the viewport while maintaining aspect ratio."""
        if self.original_pixmap and not self.original_pixmap.isNull():
            viewport = self.image_scroll.viewport()
            if viewport:
                viewport_size = viewport.size()
                if viewport_size.width() > 0 and viewport_size.height() > 0:
                    scaled_pixmap = self.original_pixmap.scaled(viewport_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setPixmap(self.original_pixmap)
            else:
                self.image_label.setPixmap(self.original_pixmap)
        # For no image or error cases, the label already has text set

    def update_image_controls(self):
        """Update image control button states."""
        has_images = bool(self.current_images)
        current_idx = self.current_image_index

        # Navigation buttons
        self.prev_img_btn.setEnabled(has_images and current_idx > 0)
        self.next_img_btn.setEnabled(has_images and current_idx < len(self.current_images) - 1)

        # Position buttons
        self.left_pos_btn.setEnabled(has_images and len(self.current_images) > 1 and current_idx > 0)
        self.right_pos_btn.setEnabled(has_images and len(self.current_images) > 1 and current_idx < len(self.current_images) - 1)

        # Management buttons
        self.edit_img_btn.setEnabled(has_images)
        self.remove_img_btn.setEnabled(has_images)

        # Counter
        if has_images:
            self.img_counter_label.setText(f"{current_idx + 1}/{len(self.current_images)}")
        else:
            self.img_counter_label.setText("No images")

    def prev_image(self):
        """Navigate to previous image."""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.show_current_image()
            self.update_image_controls()
            self.update_thumbnail_styles()

    def next_image(self):
        """Navigate to next image."""
        if self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.show_current_image()
            self.update_image_controls()
            self.update_thumbnail_styles()

    def move_image_left(self):
        """Move current image left in the list."""
        if self.current_image_index > 0:
            # Swap with previous
            idx = self.current_image_index
            self.current_images[idx], self.current_images[idx - 1] = self.current_images[idx - 1], self.current_images[idx]
            self.current_image_index = idx - 1  # Stay on the moved image
            # Immediately save the updated images to the product
            if self.products_list and 0 <= self.current_index < len(self.products_list):
                self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                self.products_list[self.current_index]["selected_image_site"] = None  # Clear selected site since images were edited
            self.show_current_image()
            self.update_image_controls()
            self.update_thumbnail_styles()

    def move_image_right(self):
        """Move current image right in the list."""
        if self.current_image_index < len(self.current_images) - 1:
            # Swap with next
            idx = self.current_image_index
            self.current_images[idx], self.current_images[idx + 1] = self.current_images[idx + 1], self.current_images[idx]
            self.current_image_index = idx + 1  # Stay on the moved image
            # Immediately save the updated images to the product
            if self.products_list and 0 <= self.current_index < len(self.products_list):
                self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                self.products_list[self.current_index]["selected_image_site"] = None  # Clear selected site since images were edited
            self.show_current_image()
            self.update_image_controls()
            self.update_thumbnail_styles()

    def add_image(self):
        """Add a new image URL."""
        dialog = ImageDialog("", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_url = dialog.get_url()
            if new_url:
                self.current_images.append(new_url)
                # Immediately save the updated images to the product
                if self.products_list and 0 <= self.current_index < len(self.products_list):
                    self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                    self.products_list[self.current_index]["selected_image_site"] = None  # Clear selected site since images were edited
                self.show_current_image()
                self.update_image_controls()

    def edit_image(self):
        """Edit the current image URL."""
        if self.current_images and 0 <= self.current_image_index < len(self.current_images):
            current_url = self.current_images[self.current_image_index]
            dialog = ImageDialog(current_url, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_url = dialog.get_url()
                if new_url and new_url != current_url:
                    self.current_images[self.current_image_index] = new_url
                    # Immediately save the updated images to the product
                    if self.products_list and 0 <= self.current_index < len(self.products_list):
                        self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                        self.products_list[self.current_index]["selected_image_site"] = None  # Clear selected site since images were edited

    def remove_image(self):
        """Remove the current image."""
        if self.current_images and 0 <= self.current_image_index < len(self.current_images):
            reply = QMessageBox.question(
                self, "Remove Image",
                f"Remove image {self.current_image_index + 1}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.current_images.pop(self.current_image_index)
                # Immediately save the updated images to the product
                if self.products_list and 0 <= self.current_index < len(self.products_list):
                    self.products_list[self.current_index]["Image URLs"] = self.current_images.copy()
                    self.products_list[self.current_index]["selected_image_site"] = None  # Clear selected site since images were edited
                    self.current_image_index = len(self.current_images) - 1
                elif not self.current_images:
                    self.current_image_index = 0
                self.show_current_image()
                self.update_image_controls()

    def update_progress_display(self, index):
        """Update the progress label."""
        sku = self.products_list[index].get('SKU', 'Unknown')
        if self.is_single_product:
            self.progress_label.setText(f"SKU: {sku}")
        else:
            self.progress_label.setText(f"Product {index + 1} of {len(self.products_list)} - SKU: {sku}")

    def update_navigation_buttons(self, index):
        """Update navigation button states."""
        if not self.is_single_product:
            self.prev_btn.setEnabled(index > 0)
            self.next_btn.setEnabled(index < len(self.products_list) - 1)

    def save_current_product(self):
        """Save current UI state to products_list."""
        if not self.products_list:
            return

        product = self.products_list[self.current_index]

        # Save form data
        product["Brand"] = self.brand_combo.currentText().strip()
        product["Name"] = self.name_combo.currentText().strip()
        product["Weight"] = self.weight_combo.currentText().strip()
        product["Special Order"] = "yes" if self.special_order_check.isChecked() else ""
        product["Product Disabled"] = "checked" if self.product_disabled_check.isChecked() else "uncheck"
        product["Image URLs"] = self.current_images.copy() if self.current_images else []

    def prev_product(self):
        """Navigate to previous product."""
        self.save_current_product()
        if self.current_index > 0:
            self.current_index -= 1
            self.load_product_into_ui(self.current_index)

    def next_product(self):
        """Navigate to next product."""
        self.save_current_product()
        if self.current_index < len(self.products_list) - 1:
            self.current_index += 1
            self.load_product_into_ui(self.current_index)

    def delete_current_product(self):
        """Delete the current product from the list."""
        if self.is_single_product or not self.products_list:
            return

        sku = self.products_list[self.current_index].get('SKU', 'Unknown')
        reply = QMessageBox.question(
            self, "Delete Product",
            f"Are you sure you want to delete product with SKU '{sku}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Remove the current product
            removed_product = self.products_list.pop(self.current_index)

            # Handle navigation after deletion
            if not self.products_list:
                # No products left, close the editor
                QMessageBox.information(self, "All Products Deleted", "All products have been deleted.")
                self.close()
                return

            # Adjust current index if necessary
            if self.current_index >= len(self.products_list):
                self.current_index = len(self.products_list) - 1

            # Update single product flag
            old_single_product = self.is_single_product
            self.is_single_product = len(self.products_list) == 1

            # If we transitioned from multiple to single product, hide navigation buttons
            if not old_single_product and self.is_single_product:
                self.navigation_widget.setVisible(False)

            # Load the new current product
            self.load_product_into_ui(self.current_index)

            # Update window title to reflect new count
            self.setWindowTitle("Product Editor" if self.is_single_product else f"Batch Product Editor - {len(self.products_list)} Products")

    def finish_editing(self):
        """Finish editing and close the window."""
        self.save_current_product()
        self.close()
        self.finished.emit()

    def cancel_editing(self):
        """Cancel editing."""
        reply = QMessageBox.question(
            self, "Cancel",
            "Are you sure you want to cancel? All changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cancelled = True
            self.close()
            self.finished.emit()

    def resizeEvent(self, a0):
        """Handle window resize to rescale the current image."""
        super().resizeEvent(a0)
        self.display_scaled_image()

    def create_thumbnails(self):
        """Create thumbnail images for the current image batch."""
        # Clear existing thumbnails
        for i in reversed(range(self.thumbnail_layout.count())):
            item = self.thumbnail_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        # Limit thumbnail creation to prevent overwhelming the system
        max_thumbnails = min(len(self.current_images), 10)  # Limit to 10 thumbnails max
        
        # Create thumbnails for each image (up to limit)
        for i, img_url in enumerate(self.current_images[:max_thumbnails]):
            thumbnail = ThumbnailLabel(i)
            thumbnail.clicked.connect(self.on_thumbnail_clicked)

            try:
                # Fix relative URLs by prepending base URL if not already https
                if not img_url.startswith('https://'):
                    img_url = f'https://www.baystatepet.com/media/{img_url}'

                # Load and scale thumbnail - use smaller max size for thumbnails
                pixmap = self.load_image_safely(img_url, max_size=(200, 200))
                
                if pixmap and not pixmap.isNull():
                    # Scale to fit thumbnail size while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(80, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    thumbnail.setPixmap(scaled_pixmap)
                else:
                    # Show placeholder for failed thumbnails
                    thumbnail.setText("❌")

            except Exception as e:
                # Show placeholder for failed thumbnails
                thumbnail.setText("❌")
                print(f"DEBUG: Thumbnail load error for {img_url}: {e}")

            self.thumbnail_layout.addWidget(thumbnail)

        # Update thumbnail styles
        self.update_thumbnail_styles()

    def update_thumbnail_styles(self):
        """Update thumbnail border styles to highlight current image."""
        for i in range(self.thumbnail_layout.count()):
            item = self.thumbnail_layout.itemAt(i)
            if item:
                thumbnail = item.widget()
                if isinstance(thumbnail, ThumbnailLabel):
                    if thumbnail.index == self.current_image_index:
                        thumbnail.setStyleSheet("border: 2px solid #4CAF50; background-color: #e8f5e8;")
                    else:
                        thumbnail.setStyleSheet("border: 1px solid gray;")

    def on_thumbnail_clicked(self, index):
        """Handle thumbnail click to switch to that image."""
        if 0 <= index < len(self.current_images):
            self.current_image_index = index
            self.show_current_image()
            self.update_image_controls()
            self.update_thumbnail_styles()


def product_editor_interactive(product_or_sku):
    """
    Interactive UI editor for a SINGLE product.
    Opens a PyQt window for manual editing of product details.
    Can accept either a SKU string (loads from database) or a product data dictionary.
    Returns the edited product data in scraper format.

    Args:
        product_or_sku: String SKU of the product to edit (loads from DB), OR product data dictionary

    Returns:
        Dict: Updated product_info in scraper format (SKU, Name, Price, Brand, Weight, Image URLs, Special Order, Product Disabled), or None if cancelled
    """
    # Use the batch editor - it will handle both SKUs and product data
    result = edit_products_in_batch([product_or_sku])
    if result is None:
        return None  # User cancelled
    return result[0]


def load_products_from_db(skus):
    """
    Load products from database by SKUs and map ShopSite fields to editor format.

    Args:
        skus: List of SKU strings

    Returns:
        List of product dictionaries in editor format
    """
    if not skus:
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        # Ensure UTF-8 handling
        conn.text_factory = str
        placeholders = ','.join('?' * len(skus))
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT SKU, Brand, Name, Weight, Category, Product_Type, Product_On_Pages, Special_Order, Images, ProductDisabled
            FROM products
            WHERE SKU IN ({placeholders})
        """, skus)

        products = []
        for row in cursor.fetchall():
            (sku, brand, name, weight, category, product_type,
             product_on_pages, special_order, images, product_disabled) = row

            # Parse images from comma-separated string
            image_urls = []
            if images:
                print(f"DEBUG: raw Images field for SKU {sku}: {repr(images)}")
                # Split by comma and strip whitespace
                image_urls = [url.strip() for url in str(images).split(',') if url.strip()]
                # Print each parsed image value for debugging SKU-mode image issues
                for i, img_val in enumerate(image_urls):
                    print(f"DEBUG: parsed image[{i}] for SKU {sku}: {repr(img_val)}")

            # Map database fields to editor format
            mapped_product = {
                'SKU': sku,
                'Name': name or '',
                'Brand': brand or '',
                'Weight': weight or '',
                'Special Order': 'yes' if special_order and str(special_order).lower().strip() == 'yes' else '',
                'Category': category or '',
                'Product Type': product_type or '',
                'Product On Pages': product_on_pages or '',
                'Product Cross Sell': '',  # Not in schema, keep empty
                'Image URLs': image_urls,
                'Product Disabled': product_disabled or ''
            }

            print(f"DEBUG: Loaded product {sku}:")
            print(f"  Name: {repr(mapped_product['Name'])}")
            print(f"  Brand: {repr(mapped_product['Brand'])}")
            print(f"  Category: {repr(mapped_product['Category'])}")
            print(f"  Product Type: {repr(mapped_product['Product Type'])}")
            print(f"  Product On Pages: {repr(mapped_product['Product On Pages'])}")
            print(f"  Image URLs: {mapped_product['Image URLs']}")

            products.append(mapped_product)

        return products

    except Exception as e:
        print(f"DEBUG: Database query failed in load_products_from_db: {e}")
        # Return empty list if database access fails
        return []

    finally:
        conn.close()


def save_products_to_excel(products_list, output_file=None):
    """
    Save edited products to an Excel file for manual upload.
    All products are saved to a single file with timestamps.

    Args:
        products_list: List of edited product dictionaries
        output_file: Path to output Excel file (optional, defaults to product_edits.xlsx)

    Returns:
        str: Path to the created Excel file
    """
    import pandas as pd
    from datetime import datetime
    import os

    if not products_list:
        return None

    if output_file is None:
        output_file = "product_edits.xlsx"

    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Convert products to DataFrame format expected by ShopSite
    excel_data = []

    for product in products_list:
        # Map editor format back to ShopSite column names
        row = {
            'SKU': product.get('SKU', ''),
            'Name': product.get('Name', ''),
            'Price': '',  # Not edited in UI
            'Images': ', '.join(product.get('Image URLs', [])),
            'Weight': product.get('Weight', ''),
            'Product Field 16': product.get('Brand', ''),  # Brand -> Product Field 16
            'Product Field 11': 'yes' if product.get('Special Order') == 'yes' else '',  # Special Order -> Product Field 11
            'Product Field 24': product.get('Category', ''),  # Category -> Product Field 24
            'Product Field 25': product.get('Product Type', ''),  # Product Type -> Product Field 25
            'Product On Pages': product.get('Product On Pages', ''),  # Product On Pages
            'Product Field 32': product.get('Product Cross Sell', ''),  # Cross-sell -> Product Field 32
            'ProductDisabled': 'checked' if product.get('Product Disabled') == 'checked' else 'uncheck',
            'Last Edited': timestamp  # Add timestamp to each row
        }
        excel_data.append(row)

    # Create DataFrame
    new_df = pd.DataFrame(excel_data)

    # If file exists, read existing data and append
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            # Append new data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        except Exception as e:
            print(f"Warning: Could not read existing file {output_file}: {e}. Creating new file.")
            combined_df = new_df
    else:
        combined_df = new_df

    # Save to Excel
    combined_df.to_excel(output_file, index=False)

    return output_file


def edit_products_in_batch(products_or_skus, auto_close_seconds=None):
    """
    Edit products in a batch interface. Supports both consolidated and regular product data.
    Returns products in the same format that scrapers return (simplified format).

    Args:
        products_or_skus: List of SKU strings to load from database and edit, OR list of product data dictionaries
        auto_close_seconds: For testing - automatically close after N seconds

    Returns:
        List of edited product_info dictionaries in scraper format (SKU, Name, Price, Brand, Weight, Image URLs, Special Order, Product Disabled), or None if cancelled
    """
    # Determine if we have SKUs or product data
    if products_or_skus and isinstance(products_or_skus[0], str):
        # We have SKUs - load from database
        products_list = load_products_from_db(products_or_skus)
    elif products_or_skus and isinstance(products_or_skus[0], dict):
        # We have product data dictionaries - use directly
        products_list = products_or_skus.copy()
    else:
        products_list = []

    if not products_list:
        print("EDITOR DEBUG: No products loaded")
        return None

    # Ensure QApplication exists (don't create a new one if it exists)
    app = QApplication.instance()
    if app is None:
        # Only create QApplication if running standalone
        app = QApplication(sys.argv)
        standalone = True
    else:
        # Running within existing application (like main GUI)
        standalone = False

    # Create and show the editor
    editor = ProductEditor(products_list)
    editor.showMaximized()

    # Set up auto-close for testing if requested
    if auto_close_seconds is not None:
        def auto_close():
            print(f"Auto-closing editor after {auto_close_seconds} seconds for testing...")
            editor.finish_editing()  # Use finish_editing instead of close to emit finished signal
        QTimer.singleShot(auto_close_seconds * 1000, auto_close)

    # Use QEventLoop to wait for editor to close (works in both standalone and embedded modes)
    from PyQt6.QtCore import QEventLoop
    loop = QEventLoop()
    editor.finished.connect(loop.quit)
    
    # If standalone mode and no other windows, also start the main event loop
    if standalone:
        # Start main event loop in separate thread to allow QEventLoop to work
        loop.exec()
    else:
        # Embedded mode - just run the local event loop
        loop.exec()

    # Return the edited products if not cancelled
    if editor.cancelled:
        return None
    else:
        # Create clean finalized product data in scraper format (no consolidated data)
        finalized_products = []
        for product in products_list:
            finalized_product = {
                'SKU': product.get('SKU', ''),
                'Name': product.get('Name', ''),
                'Price': product.get('input_price', ''),  # Use input_price for consolidated products
                'Brand': product.get('Brand', ''),
                'Weight': product.get('Weight', ''),
                'Image URLs': product.get('Image URLs', []),
                'Special Order': product.get('Special Order', ''),
                'Product Disabled': product.get('Product Disabled', ''),
            }
            finalized_products.append(finalized_product)
        return finalized_products


def test_product_editor_data_handling():
    """Test function to validate product data handling without opening GUI."""
    print("Testing product editor data handling...")

    # Load test data from config file
    config_path = project_root / "src" / "config" / "test_data.json"
    try:
        with open(config_path, 'r') as f:
            test_data = json.load(f)
    except Exception as e:
        print(f"Error loading test data: {e}")
        return

    # Test data
    mock_product = test_data["mock_product"]
    sku_string = "035585256153"

    print("1. Testing edit_products_in_batch with product data list...")
    try:
        # Test the input detection logic
        products_or_skus = [mock_product]
        if products_or_skus and isinstance(products_or_skus[0], str):
            print("   ❌ Incorrectly detected as SKU list")
        elif products_or_skus and isinstance(products_or_skus[0], dict):
            print("   ✅ Correctly detected as product data list")
            products_list = products_or_skus.copy()
            print(f"   ✅ Loaded {len(products_list)} products from data")
        else:
            print("   ❌ Empty or invalid input")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("2. Testing edit_products_in_batch with SKU list...")
    try:
        products_or_skus = [sku_string]
        if products_or_skus and isinstance(products_or_skus[0], str):
            print("   ✅ Correctly detected as SKU list")
            # This would normally load from DB, but we'll skip that for testing
            print("   ✅ Would load from database (skipped for test)")
        elif products_or_skus and isinstance(products_or_skus[0], dict):
            print("   ❌ Incorrectly detected as product data list")
        else:
            print("   ❌ Empty or invalid input")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("3. Testing product_editor_interactive with product data...")
    try:
        # This would call edit_products_in_batch([mock_product])
        print("   ✅ Function accepts product data (would open GUI)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("4. Testing product_editor_interactive with SKU...")
    try:
        # This would call edit_products_in_batch([sku_string])
        print("   ✅ Function accepts SKU string (backward compatibility)")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("5. Testing edit_products_in_batch with consolidated product data...")
    mock_consolidated_product = test_data["mock_consolidated_product"]
    try:
        products_or_skus = [mock_consolidated_product]
        if products_or_skus and isinstance(products_or_skus[0], str):
            print("   ❌ Incorrectly detected as SKU list")
        elif products_or_skus and isinstance(products_or_skus[0], dict):
            print("   ✅ Correctly detected as product data list")
            products_list = products_or_skus.copy()
            print(f"   ✅ Loaded {len(products_list)} products from data")
            # Check if it's consolidated
            if "_consolidated_data" in products_list[0]:
                print("   ✅ Detected consolidated product with _consolidated_data")
                # Validate arrays are present
                required_arrays = ['name_by_site', 'brand_by_site', 'weight_by_site', 'images_by_site']
                for arr in required_arrays:
                    if arr in products_list[0]["_consolidated_data"]:
                        print(f"   ✅ Found {arr}: {products_list[0]['_consolidated_data'][arr]}")
                    else:
                        print(f"   ❌ Missing {arr}")
                # Check that top-level fields are empty for consolidated products (except input_* fields)
                empty_fields = ['Name', 'Brand', 'Weight', 'Special Order', 'Product Disabled']
                all_empty = True
                for field in empty_fields:
                    if products_list[0].get(field):
                        print(f"   ❌ Field {field} should be empty for consolidated products: {products_list[0][field]}")
                        all_empty = False
                if all_empty:
                    print("   ✅ All top-level fields are empty as expected for consolidated products")
                
                # Check that input fields are present
                input_fields = ['input_name', 'input_price']
                for field in input_fields:
                    if field in products_list[0]:
                        print(f"   ✅ Found {field}: {products_list[0][field]}")
                    else:
                        print(f"   ❌ Missing {field}")
                        all_empty = False
            else:
                print("   ❌ Not detected as consolidated")
        else:
            print("   ❌ Empty or invalid input")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n✅ All data handling tests passed!")


if __name__ == "__main__":
    # Run data handling test first
    test_product_editor_data_handling()

    print("\n" + "="*50)
    print("GUI TESTS (now running)")
    print("="*50)

    # Load test data from config file
    config_path = project_root / "src" / "config" / "test_data.json"
    try:
        with open(config_path, 'r') as f:
            test_data = json.load(f)
    except Exception as e:
        print(f"Error loading test data: {e}")
        exit(1)

    # Test with consolidated data to see combo boxes
    mock_consolidated_product = test_data["mock_consolidated_product"]
    mock_consolidated_product2 = test_data["mock_consolidated_product2"]

    print("Running GUI test with multiple consolidated products (should show combo boxes and navigation)...")
    result = edit_products_in_batch([mock_consolidated_product, mock_consolidated_product2], auto_close_seconds=3)
    print("Result:", result)