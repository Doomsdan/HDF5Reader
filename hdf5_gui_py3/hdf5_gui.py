"""Compatibility entry point for the HDF5 GUI.

The implementation is split into focused modules:
- gui_sql.py: SQL query builders
- gui_streams.py: stdout/stderr bridge
- gui_widgets.py: reusable widgets and dialogs
- gui_window.py: main application window
"""

import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import lauchaecker_config as lconf
from gui_sql import *
from gui_streams import XStream
from gui_widgets import AddressBookDialog, CalendarDialog, CustomerCompleter, TransferList
from gui_window import Window


__all__ = [
    "QtCore",
    "QtGui",
    "QtWidgets",
    "QObject",
    "pyqtSignal",
    "QApplication",
    "QCalendarWidget",
    "QComboBox",
    "QDialog",
    "QFileDialog",
    "QGridLayout",
    "QHeaderView",
    "QLabel",
    "QLineEdit",
    "QPushButton",
    "QTabWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QTextBrowser",
    "QVBoxLayout",
    "QWidget",
    "lconf",
    "sql_param",
    "create_kunden_table_sql",
    "create_anfragen_table_sql",
    "history_query",
    "customer_names_query",
    "insert_customer_query",
    "customer_id_query",
    "insert_anfrage_query",
    "XStream",
    "TransferList",
    "CustomerCompleter",
    "AddressBookDialog",
    "CalendarDialog",
    "Window",
]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Window()
    main.show()
    sys.exit(app.exec_())
