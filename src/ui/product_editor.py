import os
import sqlite3
import time
import traceback
# Database setup
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QDialogButtonBox, QFormLayout, QFrame, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DB_PATH = Path(PROJECT_ROOT) / "data" / "databases" / "products.db"


class ImageDialog(QDialog):
    """Simple dialog for editing image URLs."""

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


class ProductEditor(QMainWindow):
    """Clean, modern product editor rebuilt from scratch."""

    finished = pyqtSignal()

    def __init__(self, products_list, parent=None):
        super().__init__(parent)

        # State
        self.products_list = products_list
        self.current_index = 0
        self.current_images = []
        self.image_cache = {}
        self.current_image_index = 0
        self.cancelled = False
        self.is_single_product = len(products_list) == 1

        # Window setup
        title = (
            "Product Editor"
            if self.is_single_product
            else f"Batch Product Editor - {len(products_list)} Products"
        )
        self.setWindowTitle(title)
        self.resize(1200, 800)

        # Apply the global dark theme.
        try:
            from src.ui.styling import STYLESHEET

            self.setStyleSheet(STYLESHEET)
        except (ImportError, ModuleNotFoundError):
            print("CRITICAL: Could not import stylesheet. UI will be unstyled.")
            # Fallback to a very basic theme if the import fails
            self.setStyleSheet(
                "QMainWindow { background-color: #1e1e1e; color: #ffffff; }"
            )

        # Build UI
        self._init_ui()

        # Load first product with delay to ensure window is ready
        QTimer.singleShot(100, lambda: self.load_product_into_ui(0))

    def _init_ui(self):
        """Build the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Content area
        content = QWidget()
        content_layout = QHBoxLayout(content)

        # Left: Form
        left = self._create_form_panel()
        content_layout.addWidget(left)

        # Right: Images
        right = self._create_image_panel()
        content_layout.addWidget(right, 1)

        main_layout.addWidget(content, 1)

        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_form_panel(self):
        """Create form fields panel."""
        panel = QWidget()
        panel.setFixedWidth(400)
        layout = QVBoxLayout(panel)

        # Info group
        info_box = QGroupBox("Product Information")
        info_layout = QFormLayout(info_box)

        self.sku_label = QLabel("SKU: ")
        self.sku_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addRow(self.sku_label)

        self.price_label = QLabel("Price: ")
        info_layout.addRow(self.price_label)

        self.input_name_label = QLabel("Input Name: ")
        self.input_name_label.setVisible(False)
        info_layout.addRow(self.input_name_label)

        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        info_layout.addRow("Brand:", self.brand_combo)

        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        info_layout.addRow("Name:", self.name_combo)

        self.weight_combo = QComboBox()
        self.weight_combo.setEditable(True)
        info_layout.addRow("Weight:", self.weight_combo)

        layout.addWidget(info_box)

        # Options
        opt_box = QGroupBox("Options")
        opt_layout = QHBoxLayout(opt_box)

        self.special_order_check = QCheckBox("Special Order")
        opt_layout.addWidget(self.special_order_check)

        self.product_disabled_check = QCheckBox("Disabled")
        opt_layout.addWidget(self.product_disabled_check)

        layout.addWidget(opt_box)

        # Image sources (consolidated products)
        self.image_set_group = QGroupBox("Image Sources")
        self.image_set_group.setVisible(False)
        img_src_layout = QVBoxLayout(self.image_set_group)
        self.image_buttons_widget = QWidget()
        self.image_buttons_layout = QVBoxLayout(self.image_buttons_widget)
        img_src_layout.addWidget(self.image_buttons_widget)
        layout.addWidget(self.image_set_group)

        layout.addStretch()
        return panel

    def _create_image_panel(self):
        """Create image display panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Main image
        self.image_label = QLabel("No image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(300, 300)
        layout.addWidget(self.image_label, 1)

        # Counter
        self.img_counter_label = QLabel("No images")
        self.img_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Navigation controls container (fixed width)
        nav_container = QWidget()
        nav_container.setFixedWidth(250)  # Fixed width for compact layout
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(5)  # Reduce spacing between elements

        self.prev_img_btn = QPushButton("< Prev")
        self.prev_img_btn.clicked.connect(self.prev_image)
        nav_layout.addWidget(self.prev_img_btn)

        # Counter in the middle
        nav_layout.addWidget(self.img_counter_label, 1)  # Give counter stretch factor

        self.next_img_btn = QPushButton("Next >")
        self.next_img_btn.clicked.connect(self.next_image)
        nav_layout.addWidget(self.next_img_btn)

        layout.addWidget(nav_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Position controls
        pos_layout = QHBoxLayout()
        self.left_pos_btn = QPushButton("Move Left")
        self.left_pos_btn.clicked.connect(self.move_image_left)
        pos_layout.addWidget(self.left_pos_btn)

        self.right_pos_btn = QPushButton("Move Right")
        self.right_pos_btn.clicked.connect(self.move_image_right)
        pos_layout.addWidget(self.right_pos_btn)

        layout.addLayout(pos_layout)

        # Management
        ctrl2 = QHBoxLayout()
        self.add_img_btn = QPushButton("Add")
        self.add_img_btn.clicked.connect(self.add_image)
        ctrl2.addWidget(self.add_img_btn)

        self.edit_img_btn = QPushButton("Edit URL")
        self.edit_img_btn.clicked.connect(self.edit_image)
        ctrl2.addWidget(self.edit_img_btn)

        self.remove_img_btn = QPushButton("Remove")
        self.remove_img_btn.clicked.connect(self.remove_image)
        ctrl2.addWidget(self.remove_img_btn)

        layout.addLayout(ctrl2)

        return panel

    def _create_footer(self):
        """Create footer with navigation."""
        footer = QWidget()
        layout = QHBoxLayout(footer)

        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        layout.addStretch()

        if not self.is_single_product:
            self.prev_btn = QPushButton("< Previous")
            self.prev_btn.clicked.connect(self.prev_product)
            layout.addWidget(self.prev_btn)

            self.next_btn = QPushButton("Next >")
            self.next_btn.clicked.connect(self.next_product)
            layout.addWidget(self.next_btn)

            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.delete_btn.clicked.connect(self.delete_current_product)
            layout.addWidget(self.delete_btn)

        finish_text = "OK" if self.is_single_product else "Finish"
        self.finish_btn = QPushButton(finish_text)
        self.finish_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.finish_btn.clicked.connect(self.finish_editing)
        layout.addWidget(self.finish_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: #999; color: white;")
        self.cancel_btn.clicked.connect(self.cancel_editing)
        layout.addWidget(self.cancel_btn)

        return footer

    def load_product_into_ui(self, index):
        """Load product data into the UI."""
        if not (0 <= index < len(self.products_list)):
            return

        product = self.products_list[index]
        is_consolidated = "_consolidated_data" in product

        # Basic info
        sku = product.get("SKU", "Unknown")
        self.sku_label.setText(f"SKU: {sku}")

        if is_consolidated:
            prices = product["_consolidated_data"].get("price_options", [])
            price = prices[0] if prices else "N/A"
        else:
            price = product.get("Price", "N/A")
        self.price_label.setText(f"Price: {price}")

        if is_consolidated:
            input_names = product["_consolidated_data"].get("name_options", [])
            self.input_name_label.setText(
                f"Input Name: {input_names[0] if input_names else 'N/A'}"
            )
            self.input_name_label.setVisible(True)
        else:
            self.input_name_label.setVisible(False)

        # Combo boxes
        if is_consolidated:
            cons = product["_consolidated_data"]

            # Brand
            self.brand_combo.clear()
            brand_options = cons.get("brand_options", [])
            self.brand_combo.addItems(brand_options)
            current_brand = product.get("Brand", "")
            # Default to first option if no current value
            if not current_brand and brand_options:
                current_brand = brand_options[0]
            self.brand_combo.setCurrentText(current_brand)
            # Name
            self.name_combo.clear()
            name_options = cons.get("name_options", [])
            self.name_combo.addItems(name_options)
            current_name = product.get("Name", "")
            # Default to first option if no current value
            if not current_name and name_options:
                current_name = name_options[0]
            self.name_combo.setCurrentText(current_name)
            # Weight
            self.weight_combo.clear()
            weight_options = cons.get("weight_options", [])
            self.weight_combo.addItems(weight_options)
            current_weight = product.get("Weight", "")
            # Default to first option if no current value
            if not current_weight and weight_options:
                current_weight = weight_options[0]
            self.weight_combo.setCurrentText(current_weight)

            # Load images - prioritize saved images over consolidated data
            saved_urls = product.get("Image URLs", [])
            if isinstance(saved_urls, str):
                saved_urls = [u.strip() for u in saved_urls.split(",") if u.strip()]

            if saved_urls:
                # Use saved images
                self.current_images = saved_urls
                self.current_image_index = 0
                self.image_set_group.setVisible(False)
                self.show_current_image()
            else:
                # Setup image sources from consolidated data
                self._setup_image_sources(cons, product)
        else:
            self.brand_combo.clear()
            self.brand_combo.setCurrentText(product.get("Brand", ""))

            self.name_combo.clear()
            self.name_combo.setCurrentText(product.get("Name", ""))

            self.weight_combo.clear()
            self.weight_combo.setCurrentText(product.get("Weight", ""))

            self.image_set_group.setVisible(False)

            # Load images
            urls = product.get("Image URLs", [])
            if isinstance(urls, str):
                urls = [u.strip() for u in urls.split(",") if u.strip()]
            self.current_images = urls
            self.current_image_index = 0
            self.show_current_image()

        # Checkboxes
        self.special_order_check.setChecked(product.get("Special Order") == "yes")
        self.product_disabled_check.setChecked(
            product.get("Product Disabled") == "checked"
        )

        # Update UI
        self.update_progress_display(index)
        if not self.is_single_product:
            self.prev_btn.setEnabled(index > 0)
            self.next_btn.setEnabled(index < len(self.products_list) - 1)

    def _setup_image_sources(self, consolidated_data, product):
        """Setup image source buttons for consolidated products."""
        image_sets = consolidated_data.get("images_by_site", {})
        if not image_sets:
            self.image_set_group.setVisible(False)
            return

        # Clear old buttons
        while self.image_buttons_layout.count():
            item = self.image_buttons_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Create buttons
        self.image_source_buttons = {}
        for site, images in image_sets.items():
            btn = QPushButton(f"{site} ({len(images)} images)")
            btn.clicked.connect(lambda checked, s=site: self._select_image_source(s))
            self.image_buttons_layout.addWidget(btn)
            self.image_source_buttons[site] = btn

        self.image_set_group.setVisible(True)
        self.image_sets = image_sets

        # Select first source
        if image_sets:
            first_site = list(image_sets.keys())[0]
            self._select_image_source(first_site)

    def _select_image_source(self, site):
        """Select an image source."""
        if hasattr(self, "image_sets") and site in self.image_sets:
            self.current_images = self.image_sets[site]
            self.current_image_index = 0
            self.show_current_image()

            # Highlight button
            for s, btn in self.image_source_buttons.items():
                if s == site:
                    btn.setStyleSheet("background-color: #2196F3; color: white;")
                else:
                    btn.setStyleSheet("")

    def show_current_image(self):
        """Display current image."""
        if not self.current_images or self.current_image_index >= len(
            self.current_images
        ):
            self.image_label.setText("No image")
            self.image_label.setPixmap(QPixmap())
            self.update_image_controls()
            return

        url = self.current_images[self.current_image_index]

        # Show loading placeholder immediately
        self.image_label.setText("Loading image...")
        self.image_label.setPixmap(QPixmap())

        # Try to load from cache
        if url in self.image_cache:
            pixmap = self.image_cache[url]
        else:
            # Load image
            pixmap = self._load_image(url)
            if pixmap and not pixmap.isNull():
                self.image_cache[url] = pixmap

        if pixmap and not pixmap.isNull():
            # Scale to fit
            scaled = pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText(f"Failed to load:\n{url[:50]}...")

        self.update_image_controls()

    def _load_image(self, url):
        """Load image from URL."""
        try:
            from PyQt6.QtCore import QEventLoop, QUrl
            from PyQt6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                                         QNetworkRequest)

            manager = QNetworkAccessManager()
            request = QNetworkRequest(QUrl(url))
            request.setRawHeader(b"User-Agent", b"Mozilla/5.0")

            loop = QEventLoop()
            reply = manager.get(request)
            if reply is None:
                return None
            reply.finished.connect(loop.quit)

            timer = QTimer()
            timer.timeout.connect(loop.quit)
            timer.setSingleShot(True)
            timer.start(10000)  # 10 sec timeout

            loop.exec()
            timer.stop()

            if reply.error() == QNetworkReply.NetworkError.NoError:
                data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    return pixmap

            return None
        except Exception as e:
            print(f"Image load error: {e}")
            return None

    def update_image_controls(self):
        """Update image button states."""
        has_imgs = bool(self.current_images)
        idx = self.current_image_index

        self.prev_img_btn.setEnabled(has_imgs and idx > 0)
        self.next_img_btn.setEnabled(has_imgs and idx < len(self.current_images) - 1)
        self.left_pos_btn.setEnabled(
            has_imgs and len(self.current_images) > 1 and idx > 0
        )
        self.right_pos_btn.setEnabled(
            has_imgs
            and len(self.current_images) > 1
            and idx < len(self.current_images) - 1
        )
        self.edit_img_btn.setEnabled(has_imgs)
        self.remove_img_btn.setEnabled(has_imgs)

        if has_imgs:
            self.img_counter_label.setText(
                f"Image {idx + 1} of {len(self.current_images)}"
            )
        else:
            self.img_counter_label.setText("No images")

    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.show_current_image()

    def next_image(self):
        if self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.show_current_image()

    def move_image_left(self):
        if self.current_image_index > 0:
            idx = self.current_image_index
            self.current_images[idx], self.current_images[idx - 1] = (
                self.current_images[idx - 1],
                self.current_images[idx],
            )
            self.current_image_index -= 1
            self.show_current_image()

    def move_image_right(self):
        if self.current_image_index < len(self.current_images) - 1:
            idx = self.current_image_index
            self.current_images[idx], self.current_images[idx + 1] = (
                self.current_images[idx + 1],
                self.current_images[idx],
            )
            self.current_image_index += 1
            self.show_current_image()

    def add_image(self):
        dialog = ImageDialog("", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            url = dialog.get_url()
            if url:
                self.current_images.append(url)
                self.current_image_index = len(self.current_images) - 1
                self.show_current_image()

    def edit_image(self):
        if self.current_images and 0 <= self.current_image_index < len(
            self.current_images
        ):
            dialog = ImageDialog(self.current_images[self.current_image_index], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                url = dialog.get_url()
                if url:
                    old_url = self.current_images[self.current_image_index]
                    self.current_images[self.current_image_index] = url
                    if old_url in self.image_cache:
                        del self.image_cache[old_url]
                    self.show_current_image()

    def remove_image(self):
        if self.current_images and 0 <= self.current_image_index < len(
            self.current_images
        ):
            self.current_images.pop(self.current_image_index)
            if (
                self.current_image_index >= len(self.current_images)
                and self.current_image_index > 0
            ):
                self.current_image_index -= 1
            self.show_current_image()

    def save_current_product(self):
        """Save UI state to product."""
        if not self.products_list:
            return

        product = self.products_list[self.current_index]
        product["Brand"] = self.brand_combo.currentText().strip()
        product["Name"] = self.name_combo.currentText().strip()
        product["Weight"] = self.weight_combo.currentText().strip()
        product["Special Order"] = "yes" if self.special_order_check.isChecked() else ""
        product["Product Disabled"] = (
            "checked" if self.product_disabled_check.isChecked() else "uncheck"
        )
        product["Image URLs"] = (
            self.current_images.copy() if self.current_images else []
        )

    def prev_product(self):
        self.save_current_product()
        if self.current_index > 0:
            self.current_index -= 1
            self.load_product_into_ui(self.current_index)

    def next_product(self):
        self.save_current_product()
        if self.current_index < len(self.products_list) - 1:
            self.current_index += 1
            self.load_product_into_ui(self.current_index)

    def delete_current_product(self):
        if self.is_single_product or not self.products_list:
            return

        sku = self.products_list[self.current_index].get("SKU", "Unknown")
        reply = QMessageBox.question(
            self,
            "Delete Product",
            f"Delete product {sku}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.products_list[self.current_index]
            if self.current_index >= len(self.products_list):
                self.current_index = len(self.products_list) - 1
            if self.products_list:
                self.load_product_into_ui(self.current_index)
            else:
                self.finish_editing()

    def update_progress_display(self, index):
        sku = self.products_list[index].get("SKU", "Unknown")
        if self.is_single_product:
            self.progress_label.setText(f"Editing: {sku}")
        else:
            self.progress_label.setText(
                f"Product {index + 1} of {len(self.products_list)}: {sku}"
            )

    def finish_editing(self):
        self.save_current_product()
        self.close()
        self.finished.emit()

    def cancel_editing(self):
        reply = QMessageBox.question(
            self,
            "Cancel",
            "Cancel? All changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cancelled = True
            self.close()
            self.finished.emit()


def edit_products_in_batch(products_or_skus, auto_close_seconds=None):
    """
    Edit products in batch interface.

    Args:
        products_or_skus: List of SKUs or product dicts
        auto_close_seconds: Auto-close after N seconds (for testing)

    Returns:
        List of edited products, or None if cancelled
    """
    # Determine input type
    if products_or_skus and isinstance(products_or_skus[0], str):
        products_list = load_products_from_db(products_or_skus)
    elif products_or_skus and isinstance(products_or_skus[0], dict):
        products_list = products_or_skus
    else:
        return None

    if not products_list:
        QMessageBox.warning(None, "No Products", "No products to edit.")
        return None

    # Ensure QApplication
    app = QApplication.instance()
    standalone = False
    if app is None:
        app = QApplication([])
        standalone = True

    # Create editor
    editor = ProductEditor(products_list)
    editor.show()

    # Auto-close for testing
    if auto_close_seconds is not None:
        QTimer.singleShot(auto_close_seconds * 1000, editor.finish_editing)

    # Event loop
    from PyQt6.QtCore import QEventLoop

    loop = QEventLoop()
    editor.finished.connect(loop.quit)

    if standalone:
        loop.exec()
    else:
        loop.exec()

    # Return results
    if editor.cancelled:
        return None
    else:
        return products_list


def product_editor_interactive(product_or_sku):
    """Edit a single product interactively."""
    result = edit_products_in_batch([product_or_sku])
    if result is None:
        return None
    return result[0]


def load_products_from_db(skus):
    """Load products from database by SKUs."""
    if not skus:
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.text_factory = str
        placeholders = ",".join("?" * len(skus))
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT SKU, Brand, Name, Weight, Category, Product_Type, Product_On_Pages, 
                   Special_Order, Images, ProductDisabled
            FROM products
            WHERE SKU IN ({placeholders})
        """,
            skus,
        )

        products = []
        for row in cursor.fetchall():
            (
                sku,
                brand,
                name,
                weight,
                category,
                product_type,
                pages,
                special,
                images,
                disabled,
            ) = row

            img_list = []
            if images:
                raw_images = [i.strip() for i in images.split(",") if i.strip()]
                # Convert relative paths to full URLs
                base_url = "https://www.baystatepet.com/media/"
                for img in raw_images:
                    if img.startswith("http"):
                        # Already a full URL
                        img_list.append(img)
                    else:
                        # Convert relative path to full URL
                        img_list.append(base_url + img)

            products.append(
                {
                    "SKU": sku or "",
                    "Brand": brand or "",
                    "Name": name or "",
                    "Weight": weight or "",
                    "Category": category or "",
                    "Product Type": product_type or "",
                    "Product On Pages": pages or "",
                    "Special Order": "yes" if special == "yes" else "",
                    "Image URLs": img_list,
                    "Product Disabled": (
                        "checked" if disabled == "checked" else "uncheck"
                    ),
                }
            )

        return products
    except Exception as e:
        print(f"DB error: {e}")
        return []
    finally:
        conn.close()


if __name__ == "__main__":
    print("Testing new product editor...")

    # Test with dummy data
    test_products = [
        {
            "SKU": "TEST001",
            "Name": "Test Product",
            "Price": "$10.99",
            "Brand": "Test Brand",
            "Weight": "1 LB",
            "Special Order": "",
            "Product Disabled": "uncheck",
            "Image URLs": [],
        }
    ]

    result = edit_products_in_batch(test_products, auto_close_seconds=3)
    print(f"Result: {result}")
