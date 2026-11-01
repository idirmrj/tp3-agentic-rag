# Scenario 3 : Information insuffisante

**Question :** Mon patron m'a viré parce que j'ai posté des trucs sur Facebook, est-ce que c'est légal ?

**Comportement attendu :** premier retrieval insuffisant -> reformulation ou external_search

## Trace d'execution

| Etape | Type | Contenu |
|---|---|---|
| 1 | DECISION | Preuve documentaire necessaire : recherche dans le corpus -> search_cases |
| 2 | TOOL | search_cases({"k": 3, "query": "licenciement pour faute grave due à des publications sur les réseaux sociaux"}) |
| 3 | OBSERVATION | 3 affaires : 60343641d5b4be279b2bc0e5 (15.78), 6079b1f79ba5988459c547f5 (15.07), 6079b1f59ba5988459c54692 (14.87) |
| 4 | DECISION | Preuve documentaire necessaire : recherche dans le corpus -> search_cases |
| 5 | TOOL | search_cases({"k": 3, "query": "licenciement pour faute grave due à des publications sur les réseaux sociaux"}) |
| 6 | OBSERVATION | 3 affaires : 60343641d5b4be279b2bc0e5 (15.78), 6079b1f79ba5988459c547f5 (15.07), 6079b1f59ba5988459c54692 (14.87) |
| 7 | DECISION | Preuves jugees suffisantes : redaction de la reponse |
| 8 | DRAFT | Reponse redigee a partir de 3 passages, 1 citations |
| 9 | CHECK | Preuves suffisantes : non -> les passages recuperes ne repondent pas a la question |
| 10 | DECISION | Preuve documentaire necessaire : recherche dans le corpus -> search_cases |
| 11 | TOOL | search_cases({"k": 3, "query": "licenciement pour faute professionnelle due à des publications sur les réseaux sociaux"}) |
| 12 | OBSERVATION | 3 affaires : 6079b1f69ba5988459c546bd (14.91), 6079b1f69ba5988459c546ef (12.97), 6079b1f79ba5988459c547f5 (11.61) |
| 13 | DECISION | Preuves jugees suffisantes : redaction de la reponse |
| 14 | DRAFT | Reponse redigee a partir de 5 passages, 0 citations |
| 15 | CHECK | Preuves suffisantes : non -> les passages recuperes ne repondent pas a la question |
| 16 | FINAL | Statut : max_iterations. 0 sources citees (0 corpus, 0 externe) |

## Reponse finale

Statut : **max_iterations**

Je n'ai pas trouve de preuves suffisantes pour repondre de facon fiable (limite de 5 decisions atteinte).

## Sources citees

Aucune

## Statistiques

- Appels LLM : 7
- Appels outils : 3
- Latence : 96.9 s
