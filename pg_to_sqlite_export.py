# pg_to_sqlite_export.py
import sqlite3, psycopg2, os
from dotenv import load_dotenv
load_dotenv()

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "company")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

sqlite_db = os.getenv("SQLITE_PATH", "company.db")

pg = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
pg_cur = pg.cursor()

# create sqlite and tables
if os.path.exists(sqlite_db):
    os.remove(sqlite_db)
sconn = sqlite3.connect(sqlite_db)
scur = sconn.cursor()

# Fetch table list from Postgres public schema
pg_cur.execute("""
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_type='BASE TABLE';
""")
tables = [r[0] for r in pg_cur.fetchall()]

for t in tables:
    # fetch create-like structure (we'll create simple columns using information_schema)
    pg_cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (t,))
    cols = pg_cur.fetchall()
    # Build simple CREATE TABLE with TEXT for safety or map types
    col_defs = []
    for col_name, data_type in cols:
        # map some types
        if data_type.startswith("integer") or "int" in data_type:
            dt = "INTEGER"
        elif data_type in ("date","timestamp without time zone","timestamp with time zone"):
            dt = "TEXT"
        else:
            dt = "TEXT"
        col_defs.append(f"{col_name} {dt}")
    create_sql = f"CREATE TABLE {t} ({', '.join(col_defs)});"
    scur.execute(create_sql)

    # copy rows
    pg_cur.execute(f"SELECT * FROM {t};")
    rows = pg_cur.fetchall()
    if rows:
        placeholders = ",".join(["?"] * len(rows[0]))
        scur.executemany(f"INSERT INTO {t} VALUES ({placeholders})", rows)
    sconn.commit()

pg_cur.close()
pg.close()
sconn.close()
print("Exported PostgreSQL data to", sqlite_db)
