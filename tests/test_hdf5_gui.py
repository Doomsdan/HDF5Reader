import importlib.util
import os
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
        self.conn = sqlite3.connect(db_path)
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Kunden (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Anfragen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kunden_id INTEGER,
                zeitpunkt TEXT,
                start_date TEXT,
                end_date TEXT,
                parameter TEXT,
                FOREIGN KEY(kunden_id) REFERENCES Kunden(id)
            )
        """)
        cursor.execute(
            "INSERT OR IGNORE INTO Kunden (name) VALUES (?)",
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

        assert window.count() == 2
        assert window.tabText(0) == "Anfrage"
        assert window.tabText(1) == "Historie"
        assert window.hdf5_line.text() == str(sample_lauchaecker_hdf5.path)
        assert window.transfer_list.list_available.count() > 0
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
        window.working_dir = str(tmp_path)
        window.working_dir_line.setText(str(tmp_path))
        window.hdf5_line.setText(str(sample_lauchaecker_hdf5.path))
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
        qapp.processEvents()

        window.run(save_to_db=True)
        qapp.processEvents()

        console_text = window.console.toPlainText()
        export_root = tmp_path / "Export"
        export_files = list(export_root.rglob("*.txt"))
        assert len(export_files) == 1, (
            f"Expected one export file in {export_root}, found "
            f"{len(export_files)}.\nGUI console output:\n{console_text}"
        )

        content = export_files[0].read_text(encoding="utf-8")
        assert content.startswith("date\tTa_2m\trh_2m\n")
        assert len(content.splitlines()) == 1 + 24 * 60
        assert "Finished" in console_text
        assert window.history_table.rowCount() == 1
    finally:
        window.conn.close()
        window.close()
        gui_module.XStream._stdout = None
        gui_module.XStream._stderr = None
