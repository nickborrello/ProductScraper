# PyQt6 UI Development Guide for ProductScraper

## Extension Setup
- **Qt Designer Path**: `C:\Users\Nick\AppData\Roaming\Python\Python313\site-packages\qt6_applications\Qt\bin\designer.exe`
- **UI Files Location**: `./ui_designs/` directory
- **Compiled UI Output**: `./src/ui/` directory

## Workflow for UI Development

### 1. Create New UI Form
1. Right-click in Explorer → "PYQT: New Form"
2. Design your interface in Qt Designer
3. Save as `.ui` file in `./ui_designs/`
4. Right-click `.ui` file → "PYQT: Compile Form"
5. Generated `.py` file appears in configured output path

### 2. Edit Existing UI
1. Right-click `.ui` file → "PYQT: Edit In Designer"
2. Make changes and save
3. Recompile to update Python code

### 3. Preview UI
- Right-click `.ui` file → "PYQT: Preview"

## VSCode Settings Configuration

The following settings have been configured in `.vscode/settings.json`:
```json
{
    "pyqt-integration.qtdesigner.path": "C:\\Users\\Nick\\AppData\\Roaming\\Python\\Python313\\site-packages\\qt6_applications\\Qt\\bin\\designer.exe",
    "pyqt-integration.pyuic.cmd": "pyuic6",
    "pyqt-integration.pyuic.compile.filepath": "${workspace}\\src\\ui\\Ui_${ui_name}.py",
    "pyqt-integration.pyuic.compile.addOptions": "-x",
    "pyqt-integration.pyrcc.cmd": "pyrcc6",
    "pyqt-integration.pyrcc.compile.filepath": "${workspace}\\src\\ui\\${qrc_name}_rc.py"
}
```

## Current UI Files to Potentially Redesign
- `product_viewer.py` - Database product browser
- `product_classify_ui.py` - Classification interface
- `product_creator_ui.py` - Product creation tool
- `product_cross_sell_ui.py` - Cross-sell management
- `product_editor.py` - Product editing interface

## Benefits of Using Qt Designer
- Visual drag-and-drop interface design
- Automatic Python code generation
- Professional UI layouts
- Easy maintenance and updates
- Separation of UI design from business logic