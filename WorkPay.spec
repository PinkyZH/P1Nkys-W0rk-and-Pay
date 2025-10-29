# WorkPay.spec – PyInstaller Build-Konfiguration für Windows
# Baue mit:  pyinstaller WorkPay.spec

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

proj_root = Path(__file__).parent

entry_script = str(proj_root / "app.py")
app_name = "WorkPay"

# -------- Daten/Assets sammeln (allgemein) --------
datas = []

# Übliche Ressource-Ordner im Root
for p in ["i18n", "lang", "locale", "locales", "translations", "assets", "resources", "res", "icons", "images", "ui_files", "core_files":]
    d = proj_root / p
    if d.exists():
        datas.append((str(d), p))

# Einzelne Konfigurationen im Root (optional)
for cfg in ["config.ini", "settings.ini", "config.yaml", "settings.yaml"]:
    f = proj_root / cfg
    if f.exists():
        datas.append((str(f), "."))

# -------- Paket-spezifische Daten (PySide6 / Matplotlib / ReportLab / OpenPyXL) --------
datas += collect_data_files("PySide6", include_py_files=False)
binaries = collect_dynamic_libs("PySide6")

# ReportLab/OpenPyXL/Matplotlib – Fonts, Backends, Templates etc.
datas += collect_data_files("reportlab", include_py_files=True)
datas += collect_data_files("openpyxl", include_py_files=True)
datas += collect_data_files("matplotlib", include_py_files=True)

# -------- Deine lokalen Pakete `ui` und `core` vollständig einbinden --------
# 1) Python-Module: über hiddenimports sicherheitshalber erzwingen
hiddenimports = []
for pkg in ["core", "ui", "sqlalchemy", "sqlalchemy.dialects", "sqlalchemy.ext",
            "PySide6", "matplotlib"]:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# 2) Nicht-Python-Dateien innerhalb core/ und ui/ als Daten beilegen
#    (Python-Dateien werden von PyInstaller ohnehin als Module gebündelt.)
def add_tree_as_data(folder_name: str):
    folder = proj_root / folder_name
    if folder.exists():
        # alles außer Python-Quellen & __pycache__
        from PyInstaller.building.build_main import TOC
        from PyInstaller.building.datastruct import Tree
        datas_tree = Tree(
            str(folder),
            prefix=folder_name,  # im Bundle unter gleichem Pfad
            excludes=["*.py", "*.pyc", "*.pyo", "__pycache__"]
        )
        return datas_tree
    return None

ui_tree  = add_tree_as_data("ui")
core_tree = add_tree_as_data("core")

block_cipher = None

a = Analysis(
    [entry_script],
    pathex=[str(proj_root)],
    binaries=binaries,
    datas=datas,           # allgemeine Daten
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# EXE (fensterbasiert; falls Konsole gewünscht -> console=True)
exe = EXE(
    a.pure,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    icon=str(proj_root / "assets" / "icon.ico") if (proj_root / "assets" / "icon.ico").exists() else None,
)

# Alles einsammeln (inkl. der Bäume für core/ui Nicht-Python)
collected = [exe, a.binaries, a.zipfiles, a.datas]
if ui_tree:
    collected.append(ui_tree)
if core_tree:
    collected.append(core_tree)

coll = COLLECT(
    *collected,
    name=app_name
)
