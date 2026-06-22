"""Home tab construction and input helpers for the main GUI window."""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from gui_streams import XStream
from gui_widgets import TransferList


AVAILABLE_VARIABLES = [
    "Ta_2m", "rh_2m", "Ta_18m", "rh_18m", "p", "rr_01", "rr_02", "rr_03",
    "rr_04", "rr_05", "rr_06", "rr_07", "rr_09", "rr_10", "u_2m",
    "dd_2m", "dd_2m_sigma", "u_19m", "dd_19m", "dd_19m_sigma", "G",
    "RK", "A", "E", "CaseTemp", "TC_01", "TC_02", "Tg_2cm", "Tg_5cm",
    "Tg_10cm", "Tg_20cm", "Tg_50cm", "Qg", "VWC_01", "VWC_02",
    "VWC_03", "VWC_04", "VWC_05",
]


class HomeTabMixin:
    def home(self):
        self.main_layout = QtWidgets.QHBoxLayout()
        self.grid = QGridLayout()
        self.right_layout = QVBoxLayout()
        row = 1

        row = self._add_customer_input(row)
        row = self._add_date_inputs(row)
        row = self._add_variable_picker(row)
        row = self._add_console(row)
        self._add_run_button(row)

        self.main_layout.addLayout(self.grid, 2)
        self.main_layout.addLayout(self.right_layout, 1)
        self.tab_home.setLayout(self.main_layout)

    def _add_customer_input(self, row):
        self.customer_lab = QLabel('Kunde:')
        self.customer_combo = QtWidgets.QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.lineEdit().setPlaceholderText("Kunde suchen oder neu eingeben...")
        self.customer_btn = QPushButton('Addressbuch')
        self.customer_btn.clicked.connect(self.open_addressbook_anfrage)
        self.grid.addWidget(self.customer_lab, row, 0)
        self.grid.addWidget(self.customer_combo, row, 1, 1, 10)
        self.grid.addWidget(self.customer_btn, row, 11, 1, 2)
        self.customer_lab.setToolTip('Name des Kunden auswaehlen oder neu eingeben')
        self.customer_combo.setToolTip('Name des Kunden auswaehlen oder neu eingeben')
        self.load_customers()
        return row + 1

    def _add_date_inputs(self, row):
        self.duration_lab = QLabel('Duration:')
        self.start_lab = QLabel('Start date:')
        self.start_date_display = QLineEdit()
        self.start_date_display.setReadOnly(True)
        self.start_date_display.setObjectName("DateDisplay")

        self.end_lab = QLabel('End date:')
        self.end_date_display = QLineEdit()
        self.end_date_display.setReadOnly(True)
        self.end_date_display.setObjectName("DateDisplay")

        start_layout = QtWidgets.QHBoxLayout()
        start_layout.setContentsMargins(0, 0, 6, 0)
        start_layout.addWidget(self.start_lab)
        start_layout.addWidget(self.start_date_display)

        end_layout = QtWidgets.QHBoxLayout()
        end_layout.setContentsMargins(6, 0, 0, 0)
        end_layout.addWidget(self.end_lab)
        end_layout.addWidget(self.end_date_display)

        self.cal_start = QtWidgets.QCalendarWidget()
        self.cal_end = QtWidgets.QCalendarWidget()
        self.configure_calendar(self.cal_start)
        self.configure_calendar(self.cal_end)
        self.start_calendar_panel = self.calendar_panel(self.cal_start, right_margin=16)
        self.end_calendar_panel = self.calendar_panel(self.cal_end, left_margin=16)

        self.grid.addWidget(self.duration_lab, row, 0)
        self.grid.addLayout(start_layout, row, 1, 1, 6)
        self.grid.addLayout(end_layout, row, 7, 1, 6)
        self.grid.addWidget(self.start_calendar_panel, row + 1, 1, 1, 6)
        self.grid.addWidget(self.end_calendar_panel, row + 1, 7, 1, 6)

        self.cal_start.selectionChanged.connect(self.date_changed)
        self.cal_end.selectionChanged.connect(self.date_changed)
        self.duration_lab.setToolTip(str('Select the duration'))
        self.start_lab.setToolTip(str('Select Start date'))
        self.end_lab.setToolTip(str('Select End date'))
        self.date_changed()
        return row + 2

    def _add_variable_picker(self, row):
        self.var_lab = QLabel('Parameters:')
        self.transfer_list = TransferList(AVAILABLE_VARIABLES)
        self.transfer_list.setMaximumWidth(700)
        self.right_layout.addWidget(self.var_lab)
        self.right_layout.addWidget(self.transfer_list)
        return row

    def _add_console(self, row):
        self.console = QTextBrowser(self)
        self.console_lab = QLabel('Console')
        self.grid.addWidget(self.console_lab, row, 0)
        self.grid.addWidget(self.console, row, 1, 1, 12)
        XStream.stdout().messageWritten.connect(self.append_to_console)
        XStream.stderr().messageWritten.connect(self.append_to_console)
        return row + 1

    def _add_run_button(self, row):
        self.run_lab = QLabel(' ')
        self.run_btn = QPushButton(' Run')
        self.run_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.run_btn.setObjectName("RunButton")
        self.run_btn.clicked.connect(lambda checked: self.run(save_to_db=True))
        self.grid.addWidget(self.run_lab, row, 0)
        self.grid.addWidget(self.run_btn, row, 1, 1, 12)

    def append_to_console(self, text):
        self.console.insertPlainText(text)
        self.console.moveCursor(QtGui.QTextCursor.End)

    def date_changed(self):
        try:
            date_start = self.cal_start.selectedDate()
            self.pydate_start = date_start.toPyDate()
            date_end = self.cal_end.selectedDate()
            self.pydate_end = date_end.toPyDate()

            self.start_date_display.setText(self.pydate_start.strftime("%Y-%m-%d"))
            self.end_date_display.setText(self.pydate_end.strftime("%Y-%m-%d"))

            assert self.pydate_start
            assert self.pydate_end
            self.console.clear()
            print("Duration: ", self.pydate_start, "to ", self.pydate_end)
        except:
            print("Please specify a valid duration")

    def load_entry_to_ui(self, row_data):
        kunde = str(row_data[1])
        start_str = str(row_data[3])
        end_str = str(row_data[4])
        params_str = str(row_data[5])

        self.customer_combo.setCurrentText(kunde)
        self.cal_start.setSelectedDate(QtCore.QDate.fromString(start_str, "yyyy-MM-dd"))
        self.cal_end.setSelectedDate(QtCore.QDate.fromString(end_str, "yyyy-MM-dd"))
        self.transfer_list.set_selected_variables(params_str.split(","))
        return True
