import os
import re
import json
import sqlite3
from typing import Any, Dict
from dotenv import load_dotenv
from decimal import Decimal

load_dotenv()

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").lower()  # 'sqlite' or 'postgres'
DB_PATH = os.getenv("SQLITE_PATH", "company.db")
# Postgres connection env vars (used when DB_BACKEND == "postgres")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DATABASE = os.getenv("PG_DATABASE", "company")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEN_MODEL = os.getenv("GEN_MODEL", "models/gemini-2.5-flash")

if not GEMINI_KEY:
    print("WARNING: GEMINI_API_KEY not set. Set it in .env or environment variables.")

# import LLM SDK late (avoid error if not installed)
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    genai = None
    print("Warning: google.generativeai not available or not configured:", e)

# FastAPI and Gradio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import gradio as gr

app = FastAPI(title="DataAnalyser Team")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

from decimal import Decimal

def convert_json_safe(obj):
    """Convert Decimal, date, tuple etc. into JSON-safe objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    if hasattr(obj, "isoformat"): 
        return obj.isoformat()
    if isinstance(obj, tuple):
        return [convert_json_safe(i) for i in obj]
    if isinstance(obj, list):
        return [convert_json_safe(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_json_safe(v) for k, v in obj.items()}
    return obj


#Database connection 
def get_pg_connection():
    import psycopg2
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE, user=PG_USER, password=PG_PASSWORD
    )

def get_sqlite_connection():
    return sqlite3.connect(DB_PATH)

def run_query_statements(sql: str) -> Dict[str, Any]:
    """
    Execute one or more read-only statements (SELECT/WITH) against the selected DB backend.
    Returns {'multi_results': [...]} or {'error': '...'}
    """
    sql = sql.strip()
    if not sql:
        return {"error": "Empty SQL after cleaning."}

    
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    results = []
    try:
        if DB_BACKEND == "postgres":
            conn = get_pg_connection()
            cur = conn.cursor()
            for stmt in statements:
                if not re.match(r'^\s*(SELECT|WITH)\b', stmt, flags=re.IGNORECASE):
                    results.append({"query": stmt, "error": "Only SELECT/WITH allowed for safety."})
                    continue
                
                cur.execute(stmt)
                try:
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchall()
                except Exception:
                    cols, rows = [], []
                results.append({
                    "query": stmt,
                    "columns": convert_json_safe(cols),
                    "rows": convert_json_safe(rows)
                })
            conn.close()
        else:
            conn = get_sqlite_connection()
            cur = conn.cursor()
            for stmt in statements:
                if not re.match(r'^\s*(SELECT|WITH)\b', stmt, flags=re.IGNORECASE):
                    results.append({"query": stmt, "error": "Only SELECT/WITH allowed for safety."})
                    continue
                cur.execute(stmt)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchall()
                results.append({
                    "query": stmt,
                    "columns": convert_json_safe(cols),
                    "rows": convert_json_safe(rows)
                })
            conn.close()
        return {"multi_results": results}
    except Exception as e:
        return {"error": f"SQL execution error: {str(e)}"}


# Extracting Schema 

def get_schema_description() -> str:
    """
    Produce a simple schema description for prompting the LLM.
    Works for both DB backends.
    """
    try:
        if DB_BACKEND == "postgres":
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type='BASE TABLE';
            """)
            tables = [r[0] for r in cur.fetchall()]
            schema_lines = []
            for t in tables:
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s;", (t,))
                cols = [r[0] for r in cur.fetchall()]
                schema_lines.append(f"{t}({', '.join(cols)})")
            conn.close()
        else:
            conn = get_sqlite_connection()
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cur.fetchall()]
            schema_lines = []
            for t in tables:
                cur.execute(f"PRAGMA table_info({t});")
                cols = [r[1] for r in cur.fetchall()]
                schema_lines.append(f"{t}({', '.join(cols)})")
            conn.close()
        return "Tables:\n" + "\n".join(schema_lines)
    except Exception as e:
        return f"Schema unavailable: {str(e)}"


# LLM helpers

def clean_sql_from_llm(raw_sql: str) -> str:
    if not raw_sql:
        return ""
    # using regular expression to extract query correctly
    m = re.search(r'```(?:sql|sqlite)?(.*?)```', raw_sql, flags=re.DOTALL | re.IGNORECASE)
    if m:
        sql = m.group(1).strip()
    else:
        sql = re.sub(r'(?i)\b(sqlite|sql)\b', '', raw_sql)
        sql = sql.strip().strip('`').strip()
    sql = re.sub(r'^(ite|lite|qlite|sqlite)\s*[:\-]*\s*', '', sql, flags=re.IGNORECASE)
    return sql

def generate_with_model(prompt: str) -> str:
    if genai is None:
        return "LLM not configured. Set GEMINI_API_KEY in .env."
    model = genai.GenerativeModel(GEN_MODEL)
    resp = model.generate_content(prompt)
    return resp.text if hasattr(resp, "text") else str(resp)


# Pipeline

