"""Settings tab and database import helpers for the main GUI window."""

import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

import lauchaecker_config as lconf
from gui_sql import (
    create_anfragen_table_sql,
    create_kunden_table_sql,
    ensure_anfragen_time_delta_column,
)


class SettingsMixin:
    settings_path = Path(__file__).resolve().parent / "settings.json"

    def load_settings(self):
        self.settings_path = Path(self.settings_path)
        settings = {}
        try:
            with self.settings_path.open("r", encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError):
            pass

        if not isinstance(settings, dict):
            settings = {}
        self.app_settings = settings
        self.hdf5_location = str(
            settings.get("hdf5_file") or lconf.hdf5_filename
        )
        self.output_folder = str(
            settings.get("output_folder")
            or Path(self.hdf5_location).parent / "Export"
        )
        self.shadow_mode = bool(settings.get("shadow_mode", False))
        lconf.hdf5_filename = self.hdf5_location

    def settings_ui(self):
        layout = QVBoxLayout(self.tab_settings)

        layout.addWidget(QLabel("HDF5 File Location:"))
        hdf5_layout = QHBoxLayout()
        self.settings_hdf5_line = QLineEdit(self.hdf5_location)
        self.settings_hdf5_browse_button = QPushButton("Browse")
        self.settings_hdf5_browse_button.clicked.connect(
            self.select_hdf5_location
        )
        hdf5_layout.addWidget(self.settings_hdf5_line)
        hdf5_layout.addWidget(self.settings_hdf5_browse_button)
        layout.addLayout(hdf5_layout)

        layout.addWidget(QLabel("Output Folder:"))
        output_layout = QHBoxLayout()
        self.settings_output_folder_line = QLineEdit(self.output_folder)
        self.settings_output_folder_browse_button = QPushButton("Browse")
        self.settings_output_folder_browse_button.clicked.connect(
            self.select_output_folder
        )
        output_layout.addWidget(self.settings_output_folder_line)
        output_layout.addWidget(self.settings_output_folder_browse_button)
        layout.addLayout(output_layout)

        self.settings_shadow_mode_checkbox = QCheckBox(
            "Shadow Modus aktivieren"
        )
        self.settings_shadow_mode_checkbox.setChecked(self.shadow_mode)
        self.settings_shadow_mode_checkbox.setToolTip(
            "Im Shadow Modus werden keine Daten in der Datenbank gespeichert."
        )
        layout.addWidget(self.settings_shadow_mode_checkbox)

        self.settings_save_button = QPushButton("Save Settings")
        self.settings_save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.settings_save_button)

        self.hdf5_settings_status = QLabel("")
        self.hdf5_settings_status.setWordWrap(True)
        layout.addWidget(self.hdf5_settings_status)

        self.import_database_button = QPushButton("Import Database")
        self.import_database_button.clicked.connect(self.import_database)
        layout.addWidget(self.import_database_button)

        self.database_import_status = QLabel("")
        self.database_import_status.setWordWrap(True)
        layout.addWidget(self.database_import_status)
        layout.addStretch()

    def select_hdf5_location(self, checked=False):
        start_path = self.settings_hdf5_line.text().strip()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "HDF5-Datei auswählen",
            start_path,
            "HDF5-Dateien (*.h5 *.hdf5);;Alle Dateien (*)",
        )
        if not file_name:
            return False

        self.settings_hdf5_line.setText(file_name)
        return True

    def select_output_folder(self, checked=False):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Output Folder auswählen",
            self.settings_output_folder_line.text().strip(),
        )
        if not folder:
            return False

        self.settings_output_folder_line.setText(folder)
        return True

    def save_settings(self, checked=False):
        hdf5_path = self.settings_hdf5_line.text().strip()
        output_folder = self.settings_output_folder_line.text().strip()
        shadow_mode = self.settings_shadow_mode_checkbox.isChecked()
        if not hdf5_path:
            self.hdf5_settings_status.setText(
                "Bitte eine HDF5-Datei angeben."
            )
            return False
        if not output_folder:
            self.hdf5_settings_status.setText(
                "Bitte einen Output Folder angeben."
            )
            return False
        temp_path = self.settings_path.with_suffix(".json.tmp")
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.app_settings["hdf5_file"] = hdf5_path
            self.app_settings["output_folder"] = output_folder
            self.app_settings["shadow_mode"] = shadow_mode
            self.app_settings.pop("working_directory", None)
            with temp_path.open("w", encoding="utf-8") as settings_file:
                json.dump(
                    self.app_settings,
                    settings_file,
                    ensure_ascii=False,
                    indent=2,
                )
                settings_file.write("\n")
            os.replace(str(temp_path), str(self.settings_path))
        except OSError as error:
            temp_path.unlink(missing_ok=True)
            self.hdf5_settings_status.setText(
                f"Settings konnten nicht gespeichert werden: {error}"
            )
            return False

        self.hdf5_location = hdf5_path
        self.output_folder = output_folder
        self.shadow_mode = shadow_mode
        lconf.hdf5_filename = self.hdf5_location
        self.hdf5_settings_status.setText("Settings wurden gespeichert.")
        return True

    def import_database(self, checked=False, source_path=None):
        if self.shadow_mode:
            self.database_import_status.setText(
                "Shadow Modus ist aktiv: Datenbank wurde nicht importiert."
            )
            return False

        if source_path is None:
            source_path, _ = QFileDialog.getOpenFileName(
                self,
                "SQLite-Datenbank importieren",
                "",
                "SQLite-Datenbanken (*.db *.sqlite *.sqlite3);;Alle Dateien (*)",
            )
        if not source_path:
            return False

        source = Path(source_path)
        destination = Path(self.database_path)
        temp_path = None

        try:
            if not source.is_file():
                raise OSError("Die ausgewählte Datei wurde nicht gefunden.")
            if source.resolve() == destination.resolve():
                self.database_import_status.setText(
                    "Diese Datenbank befindet sich bereits im Programmordner."
                )
                return False

            destination.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(
                prefix="anfragen_log_",
                suffix=".importing",
                dir=str(destination.parent),
            )
            os.close(handle)
            temp_path = Path(temp_name)

            # Context management commits SQLite transactions but does not close
            # connections, which prevents replacing the file on Windows.
            with closing(sqlite3.connect(str(source))) as source_conn:
                check_result = source_conn.execute("PRAGMA quick_check").fetchone()
                if not check_result or check_result[0] != "ok":
                    raise sqlite3.DatabaseError("Die SQLite-Prüfung ist fehlgeschlagen.")

                with closing(sqlite3.connect(str(temp_path))) as imported_conn:
                    source_conn.backup(imported_conn)
                    imported_conn.execute(create_kunden_table_sql())
                    imported_conn.execute(create_anfragen_table_sql())
                    ensure_anfragen_time_delta_column(imported_conn)
                    imported_conn.commit()

            self.conn.close()
            os.replace(str(temp_path), str(destination))
            temp_path = None
            self.conn = sqlite3.connect(str(destination))

            self.load_customers()
            self.load_history()
            self.load_stats()
            self.database_import_status.setText(
                f"Datenbank erfolgreich importiert: {source.name}"
            )
            return True
        except (OSError, sqlite3.Error) as error:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            try:
                self.conn.execute("SELECT 1")
            except sqlite3.Error:
                self.conn = sqlite3.connect(str(destination))
            self.database_import_status.setText(
                f"Datenbank konnte nicht importiert werden: {error}"
            )
            return False
