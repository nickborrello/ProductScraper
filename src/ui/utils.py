import os
import sys
from PyQt6.QtWidgets import QApplication, QFileDialog

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def select_excel_file():
    """Select an Excel file using GUI dialog if available, otherwise text-based."""
    try:
        # Create a minimal QApplication if one doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Excel File",
            os.path.join(PROJECT_ROOT, "src", "data", "spreadsheets"),
            "Excel Files (*.xlsx *.xls);;All Files (*)",
        )

        # Don't quit the app if it was created just for this dialog
        if app and len(app.allWidgets()) == 0:
            app.quit()

        return file_path if file_path else None
    except Exception as e:
        print(f"❌ PyQt6 dialog failed: {e}")
        print("💡 Falling back to text-based file selection...")
        return select_excel_file_text()


def select_excel_file_text():
    """Text-based file selection fallback when GUI is not available."""
    input_dir = os.path.join(PROJECT_ROOT, "src", "data", "spreadsheets")
    print(f"📁 Looking for Excel files in: {input_dir}")

    # List available Excel files
    if os.path.exists(input_dir):
        excel_files = [
            f for f in os.listdir(input_dir) if f.endswith((".xlsx", ".xls"))
        ]
        if excel_files:
            print("📁 Available Excel files:")
            for i, file in enumerate(excel_files, 1):
                print(f"  {i}. {file}")
            print("  0. Enter custom path")

            while True:
                try:
                    choice = input(
                        "➤ Select file number or enter custom path: "
                    ).strip()
                    if choice == "0":
                        file_path = input("➤ Enter full path to Excel file: ").strip()
                        if file_path and os.path.exists(file_path):
                            return file_path
                        else:
                            print("❌ File not found. Try again.")
                    elif choice.isdigit() and 1 <= int(choice) <= len(excel_files):
                        file_path = os.path.join(
                            input_dir, excel_files[int(choice) - 1]
                        )
                        return file_path
                    else:
                        print("❌ Invalid choice. Try again.")
                except KeyboardInterrupt:
                    return None
        else:
            print("❌ No Excel files found in input directory.")
    else:
        print(f"❌ Input directory not found: {input_dir}")

    # Fallback to manual path entry
    while True:
        try:
            file_path = input(
                "➤ Enter full path to Excel file (or press Enter to cancel): "
            ).strip()
            if not file_path:
                return None
            if os.path.exists(file_path):
                return file_path
            else:
                print("❌ File not found. Try again.")
        except KeyboardInterrupt:
            return None
