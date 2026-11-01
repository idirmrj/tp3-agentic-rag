"""
agent.py : la boucle agentique avec LangGraph (partie B du TP3).

    START -> agent --(tool_call)--> tools --> agent
                   --(reponse)----> verifier --(ok)--> final -> END
                                             --(ko)--> agent  (avec la raison de l'echec)
             (5 iterations max -> final avec "preuves insuffisantes")

Test en ligne de commande :
    python agent.py "ta question"
"""

import json
import operator
import os
import sys
import time
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from tools import TOOLS
from verifier import verify

# ---------------------------------------------------------------- config
MODEL = os.getenv("MODEL", "qwen2.5:7b")
MAX_ITER = 5

llm = ChatOllama(model=MODEL, temperature=0, num_ctx=8192)
llm_with_tools = llm.bind_tools(TOOLS)
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

SYSTEM_PROMPT = """Tu es un assistant juridique qui repond a partir de decisions de la Cour de cassation.

Outils :
- search_cases : chercher des affaires dans le corpus local
- read_case : lire les passages d'une affaire precise
- external_search : chercher sur le web juridique, seulement si le corpus ne suffit pas

Regles :
1. Utilise UNIQUEMENT les informations renvoyees par les outils, jamais tes connaissances.
2. Si les extraits de search_cases suffisent, reponds directement. Sinon lis l'affaire avec read_case.
3. Si la recherche ne donne rien d'utile, reformule avec d'autres mots-cles juridiques,
   puis utilise external_search en dernier recours.
4. Chaque affirmation de ta reponse finale cite sa source :
   [chunk_id] pour le corpus (ex: [JURITEXT000046#2]), [URL] pour le web.
5. Si les preuves manquent, dis-le clairement au lieu d'inventer.
Reponds en francais, de facon concise."""

# texte affiche dans la trace quand le LLM ne justifie pas son choix
DEFAULT_REASON = {
    "search_cases": "Preuve documentaire necessaire : recherche dans le corpus",
    "read_case": "Besoin des passages exacts : lecture d'une affaire",
    "external_search": "Corpus insuffisant : recherche externe",
}


# ---------------------------------------------------------------- etat partage
class State(TypedDict):
    query: str
    messages: Annotated[list, add_messages]       # historique LLM (s'ajoute)
    documents: dict                               # chunk_id -> passage du corpus
    external: dict                                # url -> source externe
    iterations: int
    verification: dict
    final_answer: str
    sources: list
    status: str
    trace: Annotated[list, operator.add]          # lignes de trace (s'ajoutent)
    n_llm_calls: Annotated[int, operator.add]     # compteur (bonus observabilite)


def log(type_: str, content: str) -> dict:
    return {"type": type_, "content": content}


# ---------------------------------------------------------------- helpers outils
def summarize(name: str, result: dict) -> str:
    """resume court d'un resultat d'outil, pour la trace"""
    if name == "search_cases":
        res = result.get("results", [])
        if not res:
            return "0 resultat"
        ids = ", ".join(f"{r['case_id']} ({r['score']})" for r in res)
        return f"{len(res)} affaires : {ids}"
    if name == "read_case":
        return (f"Affaire {result['case_id']} du {result['date']} : "
                f"{len(result['passages'])} passages lus sur {result['nb_passages_total']}")
    if name == "external_search":
        return f"{len(result.get('results', []))} liens externes"
    return str(result)[:200]


def collect(result: dict, documents: dict, external: dict):
    """range les preuves recuperees dans l'etat, pour que le verificateur puisse les controler"""
    if result.get("source") == "corpus":
        for p in result.get("passages", []):                     # read_case
            documents[p["chunk_id"]] = {"case_id": result["case_id"], "text": p["text"], "source": "corpus"}
        for r in result.get("results", []):                      # search_cases
            documents.setdefault(r["best_chunk"], {"case_id": r["case_id"], "text": r["extrait"], "source": "corpus"})
    if result.get("source") == "externe":
        for r in result.get("results", []):
            external[r["url"]] = {"titre": r["titre"], "text": r["extrait"], "source": "externe"}


# ---------------------------------------------------------------- noeuds
def agent_node(state: State):
    response = llm_with_tools.invoke(state["messages"])

    if response.tool_calls:
        names = ", ".join(tc["name"] for tc in response.tool_calls)
        reason = response.content.strip() or DEFAULT_REASON.get(response.tool_calls[0]["name"], "")
        entry = log("DECISION", f"{reason} -> {names}")
    else:
        entry = log("DECISION", "Elements suffisants : redaction d'une reponse, envoyee au verificateur")

    return {"messages": [response], "iterations": state["iterations"] + 1,
            "trace": [entry], "n_llm_calls": 1}


