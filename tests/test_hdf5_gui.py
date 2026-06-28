import importlib.util
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest


QtCore = pytest.importorskip("PyQt5.QtCore")
QtTest = pytest.importorskip("PyQt5.QtTest")


def _load_gui_module(monkeypatch):
    gui_dir = Path(__file__).resolve().parents[1] / "hdf5_gui_py3"
    gui_file = gui_dir / "hdf5_gui.py"
    monkeypatch.syspath_prepend(str(gui_dir))

    existing_module = sys.modules.get("hdf5_gui")
    if existing_module is not None:
        existing_file = getattr(existing_module, "__file__", None)
        if existing_file and Path(existing_file).resolve() == gui_file:
            return existing_module

    spec = importlib.util.spec_from_file_location("hdf5_gui", gui_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hdf5_gui"] = module
    spec.loader.exec_module(module)
    return module


def _install_temp_database(monkeypatch, gui_module, db_path):
    def setup_database(self):
        self.database_path = str(db_path)
        if self.shadow_mode:
            self.conn = sqlite3.connect(":memory:")
        else:
            self.conn = sqlite3.connect(self.database_path)
        cursor = self.conn.cursor()
        cursor.execute(gui_module.create_kunden_table_sql())
        cursor.execute(gui_module.create_anfragen_table_sql())
        if not self.shadow_mode:
            cursor.execute(
                gui_module.insert_customer_query(),
                ("Testkunde",),
            )
        self.conn.commit()

    monkeypatch.setattr(gui_module.Window, "setup_database", setup_database)


@pytest.fixture
def gui_module(monkeypatch, sample_lauchaecker_hdf5, tmp_path):
    hdf5_gui = _load_gui_module(monkeypatch)

    monkeypatch.setattr(
        hdf5_gui.lconf,
        "hdf5_filename",
        str(sample_lauchaecker_hdf5.path),
    )
    _install_temp_database(monkeypatch, hdf5_gui, tmp_path / "anfragen_log.db")
    monkeypatch.setattr(
        hdf5_gui.Window,
        "settings_path",
        tmp_path / "settings.json",
    )
    return hdf5_gui


@pytest.fixture
def restored_process_state():
    cwd = Path.cwd()
    stdout = sys.stdout
    stderr = sys.stderr
    yield
    os.chdir(cwd)
    sys.stdout = stdout
    sys.stderr = stderr


@pytest.mark.gui
def test_transfer_list_moves_selected_variables(qapp, gui_module):
    widget = gui_module.TransferList(["Ta_2m", "rh_2m"])
    widget.show()
    qapp.processEvents()

    widget.list_available.item(0).setSelected(True)
    QtTest.QTest.mouseClick(widget.btn_add, QtCore.Qt.LeftButton)
    qapp.processEvents()

    assert widget.get_selected_variables() == ["Ta_2m"]

    widget.close()


@pytest.mark.gui
def test_window_starts_with_generated_hdf5_testdata(
    qapp,
    gui_module,
    sample_lauchaecker_hdf5,
    restored_process_state,
):
    window = gui_module.Window()
    try:
        window.show()
        qapp.processEvents()

        assert window.count() == 4
        assert window.tabText(0) == "Anfrage"
        assert window.tabText(1) == "Historie"
        assert window.tabText(2) == "Statistik"
        assert window.tabText(3) == ""
        assert window.stats_navigation.count() == 3
        assert window.stats_navigation.currentRow() == 0
        assert window.stats_pages.currentIndex() == 0
        assert window.parameter_stats_chart.axes is not None
        assert window.parameter_customer_stats_chart.axes is not None
        assert window.customer_stats_chart.axes is not None
        window.stats_navigation.setCurrentRow(2)
        qapp.processEvents()
        assert window.stats_pages.currentIndex() == 2
        assert window.tab_settings.layout() is not None
        assert not window.tabBar().isTabVisible(window.settings_tab_index)
        assert window.tabBar().tabSizeHint(window.settings_tab_index).isEmpty()
        assert window.cornerWidget(QtCore.Qt.TopRightCorner) is window.settings_tab_button
        QtTest.QTest.mouseClick(window.settings_tab_button, QtCore.Qt.LeftButton)
        qapp.processEvents()
        assert window.currentWidget() is window.tab_settings
        assert window.settings_tab_button.property("selected") is True
        assert window.import_database_button.text() == "Import Database"
        assert window.settings_hdf5_line.text() == str(sample_lauchaecker_hdf5.path)
        assert window.settings_output_folder_line.text() == str(
            sample_lauchaecker_hdf5.path.parent / "Export"
        )
        assert not window.settings_shadow_mode_checkbox.isChecked()
        assert window.windowState() & QtCore.Qt.WindowMaximized
        assert not hasattr(window, "hdf5_line")
        assert not hasattr(window, "working_dir_line")
        assert window.transfer_list.list_available.count() > 0
        assert window.main_layout.stretch(0) == 2
        assert window.main_layout.stretch(1) == 1
        assert window.main_layout.spacing() == 14
        assert window.grid.horizontalSpacing() == 10
        assert window.grid.verticalSpacing() == 10
        assert window.right_layout.spacing() == 10
        assert window.transfer_list.maximumWidth() == 700
        assert window.transfer_list.list_available.minimumWidth() == 160
        assert window.transfer_list.list_selected.minimumWidth() == 160
        assert window.time_delta_input.text() == "1"
        assert [
            window.time_delta_unit.itemText(index)
            for index in range(window.time_delta_unit.count())
        ] == ["Minuten", "Stunden", "Tage"]
        assert window.transfer_list.available_lab.text() == "Verfügbar"
        assert window.transfer_list.selected_lab.text() == "Ausgewählt"
        assert window.start_calendar_panel.layout().contentsMargins().top() == 4
        assert window.start_calendar_panel.layout().contentsMargins().right() == 16
        assert window.start_calendar_panel.layout().contentsMargins().bottom() == 6
        assert window.end_calendar_panel.layout().contentsMargins().left() == 16
        for calendar in (window.cal_start, window.cal_end):
            assert calendar.font().pointSize() == 8
            assert calendar.horizontalHeaderFormat() == gui_module.QCalendarWidget.ShortDayNames
            assert calendar.verticalHeaderFormat() == gui_module.QCalendarWidget.NoVerticalHeader
            assert calendar.maximumHeight() >= calendar.sizeHint().height()
            assert calendar.minimumSize().expandedTo(calendar.sizeHint()) == calendar.minimumSize()
            assert calendar.sizePolicy().horizontalPolicy() == gui_module.QtWidgets.QSizePolicy.Fixed
            assert calendar.maximumSize() == calendar.sizeHint()
    finally:
        window.conn.close()
        window.close()


@pytest.mark.gui
def test_settings_imports_sqlite_database(
    qapp,
    gui_module,
    tmp_path,
    restored_process_state,
):
    source_db = tmp_path / "import.sqlite"
    with sqlite3.connect(source_db) as conn:
        conn.execute(gui_module.create_kunden_table_sql())
        conn.execute(gui_module.create_anfragen_table_sql())
        conn.execute("INSERT INTO Kunden (name) VALUES (?)", ("Importkunde",))

    window = gui_module.Window()
    try:
        assert window.import_database(source_path=str(source_db))
        assert window.database_import_status.text() == (
            "Datenbank erfolgreich importiert: import.sqlite"
        )

        customers = [
            window.customer_combo.itemText(index)
            for index in range(window.customer_combo.count())
        ]
        assert customers == ["Importkunde"]

        with sqlite3.connect(window.database_path) as conn:
            assert conn.execute("SELECT name FROM Kunden").fetchall() == [
                ("Importkunde",),
            ]
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_time_delta_is_converted_to_minutes(qapp, gui_module, restored_process_state):
    window = gui_module.Window()
    try:
        expected_minutes = {
            "Minuten": 2,
            "Stunden": 120,
            "Tage": 2880,
        }
        window.time_delta_input.setText("2")

        for unit, expected in expected_minutes.items():
            window.time_delta_unit.setCurrentText(unit)
            assert window.time_delta_minutes() == expected
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_parameter_customer_stats_can_be_filtered(
    qapp,
    gui_module,
    restored_process_state,
):
    window = gui_module.Window()
    try:
        window.conn.execute("INSERT INTO Kunden (name) VALUES (?)", ("Andere",))
        customer_ids = dict(
            window.conn.execute("SELECT name, id FROM Kunden").fetchall()
        )
        window.conn.executemany(
            """
            INSERT INTO Anfragen
                (kunden_id, zeitpunkt, start_date, end_date, parameter)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (customer_ids["Testkunde"], "2026-06-01", "", "", "Ta_2m,rh_2m"),
                (customer_ids["Andere"], "2026-06-02", "", "", "Ta_2m"),
            ],
        )
        window.conn.commit()
        window.load_stats()

        assert window.parameter_customer_stats_table.rowCount() == 3

        def check_value(filter_dropdown, value):
            filter_dropdown.set_selected_values(
                filter_dropdown.selected_values() | {value}
            )

        breakdown_filters = window.stats_filters["parameter_customers"]
        check_value(breakdown_filters["customers"], "Testkunde")
        assert window.parameter_customer_stats_table.rowCount() == 2

        check_value(breakdown_filters["parameters"], "Ta_2m")
        check_value(breakdown_filters["parameters"], "rh_2m")
        assert window.parameter_customer_stats_table.rowCount() == 2
        check_value(breakdown_filters["customers"], "Andere")
        assert window.parameter_customer_stats_table.rowCount() == 3
        assert len(window.parameter_customer_stats_chart.axes.patches) == 3
        assert breakdown_filters["customers"].lineEdit().text() == (
            "Andere, Testkunde"
        )

        parameter_filters = window.stats_filters["parameters"]
        assert set(parameter_filters) == {"parameters"}
        check_value(parameter_filters["parameters"], "rh_2m")
        assert window.parameter_stats_table.rowCount() == 1

        customer_filters = window.stats_filters["customers"]
        assert set(customer_filters) == {"customers"}
        check_value(customer_filters["customers"], "Andere")
        assert window.customer_stats_table.rowCount() == 1
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_hdf5_location_is_persisted_between_windows(
    qapp,
    gui_module,
    sample_lauchaecker_hdf5,
    restored_process_state,
):
    first_window = gui_module.Window()
    try:
        first_window.settings_hdf5_line.setText(
            str(sample_lauchaecker_hdf5.path)
        )
        output_folder = sample_lauchaecker_hdf5.path.parent / "Text Exports"
        first_window.settings_output_folder_line.setText(str(output_folder))
        assert first_window.save_settings()
        assert json.loads(
            first_window.settings_path.read_text(encoding="utf-8")
        ) == {
            "hdf5_file": str(sample_lauchaecker_hdf5.path),
            "output_folder": str(output_folder),
            "shadow_mode": False,
        }
    finally:
        first_window.conn.close()
        first_window.close()

    gui_module.lconf.hdf5_filename = "not-the-persisted-path.h5"
    second_window = gui_module.Window()
    try:
        assert second_window.settings_hdf5_line.text() == str(
            sample_lauchaecker_hdf5.path
        )
        assert second_window.hdf5_location == str(sample_lauchaecker_hdf5.path)
        assert second_window.settings_output_folder_line.text() == str(
            output_folder
        )
        assert second_window.output_folder == str(output_folder)
    finally:
        second_window.conn.close()
        second_window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_shadow_mode_is_persisted_between_windows(
    qapp,
    gui_module,
    sample_lauchaecker_hdf5,
    restored_process_state,
):
    first_window = gui_module.Window()
    try:
        first_window.settings_hdf5_line.setText(
            str(sample_lauchaecker_hdf5.path)
        )
        first_window.settings_output_folder_line.setText(
            str(sample_lauchaecker_hdf5.path.parent / "Export")
        )
        first_window.settings_shadow_mode_checkbox.setChecked(True)
        assert first_window.save_settings()
        assert json.loads(
            first_window.settings_path.read_text(encoding="utf-8")
        )["shadow_mode"] is True
    finally:
        first_window.conn.close()
        first_window.close()

    second_window = gui_module.Window()
    try:
        assert second_window.shadow_mode is True
        assert second_window.settings_shadow_mode_checkbox.isChecked()
        assert second_window.customer_combo.count() == 0
    finally:
        second_window.conn.close()
        second_window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_shadow_mode_blocks_database_import(
    qapp,
    gui_module,
    tmp_path,
    restored_process_state,
):
    source_db = tmp_path / "import.sqlite"
    with sqlite3.connect(source_db) as conn:
        conn.execute(gui_module.create_kunden_table_sql())

    window = gui_module.Window()
    try:
        window.shadow_mode = True
        assert not window.import_database(source_path=str(source_db))
        assert window.database_import_status.text() == (
            "Shadow Modus ist aktiv: Datenbank wurde nicht importiert."
        )
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_window_run_exports_selected_generated_hdf5_data(
    qapp,
    gui_module,
    sample_lauchaecker_hdf5,
    tmp_path,
    restored_process_state,
):
    window = gui_module.Window()
    try:
        export_hdf5 = tmp_path / "export_test.h5"
        export_root = tmp_path / "Text Exports"
        shutil.copy2(sample_lauchaecker_hdf5.path, export_hdf5)
        window.settings_hdf5_line.setText(str(export_hdf5))
        window.settings_output_folder_line.setText(str(export_root))
        assert window.save_settings()
        window.customer_combo.setCurrentText("Testkunde")
        window.cal_start.setSelectedDate(QtCore.QDate(
            sample_lauchaecker_hdf5.start_date.year,
            sample_lauchaecker_hdf5.start_date.month,
            sample_lauchaecker_hdf5.start_date.day,
        ))
        window.cal_end.setSelectedDate(QtCore.QDate(
            sample_lauchaecker_hdf5.end_date.year,
            sample_lauchaecker_hdf5.end_date.month,
            sample_lauchaecker_hdf5.end_date.day,
        ))
        window.date_changed()
        window.transfer_list.set_selected_variables(
            list(sample_lauchaecker_hdf5.variables)
        )
        window.time_delta_input.setText("1")
        window.time_delta_unit.setCurrentText("Stunden")
        qapp.processEvents()

        window.run(save_to_db=True)
        qapp.processEvents()

        console_text = window.console.toPlainText()
        export_files = list(export_root.rglob("*.txt"))
        assert len(export_files) == 1, (
            f"Expected one export file in {export_root}, found "
            f"{len(export_files)}.\nGUI console output:\n{console_text}"
        )

        content = export_files[0].read_text(encoding="utf-8")
        assert content.startswith("date\tTa_2m\trh_2m\n")
        assert len(content.splitlines()) == 1 + 24
        assert "Finished" in console_text
        assert window.history_table.rowCount() == 1
        assert window.history_table.columnCount() == 9
        assert window.history_table.item(0, 6).text() == "60"
        assert window.conn.execute(
            "SELECT time_delta FROM Anfragen"
        ).fetchone() == (60,)

        history_row = window.conn.execute(
            """
            SELECT Anfragen.id, Kunden.name, Anfragen.zeitpunkt,
                   Anfragen.start_date, Anfragen.end_date,
                   Anfragen.parameter, Anfragen.time_delta
            FROM Anfragen
            JOIN Kunden ON Anfragen.kunden_id = Kunden.id
            """
        ).fetchone()
        window.time_delta_input.setText("5")
        window.time_delta_unit.setCurrentText("Tage")
        window.load_entry_to_ui(history_row)
        assert window.time_delta_input.text() == "60"
        assert window.time_delta_unit.currentText() == "Minuten"
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None


@pytest.mark.gui
def test_shadow_mode_run_exports_without_saving_request(
    qapp,
    gui_module,
    sample_lauchaecker_hdf5,
    tmp_path,
    restored_process_state,
):
    window = gui_module.Window()
    try:
        export_hdf5 = tmp_path / "shadow_export_test.h5"
        export_root = tmp_path / "Shadow Exports"
        shutil.copy2(sample_lauchaecker_hdf5.path, export_hdf5)
        window.settings_hdf5_line.setText(str(export_hdf5))
        window.settings_output_folder_line.setText(str(export_root))
        window.settings_shadow_mode_checkbox.setChecked(True)
        assert window.save_settings()
        window.customer_combo.setCurrentText("Shadowkunde")
        window.cal_start.setSelectedDate(QtCore.QDate(
            sample_lauchaecker_hdf5.start_date.year,
            sample_lauchaecker_hdf5.start_date.month,
            sample_lauchaecker_hdf5.start_date.day,
        ))
        window.cal_end.setSelectedDate(QtCore.QDate(
            sample_lauchaecker_hdf5.end_date.year,
            sample_lauchaecker_hdf5.end_date.month,
            sample_lauchaecker_hdf5.end_date.day,
        ))
        window.date_changed()
        window.transfer_list.set_selected_variables(
            list(sample_lauchaecker_hdf5.variables)
        )
        qapp.processEvents()

        window.run(save_to_db=True)
        qapp.processEvents()

        console_text = window.console.toPlainText()
        assert "Shadow Modus aktiv" in console_text
        assert len(list(export_root.rglob("*.txt"))) == 1
        assert window.conn.execute("SELECT COUNT(*) FROM Anfragen").fetchone() == (0,)
        assert window.conn.execute(
            "SELECT COUNT(*) FROM Kunden WHERE name = ?",
            ("Shadowkunde",),
        ).fetchone() == (0,)
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None
