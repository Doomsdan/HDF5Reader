"""Statistics tab for request, parameter, and customer usage."""

from collections import Counter

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PyQt5 import QtCore, QtGui, QtWidgets
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


class MultiSelectComboBox(QtWidgets.QComboBox):
    """Compact checkable dropdown that keeps the popup open while selecting."""

    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, plural_name, parent=None):
        super(MultiSelectComboBox, self).__init__(parent)
        self.plural_name = plural_name
        self.all_text = f"Alle {plural_name}"
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText(self.all_text)
        self.setMinimumWidth(230)
        self.setMaxVisibleItems(14)
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if (
            watched is self.view().viewport()
            and event.type() == QtCore.QEvent.MouseButtonRelease
        ):
            index = self.view().indexAt(event.pos())
            if not index.isValid():
                return True
            item = self.model().itemFromIndex(index)
            if item.data(QtCore.Qt.UserRole) is None:
                self._set_all_unchecked()
            else:
                item.setCheckState(
                    QtCore.Qt.Unchecked
                    if item.checkState() == QtCore.Qt.Checked
                    else QtCore.Qt.Checked
                )
            self._update_display_text()
            self.selectionChanged.emit()
            return True
        return super(MultiSelectComboBox, self).eventFilter(watched, event)

    def set_options(self, values):
        selected = self.selected_values()
        self.clear()

        all_item = QtGui.QStandardItem(self.all_text)
        all_item.setData(None, QtCore.Qt.UserRole)
        self.model().appendRow(all_item)
        for value in values:
            item = QtGui.QStandardItem(value)
            item.setData(value, QtCore.Qt.UserRole)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled
                | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsUserCheckable
            )
            item.setCheckState(
                QtCore.Qt.Checked
                if value in selected
                else QtCore.Qt.Unchecked
            )
            self.model().appendRow(item)
        self.setCurrentIndex(-1)
        self._update_display_text()

    def selected_values(self):
        return {
            self.model().item(index).data(QtCore.Qt.UserRole)
            for index in range(self.count())
            if self.model().item(index).data(QtCore.Qt.UserRole) is not None
            and self.model().item(index).checkState() == QtCore.Qt.Checked
        }

    def set_selected_values(self, values):
        values = set(values)
        for index in range(self.count()):
            item = self.model().item(index)
            value = item.data(QtCore.Qt.UserRole)
            if value is not None:
                item.setCheckState(
                    QtCore.Qt.Checked
                    if value in values
                    else QtCore.Qt.Unchecked
                )
        self._update_display_text()
        self.selectionChanged.emit()

    def _set_all_unchecked(self):
        for index in range(self.count()):
            item = self.model().item(index)
            if item.data(QtCore.Qt.UserRole) is not None:
                item.setCheckState(QtCore.Qt.Unchecked)

    def _update_display_text(self):
        selected = sorted(self.selected_values(), key=str.casefold)
        if not selected:
            text = self.all_text
        elif len(selected) <= 2:
            text = ", ".join(selected)
        else:
            text = f"{len(selected)} {self.plural_name} ausgew\u00e4hlt"
        self.lineEdit().setText(text)
        self.setToolTip(", ".join(selected) if selected else self.all_text)


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


