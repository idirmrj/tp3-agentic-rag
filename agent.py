"""
agent.py : la boucle agentique avec LangGraph (partie B du TP3).

Chaque role est separe :
- agent      : DECIDE la prochaine action (chercher, lire, chercher sur le web, ou "pret a repondre")
- tools      : EXECUTE l'outil et range les preuves dans l'etat
- generate   : REDIGE la reponse, uniquement a partir des preuves recuperees
- verifier   : CONTROLE la reponse (citations valides + affirmations sourcees)

    START -> agent --(outil)--> tools --> agent
                   --(pret)---> generate --> verifier --(ok)--> final -> END
                                                      --(ko)--> agent (avec la raison de l'echec)
    5 decisions max, puis arret controle.

Test en ligne de commande :
    python agent.py "ta question"
"""

import json
import operator
import os
import re
import sys
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
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

# prompt de l'agent : il choisit des actions, il n'ecrit PAS la reponse
AGENT_PROMPT = """Tu pilotes la recherche d'un assistant juridique sur des decisions de la Cour de cassation.
Ton seul role : choisir la prochaine action. Tu n'ecris pas la reponse finale.

Outils :
- search_cases : cherche dans le corpus, renvoie le passage le plus pertinent de chaque affaire
- read_case : lit d'autres passages d'une affaire (solution, motifs), avec la question en focus
- external_search : web juridique, si le corpus ne parle pas du sujet

Methode :
1. Pour chercher, traduis la question en termes juridiques (ex : "vire" -> "licenciement").
2. Pour expliquer une decision (solution, motifs), utilise read_case sur l'affaire.
3. Si les passages ne parlent pas du sujet : reformule la recherche, puis external_search.
4. Si une verification echoue, choisis une action DIFFERENTE pour trouver de nouvelles preuves.
5. Quand les passages recuperes suffisent pour repondre, ecris seulement : PRET"""

# prompt du redacteur : c'est le "QA fonde sur les passages" du TP2
GENERATE_PROMPT = """Tu reponds a une question juridique UNIQUEMENT a partir des passages fournis.
- Reprends ce qui est ecrit dans les passages. N'ajoute aucune definition ni connaissance personnelle.
- Apres chaque phrase, recopie entre crochets l'identifiant du passage utilise,
  exactement comme il apparait devant le passage.
- 4 phrases maximum, en francais.
- Si les passages ne permettent pas de repondre, ecris seulement : PREUVES INSUFFISANTES"""

DEFAULT_REASON = {
    "search_cases": "Preuve documentaire necessaire : recherche dans le corpus",
    "read_case": "Besoin des passages exacts : lecture d'une affaire",
    "external_search": "Corpus insuffisant : recherche externe",
}


# ---------------------------------------------------------------- etat partage
class State(TypedDict):
    query: str
    messages: Annotated[list, add_messages]       # historique de l'agent (s'ajoute)
    documents: dict                               # chunk_id -> passage du corpus
    external: dict                                # url -> source externe
    read_cases: list                              # affaires deja lues avec read_case
    external_done: bool                           # external_search deja appele ?
    draft: str                                    # derniere reponse redigee
    evidence_at_draft: int                        # nb de preuves au moment de la redaction
    iterations: int
    verification: dict
    final_answer: str
    sources: list
    status: str
    trace: Annotated[list, operator.add]          # lignes de trace (s'ajoutent)
    n_llm_calls: Annotated[int, operator.add]     # compteur (bonus observabilite)


def log(type_: str, content: str) -> dict:
    return {"type": type_, "content": content}


def evidence_count(state) -> int:
    return len(state["documents"]) + len(state["external"])


