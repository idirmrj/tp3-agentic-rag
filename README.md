# TP3 : Agentic RAG sur la jurisprudence

Un assistant qui répond à des questions juridiques à partir de décisions de la Cour de cassation.
Il décide lui-même quoi chercher, quelle affaire lire, et il ne rend sa réponse que si elle est vérifiée.

## Comment j'ai fait (TP1 et TP2 rattrapés)

Je n'avais pas fait les TP1 et TP2, donc j'ai repris uniquement ce dont le TP3 a besoin :

- **Du TP1** : un LLM local avec Ollama, appelé par un backend, et une sortie JSON validée en code
  (utilisée par le vérificateur).
- **Du TP2** : une version simple du RAG. 3000 décisions, découpées en passages de 400 mots,
  avec un index BM25 (`retrieval.py`).

Le TP3 est construit par-dessus : le RAG devient un outil que l'agent choisit d'appeler.

## Le principe

```
question -> agent -> outil -> agent -> ... -> réponse -> vérificateur -> réponse finale
                                                              |
                                          pas OK : retour à l'agent
```

1. L'agent choisit une action : chercher dans le corpus, lire une affaire, chercher sur le web, ou répondre.
2. Le vérificateur contrôle la réponse : elle cite des passages qui existent vraiment, et chaque phrase
   est appuyée par ces passages. Sinon, l'agent doit chercher à nouveau ou corriger.
3. On s'arrête quand la réponse est vérifiée, ou après 5 tours ("preuves insuffisantes").

Toutes les étapes s'affichent en direct dans l'interface.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `retrieval.py` | Le RAG simple (version TP2) : index BM25, recherche, lecture d'une affaire |
| `tools.py` | Les 3 outils de l'agent : `search_cases`, `read_case`, `external_search` |
| `agent.py` | La boucle de l'agent (LangGraph) |
| `verifier.py` | La vérification de la réponse |
| `api.py` + `static/index.html` | Le backend et la page web |
| `run_scenarios.py` | Lance les 3 scénarios et sauvegarde les traces dans `traces/` |

## Lancer le projet

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5:7b

python retrieval.py         
uvicorn api:app --reload      # puis ouvrir http://localhost:8000
```

Pour relancer les tests : `python run_scenarios.py`.

## Choix à noter

- **Qwen 2.5 7B** au lieu du Llama 1B du TP1 : le 1B n'arrive pas à appeler des outils correctement.
- **Garde-fou en code** : si le modèle veut répondre sans avoir rien cherché, on force une recherche.
  La consigne dans le prompt ne suffisait pas.

## Rendu

- Traces des 3 scénarios : `traces/`
- Schéma : `docs/architecture.png`
- Analyse : `ANALYSE.md`
