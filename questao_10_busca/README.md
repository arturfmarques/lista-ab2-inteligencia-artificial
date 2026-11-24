# Questão 10: planejamento de rotas para entregas urbanas

`python busca_rotas.py` executa todas as buscas e imprime os traços. A saída
completa está em [`resultados.txt`](resultados.txt).

O enunciado pede "Busca em Profundidade (BFS)". Como o nome e a sigla não
batem, o programa executa as duas: busca em profundidade (DFS) e em largura (BFS).

Convenções: busca em grafo (sem reexpandir estados), vizinhos em ordem
alfabética, teste de objetivo na expansão (DFS, UCS, A*) e na geração (BFS).
Empates: UCS por nome do estado; A* por menor h(n) e depois nome.

| Algoritmo | Rota | Custo | Nós expandidos | Completo | Ótimo |
|---|---|---|---|---|---|
| DFS | A-B-C-F-E-D-G-H-I | 29 | 9 | sim (grafo finito) | não |
| BFS | A-B-C-F-I | 15 | 7 | sim | não (custos diferentes) |
| UCS | A-B-E-F-I | 13 | 9 | sim | sim |
| A* | A-B-E-H-I | 13 | 6 | sim | sim (h consistente) |

A heurística dada é admissível e consistente (o programa verifica as duas
propriedades). Há duas rotas ótimas de custo 13; UCS e A* encontram uma ou
outra conforme o desempate.

Variante com D e F obrigatórios: estado `(local, visitou_D, visitou_F)`,
objetivo `(I, True, True)`. Rota ótima A-D-E-F-I, custo 14. A* com
h((n, d, f)) = h(n) expande 11 estados; UCS expande 21.
