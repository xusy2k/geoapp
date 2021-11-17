import click
from flask import current_app, g
from flask.cli import with_appcontext
import os
import pandas as pd
import psycopg2
import sqlite3


from collections import namedtuple


def dictfetchall(cursor):
    """Return all rows from a cursor as a namedtuple

    :param cursor
    """
    desc = cursor.description
    headers = [col[0] for col in desc]
    result = []
    for row in cursor.fetchall():
        item = dict(zip(headers, row))
        result.append(item)
    return result


def namedtuplefetchall(cursor):
    """Return all rows from a cursor as a namedtuple

    :param cursor
    """
    desc = cursor.description
    nt_result = namedtuple("Result", [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


def get_db():
    if "db" not in g:
        db_host = os.getenv("FLASK_DB_HOST")
        db_name = os.getenv("FLASK_DB_NAME")
        db_port = os.getenv("FLASK_DB_PORT")
        db_user = os.getenv("FLASK_DB_USER")
        db_pass = os.getenv("FLASK_DB_PASS")
        if db_host and db_name and db_user:
            db_kw = dict(
                {
                    "dbname": db_name,
                    "user": db_user,
                    "password": db_pass,
                    "host": db_host,
                }
            )
            if db_port:
                db_kw["port"] = db_port

            conn = psycopg2.connect(**db_kw)
            g.db = conn
        else:
            g.db = sqlite3.connect(
                current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def init_postgres_db():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    file_name = os.path.join(data_dir, "postal_codes.csv")
    df = pd.read_csv(file_name)  # , usecols=["the_geom", "code", "id"])
    sql_tmp = (
        "INSERT INTO app_postalcode(id, code, the_geom) VALUES"
        "(%(id)s, '%(code)s', ST_Multi(ST_GeomFromEWKT('%(the_geom)s')))"
    )
    for index, row in df.iterrows():
        sql = sql_tmp % row
        print(sql)
        db_query(sql)

    file_name = os.path.join(data_dir, "paystats.csv")
    df = pd.read_csv(file_name)
    sql_tmp = (
        "INSERT INTO app_paystats (id, postal_code_id, amount, p_month, p_age, p_gender)"
        "VALUES(%(id)s, %(postal_code_id)s, '%(amount)s', '%(p_month)s', '%(p_age)s', '%(p_gender)s')"
    )
    for index, row in df.iterrows():
        sql = sql_tmp % row
        print(sql)
        db_query(sql)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


@click.command("init-postgres-db")
@with_appcontext
def init_postgres_db_command():
    """Clear the existing data and create new tables."""
    init_postgres_db()
    click.echo("Initialized the database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(init_postgres_db_command)


def db_query(sql):
    """Executes raw query on the database

    sample of use:

    results = db_query('SELECT id, username from app_user')

    :param sql: SQL to execute
    :return: List of dictonaries // number of affected rows
    """
    connection = get_db()
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        if "select " in sql.replace("\n", "").replace("\t", "").lower():
            result = dictfetchall(cursor)
        else:
            connection.commit()
            result = cursor.rowcount
        return result
    except Exception as e:
        pass
    finally:
        cursor.close()
