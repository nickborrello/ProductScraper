from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFrame, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path
from src.ui.widgets import LogViewer
from src.scrapers.parser.yaml_parser import ScraperConfigParser
import pandas as pd

class ScraperView(QWidget):
    # Signals to communicate with MainWindow
    start_scraping_signal = pyqtSignal(str, list, list) # file_path, selected_scrapers, items_to_scrape
    cancel_scraping_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.parser = ScraperConfigParser()
        self.items_to_scrape = []
        self.init_ui()
        self.load_scrapers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFrame, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QCheckBox, QStackedWidget, QSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from pathlib import Path
import pandas as pd
import os
from src.ui.widgets import LogViewer
from src.scrapers.parser.yaml_parser import ScraperConfigParser
from src.core.settings_manager import settings

class ScraperView(QWidget):
    # Signals to communicate with MainWindow
    start_scraping_signal = pyqtSignal(str, list, list) # file_path, selected_scrapers, items_to_scrape
    cancel_scraping_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.parser = ScraperConfigParser()
        self.items_to_scrape = []
        self.init_ui()
        self.load_scrapers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 10, 10, 10)

        # Main Content Splitter (3 Columns)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel: Configuration ---
        left_panel = QWidget()
        left_panel.setMaximumWidth(300)  # Fix sidebar width
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(10)
        
        # File Selection
        file_group = QFrame()
        file_group.setProperty("class", "card")
        file_layout = QVBoxLayout(file_group)
        file_layout.addWidget(QLabel("<b>1. Input File</b>"))
        
        self.btn_select_file = QPushButton("📂 Select Excel")
        self.btn_select_file.clicked.connect(self.select_file)
        file_layout.addWidget(self.btn_select_file)
        
        self.lbl_selected_file = QLabel("No file selected")
        self.lbl_selected_file.setProperty("class", "subtitle")
        self.lbl_selected_file.setWordWrap(True)
        file_layout.addWidget(self.lbl_selected_file)
        left_layout.addWidget(file_group)

        # Scraper Selection
        scraper_group = QFrame()
        scraper_group.setProperty("class", "card")
        scraper_layout = QVBoxLayout(scraper_group)
        scraper_layout.addWidget(QLabel("<b>2. Scrapers</b>"))
        
        self.scraper_list = QListWidget()
        self.scraper_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        scraper_layout.addWidget(self.scraper_list)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_scrapers)
        scraper_layout.addWidget(refresh_btn)
        left_layout.addWidget(scraper_group)

        # Settings Group
        settings_group = QFrame()
        settings_group.setProperty("class", "card")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.addWidget(QLabel("<b>3. Settings</b>"))

        # Max Workers
        workers_layout = QHBoxLayout()
        workers_layout.addWidget(QLabel("Max Workers:"))
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 10)
        self.spin_workers.setValue(settings.get("max_workers", 2))
        self.spin_workers.valueChanged.connect(lambda v: settings.set("max_workers", v))
        workers_layout.addWidget(self.spin_workers)
        settings_layout.addLayout(workers_layout)

        # Headless Mode
        self.chk_headless = QCheckBox("Headless Mode")
        self.chk_headless.setChecked(settings.get("selenium_headless", True))
        self.chk_headless.toggled.connect(lambda v: settings.set("selenium_headless", v))
        settings_layout.addWidget(self.chk_headless)

        left_layout.addWidget(settings_group)
        
        # Actions
        action_layout = QVBoxLayout()
        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.clicked.connect(self.start_scraping)
        self.btn_start.setEnabled(False)

        self.btn_cancel = QPushButton("⏹ Stop")
        self.btn_cancel.setProperty("class", "danger")
        self.btn_cancel.clicked.connect(self.cancel_scraping)
        self.btn_cancel.setEnabled(False)
        
        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_cancel)
        left_layout.addLayout(action_layout)
        
        splitter.addWidget(left_panel)

        # --- Right Panel: Dynamic Content (Stack) ---
        self.right_panel_stack = QStackedWidget()
        
        # Page 0: Preview Table
        preview_page = QWidget()
        preview_layout = QVBoxLayout(preview_page)
        preview_layout.setContentsMargins(5, 0, 5, 0)
        
        preview_group = QFrame()
        preview_group.setProperty("class", "card")
        preview_group_layout = QVBoxLayout(preview_group)
        
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("<b>3. Data Preview</b>"))
        preview_header.addStretch()
        
        self.btn_select_all = QPushButton("☑ Select All")
        self.btn_select_all.clicked.connect(self.select_all_items)
        self.btn_select_all.setEnabled(False)
        preview_header.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("☐ Deselect All")
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        self.btn_deselect_all.setEnabled(False)
        preview_header.addWidget(self.btn_deselect_all)

        self.btn_delete_selected = QPushButton("🗑️ Delete Selected")
        self.btn_delete_selected.clicked.connect(self.delete_selected_items)
        self.btn_delete_selected.setEnabled(False)
        preview_header.addWidget(self.btn_delete_selected)
        preview_group_layout.addLayout(preview_header)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["", "SKU", "Name", "Price"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        preview_group_layout.addWidget(self.preview_table)
        
        preview_layout.addWidget(preview_group)
        self.right_panel_stack.addWidget(preview_page)

        # Page 1: Logs & Progress
        logs_page = QWidget()
        logs_layout = QVBoxLayout(logs_page)
        logs_layout.setContentsMargins(5, 0, 0, 0)

        # Progress
        progress_group = QFrame()
        progress_group.setProperty("class", "card")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        
        progress_layout.addWidget(QLabel("Status"))
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        logs_layout.addWidget(progress_group)

        # Logs
        logs_label = QLabel("Live Logs")
        logs_label.setProperty("class", "h2")
        logs_layout.addWidget(logs_label)
        
        self.log_viewer = LogViewer()
        logs_layout.addWidget(self.log_viewer)
        
        self.right_panel_stack.addWidget(logs_page)
        
        splitter.addWidget(self.right_panel_stack)
        
        # Set Stretch Factors (Config: 0, Main: 1) - Let max width handle left panel
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)

        self.selected_file_path = None

    def update_status(self, text):
        self.status_label.setText(text)

    def log_message(self, message, level="INFO"):
        self.log_viewer.log(message, level)

    def load_scrapers(self):
        """Load available scrapers into the list widget."""
        self.scraper_list.clear()
        configs_dir = Path("src/scrapers/configs")
        if not configs_dir.exists():
            return

        try:
            for config_file in configs_dir.glob("*.yaml"):
                if config_file.name == "sample_config.yaml":
                    continue
                try:
                    config = self.parser.load_from_file(str(config_file))
                    item = QListWidgetItem(config.name)
                    item.setData(Qt.ItemDataRole.UserRole, config.name)
                    self.scraper_list.addItem(item)
                except Exception as e:
                    print(f"Error loading {config_file}: {e}")
        except Exception as e:
            self.log_message(f"Error loading scrapers: {e}", "ERROR")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.lbl_selected_file.setText(os.path.basename(file_path))
            self.btn_start.setEnabled(True)
            self.load_preview_data(file_path)

    def load_preview_data(self, file_path):
        """Load Excel data into the preview table."""
        try:
            df = pd.read_excel(file_path)
            
            # Normalize columns
            df.columns = df.columns.str.strip()
            
            # Determine SKU column
            sku_col = None
            if 'SKU_NO' in df.columns:
                sku_col = 'SKU_NO'
            elif 'SKU' in df.columns:
                sku_col = 'SKU'
            else:
                sku_col = df.columns[0] # Fallback
            
            # Determine Name/Description
            # User requested "combined Descriptions should be called the Name"
            name_col = 'Name'
            if 'DESCRIPTION1' in df.columns and 'DESCRIPTION2' in df.columns:
                df['Name'] = df['DESCRIPTION1'].fillna('') + ' ' + df['DESCRIPTION2'].fillna('')
            elif 'DESCRIPTION1' in df.columns:
                df['Name'] = df['DESCRIPTION1']
            elif 'Description' in df.columns:
                df['Name'] = df['Description']
            elif 'Name' in df.columns:
                pass # Already has Name
            else:
                 df['Name'] = ""

            # Determine Price Column
            price_col = None
            for col in df.columns:
                if col.upper() in ['PRICE', 'COST', 'MSRP', 'RETAIL_PRICE', 'RETAIL', 'LIST_PRICE']:
                    price_col = col
                    break

            self.items_to_scrape = []
            self.preview_table.setRowCount(0)
            
            for index, row in df.iterrows():
                sku = str(row[sku_col])
                name = str(row.get('Name', ''))
                price = str(row[price_col]) if price_col and pd.notna(row[price_col]) else ""
                
                self.items_to_scrape.append({
                    'sku': sku,
                    'description': name, # Keep key as description for compatibility, or add name
                    'name': name,
                    'price': price,
                    'search_term': sku 
                })
                
                row_idx = self.preview_table.rowCount()
                self.preview_table.insertRow(row_idx)
                
                # Checkbox
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                chk_item.setCheckState(Qt.CheckState.Checked)
                self.preview_table.setItem(row_idx, 0, chk_item)
                
                # SKU
                self.preview_table.setItem(row_idx, 1, QTableWidgetItem(sku))
                
                # Name
                # Store the full item data in the UserRole of the name item for easy retrieval
                name_item = QTableWidgetItem(name)
                name_item.setData(Qt.ItemDataRole.UserRole, self.items_to_scrape[-1])
                self.preview_table.setItem(row_idx, 2, name_item)

                # Price
                self.preview_table.setItem(row_idx, 3, QTableWidgetItem(price))

            self.btn_delete_selected.setEnabled(True)
            self.btn_select_all.setEnabled(True)
            self.btn_deselect_all.setEnabled(True)
            # Ensure we are on the preview page
            self.right_panel_stack.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Excel file:\n{str(e)}")
            self.lbl_selected_file.setText("Error loading file")
            self.selected_file_path = None
            self.btn_start.setEnabled(False)

    def select_all_items(self):
        """Check all items in the table."""
        for row in range(self.preview_table.rowCount()):
            item = self.preview_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def deselect_all_items(self):
        """Uncheck all items in the table."""
        for row in range(self.preview_table.rowCount()):
            item = self.preview_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def delete_selected_items(self):
        """Remove selected rows from the table."""
        selected_rows = sorted(set(index.row() for index in self.preview_table.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            return

        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to remove {len(selected_rows)} items from the list?\n(This does not affect the original Excel file)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for row in selected_rows:
                self.preview_table.removeRow(row)

    def start_scraping(self):
        if not self.selected_file_path:
            return

        selected_items = self.scraper_list.selectedItems()
        selected_scrapers = [item.text() for item in selected_items]
        
        # Gather items from table
        items_to_scrape = []
        for row in range(self.preview_table.rowCount()):
            chk_item = self.preview_table.item(row, 0)
            if chk_item.checkState() == Qt.CheckState.Checked:
                # Retrieve data from the description item (column 2)
                item_data = self.preview_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
                if item_data:
                    items_to_scrape.append(item_data)
        
        if not items_to_scrape:
             QMessageBox.warning(self, "No Items", "No items selected for scraping.")
             return

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_select_file.setEnabled(False)
        self.scraper_list.setEnabled(False)
        self.preview_table.setEnabled(False)
        self.btn_delete_selected.setEnabled(False)
        self.btn_select_all.setEnabled(False)
        self.btn_deselect_all.setEnabled(False)
        
        # Switch to Logs View
        self.right_panel_stack.setCurrentIndex(1)
        
        self.start_scraping_signal.emit(self.selected_file_path, selected_scrapers, items_to_scrape)

    def cancel_scraping(self):
        self.cancel_scraping_signal.emit()
        self.btn_cancel.setEnabled(False)
        # Switch back to Preview View
        self.right_panel_stack.setCurrentIndex(0)

    def on_scraping_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_select_file.setEnabled(True)
        self.scraper_list.setEnabled(True)
        self.preview_table.setEnabled(True)
        self.btn_delete_selected.setEnabled(True)
        self.btn_select_all.setEnabled(True)
        self.btn_deselect_all.setEnabled(True)
        # Switch back to Preview View
        self.right_panel_stack.setCurrentIndex(0)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, text):
        self.status_label.setText(text)

    def log_message(self, message, level="INFO"):
        self.log_viewer.log(message, level)
