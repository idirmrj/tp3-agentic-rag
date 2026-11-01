# Scenario 1 : RAG simple

**Question :** Qu'est-ce qui caractérise une faute grave en droit du travail ?

**Comportement attendu :** une seule recherche suffit, peu d'etapes

## Trace d'execution

| Etape | Type | Contenu |
|---|---|---|
| 1 | DECISION | Preuve documentaire necessaire : recherche dans le corpus -> search_cases |
| 2 | TOOL | search_cases({"k": 3, "query": "faute grave"}) |
| 3 | OBSERVATION | 3 affaires : 60793aab9ba5988459c3c220 (10.49), 6079b1f69ba5988459c546c0 (9.54), 6079b1f49ba5988459c544d1 (9.4) |
| 4 | DECISION | Besoin des passages exacts : lecture d'une affaire -> read_case |
| 5 | TOOL | read_case({"case_id": "6079b1f69ba5988459c546c0"}) |
| 6 | OBSERVATION | Affaire 6079b1f69ba5988459c546c0 du 1965-01-25 : 2 passages lus sur 2 |
| 7 | DECISION | Besoin des passages exacts : lecture d'une affaire -> read_case |
| 8 | TOOL | read_case({"case_id": "60793aab9ba5988459c3c220"}) |
| 9 | OBSERVATION | Affaire 60793aab9ba5988459c3c220 du 1961-04-26 : 2 passages lus sur 2 |
| 10 | DECISION | Besoin des passages exacts : lecture d'une affaire -> read_case |
| 11 | TOOL | read_case({"case_id": "6079b1f49ba5988459c544d1"}) |
| 12 | OBSERVATION | Affaire 6079b1f49ba5988459c544d1 du 1965-02-03 : 2 passages lus sur 2 |
| 13 | DECISION | Preuves jugees suffisantes : redaction de la reponse |
| 14 | DRAFT | Reponse redigee a partir de 6 passages, 1 citations |
| 15 | CHECK | Preuves suffisantes : oui, 1 citations valides |
| 16 | FINAL | Statut : ok. 1 sources citees (1 corpus, 0 externe) |

## Reponse finale

Statut : **ok**

Selon les passages fournis, une faute grave en droit du travail peut être caractérisée par la violation d'une obligation contractuelle prévue comme telle dans le contrat de travail. Par exemple, l'article 6 d'un contrat mentionné indique que l'inexécution d'une obligation, après mise en demeure restée sans effet, sera considérée comme une faute grave entraînant la rupture du contrat sans délai ni indemnité. [6079b1f69ba5988459c546c0#0]

## Sources citees

- `6079b1f69ba5988459c546c0#0` (corpus) : SUR LE MOYEN UNIQUE, PRIS DE LA VIOLATION DES ARTICLES 1134 ET 1382 DU CODE CIVIL, 23 DU LIVRE 1ER DU CODE DU TRAVAIL, 7 DE LA LOI DU 20 AVRIL 1810, DENATURATION DES DOCUMENTS DE LA CAUSE, DEFAUT DE M...

## Statistiques

- Appels LLM : 7
- Appels outils : 4
- Latence : 133.1 s
