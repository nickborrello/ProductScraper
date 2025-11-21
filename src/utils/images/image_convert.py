import os
from tkinter import Tk, filedialog

from PIL import Image


def select_folder():
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder_selected = filedialog.askdirectory(title="Select Folder with Images")
    root.destroy()
    return folder_selected


def process_and_replace_image(path):
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            width, height = img.size

            # Resize proportionally to fit inside 1000x1000
            if width > height:
                new_width = 1000
                new_height = int((height / width) * 1000)
            else:
                new_height = 1000
                new_width = int((width / height) * 1000)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Create white background canvas
            new_img = Image.new("RGB", (1000, 1000), (255, 255, 255))
            paste_x = (1000 - new_width) // 2
            paste_y = (1000 - new_height) // 2
            new_img.paste(img, (paste_x, paste_y))

            # Force save as .jpg and overwrite original
            save_path = os.path.splitext(path)[0] + ".jpg"
            new_img.save(save_path, "JPEG", quality=95)

            if save_path != path:
                os.remove(path)

            print(f"✅ Converted: {path} -> {save_path}")
    except Exception as e:
        print(f"❌ Failed to convert {path}: {e}")


def convert_all_images(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")):
                process_and_replace_image(os.path.join(root, file))


if __name__ == "__main__":
    folder = select_folder()
    if folder:
        print(f"📂 Processing folder: {folder}")
        convert_all_images(folder)
    else:
        print("❌ No folder selected.")
