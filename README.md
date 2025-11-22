# DataAnalyzer Team - Multi-Agent RAG System

## Overview

This project implements a multi-agent Retrieval-Augmented Generation (RAG) system capable of understanding natural-language questions, generating SQL queries, executing them, and producing human-readable insights.  
It includes both:

- FastAPI backend (with the `/ask` API endpoint)
- Gradio web dashboard UI

The system supports **SQLite** (default) and **PostgreSQL**, and uses **Google Gemini 2.5 Flash** as the LLM (you can use any llm its free tier only).

---

## Features

- Multi-Agent architecture:
  - Schema Agent
  - SQL Generator Agent
  - Query Executor Agent
  - Synthesizer Agent
- Natural-language question → SQL query pipeline
- Safe SQL execution
- Dynamic schema extraction
- Gradio dashboard UI
- FastAPI `/ask` endpoint for programmatic access
- SQLite and PostgreSQL backend support
- Clean layout
- Error handling for invalid SQL, missing columns, connection issues, etc.

---

## Tech Stack

- FastAPI (API backend)
- Gradio (web dashboard UI)
- Google Gemini 2.5 Flash (LLM)
- SQLite / PostgreSQL (database)
- Python 3.10+

---

## Project Structure

```
multi_agent_rag/
│
├── app.py
├── company.db
├── faker_setup_postgres.py
├── requirements.txt
├── README.md
├── pg_to_sqliteexport.py
└── db_setup_postgres.py
```

---

## Installation

### 1. Clone the repository

```
git clone https://github.com/Chetan260302/Multi_Agent_Rag.git
cd <Multi_Agent_Rag>
```

---

### 2. Create and activate virtual environment (recommended)

```
python -m venv venv
```

Windows:
```
venv\Scripts\activate
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_key_here

DB_BACKEND=sqlite        # or postgres

# When using sqlite
SQLITE_PATH=company.db

# When using PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=company
PG_USER=postgres
PG_PASSWORD=your_password
```

You must generate your own Gemini API key from Google AI Studio.

---

## Running Locally

Start the app:

```
python app.py
```

### Access:

FastAPI API docs as well /ask post endpoint:
```
http://localhost:8000/docs
```
## API Endpoint

### POST `/ask`

#### Click on Try it out 

<img width="1286" height="408" alt="image" src="https://github.com/user-attachments/assets/d5b1f42a-ed52-416a-9d3a-7542be7957e3" />

#### Request:

<img width="1277" height="430" alt="image" src="https://github.com/user-attachments/assets/4d5e74f0-f34d-42b0-a5b4-a0a439998dee" />


### Response:

<img width="1238" height="536" alt="image" src="https://github.com/user-attachments/assets/a8b71bb3-6730-4074-8bcf-32571da55d13" />

#### Gradio UI dashboard:
```
http://localhost:8000/ui
```

<img width="1203" height="623" alt="image" src="https://github.com/user-attachments/assets/cfcbd557-aa4e-4392-9188-dcfa8ec696f5" />

## PostgreSQL Setup (optional)

If you want to use PostgreSQL instead of SQLite:

1. Install PostgreSQL  
2. Create a database named `company`  
3. Run fake data generator (optional):

```
python faker_setup_postgres.py
```

4. Set `DB_BACKEND=postgres` in `.env`

---

## SQLite vs PostgreSQL

| Feature | SQLite | PostgreSQL |
|--------|--------|-------------|
| Local testing | Yes | Yes |
| HF support | Yes | No (unless Docker) |
| Installation | None | Requires server |
| Performance | Good | Better for large datasets |

---

## Notes

- `company.db` is included for direct testing  
- `.env` should NOT be committed  
- SQL execution is safely restricted to **SELECT/WITH only**  
- No destructive commands are allowed  



