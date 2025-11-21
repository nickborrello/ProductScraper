import os
import shutil

import win32com.client

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

gen_py_cache = os.path.join(str(os.getenv("LOCALAPPDATA")), "Temp", "gen_py")
if os.path.exists(gen_py_cache):
    print(f"🧹 Detected corrupted COM cache. Removing: {gen_py_cache}")
    shutil.rmtree(gen_py_cache, ignore_errors=True)


def convert_xlsx_to_xls_with_excel(results_folder=None):
    # Use session-specific results folder or default to global spreadsheets folder
    if results_folder is not None:
        assert isinstance(results_folder, str)
        folder = os.path.join(results_folder, "data")
    else:
        folder = os.path.join(PROJECT_ROOT, "src", "data", "spreadsheets")
    # Check if output folder exists
    if not os.path.exists(folder):
        print(f"⚠️ Output folder not found: {folder}")
        return

    try:
        excel = win32com.client.Dispatch("Excel.Application")
        # Try to set visibility, but don't fail if it doesn't work
        try:
            excel.Visible = False
        except AttributeError:
            print(
                "⚠️ Could not set Excel visibility (this is usually fine for background processing)"
            )

        converted_count = 0
        for filename in os.listdir(folder):
            if filename.endswith(".xlsx") and not filename.startswith("~$"):
                xlsx_path = os.path.join(folder, filename)
                xls_path = os.path.join(folder, filename.replace(".xlsx", ".xls"))
                try:
                    wb = excel.Workbooks.Open(xlsx_path)
                    wb.SaveAs(xls_path, FileFormat=56)  # 56 = Excel 97-2003 Workbook (*.xls)
                    wb.Close(False)
                    os.remove(xlsx_path)
                    print(f"✅ Converted and deleted: {filename} → {os.path.basename(xls_path)}")
                    converted_count += 1
                except Exception as e:
                    print(f"❌ Error converting {filename}: {e}")

        excel.Quit()

        if converted_count == 0:
            print("ℹ️ No .xlsx files found to convert")
        else:
            print(f"✅ Successfully converted {converted_count} files")

    except Exception as e:
        print(f"❌ Excel conversion failed: {e}")
        print("💡 This might be due to Excel not being installed or COM issues")
        print("   The .xlsx files will remain in the output folder")


if __name__ == "__main__":
    convert_xlsx_to_xls_with_excel()
