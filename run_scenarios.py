"""
run_scenarios.py : lance les 3 scenarios du TP3 et sauvegarde les traces (section 6),
puis compare l'agent a un RAG statique facon TP2 (section 7).

Sorties dans traces/ :
  s1_agent.json / s1_agent.md   (idem s2, s3)   -> les 3 traces a rendre
  comparaison.md                                -> tableau agent vs RAG statique

Lancer :  python run_scenarios.py
"""

import json
import os
import time

from langchain_core.messages import HumanMessage, SystemMessage

import retrieval
from agent import llm, stream_run
from verifier import verify

SCENARIOS = {
    "s1": {"titre": "RAG simple",
           "question": "Qu'est-ce qui caractérise une faute grave en droit du travail ?",
           "attendu": "une seule recherche suffit, peu d'etapes"},
    "s2": {"titre": "Recherche multi-etapes",
           "question": "Trouve une affaire de licenciement pour faute grave, lis la décision et donne la solution retenue par la Cour et ses motifs.",
           "attendu": "trouver une affaire (search_cases) puis la lire (read_case)"},
    "s3": {"titre": "Information insuffisante",
           "question": "Mon patron m'a viré parce que j'ai posté des trucs sur Facebook, est-ce que c'est légal ?",
           "attendu": "premier retrieval insuffisant -> reformulation ou external_search"},
}

OUT_DIR = "traces"


# ---------------------------------------------------------------- agent
def run_agent(question: str) -> dict:
    trace, result = [], None
    for entry in stream_run(question):
        if entry["type"] == "RESULT":
            result = entry
        else:
            trace.append(entry)
            print(f"  {len(trace):>2} {entry['type']:<12} {entry['content'][:110]}")
    return {"trace": trace, **result}


# ---------------------------------------------------------------- RAG statique (equivalent TP2)
STATIC_PROMPT = """Tu es un assistant juridique. Reponds UNIQUEMENT a partir des passages fournis.
Cite chaque affirmation avec l'identifiant du passage entre crochets, ex: [JURITEXT000046#2].
Si les passages ne suffisent pas, dis-le."""


def run_static_rag(question: str, k: int = 3) -> dict:
    """pipeline fixe : 1 recherche -> top k passages -> 1 appel LLM. Pas de decision, pas de boucle."""
    t0 = time.time()
    idx = retrieval.load_index()
    chunk_by_id = {c["chunk_id"]: c for c in idx["chunks"]}

    hits = retrieval.search(question, k=k)
    documents = {h["best_chunk"]: {"text": chunk_by_id[h["best_chunk"]]["text"], "source": "corpus"} for h in hits}
    context = "\n\n".join(f"[{cid}] {d['text']}" for cid, d in documents.items())

    answer = llm.invoke([SystemMessage(content=STATIC_PROMPT),
                         HumanMessage(content=f"PASSAGES :\n{context}\n\nQUESTION : {question}")]).content
    latency = round(time.time() - t0, 1)

    # on passe la reponse au meme verificateur, hors chrono, juste pour mesurer si elle est bien sourcee
    check = verify(answer, documents, {})
    return {"answer": answer, "latency_s": latency, "llm_calls": 1, "verified": check["ok"],
            "reasons": check["reasons"]}


# ---------------------------------------------------------------- export markdown
def trace_to_md(key: str, sc: dict, run: dict) -> str:
    lines = [f"# Scenario {key[1]} : {sc['titre']}", "",
             f"**Question :** {sc['question']}", "",
             f"**Comportement attendu :** {sc['attendu']}", "",
             "## Trace d'execution", "",
             "| Etape | Type | Contenu |", "|---|---|---|"]
    for i, e in enumerate(run["trace"], 1):
        content = e["content"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {e['type']} | {content} |")
    lines += ["", "## Reponse finale", "", f"Statut : **{run['status']}**", "", run["answer"], "",
              "## Sources citees", ""]
    lines += [f"- `{s['id']}` ({s['source']}) : {s['text'][:200]}..." for s in run["sources"]] or ["Aucune"]
    st = run["stats"]
    lines += ["", "## Statistiques", "",
              f"- Appels LLM : {st['llm_calls']}",
              f"- Appels outils : {st['tool_calls']}",
              f"- Latence : {st['latency_s']} s", ""]
    return "\n".join(lines)


def save(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []

    for key, sc in SCENARIOS.items():
        print(f"\n=== {key.upper()} : {sc['titre']} ===\n{sc['question']}\n-- Agent")
        agent_run = run_agent(sc["question"])
        save(f"{OUT_DIR}/{key}_agent.json", json.dumps({"scenario": key, **sc, **agent_run}, ensure_ascii=False, indent=2))
        save(f"{OUT_DIR}/{key}_agent.md", trace_to_md(key, sc, agent_run))

        print("-- RAG statique")
        static_run = run_static_rag(sc["question"])
        save(f"{OUT_DIR}/{key}_static.json", json.dumps({"scenario": key, **sc, **static_run}, ensure_ascii=False, indent=2))
        print(f"  verifie : {static_run['verified']} | {static_run['latency_s']} s")

        rows.append((key, sc, agent_run, static_run))

    # tableau de comparaison agent vs RAG statique
    md = ["# Comparaison Agentic RAG vs RAG statique (TP2)", "",
          "| Scenario | Systeme | Appels LLM | Outils | Latence (s) | Reponse verifiee |",
          "|---|---|---|---|---|---|"]
    for key, sc, a, s in rows:
        md.append(f"| {key.upper()} {sc['titre']} | Agent | {a['stats']['llm_calls']} | {a['stats']['tool_calls']} "
                  f"| {a['stats']['latency_s']} | {'oui' if a['status'] == 'ok' else 'non (' + a['status'] + ')'} |")
        md.append(f"| | RAG statique | 1 | 1 (fixe) | {s['latency_s']} | {'oui' if s['verified'] else 'non'} |")
    md += ["", "Note : 'Appels LLM' de l'agent inclut le LLM juge du verificateur. "
               "La reponse du RAG statique est passee au meme verificateur, hors chrono.", ""]
    for key, sc, a, s in rows:
        md += [f"## {key.upper()} : reponses", "", "**Agent :**", "", a["answer"], "",
               "**RAG statique :**", "", s["answer"], ""]
    save(f"{OUT_DIR}/comparaison.md", "\n".join(md))

    print(f"\nTermine. Fichiers dans {OUT_DIR}/")
