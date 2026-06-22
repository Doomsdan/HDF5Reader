"""Statistics tab for request, parameter, and customer usage."""

from collections import Counter

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def aggregate_request_stats(rows):
    """Aggregate ``(customer, comma-separated parameters)`` request rows."""
    parameter_counts = Counter()
    parameter_customer_counts = Counter()
    customer_request_counts = Counter()

    for customer, parameters in rows:
        customer = (customer or "").strip()
        if customer:
            customer_request_counts[customer] += 1

        for parameter in (parameters or "").split(","):
            parameter = parameter.strip()
            if not parameter:
                continue
            parameter_counts[parameter] += 1
            if customer:
                parameter_customer_counts[(parameter, customer)] += 1

    by_count_then_name = lambda item: (-item[1], item[0].casefold())
    parameter_usage = sorted(parameter_counts.items(), key=by_count_then_name)
    customer_requests = sorted(
        customer_request_counts.items(), key=by_count_then_name
    )
    parameter_customers = sorted(
        (
            (parameter, customer, count)
            for (parameter, customer), count in parameter_customer_counts.items()
        ),
        key=lambda item: (-item[2], item[0].casefold(), item[1].casefold()),
    )
    return parameter_usage, parameter_customers, customer_requests


class StatsMixin:
    def stats_ui(self):
        layout = QtWidgets.QHBoxLayout(self.tab_stats)

        navigation_layout = QVBoxLayout()
        navigation_layout.addWidget(QLabel("Statistik ausw\u00e4hlen"))
        self.stats_navigation = QListWidget()
        self.stats_navigation.setObjectName("StatsNavigation")
        self.stats_navigation.addItems([
            "Parameter insgesamt",
            "Parameter nach Kunde",
            "Anfragen nach Kunde",
        ])
        self.stats_navigation.setFixedWidth(230)
        navigation_layout.addWidget(self.stats_navigation)
        layout.addLayout(navigation_layout)

        content_layout = QVBoxLayout()

        toolbar = QtWidgets.QHBoxLayout()
        self.refresh_stats_btn = QPushButton("Aktualisieren")
        self.refresh_stats_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        )
        self.refresh_stats_btn.clicked.connect(self.load_stats)
        toolbar.addWidget(self.refresh_stats_btn)
        toolbar.addStretch()
        content_layout.addLayout(toolbar)

        self.parameter_stats_table = self._create_stats_table(
            ["Parameter", "Anzahl"]
        )
        self.parameter_customer_stats_table = self._create_stats_table(
            ["Parameter", "Kunde", "Anzahl"]
        )
        self.customer_stats_table = self._create_stats_table(
            ["Kunde", "Anfragen"]
        )

        self.stats_pages = QStackedWidget()
        self.stats_pages.addWidget(self._stats_page(
            "Parameter insgesamt", self.parameter_stats_table
        ))
        self.stats_pages.addWidget(self._stats_page(
            "Parameter nach Kunde", self.parameter_customer_stats_table
        ))
        self.stats_pages.addWidget(self._stats_page(
            "Anfragen nach Kunde", self.customer_stats_table
        ))
        self.stats_navigation.currentRowChanged.connect(
            self.stats_pages.setCurrentIndex
        )
        self.stats_navigation.setCurrentRow(0)
        content_layout.addWidget(self.stats_pages)
        layout.addLayout(content_layout, 1)
        self.load_stats()

    def _create_stats_table(self, headers):
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def _stats_page(self, title, table):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(table)
        page_layout.addWidget(group)
        return page

    def load_stats(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT Kunden.name, Anfragen.parameter
            FROM Anfragen
            JOIN Kunden ON Anfragen.kunden_id = Kunden.id
            """
        )
        parameter_usage, parameter_customers, customer_requests = (
            aggregate_request_stats(cursor.fetchall())
        )
        self._fill_stats_table(self.parameter_stats_table, parameter_usage)
        self._fill_stats_table(
            self.parameter_customer_stats_table, parameter_customers
        )
        self._fill_stats_table(self.customer_stats_table, customer_requests)

    def _fill_stats_table(self, table, rows):
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                if isinstance(value, int):
                    item.setData(QtCore.Qt.DisplayRole, value)
                    item.setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                table.setItem(row_index, column_index, item)
