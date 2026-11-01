"""
retrieval.py : la base RAG (equivalent minimal du TP2).

- charge un sous-ensemble de decisions de la Cour de cassation
- decoupe chaque decision en chunks
- construit un index BM25 et le sauvegarde dans data/index.pkl
- expose 2 fonctions utilisees par les outils de l'agent :
    search(query, k)   -> les affaires les plus pertinentes
    get_case(case_id)  -> les passages d'une affaire

Lancer une premiere fois :  python retrieval.py
"""

import os
import pickle
import re

from rank_bm25 import BM25Okapi

N_DECISIONS = 3000    
CHUNK_WORDS = 400 
OVERLAP_WORDS = 50   
INDEX_PATH = "data/index.pkl"

STOPWORDS = set("""
le la les un une des du de d l et ou en au aux a à ce ces cet cette qui que quoi
dont il elle ils elles on se sa son ses leur leurs par pour sur dans avec sans
est sont été être a ont pas ne n y s qu c plus comme mais si
""".split())

def tokenize(text: str) -> list[str]:
    """minuscules + mots alphanumeriques + suppression des stopwords"""
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def chunk_text(text: str) -> list[str]:
    """decoupe un texte en morceaux de CHUNK_WORDS mots avec chevauchement"""
    words = text.split()
    step = CHUNK_WORDS - OVERLAP_WORDS
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + CHUNK_WORDS]))
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def build_index():
    from datasets import load_dataset

    print(f"Chargement de {N_DECISIONS} decisions (streaming)...")
    ds = load_dataset("antoinejeannot/jurisprudence", "cour_de_cassation",
                      split="train", streaming=True)

    cases = {}  
    chunks = [] 

    for i, row in enumerate(ds):
        if i == 0:
            print("Colonnes du dataset :", list(row.keys()))

        text = row.get("text") or ""
        if len(text.split()) < 100:   
            continue

        case_id = str(row.get("id") or row.get("number") or i)
        cases[case_id] = {
            "case_id": case_id,
            "date": str(row.get("decision_date", "")),
            "chambre": str(row.get("chamber", "")),
            "numero": str(row.get("number", "")),
            "solution": str(row.get("solution", "")),
        }
        for j, chunk in enumerate(chunk_text(text)):
            chunks.append({"chunk_id": f"{case_id}#{j}", "case_id": case_id, "text": chunk})

        if len(cases) >= N_DECISIONS:
            break

    print(f"{len(cases)} decisions, {len(chunks)} chunks. Construction BM25...")
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])

    os.makedirs("data", exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks, "cases": cases}, f)
    print(f"Index sauvegarde dans {INDEX_PATH}")


_INDEX = None

def load_index():
    """charge l'index une seule fois (cache en memoire)"""
    global _INDEX
    if _INDEX is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError("Index absent : lance d'abord `python retrieval.py`")
        with open(INDEX_PATH, "rb") as f:
            _INDEX = pickle.load(f)
    return _INDEX


def search(query: str, k: int = 5) -> list[dict]:
    """
    Renvoie les k affaires les plus pertinentes.
    Une affaire = son meilleur chunk (pour ne pas avoir 5 fois la meme affaire).
    """
    idx = load_index()
    scores = idx["bm25"].get_scores(tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results, seen = [], set()
    for i in ranked:
        if scores[i] <= 0 or len(results) >= k:
            break
        chunk = idx["chunks"][i]
        if chunk["case_id"] in seen:
            continue
        seen.add(chunk["case_id"])
        results.append({
            **idx["cases"][chunk["case_id"]],
            "score": round(float(scores[i]), 2),
            "best_chunk": chunk["chunk_id"],
            "extrait": chunk["text"][:300] + "...",
        })
    return results


def get_case(case_id: str) -> dict:
    """Renvoie les metadonnees et tous les passages d'une affaire."""
    idx = load_index()
    if case_id not in idx["cases"]:
        raise KeyError(f"Affaire inconnue : {case_id}")
    passages = [{"chunk_id": c["chunk_id"], "text": c["text"]}
                for c in idx["chunks"] if c["case_id"] == case_id]
    return {**idx["cases"][case_id], "passages": passages}


if __name__ == "__main__":
    if not os.path.exists(INDEX_PATH):
        build_index()

    query = "licenciement pour faute grave"
    print(f"\n=== search('{query}') ===")
    results = search(query, k=3)
    for r in results:
        print(f"- {r['case_id']} | {r['date']} | {r['chambre']} | score {r['score']}")
        print(f"  {r['extrait'][:150]}")

    if results:
        case = get_case(results[0]["case_id"])
        print(f"\n=== get_case('{case['case_id']}') ===")
        print(f"{len(case['passages'])} passages, solution : {case['solution']}")