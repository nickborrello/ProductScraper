import sqlite3
import json
from pathlib import Path
import sys
import os

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QComboBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt
try:
    # Try relative import first (when run as part of package)
    from .product_editor import edit_products_in_batch
except ImportError:
    try:
        # Try absolute import from src.ui (when run as standalone script)
        from src.ui.product_editor import edit_products_in_batch
    except ImportError:
        # Last resort - import from current directory
        from product_editor import edit_products_in_batch

# Database path - find it relative to project root
from pathlib import Path
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = Path(PROJECT_ROOT) / "data" / "databases" / "products.db"

class ProductViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Product Database Viewer - Professional Edition")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                gridline-color: #4a4a4a;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #4a4a4a;
            }
            QTableWidget::item:selected {
                background-color: #4a4a4a;
            }
            QHeaderView::section {
                background-color: #343a40;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #495057;
                font-weight: bold;
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
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ffffff;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                selection-background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
        """)

        # Database connection
        self.conn = None
        self.connect_db()

        # State variables
        self.current_page = 0
        self.page_size = 50
        self.total_products = 0
        self.search_term = ""
        self.selected_products = set()  # Store SKUs of selected products
        self.show_disabled = True

        # Create UI
        self.create_widgets()
        self.load_products()

    def connect_db(self):
        """Connect to the database."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found: {DB_PATH}")
        self.conn = sqlite3.connect(DB_PATH)
        # Ensure UTF-8 handling
        self.conn.text_factory = str

    def create_widgets(self):
        """Create the main UI components."""
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Search and Filter Card
        search_card = QGroupBox("🔍 Search & Filter")
        search_card.setStyleSheet("""
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
        search_layout = QHBoxLayout(search_card)
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(15, 15, 15, 15)

        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by SKU, brand, or product name...")
        self.search_input.textChanged.connect(self.on_search_change)
        search_layout.addWidget(self.search_input)

        self.show_disabled_cb = QCheckBox("Show disabled products")
        self.show_disabled_cb.setChecked(True)
        self.show_disabled_cb.stateChanged.connect(self.on_filter_change)
        search_layout.addWidget(self.show_disabled_cb)

        search_layout.addWidget(QLabel("Items per page:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["25", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_change)
        search_layout.addWidget(self.page_size_combo)

        layout.addWidget(search_card)

        # Products Table Card
        table_card = QGroupBox("📊 Product Database")
        table_card.setStyleSheet("""
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
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Select", "SKU", "Brand", "Product Name", "Disabled"])
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self.on_table_click)
        
        # Set column widths and resize modes
        self.table.setColumnWidth(0, 60)  # Select checkbox column - small
        self.table.setColumnWidth(2, 150)  # Brand column - wider
        self.table.setColumnWidth(4, 80)  # Disabled column - fixed width
        
        # Set Product Name column to stretch
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        table_layout.addWidget(self.table)

        layout.addWidget(table_card)

        # Action Buttons Card
        action_card = QGroupBox("⚡ Actions")
        action_card.setStyleSheet("""
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
        button_layout = QHBoxLayout(action_card)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(15, 15, 15, 15)

        self.edit_button = QPushButton("✏️ Edit Selected")
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        self.edit_button.clicked.connect(self.edit_selected_products)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)

        self.select_all_button = QPushButton("☑️ Select All")
        self.select_all_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.select_all_button.clicked.connect(self.select_all_visible)
        button_layout.addWidget(self.select_all_button)

        self.clear_selection_button = QPushButton("🗑️ Clear Selection")
        self.clear_selection_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.clear_selection_button.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_selection_button)

        button_layout.addStretch()
        layout.addWidget(action_card)

        # Pagination Card
        pagination_card = QGroupBox("📄 Navigation")
        pagination_card.setStyleSheet("""
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
        pagination_layout = QHBoxLayout(pagination_card)
        pagination_layout.setSpacing(10)
        pagination_layout.setContentsMargins(15, 15, 15, 15)

        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
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
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        pagination_layout.addWidget(self.page_label)

        self.next_button = QPushButton("Next ▶")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
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
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)

        pagination_layout.addStretch()
        layout.addWidget(pagination_card)

        # Status Card
        status_card = QGroupBox("📊 Status")
        status_card.setStyleSheet("""
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
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(15, 15, 15, 15)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #cccccc;")
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_card)

    def on_search_change(self):
        """Handle search input changes."""
        self.search_term = self.search_input.text().strip()
        self.current_page = 0
        self.load_products()

    def on_filter_change(self):
        """Handle filter changes."""
        self.show_disabled = self.show_disabled_cb.isChecked()
        self.current_page = 0
        self.load_products()

    def on_page_size_change(self):
        """Handle page size changes."""
        self.page_size = int(self.page_size_combo.currentText())
        self.current_page = 0
        self.load_products()

    def load_products(self):
        """Load products from database with current filters."""
        if self.conn is None:
            QMessageBox.critical(self, "Error", "Database connection not available")
            return
        
        try:
            cursor = self.conn.cursor()

            # Build query
            query = """
                SELECT SKU, Brand, Name, ProductDisabled
                FROM products
                WHERE Name IS NOT NULL
            """

            params = []

            # Add search filter
            if self.search_term:
                search_filter = """
                    AND (SKU LIKE ? OR
                         LOWER(Brand) LIKE LOWER(?) OR
                         LOWER(Name) LIKE LOWER(?))
                """
                search_param = f"%{self.search_term}%"
                query += search_filter
                params.extend([search_param, search_param, search_param])

            # Add disabled products filter
            if not self.show_disabled:
                query += " AND (ProductDisabled IS NULL OR LOWER(ProductDisabled) != 'checked')"
                params.extend([])

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query, params)
            self.total_products = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY sku LIMIT ? OFFSET ?"
            params.extend([self.page_size, self.current_page * self.page_size])

            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Populate table
            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                sku, brand, name, product_disabled = row
                # Check if this product is selected
                is_selected = "☑" if sku in self.selected_products else "☐"
                # Format disabled status
                disabled_display = "Yes" if product_disabled and str(product_disabled).lower().strip() == "checked" else "No"

                self.table.setItem(row_idx, 0, QTableWidgetItem(is_selected))
                self.table.setItem(row_idx, 1, QTableWidgetItem(sku))
                self.table.setItem(row_idx, 2, QTableWidgetItem(brand or ""))
                self.table.setItem(row_idx, 3, QTableWidgetItem(name or ""))
                self.table.setItem(row_idx, 4, QTableWidgetItem(disabled_display))

            # Update UI
            self.update_pagination()
            self.update_status()
            self.update_edit_button()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load products: {e}")

    def on_table_click(self, row, col):
        """Handle table click events."""
        if col == 0:  # Select column
            item = self.table.item(row, 1)
            if item is not None:
                sku = item.text()
                self.toggle_selection(sku)
                self.update_table_display()

    def toggle_selection(self, sku):
        """Toggle selection state of a product."""
        if sku in self.selected_products:
            self.selected_products.remove(sku)
        else:
            self.selected_products.add(sku)

    def update_table_display(self):
        """Update table display for selections."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None:
                sku = item.text()
                is_selected = "☑" if sku in self.selected_products else "☐"
                select_item = self.table.item(row, 0)
                if select_item is not None:
                    select_item.setText(is_selected)

    def select_all_visible(self):
        """Select all products currently visible in the table."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None:
                sku = item.text()
                self.selected_products.add(sku)
        self.update_table_display()
        self.update_edit_button()

    def clear_selection(self):
        """Clear all selections."""
        self.selected_products.clear()
        self.update_table_display()
        self.update_edit_button()

    def update_pagination(self):
        """Update pagination controls."""
        total_pages = max(1, (self.total_products + self.page_size - 1) // self.page_size)
        current_page_display = self.current_page + 1

        self.page_label.setText(f"Page {current_page_display} of {total_pages}")

        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < total_pages - 1)

    def update_status(self):
        """Update status label."""
        visible_count = self.table.rowCount()
        selected_count = len(self.selected_products)

        if self.search_term:
            status = f"Found {self.total_products} products matching '{self.search_term}' | Showing {visible_count} | Selected: {selected_count}"
        else:
            status = f"Total: {self.total_products} products | Showing {visible_count} | Selected: {selected_count}"

        self.status_label.setText(status)

    def update_edit_button(self):
        """Update edit button state based on selection."""
        if self.selected_products:
            self.edit_button.setText(f"✏️ Edit Selected ({len(self.selected_products)})")
            self.edit_button.setEnabled(True)
        else:
            self.edit_button.setText("✏️ Edit Selected")
            self.edit_button.setEnabled(False)

    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_products()

    def next_page(self):
        """Go to next page."""
        total_pages = max(1, (self.total_products + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_products()

    def edit_selected_products(self):
        """Edit the selected products using the product editor."""
        if not self.selected_products:
            return
        
        try:
            # Get selected SKUs
            skus = list(self.selected_products)
            
            # Load product data from database
            products_data = self.load_products_data(skus)
            
            if not products_data:
                QMessageBox.critical(self, "Error", "Failed to load product data from database")
                return
            
            # Call the batch editor with product data
            edited_products = edit_products_in_batch(products_data)

            if edited_products:
                QMessageBox.information(self, "Success", f"Successfully edited {len(edited_products)} products")
                # Refresh the view to show any changes
                self.load_products()
            else:
                QMessageBox.information(self, "Cancelled", "Editing was cancelled")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit products: {e}")
            import traceback
            traceback.print_exc()

    def load_products_data(self, skus):
        """Load product data from database for the given SKUs."""
        if not skus:
            return []
        
        if self.conn is None:
            return []
        
        try:
            # Ensure UTF-8 handling
            self.conn.text_factory = str
            placeholders = ','.join('?' * len(skus))
            cursor = self.conn.cursor()
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
                    # Split by comma and strip whitespace
                    image_urls = [url.strip() for url in str(images).split(',') if url.strip()]
                
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
                
                products.append(mapped_product)
            
            return products
            
        except Exception as e:
            print(f"Error loading product data: {e}")
            return []

    def __del__(self):
        """Cleanup database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Main function to run the product viewer."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        standalone = True
    else:
        standalone = False

    window = ProductViewer()
    window.show()

    if standalone:
        app.exec()

if __name__ == "__main__":
    main()