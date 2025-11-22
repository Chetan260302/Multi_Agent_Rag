import sqlite3
from faker import Faker
import random

fake = Faker()
conn = sqlite3.connect("company.db")
cur = conn.cursor()


cur.executescript("""
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS projects;
""")


cur.executescript("""
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    start_date DATE,
    end_date DATE,
    budget REAL
);

CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    city TEXT,
    join_date DATE
);

                  
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    role TEXT,
    salary REAL,
    project_id INTEGER,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    employee_id INTEGER,
    amount REAL,
    sale_date DATE,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(employee_id) REFERENCES employees(id)
);
""")

PROJECTS = 30
CUSTOMERS = 200
EMPLOYEES = 50
SALES = 1000

for _ in range(PROJECTS):
    start_date = fake.date_between('-2y', 'today')
    end_date = fake.date_between(start_date, '+1y')
    cur.execute(
        "INSERT INTO projects (name, start_date, end_date, budget) VALUES (?, ?, ?, ?)",
        (fake.bs().title(), start_date, end_date, random.randint(100000, 1000000))
    )

for _ in range(CUSTOMERS):
    cur.execute(
        "INSERT INTO customers (name, city, join_date) VALUES (?, ?, ?)",
        (fake.name(), fake.city(), fake.date_between('-3y', 'today'))
    )

for _ in range(EMPLOYEES):
    cur.execute(
        "INSERT INTO employees (name, role, salary, project_id) VALUES (?, ?, ?, ?)",
        (
            fake.name(),
            random.choice(['Manager', 'Analyst', 'Sales Executive', 'Engineer']),
            random.randint(40000, 120000),
            random.randint(1, PROJECTS)
        )
    )

for _ in range(SALES):
    cur.execute(
        "INSERT INTO sales (customer_id, employee_id, amount, sale_date) VALUES (?, ?, ?, ?)",
        (
            random.randint(1, CUSTOMERS),
            random.randint(1, EMPLOYEES),
            random.randint(500, 10000),
            fake.date_between('-2y', 'today')
        )
    )

conn.commit()
conn.close()
print("company.db created successfully with fake random data")
