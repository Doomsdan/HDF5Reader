"""Main window composition for the HDF5 export GUI."""

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabBar, QTabWidget, QToolButton, QWidget

from gui_export import ExportMixin
from gui_history import HistoryMixin
from gui_home import HomeTabMixin
from gui_settings import SettingsMixin
from gui_style import WindowStyleMixin


class MainTabBar(QTabBar):
    """Tab bar that can keep internal pages out of the visible tab strip."""

    def __init__(self, parent=None):
        super(MainTabBar, self).__init__(parent)
        self.hidden_page_indices = set()

    def hide_page_tab(self, index):
        self.hidden_page_indices.add(index)
        self.setTabVisible(index, False)
        self.updateGeometry()

    def tabSizeHint(self, index):
        if index in self.hidden_page_indices:
            return QtCore.QSize(0, 0)
        return super(MainTabBar, self).tabSizeHint(index)

    def minimumTabSizeHint(self, index):
        if index in self.hidden_page_indices:
            return QtCore.QSize(0, 0)
        return super(MainTabBar, self).minimumTabSizeHint(index)


class Window(
    ExportMixin,
    HistoryMixin,
    HomeTabMixin,
    SettingsMixin,
    WindowStyleMixin,
    QTabWidget,
):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.setTabBar(MainTabBar(self))
        self.setWindowTitle('HDF5 GUI')
        self.resize(1200, 750)
        self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
        self.setup_database()
        self.set_style()
        self.load_settings()

        self.current_kunde_filter = ""
        self.current_datum_filter = ""

        self.tab_home = QWidget()
        self.tab_history = QWidget()
        self.tab_settings = QWidget()
        self.addTab(self.tab_home, "Anfrage")
        self.addTab(self.tab_history, "Historie")
        self.settings_tab_index = self.addTab(self.tab_settings, "")

        # Keep Settings as a real tab page, but expose it through a separate
        # tab-like button docked to the right edge of the tab bar.
        self.tabBar().hide_page_tab(self.settings_tab_index)
        self.settings_tab_button = QToolButton(self)
        self.settings_tab_button.setObjectName("settingsTabButton")
        self.settings_tab_button.setText("Settings")
        self.settings_tab_button.setProperty("selected", False)
        self.settings_tab_button.clicked.connect(
            lambda: self.setCurrentIndex(self.settings_tab_index)
        )
        self.currentChanged.connect(self._update_settings_tab_button)
        self.setCornerWidget(
            self.settings_tab_button,
            QtCore.Qt.TopRightCorner,
        )

        self.home()
        self.history_ui()
        self.settings_ui()

    def _update_settings_tab_button(self, index):
        self.settings_tab_button.setProperty(
            "selected",
            index == self.settings_tab_index,
        )
        self.settings_tab_button.style().unpolish(self.settings_tab_button)
        self.settings_tab_button.style().polish(self.settings_tab_button)