def process_question(question: str) -> Dict[str, Any]:
    if not question or not question.strip():
        return {"error": "Empty question."}
    schema_description = get_schema_description()

    # Schema Agent prompt
    schema_prompt = f"""
You are the Schema Agent.
Your job is to identify the relevant tables and columns needed for the user's question.
You MUST ALWAYS respond using EXACTLY this structured format:

Relevant Tables:
 - table1
 - table2

Relevant Columns:
 - table1.columnA
 - table2.columnB

DO NOT add anything else.
DO NOT explain.
DO NOT generate SQL.

Schema:
{schema_description}

Question:
{question}

Return a concise plain-text answer listing relevant tables and fields.
"""
    try:
        schema_output = generate_with_model(schema_prompt)
    except Exception as e:
        schema_output = f"Schema agent error: {str(e)}"

    # SQL generator prompt: ask for PostgreSQL SQL when DB_BACKEND==postgres else request SQLite-compatible SQL.
    dialect_hint = "PostgreSQL" if DB_BACKEND == "postgres" else "SQLite"
    extra_hint = """
Use only SELECT or WITH queries (no DROP/DELETE/INSERT/UPDATE). Use correct date functions for {dialect}.
Return only the SQL query or queries needed with no surrounding explanation.
""".replace("{dialect}", dialect_hint)

    sql_prompt = f"""
You are SQL Generator Agent.
Convert this natural language question into a valid {dialect_hint} SQL query using the schema below.
{extra_hint}
Schema:
{schema_description}

Question:
{question}
"""
    try:
        raw_sql = generate_with_model(sql_prompt)
        sql_query = clean_sql_from_llm(raw_sql)
    except Exception as e:
        raw_sql = ""
        sql_query = ""
        sql_error = f"Error generating SQL: {str(e)}"

    if not sql_query:
        return {
            "schema_agent_output": schema_output,
            "sql_query": sql_query,
            "query_result": {"error": "SQL generation returned empty result.", "raw_sql": raw_sql},
            "final_answer": "I couldn't generate a SQL query for that question. Try rephrasing."
        }

    run_result = run_query_statements(sql_query)

    # synthesizer agent prompt
    synth_prompt = f"""
        You are the Synthesizer Agent.
        Your job: Convert SQL results into a clear, short natural-language answer.

        Rules:
        1. If the result contains an error → explain the error simply.
        2. If rows exist → summarize them briefly, correctly, and factually.
        3. DO NOT invent or hallucinate numbers.
        4. Write in maximum 4 lines if possible also the output formatting should be professional.

        User question: {question}

        The SQL generated was:
        {sql_query}

        The SQL execution result was:
        {json.dumps(convert_json_safe(run_result))}

        If the SQL execution result contains an 'error', explain why and give a helpful suggestion
        (e.g., column/table not found, check field names, or adjust the question). Otherwise,
        return a brief natural language answer summarizing the results. Do not fabricate numbers.
        """
    try:
        final_answer = generate_with_model(synth_prompt)
    except Exception as e:
        final_answer = f"Synthesizer error: {str(e)}"

    return {
        "schema_agent_output": schema_output.strip(),
        "sql_query": sql_query.strip(),
        "query_result": json.loads(json.dumps(convert_json_safe(run_result))),
        "final_answer": final_answer.strip()
    }


# FastAPI endpoints

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_api(req: QueryRequest):
    return process_question(req.question)

@app.get("/")
async def root():
    return {"message": "Data Analyser Team RAG API is running. Open /ui for the dashboard."}


# Gradio UI

def build_gradio_ui():
    card_header = """
        <div style="
            background:#1565C0;
            color:white;
            padding:10px 12px;
            border-radius:8px 8px 0 0;
            font-size:20px;
            font-weight:600;
            text-align:center;
        ">
            {title}
        </div>
    """

    card_body_start = """
        <div style="
            border:1px solid #1565C0;
            border-top:none;
            padding:12px;
            border-radius:0 0 8px 8px;
            min-height:150px;
            background:#F5F9FF;
        ">
    """

    card_body_end = "</div>"

    with gr.Blocks(title="DataAnalyzer Team") as demo:

       
        gr.HTML("""
            <div style="text-align:center; margin-bottom:20px;">
                <h1 style="font-size:36px; margin:10px 0;">DataAnalyzer Team</h1>
                <p style="font-size:18px; color:#444;">Your intelligent multi-agent SQL assistant.</p>
            </div>
        """)

        
        with gr.Row():
            with gr.Column(scale=1):
                pass
            with gr.Column(scale=2):
                qbox = gr.Textbox(
                    label="Ask a Question",
                    placeholder="e.g. What was the total sales last year?",
                    lines=3
                )
                submit = gr.Button("Ask", variant="primary")
            with gr.Column(scale=1):
                pass

        gr.HTML("<hr style='margin:22px 0;'>")

        with gr.Row():

            # Schema Agent
            with gr.Column():
                gr.HTML(card_header.format(title="Schema Agent"))
                schema_card = gr.HTML(card_body_start + "" + card_body_end)

            # SQL Generator Agent
            with gr.Column():
                gr.HTML(card_header.format(title="SQL Generator"))
                sql_card = gr.Code("", language="sql")

            # Query Executor
            with gr.Column():
                gr.HTML(card_header.format(title="Query Executor"))
                result_card = gr.JSON({}, label="")

            # Synthesizer Agent
            with gr.Column():
                gr.HTML(card_header.format(title="Synthesizer Agent"))
                final_card = gr.HTML(card_body_start + "" + card_body_end)

        # Logic
        def ui_ask(question):
            if not question.strip():
                return (
                    "<p>Please enter a question.</p>",
                    "",
                    {},
                    "<p>Please enter a question.</p>"
                )

            resp = process_question(question)

            schema_html = card_body_start + resp["schema_agent_output"] + card_body_end
            final_html = card_body_start + resp["final_answer"] + card_body_end

            return (
                schema_html,
                resp["sql_query"],
                resp["query_result"],
                final_html
            )

        submit.click(
            fn=ui_ask,
            inputs=qbox,
            outputs=[schema_card, sql_card, result_card, final_card]
        )

    return demo


demo = build_gradio_ui()
gr.mount_gradio_app(app, demo, path="/ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
