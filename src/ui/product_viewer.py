import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(current_dir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DB_PATH = Path(PROJECT_ROOT) / "data" / "databases" / "products.db"

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProductViewer(QWidget):
    def __init__(self):
        super().__init__()
        
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
        self.category_filter = ""
        self.product_type_filter = ""
        self.special_order_filter = False
        self.date_from = ""
        self.date_from = ""
        self.date_to = ""
        
        # JSON Mode State
        self.json_mode = False
        self.json_data = []
        self.current_json_file = None

        # Create UI
        self.create_widgets()
        self.load_products()

    def connect_db(self):
        """Connect to the database."""
        if not DB_PATH.exists():
            # Database might be created later, so just return silently
            return
        self.conn = sqlite3.connect(DB_PATH)
        # Ensure UTF-8 handling
        self.conn.text_factory = str

    def create_widgets(self):
        """Create the main UI components."""
        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Search and Filter Card
        search_card = QGroupBox("🔍 Search & Filter")
        search_layout = QVBoxLayout(search_card)
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(15, 15, 15, 15)

        # First row: Search and basic filters
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by SKU, brand, or product name...")
        self.search_input.textChanged.connect(self.on_search_change)
        first_row.addWidget(self.search_input)

        self.show_disabled_cb = QCheckBox("Show disabled")
        self.show_disabled_cb.setChecked(True)
        self.show_disabled_cb.stateChanged.connect(self.on_filter_change)
        first_row.addWidget(self.show_disabled_cb)

        self.special_order_cb = QCheckBox("Special Order only")
        self.special_order_cb.stateChanged.connect(self.on_filter_change)
        first_row.addWidget(self.special_order_cb)

        first_row.addWidget(QLabel("Items per page:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["25", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_change)
        first_row.addWidget(self.page_size_combo)

        search_layout.addLayout(first_row)

        # Second row: Category and Product Type filters
        second_row = QHBoxLayout()
        second_row.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        self.category_combo.currentTextChanged.connect(self.on_filter_change)
        second_row.addWidget(self.category_combo)

        second_row.addWidget(QLabel("Product Type:"))
        self.product_type_combo = QComboBox()
        self.product_type_combo.addItem("All Types", "")
        self.product_type_combo.currentTextChanged.connect(self.on_filter_change)
        second_row.addWidget(self.product_type_combo)

        second_row.addWidget(QLabel("Date From:"))
        self.date_from_input = QLineEdit()
        self.date_from_input.setPlaceholderText("YYYY-MM-DD")
        self.date_from_input.textChanged.connect(self.on_filter_change)
        second_row.addWidget(self.date_from_input)

        second_row.addWidget(QLabel("Date To:"))
        self.date_to_input = QLineEdit()
        self.date_to_input.setPlaceholderText("YYYY-MM-DD")
        self.date_to_input.textChanged.connect(self.on_filter_change)
        second_row.addWidget(self.date_to_input)

        search_layout.addLayout(second_row)

        layout.addWidget(search_card)

        # Products Table Card
        table_card = QGroupBox("📊 Product Database")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(
            [
                "Select",
                "SKU",
                "Brand",
                "Product Name",
                "Price",
                "Weight",
                "Category",
                "Product Type",
                "Pages",
                "Special Order",
                "Disabled",
                "Last Updated",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )  # Make table read-only
        self.table.cellClicked.connect(self.on_table_click)

        # Set column widths and resize modes
        self.table.setColumnWidth(0, 60)  # Select checkbox column - small
        self.table.setColumnWidth(1, 120)  # SKU column
        self.table.setColumnWidth(2, 120)  # Brand column
        self.table.setColumnWidth(4, 80)  # Price column
        self.table.setColumnWidth(5, 80)  # Weight column
        self.table.setColumnWidth(6, 120)  # Category column
        self.table.setColumnWidth(7, 120)  # Product Type column
        self.table.setColumnWidth(8, 100)  # Pages column
        self.table.setColumnWidth(9, 100)  # Special Order column
        self.table.setColumnWidth(10, 80)  # Disabled column
        self.table.setColumnWidth(11, 140)  # Last Updated column
        # Set Product Name column to stretch
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        table_layout.addWidget(self.table)

        layout.addWidget(table_card)

        # Action Buttons Card
        action_card = QGroupBox("⚡ Actions")
        button_layout = QHBoxLayout(action_card)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(15, 15, 15, 15)

        self.edit_button = QPushButton("✏️ Edit Selected")
        self.edit_button.setProperty("class", "success")
        self.edit_button.clicked.connect(self.edit_selected_products)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)

        self.select_all_button = QPushButton("☑️ Select All")
        self.select_all_button.setProperty("class", "primary")
        self.select_all_button.clicked.connect(self.select_all_visible)
        button_layout.addWidget(self.select_all_button)

        self.export_button = QPushButton("💾 Export to CSV")
        self.export_button.clicked.connect(self.export_products)
        button_layout.addWidget(self.export_button)

        self.delete_button = QPushButton("🗑️ Delete Selected")
        self.delete_button.setProperty("class", "danger")
        self.delete_button.clicked.connect(self.delete_selected_products)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)

        self.clear_selection_button = QPushButton("❌ Clear Selection")
        self.clear_selection_button.setProperty("class", "secondary")
        self.clear_selection_button.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_selection_button)

        # JSON Result Actions
        self.load_json_btn = QPushButton("📂 Load Results")
        self.load_json_btn.clicked.connect(self.load_results_file)
        button_layout.addWidget(self.load_json_btn)

        self.save_json_btn = QPushButton("💾 Save JSON")
        self.save_json_btn.clicked.connect(self.save_results_to_json)
        self.save_json_btn.setVisible(False)
        button_layout.addWidget(self.save_json_btn)

        self.import_db_btn = QPushButton("📥 Import to DB")
        self.import_db_btn.clicked.connect(self.import_to_database)
        self.import_db_btn.setVisible(False)
        button_layout.addWidget(self.import_db_btn)

        button_layout.addStretch()
        layout.addWidget(action_card)

        # Pagination Card
        pagination_card = QGroupBox("📄 Navigation")
        pagination_layout = QHBoxLayout(pagination_card)
        pagination_layout.setSpacing(10)
        pagination_layout.setContentsMargins(15, 15, 15, 15)

        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setProperty("class", "secondary")
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setProperty("class", "page-label")
        pagination_layout.addWidget(self.page_label)

        self.next_button = QPushButton("Next ▶")
        self.next_button.setProperty("class", "secondary")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)

        pagination_layout.addStretch()
        layout.addWidget(pagination_card)

        # Status Card
        status_card = QGroupBox("📊 Status")
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
        # Reset scroll to top
        scrollbar = self.table.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(0)

    def on_filter_change(self, value=None):
        """Handle filter changes."""
        self.show_disabled = self.show_disabled_cb.isChecked()
        self.special_order_filter = self.special_order_cb.isChecked()
        self.category_filter = self.category_combo.currentData() or ""
        self.product_type_filter = self.product_type_combo.currentData() or ""
        self.date_from = self.date_from_input.text().strip()
        self.date_to = self.date_to_input.text().strip()
        self.current_page = 0
        self.load_products()
        # Reset scroll to top
        scrollbar = self.table.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(0)

    def on_page_size_change(self):
        """Handle page size changes."""
        self.page_size = int(self.page_size_combo.currentText())
        self.current_page = 0
        self.load_products()
        # Reset scroll to top
        scrollbar = self.table.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(0)

    def load_products(self):
        """Load products from database or JSON with current filters."""
        if self.json_mode:
            self._load_products_from_json()
            return

        if self.conn is None:
            self.status_label.setText("Database not connected (products.db not found)")
            self.table.setRowCount(0)
            return

        try:
            cursor = self.conn.cursor()

            # Build query with all columns
            query = """
                SELECT SKU, Brand, Name, Price, Weight, Category, Product_Type, 
                       Product_On_Pages, Special_Order, ProductDisabled, last_updated
                FROM products
                WHERE Name IS NOT NULL
            """

            params: list[Any] = []

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

            # Add category filter
            if self.category_filter:
                query += (
                    " AND (Category LIKE ? OR Category LIKE ? OR Category LIKE ? OR Category = ?)"
                )
                # Match: "|Category|", "Category|", "|Category", "Category"
                category_param = self.category_filter
                params.extend(
                    [
                        f"%|{category_param}|%",
                        f"{category_param}|%",
                        f"%|{category_param}",
                        category_param,
                    ]
                )

            # Add product type filter
            if self.product_type_filter:
                query += " AND (Product_Type LIKE ? OR Product_Type LIKE ? OR Product_Type LIKE ? OR Product_Type = ?)"
                # Match: "|Type|", "Type|", "|Type", "Type"
                type_param = self.product_type_filter
                params.extend(
                    [
                        f"%|{type_param}|%",
                        f"{type_param}|%",
                        f"%|{type_param}",
                        type_param,
                    ]
                )

            # Add special order filter
            if self.special_order_filter:
                query += " AND LOWER(Special_Order) = 'yes'"

            # Add disabled products filter
            if not self.show_disabled:
                query += " AND (ProductDisabled IS NULL OR LOWER(ProductDisabled) != 'checked')"

            # Add date range filter
            if self.date_from:
                query += " AND last_updated >= ?"
                params.append(self.date_from)
            if self.date_to:
                query += " AND last_updated <= ?"
                params.append(self.date_to + " 23:59:59")  # Include the entire day

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query, params)
            self.total_products = cursor.fetchone()[0]

            # Add pagination
            query += " ORDER BY last_updated DESC, sku LIMIT ? OFFSET ?"
            params.extend([self.page_size, self.current_page * self.page_size])

            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Populate table
            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                (
                    sku,
                    brand,
                    name,
                    price,
                    weight,
                    category,
                    product_type,
                    product_on_pages,
                    special_order,
                    product_disabled,
                    last_updated,
                ) = row

                self._populate_table_row(row_idx, sku, brand, name, price, weight, category, product_type, product_on_pages, special_order, product_disabled, last_updated)

            # Update filter dropdowns with available values
            self.update_filter_dropdowns()

            # Update UI
            self.update_pagination()
            self.update_status()
            self.update_edit_button()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load products: {e}")

    def _load_products_from_json(self):
        """Filter and load products from JSON data."""
        filtered_data = []
        
        # Apply filters
        for item in self.json_data:
            # Search
            if self.search_term:
                term = self.search_term.lower()
                if (term not in str(item.get("SKU", "")).lower() and 
                    term not in str(item.get("Brand", "")).lower() and 
                    term not in str(item.get("Name", "")).lower()):
                    continue
            
            # Category
            if self.category_filter and self.category_filter not in str(item.get("Category", "")):
                continue
                
            # Product Type
            if self.product_type_filter and self.product_type_filter not in str(item.get("Product Type", "")):
                continue
                
            filtered_data.append(item)
            
        self.total_products = len(filtered_data)
        
        # Pagination
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_data = filtered_data[start:end]
        
        self.table.setRowCount(len(page_data))
        for row_idx, item in enumerate(page_data):
            self._populate_table_row(
                row_idx,
                item.get("SKU", ""),
                item.get("Brand", ""),
                item.get("Name", ""),
                item.get("Price", ""),
                item.get("Weight", ""),
                item.get("Category", ""),
                item.get("Product Type", ""),
                item.get("Product On Pages", ""),
                item.get("Special Order", ""),
                item.get("Product Disabled", ""),
                item.get("last_updated", "")
            )
            
        self.update_pagination()
        self.update_status()
        self.update_edit_button()

    def _populate_table_row(self, row_idx, sku, brand, name, price, weight, category, product_type, product_on_pages, special_order, product_disabled, last_updated):
        """Helper to populate a single table row."""
        # Check if this product is selected
        is_selected = "☑" if sku in self.selected_products else "☐"

        # Format data for display
        price_display = str(price) if price else ""
        weight_display = str(weight) if weight else ""
        category_display = str(category) if category else ""
        product_type_display = str(product_type) if product_type else ""
        pages_display = str(product_on_pages) if product_on_pages else ""
        special_order_display = (
            "Yes" if special_order and str(special_order).lower().strip() == "yes" else "No"
        )
        disabled_display = (
            "Yes"
            if product_disabled and str(product_disabled).lower().strip() == "checked"
            else "No"
        )
        last_updated_display = str(last_updated) if last_updated else ""

        # Set table items
        self.table.setItem(row_idx, 0, QTableWidgetItem(is_selected))
        self.table.setItem(row_idx, 1, QTableWidgetItem(str(sku)))
        self.table.setItem(row_idx, 2, QTableWidgetItem(str(brand or "")))
        self.table.setItem(row_idx, 3, QTableWidgetItem(str(name or "")))
        self.table.setItem(row_idx, 4, QTableWidgetItem(price_display))
        self.table.setItem(row_idx, 5, QTableWidgetItem(weight_display))
        self.table.setItem(row_idx, 6, QTableWidgetItem(category_display))
        self.table.setItem(row_idx, 7, QTableWidgetItem(product_type_display))
        self.table.setItem(row_idx, 8, QTableWidgetItem(pages_display))
        self.table.setItem(row_idx, 9, QTableWidgetItem(special_order_display))
        self.table.setItem(row_idx, 10, QTableWidgetItem(disabled_display))
        self.table.setItem(row_idx, 11, QTableWidgetItem(last_updated_display))

    def update_filter_dropdowns(self):
        """Update category and product type filter dropdowns with available values."""
        if self.conn is None:
            return

        try:
            cursor = self.conn.cursor()

            # Get distinct categories - split by "|" and collect unique values
            cursor.execute(
                "SELECT DISTINCT Category FROM products WHERE Category IS NOT NULL AND Category != ''"
            )
            categories = set()
            for row in cursor.fetchall():
                category_str = row[0]
                if category_str:
                    # Split by "|" and strip whitespace
                    category_parts = [cat.strip() for cat in category_str.split("|") if cat.strip()]
                    categories.update(category_parts)
            sorted_categories = sorted(list(categories))

            # Get distinct product types - split by "|" and collect unique values
            cursor.execute(
                "SELECT DISTINCT Product_Type FROM products WHERE Product_Type IS NOT NULL AND Product_Type != ''"
            )
            product_types = set()
            for row in cursor.fetchall():
                product_type_str = row[0]
                if product_type_str:
                    # Split by "|" and strip whitespace
                    type_parts = [pt.strip() for pt in product_type_str.split("|") if pt.strip()]
                    product_types.update(type_parts)
            sorted_product_types = sorted(list(product_types))

            # Update category combo - temporarily disconnect signal to avoid recursion
            self.category_combo.currentTextChanged.disconnect(self.on_filter_change)
            current_category = self.category_combo.currentData() or ""
            self.category_combo.clear()
            self.category_combo.addItem("All Categories", "")
            for category in sorted_categories:
                self.category_combo.addItem(category, category)
            # Restore previous selection if it still exists
            if current_category:
                index = self.category_combo.findData(current_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            self.category_combo.currentTextChanged.connect(self.on_filter_change)

            # Update product type combo - temporarily disconnect signal to avoid recursion
            self.product_type_combo.currentTextChanged.disconnect(self.on_filter_change)
            current_type = self.product_type_combo.currentData() or ""
            self.product_type_combo.clear()
            self.product_type_combo.addItem("All Types", "")
            for product_type in sorted_product_types:
                self.product_type_combo.addItem(product_type, product_type)
            # Restore previous selection if it still exists
            if current_type:
                index = self.product_type_combo.findData(current_type)
                if index >= 0:
                    self.product_type_combo.setCurrentIndex(index)
            self.product_type_combo.currentTextChanged.connect(self.on_filter_change)

        except Exception as e:
            print(f"Error updating filter dropdowns: {e}")

    def on_table_click(self, row, col):
        """Handle table click events."""
        if col == 0:  # Select column
            item = self.table.item(row, 1)
            if item is not None:
                sku = item.text()
                self.toggle_selection(sku)
                self.update_table_display()
                self.update_edit_button()

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

        # Build filter description
        filter_parts = []
        if self.search_term:
            filter_parts.append(f"search: '{self.search_term}'")
        if self.category_filter:
            filter_parts.append(f"category: {self.category_filter}")
        if self.product_type_filter:
            filter_parts.append(f"type: {self.product_type_filter}")
        if self.special_order_filter:
            filter_parts.append("special order only")
        if not self.show_disabled:
            filter_parts.append("enabled only")
        if self.date_from or self.date_to:
            date_range = f"{self.date_from or 'start'} to {self.date_to or 'end'}"
            filter_parts.append(f"date: {date_range}")

        filter_desc = f" | Filters: {', '.join(filter_parts)}" if filter_parts else ""

        if self.search_term or filter_parts:
            status = f"Found {self.total_products} products{filter_desc} | Showing {visible_count} | Selected: {selected_count}"
        else:
            status = f"Total: {self.total_products} products | Showing {visible_count} | Selected: {selected_count}"

        self.status_label.setText(status)

    def update_edit_button(self):
        """Update edit button state based on selection."""
        if self.selected_products:
            self.edit_button.setText(f"✏️ Edit Selected ({len(self.selected_products)})")
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.delete_button.setText(f"🗑️ Delete Selected ({len(self.selected_products)})")
        else:
            self.edit_button.setText("✏️ Edit Selected")
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.delete_button.setText("🗑️ Delete Selected")

    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_products()
            # Reset scroll to top
            scrollbar = self.table.verticalScrollBar()
            if scrollbar is not None:
                scrollbar.setValue(0)

    def next_page(self):
        """Go to next page."""
        total_pages = max(1, (self.total_products + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_products()
            # Reset scroll to top
            scrollbar = self.table.verticalScrollBar()
            if scrollbar is not None:
                scrollbar.setValue(0)

    def edit_selected_products(self):
        """Edit the selected products using the product editor."""
        if not self.selected_products:
            return

        try:
            # Import the editor function
            try:
                edit_func = __import__(
                    "src.ui.product_editor", fromlist=["edit_products_in_batch"]
                ).edit_products_in_batch
            except ImportError:
                try:
                    edit_func = __import__(
                        "product_editor", fromlist=["edit_products_in_batch"]
                    ).edit_products_in_batch
                except ImportError:
                    edit_func = __import__(
                        "product_editor", fromlist=["edit_products_in_batch"]
                    ).edit_products_in_batch

            # Get selected SKUs
            skus = list(self.selected_products)

            # Load product data from database
            products_data = self.load_products_data(skus)

            if not products_data:
                QMessageBox.critical(self, "Error", "Failed to load product data from database")
                return

            # Call the batch editor with product data
            edited_products = edit_func(products_data)

            if edited_products:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully edited {len(edited_products)} products",
                )
                # Refresh the view to show any changes
                self.load_products()
            else:
                QMessageBox.information(self, "Cancelled", "Editing was cancelled")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit products: {e}")
            import traceback

            traceback.print_exc()

    def export_products(self):
        """Export current view or selected products to CSV."""
        if not self.conn:
            return

        try:
            # Determine what to export
            if self.selected_products:
                skus = list(self.selected_products)
                placeholders = ",".join("?" * len(skus))
                query = f"SELECT * FROM products WHERE SKU IN ({placeholders})"
                params = skus
                filename = "selected_products.csv"
            else:
                # Export all visible (filtered) products
                # We need to reconstruct the query logic or just export all if no filter
                # For simplicity, let's export all currently filtered
                # But reusing the query logic is complex. 
                # Let's ask user: Export All or Export Selected?
                # Actually, standard behavior: if selection, export selection. Else export all.
                
                # Re-run the current filter query
                # This is a bit redundant but safest
                query = """
                    SELECT *
                    FROM products
                    WHERE Name IS NOT NULL
                """
                params = []
                
                # Add search filter
                if self.search_term:
                    query += " AND (SKU LIKE ? OR LOWER(Brand) LIKE LOWER(?) OR LOWER(Name) LIKE LOWER(?))"
                    search_param = f"%{self.search_term}%"
                    params.extend([search_param, search_param, search_param])

                # Add category filter
                if self.category_filter:
                    query += " AND (Category LIKE ? OR Category LIKE ? OR Category LIKE ? OR Category = ?)"
                    category_param = self.category_filter
                    params.extend([f"%|{category_param}|%", f"{category_param}|%", f"%|{category_param}", category_param])

                # Add product type filter
                if self.product_type_filter:
                    query += " AND (Product_Type LIKE ? OR Product_Type LIKE ? OR Product_Type LIKE ? OR Product_Type = ?)"
                    type_param = self.product_type_filter
                    params.extend([f"%|{type_param}|%", f"{type_param}|%", f"%|{type_param}", type_param])

                # Add special order filter
                if self.special_order_filter:
                    query += " AND LOWER(Special_Order) = 'yes'"

                # Add disabled products filter
                if not self.show_disabled:
                    query += " AND (ProductDisabled IS NULL OR LOWER(ProductDisabled) != 'checked')"

                # Add date range filter
                if self.date_from:
                    query += " AND last_updated >= ?"
                    params.append(self.date_from)
                if self.date_to:
                    query += " AND last_updated <= ?"
                    params.append(self.date_to + " 23:59:59")

                filename = "all_products.csv"

            # Get save path
            path, _ = QFileDialog.getSaveFileName(self, "Export CSV", filename, "CSV Files (*.csv)")
            if not path:
                return

            # Execute
            df = pd.read_sql_query(query, self.conn, params=params)
            df.to_csv(path, index=False)
            
            QMessageBox.information(self, "Success", f"Exported {len(df)} products to {path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    def delete_selected_products(self):
        """Delete selected products from database."""
        if not self.selected_products:
            return

        count = len(self.selected_products)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {count} products?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                cursor = self.conn.cursor()
                skus = list(self.selected_products)
                placeholders = ",".join("?" * len(skus))
                cursor.execute(f"DELETE FROM products WHERE SKU IN ({placeholders})", skus)
                self.conn.commit()
                
                self.selected_products.clear()
                self.load_products()
                QMessageBox.information(self, "Success", f"Deleted {count} products.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete products: {e}")

    def load_results_file(self):
        """Load scraper results from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Results File", 
            str(Path(PROJECT_ROOT) / "data" / "scraper_results"), 
            "JSON Files (*.json)"
        )
        
        if not path:
            return
            
        try:
            import json
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle different JSON structures
            if isinstance(data, dict):
                # Check for "results" key (common in our scraper output)
                if "results" in data and isinstance(data["results"], list):
                    self.json_data = data["results"]
                # Check for session format
                elif "session_id" in data and "scrapers" in data:
                    # Flatten scraper results
                    self.json_data = []
                    for scraper_name, scraper_data in data.get("scrapers", {}).items():
                        if "results" in scraper_data:
                            for sku, details in scraper_data["results"].items():
                                # Flatten structure
                                item = details.copy()
                                item["SKU"] = sku
                                item["Scraper"] = scraper_name
                                self.json_data.append(item)
                else:
                    # Try to find any list in the dict
                    found_list = False
                    for key, value in data.items():
                        if isinstance(value, list):
                            self.json_data = value
                            found_list = True
                            break
                    if not found_list:
                        raise ValueError("Could not find a list of products in JSON file")
            elif isinstance(data, list):
                self.json_data = data
            else:
                raise ValueError("Invalid JSON format")
                
            self.json_mode = True
            self.current_json_file = path
            self.status_label.setText(f"Loaded {len(self.json_data)} products from {os.path.basename(path)}")
            
            # Update UI state
            self.save_json_btn.setVisible(True)
            self.import_db_btn.setVisible(True)
            self.export_button.setText("💾 Export JSON to CSV")
            
            # Reset filters and load
            self.current_page = 0
            self.load_products()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load JSON file: {e}")

    def save_results_to_json(self):
        """Save current JSON data back to file."""
        if not self.json_mode or not self.current_json_file:
            return
            
        try:
            import json
            # Create a backup first
            backup_path = self.current_json_file + ".bak"
            import shutil
            shutil.copy2(self.current_json_file, backup_path)
            
            # We need to reconstruct the original format if possible, 
            # but for now let's save the flat list or a simple structure
            # To be safe and not break the original structure if it was complex,
            # we might want to just save the list. 
            # However, our scraper output is usually specific.
            
            # Let's save as a flat list of results for now, or try to match the session format?
            # Matching session format is hard without keeping the original object.
            # Let's save as a simple list of products, which is easier to read/import later.
            
            with open(self.current_json_file, 'w', encoding='utf-8') as f:
                json.dump({"results": self.json_data}, f, indent=2)
                
            QMessageBox.information(self, "Success", f"Saved {len(self.json_data)} products to {self.current_json_file}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save JSON file: {e}")

    def import_to_database(self):
        """Import current JSON data into the database."""
        if not self.json_mode or not self.json_data:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"Import {len(self.json_data)} products into the database?\nExisting SKUs will be updated.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Use existing logic or direct DB insertion
                # We can use the result_storage module if available, or direct SQL
                
                cursor = self.conn.cursor()
                count = 0
                for item in self.json_data:
                    sku = item.get("SKU")
                    if not sku:
                        continue
                        
                    # Basic upsert logic
                    name = item.get("Name", "")
                    brand = item.get("Brand", "")
                    price = item.get("Price", "")
                    weight = item.get("Weight", "")
                    category = item.get("Category", "")
                    
                    # Check if exists
                    cursor.execute("SELECT SKU FROM products WHERE SKU = ?", (sku,))
                    exists = cursor.fetchone()
                    
                    if exists:
                        cursor.execute("""
                            UPDATE products 
                            SET Name=?, Brand=?, Price=?, Weight=?, Category=?, last_updated=CURRENT_TIMESTAMP
                            WHERE SKU=?
                        """, (name, brand, price, weight, category, sku))
                    else:
                        cursor.execute("""
                            INSERT INTO products (SKU, Name, Brand, Price, Weight, Category, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (sku, name, brand, price, weight, category))
                    count += 1
                    
                self.conn.commit()
                QMessageBox.information(self, "Success", f"Imported/Updated {count} products in database.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import to database: {e}")

    def load_products_data(self, skus):
        """Load product data from database OR JSON for the given SKUs."""
        if not skus:
            return []

        if self.json_mode:
            # Filter json_data for these SKUs
            return [item for item in self.json_data if item.get("SKU") in skus]

        if self.conn is None:
            return []

        try:
            # Ensure UTF-8 handling
            self.conn.text_factory = str
            placeholders = ",".join("?" * len(skus))
            cursor = self.conn.cursor()
            cursor.execute(
                f"""
                SELECT SKU, Brand, Name, Price, Weight, Category, Product_Type, Product_On_Pages, Special_Order, Images, ProductDisabled
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
                    price,
                    weight,
                    category,
                    product_type,
                    product_on_pages,
                    special_order,
                    images,
                    product_disabled,
                ) = row
                # Parse images from comma-separated string
                image_urls = []
                if images:
                    # Split by comma and strip whitespace
                    raw_images = [url.strip() for url in str(images).split(",") if url.strip()]
                    # Convert relative paths to full URLs
                    base_url = "https://www.baystatepet.com/media/"
                    for img in raw_images:
                        if img.startswith("http"):
                            # Already a full URL
                            image_urls.append(img)
                        else:
                            # Convert relative path to full URL
                            image_urls.append(base_url + img)

                # Map database fields to editor format
                # Deduplicate pipe-separated fields
                def deduplicate_pipe_separated(value):
                    """Split by |, remove duplicates while preserving order, rejoin with |"""
                    if not value:
                        return ""
                    parts = [part.strip() for part in str(value).split("|") if part.strip()]
                    unique_parts = list(
                        dict.fromkeys(parts)
                    )  # Preserve order while removing duplicates
                    return "|".join(unique_parts)

                mapped_product = {
                    "SKU": sku,
                    "Name": name or "",
                    "Brand": brand or "",
                    "Price": price or "",
                    "Weight": weight or "",
                    "Special Order": (
                        "yes"
                        if special_order and str(special_order).lower().strip() == "yes"
                        else ""
                    ),
                    "Category": deduplicate_pipe_separated(category),
                    "Product Type": deduplicate_pipe_separated(product_type),
                    "Product On Pages": deduplicate_pipe_separated(product_on_pages),
                    "Image URLs": image_urls,
                    "Product Disabled": product_disabled or "",
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
