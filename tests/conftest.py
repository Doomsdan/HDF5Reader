from pathlib import Path
from types import SimpleNamespace
from datetime import date, datetime, timedelta
import os
import re
import shutil
import sys
from uuid import uuid4

import numpy as np
import pytest
import tables


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HDF5_GUI_DIR = PROJECT_ROOT / "hdf5_gui_py3"

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

for path in (PROJECT_ROOT, HDF5_GUI_DIR):
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)


@pytest.fixture
def tmp_path(request):
    base = PROJECT_ROOT / "tests" / ".tmp"
    base.mkdir(exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name)[:80]
    path = base / f"{safe_name}_{uuid4().hex}"
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def qapp():
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def sample_lauchaecker_hdf5(tmp_path):
    hdf5_path = tmp_path / "lauchaecker_test.h5"
    start_date = date.today() - timedelta(days=7)
    end_date = start_date + timedelta(days=1)
    start_dt = datetime.combine(start_date, datetime.min.time())
    minutes = 24 * 60 + 2

    timestamps = np.array([
        (start_dt + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%S")
        for i in range(minutes)
    ], dtype="S19")
    temperature = np.linspace(10.0, 20.0, minutes, dtype=np.float32)
    humidity = np.linspace(60.0, 80.0, minutes, dtype=np.float32)

    with tables.open_file(hdf5_path, mode="w") as h5f:
        station_group = h5f.create_group("/", "lauchaecker")
        minute_group = h5f.create_group(station_group, "min_01")
        data_group = h5f.create_group(minute_group, "data")

        timestamp_node = h5f.create_earray(
            minute_group,
            "timestamps",
            atom=tables.StringAtom(itemsize=19),
            shape=(0,),
        )
        timestamp_node.append(timestamps)

        for varname, values in {
            "Ta_2m": temperature,
            "rh_2m": humidity,
        }.items():
            var_group = h5f.create_group(data_group, varname)
            data_node = h5f.create_earray(
                var_group,
                f"{varname}_data_raw",
                atom=tables.Float32Atom(dflt=np.nan),
                shape=(0,),
            )
            data_node.append(values)

    return SimpleNamespace(
        path=hdf5_path,
        start_date=start_date,
        end_date=end_date,
        variables=("Ta_2m", "rh_2m"),
    )
