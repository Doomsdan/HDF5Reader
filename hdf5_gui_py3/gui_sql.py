"""SQL query builders for the HDF5 GUI."""

from datetime import date, timedelta

from pypika import Column, Order, Parameter, PostgreSQLQuery, Query, Table


KUNDEN_TABLE = Table("Kunden")
ANFRAGEN_TABLE = Table("Anfragen")


def sql_param():
    return Parameter("?")


def create_kunden_table_sql():
    return (
        Query.create_table(KUNDEN_TABLE)
        .if_not_exists()
        .columns(
            Column("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            Column("name", "TEXT", nullable=False),
        )
        .unique("name")
        .get_sql()
    )


def create_anfragen_table_sql():
    return (
        Query.create_table(ANFRAGEN_TABLE)
        .if_not_exists()
        .columns(
            Column("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
            Column("kunden_id", "INTEGER"),
            Column("zeitpunkt", "TEXT"),
            Column("start_date", "TEXT"),
            Column("end_date", "TEXT"),
            Column("parameter", "TEXT"),
        )
        .foreign_key(["kunden_id"], KUNDEN_TABLE, ["id"])
        .get_sql()
    )


def history_query(kunde_filter, datum_filter):
    query = (
        Query.from_(ANFRAGEN_TABLE)
        .join(KUNDEN_TABLE)
        .on(ANFRAGEN_TABLE.kunden_id == KUNDEN_TABLE.id)
        .select(
            ANFRAGEN_TABLE.id,
            KUNDEN_TABLE.name,
            ANFRAGEN_TABLE.zeitpunkt,
            ANFRAGEN_TABLE.start_date,
            ANFRAGEN_TABLE.end_date,
            ANFRAGEN_TABLE.parameter,
        )
    )
    params = []

    if kunde_filter:
        query = query.where(KUNDEN_TABLE.name.like(sql_param()))
        params.append(f"%{kunde_filter}%")
    if datum_filter:
        if isinstance(datum_filter, (tuple, list)):
            start_date, end_date = datum_filter
            day_after_end = (
                date.fromisoformat(end_date) + timedelta(days=1)
            ).isoformat()
            query = query.where(ANFRAGEN_TABLE.zeitpunkt >= sql_param())
            query = query.where(ANFRAGEN_TABLE.zeitpunkt < sql_param())
            params.extend([start_date, day_after_end])
        else:
            query = query.where(ANFRAGEN_TABLE.zeitpunkt.like(sql_param()))
            params.append(f"{datum_filter}%")

    query = query.orderby(ANFRAGEN_TABLE.zeitpunkt, order=Order.desc)
    return query.get_sql(), params


def customer_names_query():
    return (
        Query.from_(KUNDEN_TABLE)
        .select(KUNDEN_TABLE.name)
        .orderby(KUNDEN_TABLE.name, order=Order.asc)
        .get_sql()
    )


def insert_customer_query():
    return (
        PostgreSQLQuery.into(KUNDEN_TABLE)
        .columns(KUNDEN_TABLE.name)
        .insert(sql_param())
        .on_conflict(KUNDEN_TABLE.name)
        .do_nothing()
        .get_sql()
    )


def customer_id_query():
    return (
        Query.from_(KUNDEN_TABLE)
        .select(KUNDEN_TABLE.id)
        .where(KUNDEN_TABLE.name == sql_param())
        .get_sql()
    )


def insert_anfrage_query():
    return (
        Query.into(ANFRAGEN_TABLE)
        .columns(
            ANFRAGEN_TABLE.kunden_id,
            ANFRAGEN_TABLE.zeitpunkt,
            ANFRAGEN_TABLE.start_date,
            ANFRAGEN_TABLE.end_date,
            ANFRAGEN_TABLE.parameter,
        )
        .insert(sql_param(), sql_param(), sql_param(), sql_param(), sql_param())
        .get_sql()
    )
