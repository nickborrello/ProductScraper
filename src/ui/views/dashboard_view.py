from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

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

    def update_stats(self, total_products, last_update):
        # Find the value label in the card layout (index 1)
        self.total_products_card.layout().itemAt(1).widget().setText(str(total_products))
        self.last_update_card.layout().itemAt(1).widget().setText(last_update)
