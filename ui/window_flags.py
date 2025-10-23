# workpay/ui/window_flags.py
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

def apply_window_controls(w: QWidget, *, size_grip: bool = True, maximized: bool | None = None) -> None:
    """
    Aktiviert für Dialog-Fenster Min/Max/Close-Buttons.
    Optional: SizeGrip und Startzustand (maximized=True/False/None).
    Usage: direkt nach setWindowTitle(...) aufrufen.
    """
    flags = w.windowFlags()
    flags |= Qt.WindowMinimizeButtonHint
    flags |= Qt.WindowMaximizeButtonHint
    flags |= Qt.WindowCloseButtonHint
    # manche Dialoge laufen als Sheet/Tool => sicherstellen, dass sie "Window" sind
    flags |= Qt.Window
    w.setWindowFlags(flags)
    if size_grip and hasattr(w, "setSizeGripEnabled"):
        try: w.setSizeGripEnabled(True)
        except Exception: pass
    if maximized is True:
        w.showMaximized()
    elif maximized is False:
        w.showNormal()
