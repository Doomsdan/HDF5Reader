"""Reusable Qt widgets and dialogs for the HDF5 GUI."""

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class TransferList(QtWidgets.QWidget):
    def __init__(self, available_vars, parent=None):
        super(TransferList, self).__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(6)

        # Linke Liste: Verfügbare Parameter
        self.available_lab = QLabel("Verfügbar")
        self.list_available = QtWidgets.QListWidget()
        self.list_available.setMinimumWidth(160)
        self.list_available.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_available.addItems(available_vars)

        # Rechte Liste: Ausgewählte Parameter
        self.selected_lab = QLabel("Ausgewählt")
        self.list_selected = QtWidgets.QListWidget()
        self.list_selected.setMinimumWidth(160)
        self.list_selected.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_selected.setObjectName("SelectedList")

        # Buttons in der Mitte
        vbox_buttons = QtWidgets.QVBoxLayout()
        self.btn_add = QtWidgets.QPushButton()
        self.btn_add.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
        self.btn_add.setObjectName("TransferButton")
        self.btn_remove = QtWidgets.QPushButton()
        self.btn_remove.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowLeft))
        self.btn_remove.setObjectName("TransferButton")

        vbox_buttons.addStretch()
        vbox_buttons.addWidget(self.btn_add)
        vbox_buttons.addWidget(self.btn_remove)
        vbox_buttons.addStretch()

        layout.addWidget(self.available_lab, 0, 0)
        layout.addWidget(self.selected_lab, 0, 2)
        layout.addWidget(self.list_available, 1, 0)
        layout.addLayout(vbox_buttons, 1, 1)
        layout.addWidget(self.list_selected, 1, 2)

        self.btn_add.clicked.connect(self.add_item)
        self.btn_remove.clicked.connect(self.remove_item)
        
        self.list_available.itemDoubleClicked.connect(self.add_item)
        self.list_selected.itemDoubleClicked.connect(self.remove_item)

    def add_item(self):
        for item in self.list_available.selectedItems():
            self.list_selected.addItem(self.list_available.takeItem(self.list_available.row(item)))

    def remove_item(self):
        for item in self.list_selected.selectedItems():
            self.list_available.addItem(self.list_selected.takeItem(self.list_selected.row(item)))

    def get_selected_variables(self):
        return [self.list_selected.item(i).text() for i in range(self.list_selected.count())]

    def set_selected_variables(self, var_list):
        while self.list_selected.count() > 0:
            item = self.list_selected.takeItem(0)
            self.list_available.addItem(item)
        for var in var_list:
            items = self.list_available.findItems(var, QtCore.Qt.MatchExactly)
            for item in items:
                self.list_selected.addItem(self.list_available.takeItem(self.list_available.row(item)))


class CustomerCompleter(QtWidgets.QCompleter):
    def complete(self, *args, **kwargs):
        if len(self.completionPrefix()) < 3:
            self.popup().hide()
            return
        super(CustomerCompleter, self).complete(*args, **kwargs)


class AddressBookDialog(QDialog):
    def __init__(self, parent=None, kunden=[]):
        super(AddressBookDialog, self).__init__(parent)
        self.setWindowTitle("Addressbuch Filter")
        self.resize(350, 450)
        self.layout = QVBoxLayout(self)

        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Kunde suchen...")
        self.layout.addWidget(self.search_line)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(kunden)
        self.layout.addWidget(self.list_widget)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_clear = QPushButton("Filter löschen")
        self.btn_ok = QPushButton("Bestätigen")
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_ok)
        self.layout.addLayout(btn_layout)

        self.search_line.textChanged.connect(self.filter_list)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_clear.clicked.connect(self.clear_and_accept)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        
        self.selected_customer = ""

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def accept(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items and not selected_items[0].isHidden():
            self.selected_customer = selected_items[0].text()
        else:
            self.selected_customer = self.search_line.text()
        super(AddressBookDialog, self).accept()

    def clear_and_accept(self):
        self.selected_customer = ""
        super(AddressBookDialog, self).accept()

    def get_selected_customer(self):
        return self.selected_customer


class CalendarDialog(QDialog):
    def __init__(self, parent=None):
        super(CalendarDialog, self).__init__(parent)
        self.setWindowTitle("Datum Filter")
        self.layout = QVBoxLayout(self)

        mode_layout = QtWidgets.QHBoxLayout()
        self.single_date_radio = QtWidgets.QRadioButton("Einzeldatum")
        self.date_range_radio = QtWidgets.QRadioButton("Zeitraum")
        self.single_date_radio.setChecked(True)
        mode_layout.addWidget(self.single_date_radio)
        mode_layout.addWidget(self.date_range_radio)
        mode_layout.addStretch()
        self.layout.addLayout(mode_layout)

        self.date_pages = QtWidgets.QStackedWidget()

        self.calendar = QCalendarWidget()
        self.date_pages.addWidget(self.calendar)

        range_page = QtWidgets.QWidget()
        range_layout = QtWidgets.QHBoxLayout(range_page)
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Startdatum"))
        self.start_calendar = QCalendarWidget()
        start_layout.addWidget(self.start_calendar)
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("Enddatum"))
        self.end_calendar = QCalendarWidget()
        end_layout.addWidget(self.end_calendar)
        range_layout.addLayout(start_layout)
        range_layout.addLayout(end_layout)
        self.date_pages.addWidget(range_page)
        self.layout.addWidget(self.date_pages)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_clear = QPushButton("Filter löschen")
        self.btn_ok = QPushButton("Bestätigen")
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_ok)
        self.layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_clear.clicked.connect(self.clear_and_accept)
        self.calendar.activated.connect(self.accept)
        self.single_date_radio.toggled.connect(self._update_mode)
        self.start_calendar.selectionChanged.connect(self._update_end_minimum)

        self.selected_date = ""

    def _update_mode(self, single_date):
        self.date_pages.setCurrentIndex(0 if single_date else 1)

    def _update_end_minimum(self):
        start_date = self.start_calendar.selectedDate()
        self.end_calendar.setMinimumDate(start_date)
        if self.end_calendar.selectedDate() < start_date:
            self.end_calendar.setSelectedDate(start_date)

    def accept(self):
        if self.single_date_radio.isChecked():
            self.selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        else:
            self.selected_date = (
                self.start_calendar.selectedDate().toString("yyyy-MM-dd"),
                self.end_calendar.selectedDate().toString("yyyy-MM-dd"),
            )
        super(CalendarDialog, self).accept()

    def clear_and_accept(self):
        self.selected_date = ""
        super(CalendarDialog, self).accept()

    def get_selected_date(self):
        return self.selected_date

