import sqlite3

from gui_sql import ensure_anfragen_time_delta_column, history_query


def _history_database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE Kunden (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE Anfragen (
            id INTEGER PRIMARY KEY,
            kunden_id INTEGER,
            zeitpunkt TEXT,
            start_date TEXT,
            end_date TEXT,
            parameter TEXT,
            time_delta INTEGER
        );
        INSERT INTO Kunden VALUES (1, 'Testkunde');
        INSERT INTO Anfragen VALUES
            (1, 1, '2026-06-20 08:00:00', '', '', '', 1),
            (2, 1, '2026-06-21 12:00:00', '', '', '', 60),
            (3, 1, '2026-06-22 23:59:59', '', '', '', 1440),
            (4, 1, '2026-06-23 00:00:00', '', '', '', 1);
        """
    )
    return connection


def test_history_query_filters_a_single_date():
    connection = _history_database()
    query, params = history_query("", "2026-06-21")

    rows = connection.execute(query, params).fetchall()

    assert [row[0] for row in rows] == [2]


def test_history_query_filters_an_inclusive_date_range():
    connection = _history_database()
    query, params = history_query("", ("2026-06-21", "2026-06-22"))

    rows = connection.execute(query, params).fetchall()

    assert [row[0] for row in rows] == [3, 2]


def test_existing_database_gets_time_delta_column():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE Anfragen (id INTEGER PRIMARY KEY)")

    ensure_anfragen_time_delta_column(connection)

    columns = {
        row[1] for row in connection.execute('PRAGMA table_info("Anfragen")')
    }
    assert "time_delta" in columns
