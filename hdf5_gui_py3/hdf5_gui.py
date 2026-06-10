
import sys
import os
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QObject,pyqtSignal
from PyQt5.QtWidgets import QComboBox, QCalendarWidget, QGridLayout, QVBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, QDialog, QTextBrowser, QApplication, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
import traceback
import sqlite3
import datetime
import lauchaecker_config as lconf
from pypika import Column, Order, Parameter, PostgreSQLQuery, Query, Table


KUNDEN_TABLE = Table("Kunden")
ANFRAGEN_TABLE = Table("Anfragen")


def sql_param():
    return Parameter("?")


def create_kunden_table_sql():
    return (
        Query.create_table(KUNDEN_TABLE)
        .if_not_exists()
        .columns(
            Column("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            Column("name", "TEXT", nullable=False),
        )
        .unique("name")
        .get_sql()
    )


def create_anfragen_table_sql():
    return (
        Query.create_table(ANFRAGEN_TABLE)
        .if_not_exists()
        .columns(
            Column("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            Column("kunden_id", "INTEGER"),
            Column("zeitpunkt", "TEXT"),
            Column("start_date", "TEXT"),
            Column("end_date", "TEXT"),
            Column("parameter", "TEXT"),
        )
        .foreign_key(["kunden_id"], KUNDEN_TABLE, ["id"])
        .get_sql()
    )


def history_query(kunde_filter, datum_filter):
    query = (
        Query.from_(ANFRAGEN_TABLE)
        .join(KUNDEN_TABLE)
        .on(ANFRAGEN_TABLE.kunden_id == KUNDEN_TABLE.id)
        .select(
            ANFRAGEN_TABLE.id,
            KUNDEN_TABLE.name,
            ANFRAGEN_TABLE.zeitpunkt,
            ANFRAGEN_TABLE.start_date,
            ANFRAGEN_TABLE.end_date,
            ANFRAGEN_TABLE.parameter,
        )
    )
    params = []

    if kunde_filter:
        query = query.where(KUNDEN_TABLE.name.like(sql_param()))
        params.append(f"%{kunde_filter}%")
    if datum_filter:
        query = query.where(ANFRAGEN_TABLE.zeitpunkt.like(sql_param()))
        params.append(f"{datum_filter}%")

    query = query.orderby(ANFRAGEN_TABLE.zeitpunkt, order=Order.desc)
    return query.get_sql(), params


def customer_names_query():
    return (
        Query.from_(KUNDEN_TABLE)
        .select(KUNDEN_TABLE.name)
        .orderby(KUNDEN_TABLE.name, order=Order.asc)
        .get_sql()
    )


def insert_customer_query():
    return (
        PostgreSQLQuery.into(KUNDEN_TABLE)
        .columns(KUNDEN_TABLE.name)
        .insert(sql_param())
        .on_conflict(KUNDEN_TABLE.name)
        .do_nothing()
        .get_sql()
    )


def customer_id_query():
    return (
        Query.from_(KUNDEN_TABLE)
        .select(KUNDEN_TABLE.id)
        .where(KUNDEN_TABLE.name == sql_param())
        .get_sql()
    )


def insert_anfrage_query():
    return (
        Query.into(ANFRAGEN_TABLE)
        .columns(
            ANFRAGEN_TABLE.kunden_id,
            ANFRAGEN_TABLE.zeitpunkt,
            ANFRAGEN_TABLE.start_date,
            ANFRAGEN_TABLE.end_date,
            ANFRAGEN_TABLE.parameter,
        )
        .insert(sql_param(), sql_param(), sql_param(), sql_param(), sql_param())
        .get_sql()
    )

class XStream(QObject):
    _stdout = None
    _stderr = None

    messageWritten = pyqtSignal(str)

    def flush( self ):
        pass

    def fileno( self ):
        return -1

    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(str(msg))

    @staticmethod
    def stdout():
        if ( not XStream._stdout ):
            XStream._stdout = XStream()
            sys.stdout = XStream._stdout
        return XStream._stdout

    @staticmethod
    def stderr():
        if ( not XStream._stderr ):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr

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

        self.calendar = QCalendarWidget()
        self.layout.addWidget(self.calendar)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_clear = QPushButton("Filter löschen")
        self.btn_ok = QPushButton("Bestätigen")
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_ok)
        self.layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_clear.clicked.connect(self.clear_and_accept)
        self.calendar.activated.connect(self.accept)

        self.selected_date = ""

    def accept(self):
        self.selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        super(CalendarDialog, self).accept()

    def clear_and_accept(self):
        self.selected_date = ""
        super(CalendarDialog, self).accept()

    def get_selected_date(self):
        return self.selected_date

class Window(QTabWidget):
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

    def configure_calendar(self, calendar):
        font = calendar.font()
        font.setPointSize(8)
        calendar.setFont(font)
        calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        calendar.setStyleSheet("""
        QCalendarWidget QToolButton {
            font-size: 10pt;
            padding: 1px 4px;
            min-height: 18px;
        }
        QCalendarWidget QSpinBox,
        QCalendarWidget QAbstractItemView {
            font-size: 10pt;
        }
        """)
        calendar.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        calendar.setMinimumSize(calendar.sizeHint())
        calendar.setMaximumSize(calendar.sizeHint())

    def calendar_panel(self, calendar, left_margin=0, right_margin=0):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(left_margin, 4, right_margin, 6)
        layout.setSpacing(0)
        layout.addWidget(calendar)
        return panel

    def setup_database(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anfragen_log.db')
        self.conn = sqlite3.connect(db_path)
        cursor = self.conn.cursor()
        cursor.execute(create_kunden_table_sql())
        cursor.execute(create_anfragen_table_sql())
        self.conn.commit()

    def set_style(self):
        style = """
        QWidget {
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            font-size: 10pt;
            background-color: #f4f6f9;
            color: #2c3e50;
        }
        QTabWidget::pane {
            border: 1px solid #cfd9e5;
            background: #ffffff;
            border-radius: 6px;
        }
        QTabBar::tab {
            background: #e2e8f0;
            border: 1px solid #cfd9e5;
            padding: 8px 20px;
            min-width: 150px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            color: #64748b;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom-color: #ffffff;
            font-weight: bold;
            color: #0f172a;
        }
        QTabBar::tab:hover:!selected {
            background: #cbd5e1;
        }
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 6px 14px;
            color: #0f172a;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #f1f5f9;
            border-color: #94a3b8;
        }
        QPushButton:pressed {
            background-color: #e2e8f0;
        }
        QLineEdit, QComboBox {
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 5px 8px;
            background: #ffffff;
            selection-background-color: #3b82f6;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #3b82f6;
        }
        QListWidget, QTableWidget, QCalendarWidget {
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            background: #ffffff;
            alternate-background-color: #f8fafc;
        }
        QTextBrowser {
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            background-color: #1e293b;
            color: #f8fafc;
            font-family: "Consolas", "Courier New", monospace;
            padding: 5px;
        }
        QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #1e293b;
            color: white;
        }
        QHeaderView::section {
            background-color: #f8fafc;
            padding: 4px 8px;
            border: 1px solid #e2e8f0;
            font-weight: bold;
            color: #475569;
        }
        #SelectedList {
            background-color: #eff6ff;
            border: 2px solid #3b82f6;
        }
        #DateDisplay {
            font-weight: bold;
            color: #1e293b;
            background-color: #e2e8f0;
            border: 1px solid #94a3b8;
            padding: 4px;
        }
        QCalendarWidget QAbstractItemView {
            selection-background-color: #1e293b;
            selection-color: #ffffff;
            outline: 0px;
        }
        QScrollBar:vertical {
            border: none;
            background: #f1f5f9;
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            width: 0px;
            height: 0px;
            border: none;
            background: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            border: none;
            background: #f1f5f9;
            height: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #cbd5e1;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
            height: 0px;
            border: none;
            background: none;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        #RunButton {
            background-color: #3b82f6;
            color: #ffffff;
            font-weight: bold;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
        #RunButton:hover {
            background-color: #2563eb;
        }
        #RunButton:pressed {
            background-color: #1d4ed8;
        }
        #TransferButton {
            padding: 4px;
            min-width: 35px;
            margin: 0px 4px;
        }
        QLabel {
            font-weight: bold;
        }
        """
        self.setStyleSheet(style)

    def home(self):
        self.main_layout = QtWidgets.QHBoxLayout()
        self.grid = QGridLayout()
        self.right_layout = QVBoxLayout()
        i = 1

        self.working_dir_lab = QLabel('Working Directory:')
        self.working_dir_line = QLineEdit()
        self.working_dir_btn = QPushButton('Browse')
        self.working_dir_btn.clicked.connect(lambda: self.get_input_dir(_input=True))
        self.grid.addWidget(self.working_dir_lab, i, 0)
        self.grid.addWidget(self.working_dir_line, i, 1, 1, 11)
        self.grid.addWidget(self.working_dir_btn, i, 12)
        self.working_dir_lab.setToolTip(str('Full path to the Working Directory.'))
        self.working_dir_line.setToolTip(str('Full path to the Working Directory.'))
        self.working_dir_btn.setToolTip(str('Browse to Working Directory.'))
        self.working_dir = self.working_dir_line.text()
        i += 1

        self.hdf5_lab = QLabel('HDF5 File:')
        self.hdf5_line = QLineEdit()
        self.hdf5_line.setText(lconf.hdf5_filename)
        self.hdf5_btn = QPushButton('Browse')
        self.hdf5_btn.clicked.connect(self.get_hdf5_file)
        self.grid.addWidget(self.hdf5_lab, i, 0)
        self.grid.addWidget(self.hdf5_line, i, 1, 1, 11)
        self.grid.addWidget(self.hdf5_btn, i, 12)
        self.hdf5_lab.setToolTip('Select the HDF5 input file.')
        self.hdf5_line.setToolTip('Full path to the HDF5 input file.')
        self.hdf5_btn.setToolTip('Browse for HDF5 file.')
        self.hdf5_file = self.hdf5_line.text()
        i += 1

        self.customer_lab = QLabel('Kunde:')
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.lineEdit().setPlaceholderText("Kunde suchen oder neu eingeben...")
        self.customer_btn = QPushButton('Addressbuch')
        self.customer_btn.clicked.connect(self.open_addressbook_anfrage)
        self.grid.addWidget(self.customer_lab, i, 0)
        self.grid.addWidget(self.customer_combo, i, 1, 1, 10)
        self.grid.addWidget(self.customer_btn, i, 11, 1, 2)
        self.customer_lab.setToolTip('Name des Kunden auswählen oder neu eingeben')
        self.customer_combo.setToolTip('Name des Kunden auswählen oder neu eingeben')
        self.load_customers()
        i += 1

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

        self.grid.addWidget(self.duration_lab, i, 0)
        self.grid.addLayout(start_layout, i, 1, 1, 6)
        self.grid.addLayout(end_layout, i, 7, 1, 6)
        self.grid.addWidget(self.start_calendar_panel, i+1, 1, 1, 6)
        self.grid.addWidget(self.end_calendar_panel, i+1, 7, 1, 6)

       # self.connect(self.cal_start, QtCore.SIGNAL('selectionChanged()'), self.date_changed)
        self.cal_start.selectionChanged.connect(self.date_changed)
        self.cal_end.selectionChanged.connect(self.date_changed)
        self.duration_lab.setToolTip(str('Select the duration'))
        self.start_lab.setToolTip(str('Select Start date'))
        self.end_lab.setToolTip(str('Select End date'))
        self.date_changed()
        i += 2

        self.var_lab = QLabel('Parameters:')
        alle_variablen = ["Ta_2m", "rh_2m", "Ta_18m", "rh_18m", "p", "rr_01", "rr_02", "rr_03", "rr_04", "rr_05",
                          "rr_06", "rr_07", "rr_09", "rr_10", "u_2m", "dd_2m", "dd_2m_sigma", "u_19m", "dd_19m",
                          "dd_19m_sigma", "G", "RK", "A", "E", "CaseTemp", "TC_01", "TC_02", "Tg_2cm", "Tg_5cm",
                          "Tg_10cm", "Tg_20cm", "Tg_50cm", "Qg", "VWC_01", "VWC_02", "VWC_03", "VWC_04", "VWC_05"]
        self.transfer_list = TransferList(alle_variablen)
        self.transfer_list.setMaximumWidth(700)
        
        self.right_layout.addWidget(self.var_lab)
        self.right_layout.addWidget(self.transfer_list)

        self.console = QTextBrowser(self)
        self.console_lab = QLabel('Console')
        self.grid.addWidget(self.console_lab, i, 0)
        self.grid.addWidget(self.console, i, 1, 1, 12)
        XStream.stdout().messageWritten.connect(self.append_to_console)
        XStream.stderr().messageWritten.connect(self.append_to_console)
        i += 1

        self.run_lab = QLabel(' ')
        self.run_btn = QPushButton(' Run')
        self.run_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.run_btn.setObjectName("RunButton")
        self.run_btn.clicked.connect(lambda checked: self.run(save_to_db=True))
        self.grid.addWidget(self.run_lab, i, 0)
        self.grid.addWidget(self.run_btn, i, 1, 1, 12)


        self.main_layout.addLayout(self.grid, 2)
        self.main_layout.addLayout(self.right_layout, 1)
        self.tab_home.setLayout(self.main_layout)

    def history_ui(self):
        layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels(['ID', 'Kunde', 'Zeitpunkt', 'Start', 'Ende', 'Parameter', 'Laden', 'Ausführen'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
        btn_layout = QtWidgets.QHBoxLayout()
        self.refresh_btn = QPushButton('Aktualisieren')
        self.refresh_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.load_history)
        
        self.btn_filter_kunde = QPushButton('Kunden Filter')
        self.btn_filter_kunde.clicked.connect(self.open_kunde_filter)

        self.btn_filter_datum = QPushButton('Datum Filter')
        self.btn_filter_datum.clicked.connect(self.open_datum_filter)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.btn_filter_kunde)
        btn_layout.addWidget(self.btn_filter_datum)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.history_table)
        self.tab_history.setLayout(layout)
        self.load_history()

    def load_history(self):
        try:
            cursor = self.conn.cursor()
            query, params = history_query(
                self.current_kunde_filter,
                self.current_datum_filter,
            )
            cursor.execute(query, params)
            rows = cursor.fetchall()
            self.history_table.setRowCount(len(rows))
            for row_idx, row_data in enumerate(rows):
                for col_idx, col_data in enumerate(row_data):
                    self.history_table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

                btn_load = QPushButton('Laden')
                btn_load.clicked.connect(lambda checked, d=row_data: self.action_load_to_tab(d))
                self.history_table.setCellWidget(row_idx, 6, btn_load)
                
                btn_rerun = QPushButton('Ausführen')
                btn_rerun.clicked.connect(lambda checked, d=row_data: self.action_rerun_history(d))
                self.history_table.setCellWidget(row_idx, 7, btn_rerun)
        except Exception as e:
            print("Fehler beim Laden der Historie:", e)

    def open_kunde_filter(self):
        kunden = []
        for i in range(self.customer_combo.count()):
            kunden.append(self.customer_combo.itemText(i))
        dlg = AddressBookDialog(self, kunden)
        if dlg.exec_():
            self.current_kunde_filter = dlg.get_selected_customer()
            if self.current_kunde_filter:
                self.btn_filter_kunde.setText(f"Kunde: {self.current_kunde_filter}")
            else:
                self.btn_filter_kunde.setText("Kunden Filter")
            self.load_history()

    def open_datum_filter(self):
        dlg = CalendarDialog(self)
        if dlg.exec_():
            self.current_datum_filter = dlg.get_selected_date()
            if self.current_datum_filter:
                self.btn_filter_datum.setText(f"Datum: {self.current_datum_filter}")
            else:
                self.btn_filter_datum.setText("Datum Filter")
            self.load_history()

    def open_addressbook_anfrage(self):
        kunden = []
        for i in range(self.customer_combo.count()):
            kunden.append(self.customer_combo.itemText(i))
        dlg = AddressBookDialog(self, kunden)
        dlg.setWindowTitle("Addressbuch")
        if dlg.exec_():
            selected = dlg.get_selected_customer()
            if selected:
                self.customer_combo.setCurrentText(selected)

    def load_customers(self):
        self.customer_combo.clear()
        try:
            cursor = self.conn.cursor()
            cursor.execute(customer_names_query())
            kunden = cursor.fetchall()
            for kunde in kunden:
                self.customer_combo.addItem(kunde[0])
                
            completer = CustomerCompleter(self.customer_combo.model(), self)
            completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            completer.setFilterMode(QtCore.Qt.MatchContains)
            self.customer_combo.setCompleter(completer)
        except Exception as e:
            print("Fehler beim Laden der Kunden aus der Datenbank:", e)

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


    def get_input_dir(self, _input=True):
        try:
            if _input:
                self.working_dir = str(QFileDialog.getExistingDirectory(self))
                self.working_dir_line.setText(self.working_dir)
                assert self.working_dir
                print("Working Directory set to: ", self.working_dir)
        except:
            print("Please specify a valid Working directory")

    def get_hdf5_file(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Select HDF5 File", "", "HDF5 Files (*.h5 *.hdf5);;All Files (*)")
            if file_name:
                self.hdf5_file = file_name
                self.hdf5_line.setText(self.hdf5_file)
                print("HDF5 File set to:", self.hdf5_file)
        except Exception as e:
            print("Error selecting HDF5 file:", e)

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

    def action_load_to_tab(self, row_data):
        self.load_entry_to_ui(row_data)
        self.setCurrentIndex(0)

    def action_rerun_history(self, row_data):
        self.load_entry_to_ui(row_data)
        self.run(save_to_db=False)

    def run(self, save_to_db=True):
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.console.clear()
            self.allesgut = True
            print("Running...")
            QApplication.processEvents()
    
            self.hdf5_file = self.hdf5_line.text()
            try:
                assert self.hdf5_file and os.path.isfile(self.hdf5_file)
            except:
                print("Invalid or missing HDF5 file")
                self.allesgut = False
    
            try:
                assert self.working_dir
                os.chdir(self.working_dir)
            except:
                print("Invalid Working directory")
                self.allesgut = False
    
            try:
                assert self.pydate_start
                assert self.pydate_end
            except:
                print("invalid duration")
                self.allesgut = False
    
            self.var_list = self.transfer_list.get_selected_variables()
            if not self.var_list:
                print("WARNING: var list empty")
                self.allesgut = False
    
            kunde = self.customer_combo.currentText().strip()
            if not kunde:
                print("Bitte einen Kunden angeben.")
                self.allesgut = False
            elif self.allesgut:
                # Pfad und Dateinamen automatisch generieren
                now = datetime.datetime.now()
                year_str = now.strftime("%Y")
                time_str = now.strftime("%Y%m%d%H%M%S")
                safe_kunde = kunde.replace(" ", "")
                filename = f"{safe_kunde}_{time_str}.txt"
                
                export_dir = os.path.join(self.working_dir, "Export", year_str)
                try:
                    os.makedirs(export_dir, exist_ok=True)
                    self.out_dir = os.path.join(export_dir, filename)
                except Exception as e:
                    print("Fehler beim Erstellen des Export-Ordners:", e)
                    self.allesgut = False
    
            # Zeitschritt hart auf die höchste Auflösung (1 Minute) setzen
            self.del_t = 1
    
            if self.allesgut == True:
                if save_to_db:
                    try:
                        cursor = self.conn.cursor()
                        cursor.execute(insert_customer_query(), (kunde,))
                        cursor.execute(customer_id_query(), (kunde,))
                        kunden_id = cursor.fetchone()[0]
                        
                        # Neuen Kunden direkt in die laufende Dropdown-Liste aufnehmen
                        if self.customer_combo.findText(kunde) == -1:
                            self.customer_combo.addItem(kunde)
    
                        jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        param_str = ",".join(self.var_list)
                        
                        cursor.execute(
                            insert_anfrage_query(),
                            (
                                kunden_id,
                                jetzt,
                                str(self.pydate_start),
                                str(self.pydate_end),
                                param_str,
                            ),
                        )
                        self.conn.commit()
                        print("Anfrage in Datenbank gespeichert.")
                        self.load_history()
                    except Exception as e:
                        print("Fehler beim Speichern in der Datenbank:", e)
    
                try:
                    #from lhglib.contrib.meteo import lauchaecker_hdf5_tools as lht
                    import lauchaecker_hdf5_tools as lht
                    lht.hdf52txt(start=str(self.pydate_start) + "T00:00:00", end=str(self.pydate_end)+"T00:00:00",
                                 varpath=self.var_list,outfile=str(self.out_dir), del_t=self.del_t, hdf5=self.hdf5_file)
                    print("Finished")
                except Exception as ex:
                    print(ex)
                    traceback.print_exc()
            else:
                print("Please check inputs")
        finally:
            QApplication.restoreOverrideCursor()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Window()
    main.show()
    sys.exit(app.exec_())
