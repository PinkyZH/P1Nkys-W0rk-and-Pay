# workpay/ui/common.py
from PySide6.QtWidgets import QMessageBox, QWidget

def info(parent: QWidget, title: str, text: str):
    QMessageBox.information(parent, title, text)

def warn(parent: QWidget, title: str, text: str):
    QMessageBox.warning(parent, title, text)

def error(parent: QWidget, title: str, err: Exception | str):
    QMessageBox.critical(parent, title, str(err))
