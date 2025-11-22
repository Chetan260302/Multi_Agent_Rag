import sqlite3

conn = sqlite3.connect("company.db")
cur = conn.cursor()


cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables in database:", cur.fetchall())


for table in ["customers", "employees", "projects", "sales"]:
    print(f"\n🔹 Sample rows from {table}:")
    cur.execute(f"SELECT * FROM {table} LIMIT 3;")
    for row in cur.fetchall():
        print(row)

conn.close()
