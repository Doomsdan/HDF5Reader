import sqlite3

from gui_sql import history_query


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
            parameter TEXT
        );
        INSERT INTO Kunden VALUES (1, 'Testkunde');
        INSERT INTO Anfragen VALUES
            (1, 1, '2026-06-20 08:00:00', '', '', ''),
            (2, 1, '2026-06-21 12:00:00', '', '', ''),
            (3, 1, '2026-06-22 23:59:59', '', '', ''),
            (4, 1, '2026-06-23 00:00:00', '', '', '');
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