def filter_request_rows(rows, customers=None, parameters=None):
    """Filter requests; multiple selections use OR within each category."""
    customers = set(customers or [])
    parameters = set(parameters or [])
    filtered_rows = []
    for customer, parameter_text in rows:
        customer = (customer or "").strip()
        if customers and customer not in customers:
            continue

        request_parameters = [
            parameter.strip()
            for parameter in (parameter_text or "").split(",")
            if parameter.strip()
        ]
        if parameters:
            request_parameters = [
                parameter
                for parameter in request_parameters
                if parameter in parameters
            ]
            if not request_parameters:
                continue
        filtered_rows.append((customer, ",".join(request_parameters)))
    return filtered_rows


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
        self.parameter_stats_chart = self._create_stats_chart()
        self.parameter_customer_stats_chart = self._create_stats_chart()
        self.customer_stats_chart = self._create_stats_chart()
        self.stats_filters = {}
        parameter_filters = self._create_stats_filters(
            "parameters", ("parameters",)
        )
        parameter_customer_filters = self._create_stats_filters(
            "parameter_customers", ("customers", "parameters")
        )
        customer_filters = self._create_stats_filters(
            "customers", ("customers",)
        )

        self.stats_pages = QStackedWidget()
        self.stats_pages.addWidget(self._stats_page(
            "Parameter insgesamt",
            self.parameter_stats_table,
            self.parameter_stats_chart,
            parameter_filters,
        ))
        self.stats_pages.addWidget(self._stats_page(
            "Parameter nach Kunde",
            self.parameter_customer_stats_table,
            self.parameter_customer_stats_chart,
            parameter_customer_filters,
        ))
        self.stats_pages.addWidget(self._stats_page(
            "Anfragen nach Kunde",
            self.customer_stats_table,
            self.customer_stats_chart,
            customer_filters,
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

    def _create_stats_chart(self):
        figure = Figure(constrained_layout=True)
        figure.set_facecolor("#ffffff")
        canvas = FigureCanvasQTAgg(figure)
        canvas.axes = figure.add_subplot(111)
        canvas.setMinimumWidth(420)
        return canvas

    def _create_stats_filters(self, page_key, filter_keys):
        filters = QWidget()
        filters_layout = QtWidgets.QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        page_filters = {}
        labels = {
            "customers": ("Kunden:", "Kunden"),
            "parameters": ("Parameter:", "Parameter"),
        }
        for filter_key in filter_keys:
            label, plural_name = labels[filter_key]
            filters_layout.addWidget(QLabel(label))
            filter_dropdown = MultiSelectComboBox(plural_name)
            filter_dropdown.selectionChanged.connect(
                lambda key=page_key: self.apply_stats_filters(key)
            )
            filters_layout.addWidget(filter_dropdown)
            page_filters[filter_key] = filter_dropdown
        filters_layout.addStretch()
        self.stats_filters[page_key] = page_filters
        return filters

    def _stats_page(self, title, table, chart, controls=None):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        if controls is not None:
            page_layout.addWidget(controls)

        page_content = QtWidgets.QHBoxLayout()

        table_group = QGroupBox(title)
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(table)
        page_content.addWidget(table_group, 1)

        chart_group = QGroupBox("Diagramm")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.addWidget(chart)
        page_content.addWidget(chart_group, 1)
        page_layout.addLayout(page_content, 1)
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
        self.stats_request_rows = cursor.fetchall()
        customers = sorted(
            {row[0].strip() for row in self.stats_request_rows if row[0]},
            key=str.casefold,
        )
        parameters = sorted(
            {
                parameter.strip()
                for _, parameter_text in self.stats_request_rows
                for parameter in (parameter_text or "").split(",")
                if parameter.strip()
            },
            key=str.casefold,
        )
        for page_filters in self.stats_filters.values():
            if "customers" in page_filters:
                page_filters["customers"].set_options(customers)
            if "parameters" in page_filters:
                page_filters["parameters"].set_options(parameters)
        for page_key in self.stats_filters:
            self.apply_stats_filters(page_key)

    def apply_stats_filters(self, page_key, *_args):
        page_filters = self.stats_filters[page_key]
        customer_filter = page_filters.get("customers")
        parameter_filter = page_filters.get("parameters")
        filtered_requests = filter_request_rows(
            getattr(self, "stats_request_rows", []),
            customer_filter.selected_values()
            if customer_filter is not None
            else set(),
            parameter_filter.selected_values()
            if parameter_filter is not None
            else set(),
        )
        parameter_usage, parameter_customers, customer_requests = (
            aggregate_request_stats(filtered_requests)
        )
        page_data = {
            "parameters": (
                self.parameter_stats_table,
                self.parameter_stats_chart,
                parameter_usage,
                lambda row: row[0],
            ),
            "parameter_customers": (
                self.parameter_customer_stats_table,
                self.parameter_customer_stats_chart,
                parameter_customers,
                lambda row: f"{row[0]} \u2014 {row[1]}",
            ),
            "customers": (
                self.customer_stats_table,
                self.customer_stats_chart,
                customer_requests,
                lambda row: row[0],
            ),
        }
        table, chart, rows, label_for_row = page_data[page_key]
        self._fill_stats_table(table, rows)
        self._draw_stats_chart(chart, rows, label_for_row)

    def _draw_stats_chart(self, canvas, rows, label_for_row):
        axes = canvas.axes
        axes.clear()
        visible_rows = rows[:15]
        if not visible_rows:
            axes.text(
                0.5,
                0.5,
                "Noch keine Daten",
                ha="center",
                va="center",
                color="#64748b",
                transform=axes.transAxes,
            )
            axes.set_axis_off()
            canvas.draw_idle()
            return

        labels = [label_for_row(row) for row in visible_rows]
        values = [row[-1] for row in visible_rows]
        axes.set_axis_on()
        axes.barh(labels, values, color="#3b82f6")
        axes.invert_yaxis()
        axes.set_xlabel("Anzahl")
        axes.xaxis.set_major_locator(MaxNLocator(integer=True))
        axes.grid(axis="x", color="#e2e8f0", linewidth=0.8)
        axes.set_axisbelow(True)
        axes.spines["top"].set_visible(False)
        axes.spines["right"].set_visible(False)
        axes.tick_params(axis="y", labelsize=8)
        canvas.draw_idle()

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
