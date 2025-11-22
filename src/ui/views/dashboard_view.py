import os
import sqlite3
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        
        # Database path setup
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        self.db_path = Path(project_root) / "data" / "databases" / "products.db"
        
        self.init_ui()
        self.refresh_stats()  # Load initial stats

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("Dashboard")
        header.setProperty("class", "h1")
        layout.addWidget(header)

        # Stats Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        self.total_products_card = self.create_stat_card("Total Products", "0", "📦")
        self.last_update_card = self.create_stat_card("Last Update", "Never", "🕒")
        self.active_scrapers_card = self.create_stat_card("Active Scrapers", "0", "🤖")

        stats_layout.addWidget(self.total_products_card)
        stats_layout.addWidget(self.last_update_card)
        stats_layout.addWidget(self.active_scrapers_card)
        layout.addLayout(stats_layout)

        # Recent Activity Section
        activity_label = QLabel("Recent Activity")
        activity_label.setProperty("class", "h2")
        layout.addWidget(activity_label)

        self.activity_list = QFrame()
        self.activity_list.setProperty("class", "card")
        activity_layout = QVBoxLayout(self.activity_list)
        no_activity_lbl = QLabel("No recent activity")
        no_activity_lbl.setProperty("class", "subtitle")
        activity_layout.addWidget(no_activity_lbl)
        activity_layout.addStretch()
        layout.addWidget(self.activity_list)

        # Quick Actions
        actions_label = QLabel("Quick Actions")
        actions_label.setProperty("class", "h2")
        layout.addWidget(actions_label)

        actions_layout = QHBoxLayout()
        
        self.btn_scrape = QPushButton("Start New Scrape")
        self.btn_scrape.setProperty("class", "primary")
        
        self.btn_refresh = QPushButton("Refresh Database")
        
        actions_layout.addWidget(self.btn_scrape)
        actions_layout.addWidget(self.btn_refresh)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        layout.addStretch()

    def create_stat_card(self, title, value, icon):
        card = QFrame()
        card.setProperty("class", "card")
        # card.setMinimumHeight(100) # Removed fixed height
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15) # Add some padding
        
        title_lbl = QLabel(f"{icon} {title}")
        title_lbl.setProperty("class", "subtitle")
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(value_lbl)
        # card_layout.addStretch() # Removed stretch
        
        return card

    def refresh_stats(self):
        """Load and update stats from the database."""
        # Check if database exists
        if not self.db_path.exists():
            self.update_stats(0, "No database")
            return
        
        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total products
            cursor.execute("SELECT COUNT(*) FROM products")
            total_products = cursor.fetchone()[0]
            
            # Get last update date
            cursor.execute("SELECT MAX(last_updated) FROM products")
            last_update_raw = cursor.fetchone()[0]
            
            # Format last update
            if last_update_raw:
                # Extract just the date part if it's a datetime string
                last_update = last_update_raw.split()[0] if ' ' in last_update_raw else last_update_raw
            else:
                last_update = "Never"
            
            conn.close()
            
            # Update the UI
            self.update_stats(total_products, last_update)
            
        except Exception as e:
            print(f"Error refreshing dashboard stats: {e}")
            self.update_stats(0, "Error")
    
    def update_stats(self, total_products, last_update):
        """Update the stat card displays."""
        # Find the value label in the card layout (index 1)
        self.total_products_card.layout().itemAt(1).widget().setText(str(total_products))
        self.last_update_card.layout().itemAt(1).widget().setText(last_update)
