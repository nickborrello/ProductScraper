import os
import sys
from typing import Any

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QStackedWidget, QLabel, QFrame, QMessageBox, QApplication
)

from src.ui.styling import apply_dark_theme
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.scraper_view import ScraperView
from src.ui.views.settings_view import SettingsView
from src.ui.results_hub import ResultsHub
from src.ui.widgets import Worker, LogViewer

# Import core logic (kept from original file)
from src.core.settings_manager import settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProductScraper - Professional Edition")
        self.setMinimumSize(1280, 800)
        
        # Apply theme
        apply_dark_theme(QApplication.instance())

        # Initialize worker
        self.worker = None

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        self.create_sidebar()
        
        # Content Area
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("content_area")
        self.main_layout.addWidget(self.content_area)

        # Initialize Views
        self.init_views()
        
        # Set default view
        self.switch_view(0)

    def create_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(180)
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # App Logo/Title - Removed per user request
        title_container = QFrame()
        title_container.setStyleSheet("background-color: transparent; padding: 20px;")
        title_layout = QHBoxLayout(title_container)
        # title_label = QLabel("ProductScraper")  # Removed
        # title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        # title_layout.addWidget(title_label)
        layout.addWidget(title_container)

        # Navigation Buttons
        self.nav_buttons = []
        
        self.add_nav_button("Dashboard", "📊", 0, layout)
        self.add_nav_button("Scraper", "🕸️", 1, layout)
        self.add_nav_button("Results", "🗄️", 2, layout)
        self.add_nav_button("Settings", "⚙️", 3, layout)
        
        layout.addStretch()
        
        # Version Info
        version_label = QLabel("v2.0.0")
        version_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        self.main_layout.addWidget(self.sidebar)

    def add_nav_button(self, text, icon, index, layout):
        btn = QPushButton(f"{icon}  {text}")
        btn.setProperty("class", "sidebar-btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.switch_view(index))
        layout.addWidget(btn)
        self.nav_buttons.append(btn)

    def switch_view(self, index):
        self.content_area.setCurrentIndex(index)
        
        # Update button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        
        # Refresh dashboard when switching to it
        if index == 0:
            self.refresh_dashboard()

    def init_views(self):
        # 0: Dashboard
        self.dashboard_view = DashboardView()
        self.dashboard_view.btn_scrape.clicked.connect(lambda: self.switch_view(1))
        self.dashboard_view.btn_refresh.clicked.connect(self.refresh_dashboard)
        self.content_area.addWidget(self.dashboard_view)

        # 1: Scraper
        self.scraper_view = ScraperView()
        self.scraper_view.start_scraping_signal.connect(self.start_scraping_worker)
        self.scraper_view.cancel_scraping_signal.connect(self.cancel_scraping_worker)
        self.content_area.addWidget(self.scraper_view)

        # 2: Results Hub (formerly Data/ProductViewer)
        self.results_hub = ResultsHub()
        self.content_area.addWidget(self.results_hub)

        # 3: Settings
        self.settings_view = SettingsView()
        self.content_area.addWidget(self.settings_view)

    # Worker Logic (Adapted from original)
    def start_scraping_worker(self, file_path, selected_scrapers=None, items_to_scrape=None):
        import threading
        from src.scrapers.main import run_scraping
        
        self.scraper_view.log_message(f"Starting scrape for {file_path}...", "INFO")
        if selected_scrapers:
            self.scraper_view.log_message(f"Selected scrapers: {', '.join(selected_scrapers)}", "INFO")
        
        # Create stop event
        self.stop_event = threading.Event()
        
        # Create worker
        self.worker = Worker(
            run_scraping, 
            file_path=file_path,
            selected_sites=selected_scrapers,
            items_to_scrape=items_to_scrape,
            stop_event=self.stop_event
        )
        
        # Connect signals
        self.worker.signals.log.connect(self.scraper_view.log_message)
        self.worker.signals.progress.connect(self.scraper_view.update_progress)
        self.worker.signals.status.connect(self.scraper_view.update_status)
        self.worker.signals.finished.connect(self.on_scraping_finished)
        self.worker.signals.error.connect(self.on_scraping_error)
        
        self.worker.start()

    def cancel_scraping_worker(self):
        if self.worker and self.worker.isRunning():
            self.scraper_view.log_message("Cancelling...", "WARNING")
            if hasattr(self, 'stop_event'):
                self.stop_event.set()
            self.worker.cancel()

    def on_scraping_finished(self):
        self.scraper_view.on_scraping_finished()
        self.scraper_view.log_message("Scraping process finished.", "SUCCESS")
        
        # Refresh dashboard stats after scraping
        self.refresh_dashboard()
    
    def refresh_dashboard(self):
        """Refresh the dashboard stats."""
        self.dashboard_view.refresh_stats()

    def on_scraping_error(self, error_info):
        exc_type, exc_value, exc_traceback = error_info
        self.scraper_view.log_message(f"Error: {exc_value}", "ERROR")
        self.scraper_view.on_scraping_finished() # Reset UI state
