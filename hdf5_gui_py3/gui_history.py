"""History tab and customer database helpers for the main GUI window."""

import os
import sqlite3

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from gui_sql import (
    create_anfragen_table_sql,
    create_kunden_table_sql,
    customer_names_query,
    ensure_anfragen_time_delta_column,
    history_query,
)
from gui_widgets import AddressBookDialog, CalendarDialog, CustomerCompleter


class HistoryMixin:
    def setup_database(self):
        self.database_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'anfragen_log.db',
        )
        self.conn = sqlite3.connect(self.database_path)
        cursor = self.conn.cursor()
        cursor.execute(create_kunden_table_sql())
        cursor.execute(create_anfragen_table_sql())
        ensure_anfragen_time_delta_column(self.conn)
        self.conn.commit()

    def history_ui(self):
        layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            'ID', 'Kunde', 'Zeitpunkt', 'Start', 'Ende', 'Parameter',
            'Time Delta (Min.)', 'Laden', 'Ausfuehren',
        ])
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
                self.history_table.setCellWidget(row_idx, 7, btn_load)

                btn_rerun = QPushButton('Ausfuehren')
                btn_rerun.clicked.connect(lambda checked, d=row_data: self.action_rerun_history(d))
                self.history_table.setCellWidget(row_idx, 8, btn_rerun)
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
                if isinstance(self.current_datum_filter, tuple):
                    start_date, end_date = self.current_datum_filter
                    self.btn_filter_datum.setText(
                        f"Zeitraum: {start_date} - {end_date}"
                    )
                else:
                    self.btn_filter_datum.setText(
                        f"Datum: {self.current_datum_filter}"
                    )
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

    def action_load_to_tab(self, row_data):
        self.load_entry_to_ui(row_data)
        self.setCurrentIndex(0)

    def action_rerun_history(self, row_data):
        self.load_entry_to_ui(row_data)
        self.run(save_to_db=False)
