"""Styling and shared layout helpers for the main GUI window."""

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QCalendarWidget, QVBoxLayout, QWidget


class WindowStyleMixin:
    def configure_calendar(self, calendar):
        font = calendar.font()
        font.setPointSize(8)
        calendar.setFont(font)
        calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        calendar.setStyleSheet("""
        QCalendarWidget {
            font-size: 8pt;
        }
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
        calendar.setFont(font)
        calendar.setMinimumSize(calendar.sizeHint())
        calendar.setMaximumSize(calendar.sizeHint())

    def calendar_panel(self, calendar, left_margin=0, right_margin=0):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(left_margin, 4, right_margin, 6)
        layout.setSpacing(0)
        layout.addWidget(calendar)
        return panel

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
