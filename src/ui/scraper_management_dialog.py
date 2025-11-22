        for selector in config.selectors:
            details += f"  • {selector.name}: '{selector.selector}'"
            if selector.attribute:
                details += f" → {selector.attribute}"
            if selector.multiple:
                details += " (multiple)"
            details += "\n"

        details += f"\n⚙️ Workflows ({len(config.workflows)}):\n"
        for i, workflow in enumerate(config.workflows, 1):
            details += f"  {i}. {workflow.action}: {workflow.params}\n"

        if config.login is not None:
            details += "\n🔐 Login Configuration:\n"
            details += f"  URL: {config.login.url}\n"
            details += f"  Username field: {config.login.username_field}\n"
            details += f"  Password field: {config.login.password_field}\n"
            details += f"  Submit button: {config.login.submit_button}\n"
            if config.login.success_indicator:
                details += f"  Success indicator: {config.login.success_indicator}\n"

        self.details_text.setPlainText(details)

    def add_scraper(self):
        """Open dialog to add a new scraper."""
        dialog = AddScraperDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_scrapers()  # Refresh the list

    def edit_selected_scraper(self):
        """Edit the selected scraper."""
        selected_items = self.scraper_list.selectedItems()
        if not selected_items:
            return

        scraper_name = selected_items[0].text().replace("📄 ", "").replace("❌ ", "")
        if scraper_name not in self.scraper_configs:
            QMessageBox.warning(
                self,
                "Error",
                f"Cannot edit '{scraper_name}': configuration not loaded.",
            )
            return

        config_data = self.scraper_configs[scraper_name]
        dialog = EditScraperDialog(config_data["config"], config_data["file_path"], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_scrapers()  # Refresh the list

    def delete_selected_scraper(self):
        """Delete the selected scraper."""
        selected_items = self.scraper_list.selectedItems()
        if not selected_items:
            return

        scraper_name = selected_items[0].text().replace("📄 ", "").replace("❌ ", "")

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the scraper '{scraper_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if scraper_name in self.scraper_configs:
                    file_path = self.scraper_configs[scraper_name]["file_path"]
                    os.remove(file_path)
                    QMessageBox.information(
                        self, "Success", f"Scraper '{scraper_name}' has been deleted."
                    )
                    self.load_scrapers()  # Refresh the list
                else:
                    QMessageBox.warning(self, "Error", f"Scraper '{scraper_name}' not found.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete scraper: {e!s}")
