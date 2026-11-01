"""
make_diagram.py : genere le schema du graphe agentique a partir du code LangGraph.

Sorties :
  docs/architecture.mmd  (texte Mermaid, toujours genere)
  docs/architecture.png  (image, necessite internet : rendu via mermaid.ink)

Lancer :  python make_diagram.py
"""

import os

from agent import graph

os.makedirs("docs", exist_ok=True)
g = graph.get_graph()

with open("docs/architecture.mmd", "w", encoding="utf-8") as f:
    f.write(g.draw_mermaid())
print("docs/architecture.mmd ecrit")

try:
    with open("docs/architecture.png", "wb") as f:
        f.write(g.draw_mermaid_png())
    print("docs/architecture.png ecrit")
except Exception as e:
    print(f"PNG non genere ({e}). Colle le .mmd sur https://mermaid.live pour exporter l'image.")
