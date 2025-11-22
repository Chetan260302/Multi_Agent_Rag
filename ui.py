import gradio as gr
import requests

API_URL = "http://127.0.0.1:8000/ask"

def ask_question(question):
    if not question.strip():
        return "Please enter a question.", "", "", ""
    
    payload ={"question":question}
    response=requests.post(API_URL,json=payload)

    if response.status_code !=200:
        return "API Error", "", ""
    data=response.json()

    return (
        data.get("final_answer",""),
        data.get("schema_agent_output",""),
        data.get("sql_query", ""),
        data.get("query_result", "")
    )

with gr.Blocks(title="Multi-Agent RAG System") as demo:
    gr.Markdown("# Multi-Agent RAG over SQLite")

    with gr.Row():
        question=gr.Textbox(label="Ask a Question", placeholder="e.g. What was the total sales last year")
        submit =gr.Button("Ask")

    final_answer=gr.Markdown(label="Final Answer")
    schema_output=gr.Markdown(label="Schema Agent Output")
    sql_output=gr.Markdown(label="SQL Query")
    query_result=gr.JSON(label="Query REsult")

    submit.click(ask_question,question,[final_answer,schema_output,sql_output,query_result])

demo.launch()