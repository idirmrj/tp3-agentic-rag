import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

MODEL = os.getenv("MODEL", "qwen2.5:7b")

judge_llm = ChatOllama(model=MODEL, temperature=0, format="json", num_ctx=8192)

CORPUS_CITATION = re.compile(r"\[([^\[\]\s]+#\d+)\]")     
URL_CITATION = re.compile(r"\[(https?://[^\[\]\s]+)\]")    

JUDGE_PROMPT = """Tu es un verificateur juridique strict.
On te donne une REPONSE et les PASSAGES qu'elle cite.
Verifie si chaque affirmation de la reponse est appuyee par les passages.
Une affirmation absente des passages est NON sourcee, meme si elle est vraie.
Reponds UNIQUEMENT avec ce JSON :
{"supported": true ou false, "unsupported_claims": ["affirmation non sourcee", ...]}"""


def verify(answer: str, documents: dict, external: dict) -> dict:
    """Renvoie {"ok": bool, "reasons": [...], "citations": [...], "llm_calls": int}"""
    reasons = []
    citations = list(dict.fromkeys(CORPUS_CITATION.findall(answer) + URL_CITATION.findall(answer)))

    # couche 1 
    if "PREUVES INSUFFISANTES" in answer.upper():
        return {"ok": False, "reasons": ["les passages recuperes ne repondent pas a la question"],
                "citations": [], "llm_calls": 0}
    if not answer.strip():
        reasons.append("reponse vide")
    if not documents and not external:
        reasons.append("aucune preuve recuperee : utilise d'abord les outils")
    if not citations:
        reasons.append("aucune citation [chunk_id] ou [URL] dans la reponse")
    unknown = [c for c in citations if c not in documents and c not in external]
    if unknown:
        reasons.append(f"citations inexistantes dans les sources lues : {unknown}")

    if reasons:
        return {"ok": False, "reasons": reasons, "citations": citations, "llm_calls": 0}

    # couche 2 : LLM juge
    passages = "\n\n".join(f"[{c}] {(documents.get(c) or external.get(c))['text']}" for c in citations)
    try:
        raw = judge_llm.invoke([
            SystemMessage(content=JUDGE_PROMPT),
            HumanMessage(content=f"PASSAGES :\n{passages}\n\nREPONSE :\n{answer}"),
        ]).content
        verdict = json.loads(raw)
        supported = bool(verdict.get("supported", False))
        claims = verdict.get("unsupported_claims") or []
    except Exception as e:
        return {"ok": True, "reasons": [f"juge LLM illisible ({e}), regles OK"],
                "citations": citations, "llm_calls": 1}

    if not supported:
        reasons.append("affirmations non sourcees : " + ("; ".join(map(str, claims)) or "non precise"))

    return {"ok": supported, "reasons": reasons, "citations": citations, "llm_calls": 1}