# ---------------------------------------------------------------- helpers outils
def summarize(name: str, result: dict) -> str:
    """resume court d'un resultat d'outil, pour la trace"""
    if name == "search_cases":
        res = result.get("results", [])
        if not res:
            return "0 resultat"
        return f"{len(res)} affaires : " + ", ".join(f"{r['case_id']} ({r['score']})" for r in res)
    if name == "read_case":
        return (f"Affaire {result['case_id']} du {result['date']} : "
                f"{len(result['passages'])} passages lus sur {result['nb_passages_total']}")
    if name == "external_search":
        return f"{len(result.get('results', []))} liens externes"
    return str(result)[:200]


def collect(result: dict, documents: dict, external: dict):
    """range les preuves recuperees dans l'etat"""
    if result.get("source") == "corpus":
        for p in result.get("passages", []):                     # read_case
            documents[p["chunk_id"]] = {"case_id": result["case_id"], "text": p["text"], "source": "corpus"}
        for r in result.get("results", []):                      # search_cases
            documents.setdefault(r["best_chunk"], {"case_id": r["case_id"], "text": r["passage"], "source": "corpus"})
    if result.get("source") == "externe":
        for r in result.get("results", []):
            external[r["url"]] = {"titre": r["titre"], "text": r["extrait"], "source": "externe"}


def fallback_action(state):
    """
    Garde-fous en code, quand le LLM veut repondre alors que ce n'est pas raisonnable :
    - aucune preuve encore                         -> recherche forcee
    - verification ratee et aucune preuve nouvelle -> on force une action differente
    Renvoie (outil, arguments, raison) ou None si on laisse l'agent repondre.
    """
    if evidence_count(state) == 0:
        return "search_cases", {"query": state["query"], "k": 3}, "reponse sans preuve refusee, recherche forcee"

    v = state["verification"]
    if not v or v.get("ok") or evidence_count(state) != state["evidence_at_draft"]:
        return None

    insufficient = any("ne repondent pas" in r for r in v["reasons"])
    unread = [d["case_id"] for d in state["documents"].values() if d["case_id"] not in state["read_cases"]]

    if insufficient and not state["external_done"]:
        return "external_search", {"query": state["query"]}, "corpus insuffisant, recherche externe forcee"
    if unread:
        return ("read_case", {"case_id": unread[0], "focus": state["query"]},
                "rien de nouveau depuis l'echec, lecture forcee de l'affaire la mieux classee")
    if not state["external_done"]:
        return "external_search", {"query": state["query"]}, "rien de nouveau depuis l'echec, recherche externe forcee"
    return None


# ---------------------------------------------------------------- noeuds
def agent_node(state: State):
    it = state["iterations"] + 1
    response = llm_with_tools.invoke(state["messages"])

    if response.tool_calls:
        names = ", ".join(tc["name"] for tc in response.tool_calls)
        reason = DEFAULT_REASON.get(response.tool_calls[0]["name"], "")
        return {"messages": [response], "iterations": it, "n_llm_calls": 1,
                "trace": [log("DECISION", f"{reason} -> {names}")]}

    # le LLM veut repondre : on verifie que c'est raisonnable
    forced = fallback_action(state)
    if forced:
        name, args, why = forced
        msg = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"forced_{it}", "type": "tool_call"}])
        return {"messages": [msg], "iterations": it, "n_llm_calls": 1,
                "trace": [log("DECISION", f"Garde-fou : {why} -> {name}")]}

    return {"messages": [AIMessage(content="PRET")], "iterations": it, "n_llm_calls": 1,
            "trace": [log("DECISION", "Preuves jugees suffisantes : redaction de la reponse")]}


def tools_node(state: State):
    documents, external = dict(state["documents"]), dict(state["external"])
    read_cases, external_done = list(state["read_cases"]), state["external_done"]
    messages, trace = [], []

    for tc in state["messages"][-1].tool_calls:
        trace.append(log("TOOL", f"{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"))
        try:
            result = TOOLS_BY_NAME[tc["name"]].invoke(tc["args"])
        except Exception as e:                       # outil inconnu ou mauvais arguments
            result = {"error": f"appel invalide de {tc['name']} : {e}"}

        if tc["name"] == "external_search":
            external_done = True
        if "error" in result:
            trace.append(log("ERROR", result["error"]))
        else:
            trace.append(log("OBSERVATION", summarize(tc["name"], result)))
            collect(result, documents, external)
            if tc["name"] == "read_case":
                read_cases.append(result["case_id"])

        messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=tc["id"]))

    return {"messages": messages, "documents": documents, "external": external,
            "read_cases": read_cases, "external_done": external_done, "trace": trace}


