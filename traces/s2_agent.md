# Scenario 2 : Recherche multi-etapes

**Question :** Trouve une affaire de licenciement pour faute grave, lis la décision et donne la solution retenue par la Cour et ses motifs.

**Comportement attendu :** trouver une affaire (search_cases) puis la lire (read_case)

## Trace d'execution

| Etape | Type | Contenu |
|---|---|---|
| 1 | DECISION | Preuve documentaire necessaire : recherche dans le corpus -> search_cases |
| 2 | TOOL | search_cases({"k": 3, "query": "licenciement faute grave"}) |
| 3 | OBSERVATION | 3 affaires : 6079b1f69ba5988459c547a8 (13.06), 60343641d5b4be279b2bc0e5 (12.93), 6079b1f69ba5988459c546c0 (12.91) |
| 4 | DECISION | Besoin des passages exacts : lecture d'une affaire -> read_case |
| 5 | TOOL | read_case({"case_id": "6079b1f69ba5988459c547a8"}) |
| 6 | OBSERVATION | Affaire 6079b1f69ba5988459c547a8 du 1965-04-29 : 1 passages lus sur 1 |
| 7 | DECISION | Preuves jugees suffisantes : redaction de la reponse |
| 8 | DRAFT | Reponse redigee a partir de 3 passages, 1 citations |
| 9 | CHECK | Preuves suffisantes : oui, 1 citations valides |
| 10 | FINAL | Statut : ok. 1 sources citees (1 corpus, 0 externe) |

## Reponse finale

Statut : **ok**

La cour a condamné la société Peperiot Frères à verser une indemnité de licenciement à X..., chef d'équipe licencié sur le champ pour attitude grossière et injurieuse, malgré que sa faute puisse être assez grave pour priver du préavis. Les juges ont estimé que la gravité de la faute n'était pas suffisante pour priver X des fruits de son travail satisfaisant pendant 12 ans. [6079b1f69ba5988459c547a8#0]

## Sources citees

- `6079b1f69ba5988459c547a8#0` (corpus) : SUR LE MOYEN UNIQUE : VU L'ARTICLE 1134 DU CODE CIVIL ET L'ARTICLE 7 DE LA LOI DU 20 AVRIL 1810 ; ATTENDU QUE, POUR CONDAMNER LA SOCIETE PEPERIOT FRERES A PAYER UNE INDEMNITE DE LICENCIEMENT A X..., C...

## Statistiques

- Appels LLM : 5
- Appels outils : 2
- Latence : 159.4 s