def tools_node(state: State):
    documents, external = dict(state["documents"]), dict(state["external"])
    messages, trace = [], []

    for tc in state["messages"][-1].tool_calls:
        trace.append(log("TOOL", f"{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"))
        try:
            result = TOOLS_BY_NAME[tc["name"]].invoke(tc["args"])
        except Exception as e:                       # outil inconnu ou mauvais arguments
            result = {"error": f"appel invalide de {tc['name']} : {e}"}

        if "error" in result:
            trace.append(log("ERROR", result["error"]))
        else:
            trace.append(log("OBSERVATION", summarize(tc["name"], result)))
            collect(result, documents, external)

        messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=tc["id"]))

    return {"messages": messages, "documents": documents, "external": external, "trace": trace}


def verifier_node(state: State):
    answer = state["messages"][-1].content
    result = verify(answer, state["documents"], state["external"])

    if result["ok"]:
        note = f" ({result['reasons'][0]})" if result["reasons"] else ""
        return {"verification": result, "n_llm_calls": result["llm_calls"],
                "trace": [log("CHECK", f"Preuves suffisantes : oui, {len(result['citations'])} citations valides{note}")]}

    feedback = HumanMessage(content=(
        "VERIFICATION ECHOUEE : " + " ; ".join(result["reasons"]) +
        "\nCorrige : cherche d'autres preuves avec les outils ou retire ce qui n'est pas source. "
        "Cite chaque affirmation."))
    return {"verification": result, "messages": [feedback], "n_llm_calls": result["llm_calls"],
            "trace": [log("CHECK", "Preuves suffisantes : non -> " + " ; ".join(result["reasons"]))]}


def final_node(state: State):
    v = state.get("verification") or {}
    if v.get("ok"):
        status, answer = "ok", state["messages"][-1].content
    else:
        status = "max_iterations"
        answer = (f"Je n'ai pas trouve de preuves suffisantes pour repondre de facon fiable "
                  f"(limite de {MAX_ITER} iterations atteinte).")

    sources = []
    for c in v.get("citations", []) if status == "ok" else []:
        doc = state["documents"].get(c) or state["external"].get(c)
        sources.append({"id": c, "source": doc["source"], "text": doc["text"]})

    n_ext = sum(s["source"] == "externe" for s in sources)
    summary = f"Statut : {status}. {len(sources)} sources citees ({len(sources) - n_ext} corpus, {n_ext} externe)"
    return {"final_answer": answer, "sources": sources, "status": status, "trace": [log("FINAL", summary)]}


# ---------------------------------------------------------------- routage
def route_after_agent(state: State):
    if state["messages"][-1].tool_calls:
        return "tools" if state["iterations"] < MAX_ITER else "final"
    return "verifier"


def route_after_verifier(state: State):
    if state["verification"]["ok"]:
        return "final"
    return "agent" if state["iterations"] < MAX_ITER else "final"


# ---------------------------------------------------------------- graphe
builder = StateGraph(State)
builder.add_node("agent", agent_node)
builder.add_node("tools", tools_node)
builder.add_node("verifier", verifier_node)
builder.add_node("final", final_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_agent, ["tools", "verifier", "final"])
builder.add_edge("tools", "agent")
builder.add_conditional_edges("verifier", route_after_verifier, ["agent", "final"])
builder.add_edge("final", END)

graph = builder.compile()


# ---------------------------------------------------------------- execution
def initial_state(question: str) -> dict:
    return {"query": question,
            "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)],
            "documents": {}, "external": {}, "iterations": 0, "verification": {},
            "final_answer": "", "sources": [], "status": "", "trace": [], "n_llm_calls": 0}


def stream_run(question: str):
    """Genere les lignes de trace au fil de l'eau, puis un dict de type RESULT.
    Reutilise par l'interface Streamlit et par run_scenarios.py."""
    t0, n_llm, n_tools = time.time(), 0, 0
    for update in graph.stream(initial_state(question), stream_mode="updates"):
        for node, data in update.items():
            n_llm += data.get("n_llm_calls", 0)
            for entry in data.get("trace", []):
                n_tools += entry["type"] == "TOOL"
                yield entry
            if node == "final":
                yield {"type": "RESULT", "answer": data["final_answer"], "sources": data["sources"],
                       "status": data["status"],
                       "stats": {"llm_calls": n_llm, "tool_calls": n_tools,
                                 "latency_s": round(time.time() - t0, 1)}}


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "Qu'est-ce qui caracterise une faute grave en droit du travail ?"
    print(f"QUESTION : {question}\n")
    step = 0
    for entry in stream_run(question):
        if entry["type"] == "RESULT":
            print("\n=== REPONSE ===\n" + entry["answer"])
            print("\n=== SOURCES ===")
            for s in entry["sources"]:
                print(f"[{s['source']}] {s['id']} : {s['text'][:120]}...")
            print(f"\n=== STATS === {entry['stats']}")
        else:
            step += 1
            print(f"{step:>2} {entry['type']:<12} {entry['content']}")