def generate_node(state: State):
    # les 8 derniers passages du corpus + 3 sources externes, chacun precede de son identifiant
    sources = list(state["documents"].items())[-8:] + list(state["external"].items())[-3:]
    context = "\n\n".join(f"[{sid}] {d['text']}" for sid, d in sources)

    draft = llm.invoke([SystemMessage(content=GENERATE_PROMPT),
                        HumanMessage(content=f"PASSAGES :\n{context}\n\nQUESTION : {state['query']}")]).content

    n_cit = len(set(re.findall(r"\[([^\[\]\s]+)\]", draft)))
    return {"draft": draft, "evidence_at_draft": evidence_count(state), "n_llm_calls": 1,
            "trace": [log("DRAFT", f"Reponse redigee a partir de {len(sources)} passages, {n_cit} citations")]}


def verifier_node(state: State):
    result = verify(state["draft"], state["documents"], state["external"])

    if result["ok"]:
        note = f" ({result['reasons'][0]})" if result["reasons"] else ""
        return {"verification": result, "n_llm_calls": result["llm_calls"],
                "trace": [log("CHECK", f"Preuves suffisantes : oui, {len(result['citations'])} citations valides{note}")]}

    feedback = HumanMessage(content=(
        "VERIFICATION ECHOUEE : " + " ; ".join(result["reasons"]) +
        "\nChoisis une action differente pour trouver de nouvelles preuves "
        "(read_case sur une affaire, recherche reformulee, ou external_search)."))
    return {"verification": result, "messages": [feedback], "n_llm_calls": result["llm_calls"],
            "trace": [log("CHECK", "Preuves suffisantes : non -> " + " ; ".join(result["reasons"]))]}


def final_node(state: State):
    v = state.get("verification") or {}
    if v.get("ok"):
        status, answer = "ok", state["draft"]
    else:
        status = "max_iterations"
        answer = (f"Je n'ai pas trouve de preuves suffisantes pour repondre de facon fiable "
                  f"(limite de {MAX_ITER} decisions atteinte).")

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
    return "generate"


def route_after_verifier(state: State):
    if state["verification"]["ok"]:
        return "final"
    return "agent" if state["iterations"] < MAX_ITER else "final"


# ---------------------------------------------------------------- graphe
builder = StateGraph(State)
builder.add_node("agent", agent_node)
builder.add_node("tools", tools_node)
builder.add_node("generate", generate_node)
builder.add_node("verifier", verifier_node)
builder.add_node("final", final_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_agent, ["tools", "generate", "final"])
builder.add_edge("tools", "agent")
builder.add_edge("generate", "verifier")
builder.add_conditional_edges("verifier", route_after_verifier, ["agent", "final"])
builder.add_edge("final", END)

graph = builder.compile()


# ---------------------------------------------------------------- execution
def initial_state(question: str) -> dict:
    return {"query": question,
            "messages": [SystemMessage(content=AGENT_PROMPT), HumanMessage(content=question)],
            "documents": {}, "external": {}, "read_cases": [], "external_done": False,
            "draft": "", "evidence_at_draft": 0, "iterations": 0, "verification": {},
            "final_answer": "", "sources": [], "status": "", "trace": [], "n_llm_calls": 0}


def stream_run(question: str):
    """Genere les lignes de trace au fil de l'eau, puis un dict de type RESULT.
    Reutilise par l'API et par run_scenarios.py."""
    t0, n_llm, n_tools = time.time(), 0, 0
    for update in graph.stream(initial_state(question), stream_mode="updates", config={"recursion_limit": 50}):
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
