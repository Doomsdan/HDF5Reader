"""Export workflow for the main GUI window."""

import datetime
import os
import traceback

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from gui_sql import customer_id_query, insert_anfrage_query, insert_customer_query


class ExportMixin:
    def run(self, save_to_db=True):
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.console.clear()
            self.allesgut = True
            print("Running...")
            QApplication.processEvents()

            self._validate_export_inputs()
            kunde = self.customer_combo.currentText().strip()
            if not kunde:
                print("Bitte einen Kunden angeben.")
                self.allesgut = False
            elif self.allesgut:
                self._prepare_export_path(kunde)

            self.del_t = 1

            if self.allesgut == True:
                if save_to_db:
                    self._save_request(kunde)
                self._export_hdf5()
            else:
                print("Please check inputs")
        finally:
            QApplication.restoreOverrideCursor()

    def _validate_export_inputs(self):
        self.hdf5_file = self.hdf5_location
        try:
            assert self.hdf5_file and os.path.isfile(self.hdf5_file)
        except:
            print("Invalid or missing HDF5 file")
            self.allesgut = False

        if not self.output_folder:
            print("Invalid or missing output folder")
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

    def _prepare_export_path(self, kunde):
        now = datetime.datetime.now()
        time_str = now.strftime("%Y%m%d%H%M%S")
        safe_kunde = kunde.replace(" ", "")
        filename = f"{safe_kunde}_{time_str}.txt"

        try:
            os.makedirs(self.output_folder, exist_ok=True)
            self.out_dir = os.path.join(self.output_folder, filename)
        except Exception as e:
            print("Fehler beim Erstellen des Export-Ordners:", e)
            self.allesgut = False

    def _save_request(self, kunde):
        try:
            cursor = self.conn.cursor()
            cursor.execute(insert_customer_query(), (kunde,))
            cursor.execute(customer_id_query(), (kunde,))
            kunden_id = cursor.fetchone()[0]

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

    def _export_hdf5(self):
        try:
            import lauchaecker_hdf5_tools as lht
            lht.hdf52txt(
                start=str(self.pydate_start) + "T00:00:00",
                end=str(self.pydate_end) + "T00:00:00",
                varpath=self.var_list,
                outfile=str(self.out_dir),
                del_t=self.del_t,
                hdf5=self.hdf5_file,
            )
            print("Finished")
        except Exception as ex:
            print(ex)
            traceback.print_exc()
