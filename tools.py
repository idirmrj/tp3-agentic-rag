"""
tools.py : les outils que l'agent peut appeler (partie A et D du TP3).

- search_cases(query, k)        -> recherche dans l'index du TP2 (corpus)
- read_case(case_id, focus)     -> passages d'une affaire (corpus)
- external_search(query)        -> recherche web sur des sites juridiques (externe)

Regles communes :
- chaque resultat porte un champ "source" : "corpus" ou "externe"
- une erreur ne fait jamais planter l'agent : on renvoie {"error": "..."}

Test rapide :  python tools.py
"""

from langchain_core.tools import tool

import retrieval
from retrieval import tokenize

MAX_PASSAGES = 4   # nombre max de passages renvoyes par read_case (le contexte du LLM est limite)


@tool
def search_cases(query: str, k: int = 5) -> dict:
    """Recherche des decisions de la Cour de cassation dans le corpus local.
    Renvoie une liste d'affaires avec case_id, date, chambre, score et un court extrait.
    A utiliser en premier pour trouver des affaires pertinentes."""
    try:
        results = retrieval.search(query, k=k)
        if not results:
            return {"source": "corpus", "results": [], "message": "Aucun resultat, essaie d'autres mots-cles."}
        return {"source": "corpus", "results": results}
    except Exception as e:
        return {"source": "corpus", "error": f"search_cases a echoue : {e}"}


@tool
def read_case(case_id: str, focus: str = "") -> dict:
    """Lit les passages d'une affaire precise du corpus (case_id obtenu via search_cases).
    'focus' (optionnel) = sujet de la question, pour renvoyer les passages les plus utiles.
    Chaque passage a un chunk_id a citer dans la reponse, ex: [case_id#2]."""
    try:
        case = retrieval.get_case(case_id)
        passages = case["passages"]

        if focus:
            # on classe les passages par nombre de mots en commun avec le focus
            focus_words = set(tokenize(focus))
            passages = sorted(passages,
                              key=lambda p: len(focus_words & set(tokenize(p["text"]))),
                              reverse=True)

        case["passages"] = passages[:MAX_PASSAGES]
        case["nb_passages_total"] = len(passages)
        case["source"] = "corpus"
        return case
    except KeyError:
        return {"source": "corpus", "error": f"Affaire '{case_id}' introuvable. Utilise un case_id renvoye par search_cases."}
    except Exception as e:
        return {"source": "corpus", "error": f"read_case a echoue : {e}"}


@tool
def external_search(query: str) -> dict:
    """Recherche sur le web (Legifrance, Cour de cassation, service-public).
    A utiliser seulement si le corpus local ne suffit pas.
    Les resultats sont des sources EXTERNES, a citer avec leur URL."""
    try:
        from ddgs import DDGS
        sites = "site:legifrance.gouv.fr OR site:courdecassation.fr OR site:service-public.fr"
        hits = DDGS().text(f"{query} {sites}", max_results=5)
        results = [{"titre": h.get("title", ""), "url": h.get("href", ""), "extrait": h.get("body", "")}
                   for h in hits]
        if not results:
            return {"source": "externe", "results": [], "message": "Aucun resultat externe."}
        return {"source": "externe", "results": results}
    except Exception as e:
        return {"source": "externe", "error": f"external_search a echoue : {e}"}


TOOLS = [search_cases, read_case, external_search]


# ---------------------------------------------------------------- test rapide
if __name__ == "__main__":
    print("=== search_cases ===")
    res = search_cases.invoke({"query": "licenciement faute grave", "k": 3})
    for r in res.get("results", []):
        print(f"- {r['case_id']} | {r['date']} | score {r['score']}")

    if res.get("results"):
        cid = res["results"][0]["case_id"]
        print(f"\n=== read_case({cid}) ===")
        case = read_case.invoke({"case_id": cid, "focus": "faute grave"})
        for p in case["passages"]:
            print(f"[{p['chunk_id']}] {p['text'][:120]}...")

    print("\n=== read_case (id invalide -> erreur geree) ===")
    print(read_case.invoke({"case_id": "xxx"}))

    print("\n=== external_search ===")
    ext = external_search.invoke({"query": "faute grave licenciement definition"})
    print(ext.get("error") or [r["url"] for r in ext["results"]])
