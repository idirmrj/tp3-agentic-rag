# Comparaison Agentic RAG vs RAG statique (TP2)

| Scenario | Systeme | Appels LLM | Outils | Latence (s) | Reponse verifiee |
|---|---|---|---|---|---|
| S1 RAG simple | Agent | 7 | 4 | 133.1 | oui |
| | RAG statique | 1 | 1 (fixe) | 50.9 | oui |
| S2 Recherche multi-etapes | Agent | 5 | 2 | 159.4 | oui |
| | RAG statique | 1 | 1 (fixe) | 75.3 | oui |
| S3 Information insuffisante | Agent | 7 | 3 | 96.9 | non (max_iterations) |
| | RAG statique | 1 | 1 (fixe) | 39.2 | non |

Note : 'Appels LLM' de l'agent inclut le LLM juge du verificateur. La reponse du RAG statique est passee au meme verificateur, hors chrono.

## S1 : reponses

**Agent :**

Selon les passages fournis, une faute grave en droit du travail peut être caractérisée par la violation d'une obligation contractuelle prévue comme telle dans le contrat de travail. Par exemple, l'article 6 d'un contrat mentionné indique que l'inexécution d'une obligation, après mise en demeure restée sans effet, sera considérée comme une faute grave entraînant la rupture du contrat sans délai ni indemnité. [6079b1f69ba5988459c546c0#0]

**RAG statique :**

Selon les passages fournis, une faute grave en droit du travail peut se manifester de différentes manières. Par exemple :

- Dans le premier passage [6079b1f69ba5988459c546c0#0], il est mentionné que l'article 6 du contrat prévoyait la nécessité d'une mise en demeure restée sans effet pour pouvoir invoquer une faute grave de nature à entraîner la rupture du contrat. La violation de cet article par l'employeur, qui n'a pas respecté cette procédure, a été considérée comme une faute grave.

- Dans le troisième passage [6079b1f79ba5988459c548a8#0], il est indiqué que l'employeur ne peut être condamné à verser des dommages-intérêts envers l'autre partie que si celle-ci prouve, outre le préjudice subi, l'existence d'une faute qui lui soit légalement imputable. Cela suggère qu'il faut une preuve de la faute de l'employé pour justifier un licenciement sans cause réelle et sérieuse.

Ces passages montrent que la notion de faute grave est liée à des violations graves du contrat ou des règles légales, mais aussi à la non-preuve par l'employé de son comportement fautif.

## S2 : reponses

**Agent :**

La cour a condamné la société Peperiot Frères à verser une indemnité de licenciement à X..., chef d'équipe licencié sur le champ pour attitude grossière et injurieuse, malgré que sa faute puisse être assez grave pour priver du préavis. Les juges ont estimé que la gravité de la faute n'était pas suffisante pour priver X des fruits de son travail satisfaisant pendant 12 ans. [6079b1f69ba5988459c547a8#0]

**RAG statique :**

La décision concernant un licenciement pour faute grave est présente dans le troisième passage fourni [6079b1f69ba5988459c547a8#0].

**Décision :**
L'arrêt attaque condamne la société Peperiot Frères à verser une indemnité de licenciement à X, chef d'équipe qu'elle avait licencié sur le champ le 20 septembre 1961 pour attitude grossière et injurieuse envers un ingénieur de l'EDF chargé du contrôle du chantier qui lui faisait des observations.

**Solution retenue par la Cour :**
Par ces motifs, la cour casse et annule l'arrêt rendu entre les parties par la cour d'appel de Bordeaux le 18 février 1963. Elle remet en conséquence la cause et les parties au même état ou elles étaient avant ledit arrêt et, pour être fait droit, les renvoie devant la cour d'appel d'Agen.

**Motifs :**
- Pour condamner la société Peperiot Frères à payer une indemnité de licenciement à X, chef d'équipe qu'elle avait licencié sur le champ le 20 septembre 1961 pour attitude grossière et injurieuse envers un ingénieur de l'EDF chargé du contrôle du chantier qui lui faisait des observations, l'arrêt attaqué se fonde sur ce motif que la faute commise peut être assez grave pour le priver du préavis, ne constituant pas la faute particulièrement lourde qui serait nécessaire pour le priver des fruits de son travail satisfaisant pendant 12 ans aux termes de cette entreprise.
- En statuant ainsi, alors qu'ils relevaient à l'égard de X une faute dont la gravité était suffisante pour lui priver de l'indemnité de licenciement au même titre que de l'indemnité compensatrice de préavis, les juges du fond n'ont pas tiré de leurs constatations les conséquences juridiques qui en découlaient.

## S3 : reponses

**Agent :**

Je n'ai pas trouve de preuves suffisantes pour repondre de facon fiable (limite de 5 decisions atteinte).

**RAG statique :**

Les passages fournis ne traitent pas spécifiquement de la situation où un employeur peut licencier un salarié pour des publications sur les réseaux sociaux. Ils abordent plutôt des questions liées au droit du travail et à l'appréciation de la faute dans le cadre d'un licenciement.

Pour répondre directement à votre question, il n'y a pas de texte spécifique dans ces passages qui traitent exactement de ce cas particulier. Cependant, en général, selon les principes du droit du travail français, un employeur peut licencier un salarié pour des faits graves liés au poste de travail ou à la discipline de l'entreprise, y compris certaines activités sur les réseaux sociaux si elles sont considérées comme nuisibles pour l'image de l'entreprise. Cependant, ce type de licenciement doit respecter le droit du travail et ne pas être abusif.

Pour une réponse précise à votre situation spécifique, il serait nécessaire d'examiner la nature exacte des publications sur Facebook, leur impact potentiel sur l'entreprise, ainsi que les procédures internes de l'entreprise concernant ce type de comportement.
