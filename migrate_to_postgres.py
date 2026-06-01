"""
migrate_to_postgres.py — Copia todos los datos de users.db (SQLite) a PostgreSQL.
Ejecutar UNA sola vez antes del primer deploy con PostgreSQL.

Uso:
    pip install psycopg2-binary python-dotenv
    python migrate_to_postgres.py
"""
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

import psycopg2
from auth import init_db, init_wishlist_tables, init_email_verification_table
from admin_db import init_admin_tables

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "users.db")

TABLES_WITH_SERIAL = [
    "users",
    "wishlist",
    "hidden_deals",
    "email_verifications",
    "admin_log",
    "login_attempts",
    "cache_history",
    "error_log",
    "blacklist",
    "search_log",
    "click_log",
]


def migrate():
    if not os.path.exists(SQLITE_PATH):
        print(f"No se encontró {SQLITE_PATH} — nada que migrar.")
        return

    pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        raise RuntimeError("DATABASE_URL no está definida en el entorno")

    print("Creando tablas en PostgreSQL...")
    init_db()
    init_admin_tables()
    init_wishlist_tables()
    init_email_verification_table()
    print("  Tablas creadas.")

    sq = sqlite3.connect(SQLITE_PATH)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(pg_url)
    pg_cur = pg.cursor()

    tables = [
        "users",
        "wishlist",
        "hidden_deals",
        "email_verifications",
        "admin_config",
        "admin_log",
        "login_attempts",
        "cache_history",
        "error_log",
        "blacklist",
        "search_log",
        "click_log",
    ]

    for table in tables:
        sq_cur = sq.execute(f"SELECT * FROM {table}")
        rows = sq_cur.fetchall()
        if not rows:
            print(f"  {table}: 0 filas (vacía, se omite)")
            continue

        cols = [d[0] for d in sq_cur.description]
        placeholders = ", ".join(["%s"] * len(cols))
        col_names = ", ".join(cols)
        sql = (
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT DO NOTHING"
        )

        data = [tuple(row) for row in rows]
        pg_cur.executemany(sql, data)
        pg.commit()
        print(f"  {table}: {len(data)} filas migradas")

    # Resetear secuencias SERIAL para que los próximos INSERT usen IDs correctos
    print("\nReseteando secuencias de autoincrement...")
    for table in TABLES_WITH_SERIAL:
        pg_cur.execute(f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE((SELECT MAX(id) FROM {table}), 1)
            )
        """)
        pg.commit()
        print(f"  Secuencia de {table} reseteada")

    sq.close()
    pg_cur.close()
    pg.close()
    print("\nMigración completada exitosamente.")
    print("Puedes ahora iniciar la app con: gunicorn wsgi:app --workers 4")


if __name__ == "__main__":
    migrate()
