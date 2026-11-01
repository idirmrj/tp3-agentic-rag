import json
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from agent import stream_run

app = FastAPI(title="Agentic RAG jurisprudence")


def sse(data: dict) -> str:
    """format Server-Sent Events : une ligne 'data: ...' suivie d'une ligne vide"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/run")
def run(question: str):
    def events():
        try:
            for entry in stream_run(question):    
                yield sse(entry)
        except Exception as e:                  
            yield sse({"type": "ERROR", "content": f"Erreur serveur : {e}"})
        yield sse({"type": "END"})

    return StreamingResponse(events(), media_type="text/event-stream")
