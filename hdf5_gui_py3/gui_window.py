"""Main window composition for the HDF5 export GUI."""

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget, QWidget

from gui_export import ExportMixin
from gui_history import HistoryMixin
from gui_home import HomeTabMixin
from gui_style import WindowStyleMixin


class Window(ExportMixin, HistoryMixin, HomeTabMixin, WindowStyleMixin, QTabWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle('HDF5 GUI')
        self.resize(1200, 750)
        self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
        self.setup_database()
        self.set_style()

        self.current_kunde_filter = ""
        self.current_datum_filter = ""

        self.tab_home = QWidget()
        self.tab_history = QWidget()
        self.addTab(self.tab_home, "Anfrage")
        self.addTab(self.tab_history, "Historie")

        self.home()
        self.history_ui()
