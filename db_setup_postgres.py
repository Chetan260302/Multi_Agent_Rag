# db_setup_postgres.py
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
from faker import Faker
import random
from datetime import date, timedelta

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "company")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
cur = conn.cursor()


# Drop/create tables
cur.execute("""
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS projects;
""")

cur.execute("""
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT,
    start_date DATE,
    end_date DATE,
    budget INTEGER
);
""")
cur.execute("""
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT,
    city TEXT,
    join_date DATE
);
""")
cur.execute("""
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name TEXT,
    role TEXT,
    salary INTEGER,
    project_id INTEGER REFERENCES projects(id)
);
""")
cur.execute("""
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    employee_id INTEGER REFERENCES employees(id),
    amount INTEGER,
    sale_date DATE
);
""")
conn.commit()

# Populate
fake = Faker()
NUM_PROJECTS = 30
NUM_CUSTOMERS = 200
NUM_EMPLOYEES = 50
NUM_SALES = 1000

for _ in range(NUM_PROJECTS):
    start = fake.date_between(start_date='-2y', end_date='today')
    end = fake.date_between(start_date=start, end_date='+1y')
    cur.execute("INSERT INTO projects (name, start_date, end_date, budget) VALUES (%s,%s,%s,%s)",
                (fake.bs().title(), start, end, random.randint(100000, 1000000)))

for _ in range(NUM_CUSTOMERS):
    cur.execute("INSERT INTO customers (name, city, join_date) VALUES (%s,%s,%s)",
                (fake.name(), fake.city(), fake.date_between(start_date='-3y', end_date='today')))

for _ in range(NUM_EMPLOYEES):
    cur.execute("INSERT INTO employees (name, role, salary, project_id) VALUES (%s,%s,%s,%s)",
                (fake.name(), random.choice(['Manager','Analyst','Sales Executive','Engineer']),
                 random.randint(40000,120000), random.randint(1,NUM_PROJECTS)))

for _ in range(NUM_SALES):
    cur.execute("INSERT INTO sales (customer_id, employee_id, amount, sale_date) VALUES (%s,%s,%s,%s)",
                (random.randint(1,NUM_CUSTOMERS), random.randint(1,NUM_EMPLOYEES),
                 random.randint(500,10000), fake.date_between(start_date='-2y', end_date='today')))

conn.commit()
cur.close()
conn.close()
print("Postgres DB populated.")
