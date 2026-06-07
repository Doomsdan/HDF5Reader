
import sys
import os
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QObject,pyqtSignal
from PyQt5.QtWidgets import QComboBox, QCalendarWidget, QGridLayout, QVBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, QDialog, QTextBrowser, QApplication, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
import traceback
import sqlite3
import datetime
import lauchaecker_config as lconf

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
        layout = QtWidgets.QHBoxLayout(self)

        # Linke Liste: Verfügbare Parameter
        self.list_available = QtWidgets.QListWidget()
        self.list_available.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_available.addItems(available_vars)

        # Rechte Liste: Ausgewählte Parameter
        self.list_selected = QtWidgets.QListWidget()
        self.list_selected.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Buttons in der Mitte
        vbox_buttons = QtWidgets.QVBoxLayout()
        self.btn_add = QtWidgets.QPushButton(">>")
        self.btn_remove = QtWidgets.QPushButton("<<")

        vbox_buttons.addStretch()
        vbox_buttons.addWidget(self.btn_add)
        vbox_buttons.addWidget(self.btn_remove)
        vbox_buttons.addStretch()

        layout.addWidget(self.list_available)
        layout.addLayout(vbox_buttons)
        layout.addWidget(self.list_selected)

        self.btn_add.clicked.connect(self.add_item)
        self.btn_remove.clicked.connect(self.remove_item)

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

class Window(QTabWidget):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle('HDF5 GUI')
        self.setup_database()

        self.tab_home = QWidget()
        self.tab_history = QWidget()
        self.addTab(self.tab_home, "Anfrage")
        self.addTab(self.tab_history, "Historie")

        self.home()
        self.history_ui()

    def setup_database(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anfragen_log.db')
        self.conn = sqlite3.connect(db_path)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Kunden (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Anfragen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kunden_id INTEGER,
                zeitpunkt TEXT,
                start_date TEXT,
                end_date TEXT,
                parameter TEXT,
                FOREIGN KEY(kunden_id) REFERENCES Kunden(id)
            )
        ''')
        self.conn.commit()

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
        self.grid.addWidget(self.customer_lab, i, 0)
        self.grid.addWidget(self.customer_combo, i, 1, 1, 11)
        self.customer_lab.setToolTip('Name des Kunden auswählen oder neu eingeben')
        self.customer_combo.setToolTip('Name des Kunden auswählen oder neu eingeben')
        self.load_customers()
        i += 1

        self.duration_lab = QLabel('Duration:')
        self.start_lab = QLabel('Start date:')
        self.end_lab = QLabel('End date:')
        self.cal_start = QtWidgets.QCalendarWidget()
        self.cal_end = QtWidgets.QCalendarWidget()

        self.grid.addWidget(self.duration_lab, i, 0)
        self.grid.addWidget(self.start_lab, i, 1)
        self.grid.addWidget(self.end_lab, i, 10)
        self.grid.addWidget(self.cal_start, i+1, 1)
        self.grid.addWidget(self.cal_end, i+1, 10 )

       # self.connect(self.cal_start, QtCore.SIGNAL('selectionChanged()'), self.date_changed)
        self.cal_start.selectionChanged.connect(self.date_changed)
        self.cal_end.selectionChanged.connect(self.date_changed)
        self.duration_lab.setToolTip(str('Select the duration'))
        self.start_lab.setToolTip(str('Select Start date'))
        self.end_lab.setToolTip(str('Select End date'))
        i += 2

        self.var_lab = QLabel('Parameters:')
        alle_variablen = ["Ta_2m", "rh_2m", "Ta_18m", "rh_18m", "p", "rr_01", "rr_02", "rr_03", "rr_04", "rr_05",
                          "rr_06", "rr_07", "rr_09", "rr_10", "u_2m", "dd_2m", "dd_2m_sigma", "u_19m", "dd_19m",
                          "dd_19m_sigma", "G", "RK", "A", "E", "CaseTemp", "TC_01", "TC_02", "Tg_2cm", "Tg_5cm",
                          "Tg_10cm", "Tg_20cm", "Tg_50cm", "Qg", "VWC_01", "VWC_02", "VWC_03", "VWC_04", "VWC_05"]
        self.transfer_list = TransferList(alle_variablen)
        
        self.right_layout.addWidget(self.var_lab)
        self.right_layout.addWidget(self.transfer_list)

        self.console = QTextBrowser(self)
        self.console_lab = QLabel('Console')
        self.grid.addWidget(self.console_lab, i, 0)
        self.grid.addWidget(self.console, i, 1, 1, 12)
        XStream.stdout().messageWritten.connect(self.console.insertPlainText)
        XStream.stderr().messageWritten.connect(self.console.insertPlainText)
        i += 1

        self.run_lab = QLabel(' ')
        self.run_btn = QPushButton('Run')
        self.run_btn.clicked.connect(lambda checked: self.run(save_to_db=True))
        self.grid.addWidget(self.run_lab, i, 0)
        self.grid.addWidget(self.run_btn, i, 1, 1, 12)

        self.main_layout.addLayout(self.grid)
        self.main_layout.addLayout(self.right_layout)
        self.tab_home.setLayout(self.main_layout)

    def history_ui(self):
        layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels(['ID', 'Kunde', 'Zeitpunkt', 'Start', 'Ende', 'Parameter', 'Laden', 'Ausführen'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
        btn_layout = QtWidgets.QHBoxLayout()
        self.refresh_btn = QPushButton('Aktualisieren')
        self.refresh_btn.clicked.connect(self.load_history)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.history_table)
        self.tab_history.setLayout(layout)
        self.load_history()

    def load_history(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT Anfragen.id, Kunden.name, Anfragen.zeitpunkt, Anfragen.start_date, Anfragen.end_date, Anfragen.parameter
                FROM Anfragen
                JOIN Kunden ON Anfragen.kunden_id = Kunden.id
                ORDER BY Anfragen.zeitpunkt DESC
            ''')
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

    def load_customers(self):
        self.customer_combo.clear()
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT name FROM Kunden ORDER BY name ASC')
            kunden = cursor.fetchall()
            for kunde in kunden:
                self.customer_combo.addItem(kunde[0])
        except Exception as e:
            print("Fehler beim Laden der Kunden aus der Datenbank:", e)

    def date_changed(self):
        try:
            date_start = self.cal_start.selectedDate()
            self.pydate_start = date_start.toPyDate()
            date_end = self.cal_end.selectedDate()
            self.pydate_end = date_end.toPyDate()
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
        self.console.clear()
        self.allesgut = True
        print("Running...")

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
                    cursor.execute('INSERT OR IGNORE INTO Kunden (name) VALUES (?)', (kunde,))
                    cursor.execute('SELECT id FROM Kunden WHERE name = ?', (kunde,))
                    kunden_id = cursor.fetchone()[0]
                    
                    # Neuen Kunden direkt in die laufende Dropdown-Liste aufnehmen
                    if self.customer_combo.findText(kunde) == -1:
                        self.customer_combo.addItem(kunde)

                    jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    param_str = ",".join(self.var_list)
                    
                    cursor.execute('''
                        INSERT INTO Anfragen (kunden_id, zeitpunkt, start_date, end_date, parameter)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (kunden_id, jetzt, str(self.pydate_start), str(self.pydate_end), param_str))
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Window()
    main.show()
    sys.exit(app.exec_())