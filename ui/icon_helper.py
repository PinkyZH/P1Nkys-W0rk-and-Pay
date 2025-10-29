# ui/icon_helper.py
from __future__ import annotations

import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle

# Optional: falls du später echte SVG/PNG-Assets ablegen willst
_ASSET_DIRS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons"),
]

# Fallback-Mapping auf Qt-Standard-Icons
_STD = {
    "new": QStyle.SP_FileDialogNewFolder,
    "add": QStyle.SP_DialogYesButton,
    "delete": QStyle.SP_TrashIcon,
    "refresh": QStyle.SP_BrowserReload,
    "pdf": QStyle.SP_DriveDVDIcon,
    "excel": QStyle.SP_DriveHDIcon,
    "csv_export": QStyle.SP_ArrowRight,
    "csv_import": QStyle.SP_ArrowLeft,
    "save": QStyle.SP_DialogSaveButton,
    "open": QStyle.SP_DialogOpenButton,
    "edit": QStyle.SP_FileDialogContentsView,
    "search": QStyle.SP_FileDialogListView,
    "settings": QStyle.SP_FileDialogDetailedView,
    "calendar": QStyle.SP_ComputerIcon,
    "stats": QStyle.SP_DesktopIcon,
    "payroll": QStyle.SP_DirHomeIcon,
    "rules": QStyle.SP_BrowserStop,
    "user": QStyle.SP_DirIcon,
    "admin": QStyle.SP_DirOpenIcon,
    "notify": QStyle.SP_MessageBoxInformation,
    "absence": QStyle.SP_MessageBoxQuestion,
    "approve": QStyle.SP_DialogApplyButton,
    "reject": QStyle.SP_DialogCancelButton,
    "logout": QStyle.SP_DialogCloseButton,
    "login": QStyle.SP_DialogOkButton,
    "print": QStyle.SP_FileIcon,
}


def _try_load_from_assets(name: str) -> QIcon | None:
    filename_variants = [f"{name}.svg", f"{name}.png", f"{name}.ico"]
    for base in _ASSET_DIRS:
        for fn in filename_variants:
            p = os.path.join(base, fn)
            if os.path.isfile(p):
                return QIcon(p)
    return None


def icon(name: str) -> QIcon:
    # 1) Optional Assets
    ic = _try_load_from_assets(name.lower())
    if ic is not None:
        return ic
    # 2) Qt-Standardicon
    style = QApplication.instance().style()
    sp = _STD.get(name.lower(), QStyle.SP_FileIcon)
    return style.standardIcon(sp)
