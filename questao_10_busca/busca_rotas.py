#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 10 - Lista 2 de IA (2026.2)
Planejamento de rotas para entregas urbanas: de A (centro de distribuição) até I.

Executa sobre o grafo do enunciado:
  - Busca em Profundidade (DFS) e Busca em Largura (BFS)  [busca não informada]
  - Busca de Custo Uniforme (UCS)                         [busca não informada]
  - A*, com h(n) dada no enunciado                        [busca informada]
  - Variante: rota de menor custo que passa por D e F antes de chegar a I

O enunciado diz "Busca em Profundidade (BFS)". Como a sigla BFS é de busca em
largura e o nome é de busca em profundidade, o programa executa as duas.

Convenções (iguais em todos os algoritmos, para a comparação ser justa):
  - busca em grafo: um estado já expandido não é expandido de novo;
  - vizinhos gerados em ordem alfabética;
  - DFS, UCS e A*: teste de objetivo quando o nó é retirado da fronteira (expansão);
  - BFS: teste de objetivo quando o nó é gerado (como no AIMA);
  - empates na fila de prioridade: UCS por nome do estado; A* por menor h e depois nome.

Uso:  python busca_rotas.py
Dependências: somente a biblioteca padrão do Python 3.
"""

import heapq
from collections import deque
from itertools import permutations

# ---------------------------------------------------------------------------
# Dados do problema
# ---------------------------------------------------------------------------
TRECHOS = [
    ("A", "B", 4), ("A", "D", 3), ("B", "C", 5), ("B", "E", 2),
    ("C", "F", 2), ("D", "E", 4), ("D", "G", 6), ("E", "F", 3),
    ("E", "H", 5), ("F", "I", 4), ("G", "H", 3), ("H", "I", 2),
]
H = {"A": 10, "B": 8, "C": 6, "D": 9, "E": 6, "F": 4, "G": 5, "H": 2, "I": 0}
INICIO, OBJETIVO = "A", "I"

GRAFO = {}
for u, v, c in TRECHOS:  # grafo não direcionado
    GRAFO.setdefault(u, {})[v] = c
    GRAFO.setdefault(v, {})[u] = c


def acoes(estado):
    """Ações possíveis: ir para cada vizinho, em ordem alfabética."""
    return sorted(GRAFO[estado])


def custo(u, v):
    return GRAFO[u][v]


def caminho(pais, no):
    rota = [no]
    while pais[no] is not None:
        no = pais[no]
        rota.append(no)
    return rota[::-1]


def custo_rota(rota):
    return sum(custo(a, b) for a, b in zip(rota, rota[1:]))


# ---------------------------------------------------------------------------
# Busca não informada
# ---------------------------------------------------------------------------
def dfs(inicio=INICIO, objetivo=OBJETIVO):
    pilha = [(inicio, None)]
    pais, expandidos, gerados = {}, [], 1
    while pilha:
        no, pai = pilha.pop()
        if no in pais:  # já expandido por outro caminho
            continue
        pais[no] = pai
        expandidos.append(no)
        if no == objetivo:
            return caminho(pais, no), expandidos, gerados
        # empilha em ordem inversa para expandir o vizinho alfabeticamente menor primeiro
        for viz in reversed(acoes(no)):
            if viz not in pais:
                pilha.append((viz, no))
                gerados += 1
    return None, expandidos, gerados


def bfs(inicio=INICIO, objetivo=OBJETIVO):
    if inicio == objetivo:
        return [inicio], [], 1
    fila = deque([inicio])
    pais = {inicio: None}
    expandidos, gerados = [], 1
    while fila:
        no = fila.popleft()
        expandidos.append(no)
        for viz in acoes(no):
            if viz not in pais:  # nem explorado nem na fronteira
                pais[viz] = no
                gerados += 1
                if viz == objetivo:  # teste na geração
                    return caminho(pais, viz), expandidos, gerados
                fila.append(viz)
    return None, expandidos, gerados


def melhor_primeiro(f_prioridade, desempate, rotulo, mostrar=True):
    """Busca de melhor escolha genérica. UCS e A* diferem só na prioridade."""
    g = {INICIO: 0}
    pais = {INICIO: None}
    fronteira = [(f_prioridade(INICIO, 0), desempate(INICIO), INICIO)]
    expandidos, gerados, passos = [], 1, []
    fechados = set()
    while fronteira:
        f, _, no = heapq.heappop(fronteira)
        if no in fechados or f > f_prioridade(no, g[no]):
            continue  # entrada antiga, já superada por um caminho melhor
        fechados.add(no)
        expandidos.append(no)
        passos.append((no, g[no], H[no], g[no] + H[no]))
        if no == OBJETIVO:
            if mostrar:
                print(f"  expande {no:<2} g={g[no]:>2}  -> objetivo alcançado")
            break
        for viz in acoes(no):
            novo_g = g[no] + custo(no, viz)
            if viz not in fechados and novo_g < g.get(viz, float("inf")):
                g[viz] = novo_g
                pais[viz] = no
                heapq.heappush(fronteira, (f_prioridade(viz, novo_g), desempate(viz), viz))
                gerados += 1
        if mostrar:
            abertos = sorted({(f_prioridade(n, g[n]), n) for _, _, n in fronteira
                              if n not in fechados})
            txt = ", ".join(f"{n}({v})" for v, n in abertos)
            print(f"  expande {no:<2} g={g[no]:>2}  fronteira: {txt}")
    rota = caminho(pais, OBJETIVO) if OBJETIVO in fechados else None
    return rota, expandidos, gerados, passos, g


def ucs(mostrar=True):
    return melhor_primeiro(lambda n, gn: gn, lambda n: n, "UCS", mostrar)


def astar(mostrar=True):
    return melhor_primeiro(lambda n, gn: gn + H[n], lambda n: (H[n], n), "A*", mostrar)


# ---------------------------------------------------------------------------
# Verificações sobre a heurística
# ---------------------------------------------------------------------------
def distancias_reais(destino):
    """Dijkstra a partir do destino: h*(n), o custo real de n até o destino."""
    dist = {destino: 0}
    pq = [(0, destino)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, c in GRAFO[u].items():
            if d + c < dist.get(v, float("inf")):
                dist[v] = d + c
                heapq.heappush(pq, (d + c, v))
    return dist


def verificar_heuristica():
    hstar = distancias_reais(OBJETIVO)
    print("Admissibilidade: h(n) <= h*(n)")
    print("  estado  h(n)  h*(n)  ok")
    for n in sorted(H):
        print(f"  {n:<6}  {H[n]:>4}  {hstar[n]:>5}  {'sim' if H[n] <= hstar[n] else 'NÃO'}")
    consistente = all(H[u] <= c + H[v] for u, v, c in TRECHOS) and \
        all(H[v] <= c + H[u] for u, v, c in TRECHOS)
    print(f"Consistência (h(u) <= c(u,v) + h(v) em todas as arestas): "
          f"{'sim' if consistente else 'não'}")
    return hstar


# ---------------------------------------------------------------------------
# Variante: visitar D e F (em qualquer ordem) antes de chegar a I
# ---------------------------------------------------------------------------
# Estado: (local, visitou_D, visitou_F). Inicial: (A, False, False).
# Objetivo: (I, True, True). Entrar em I antes de visitar D e F é proibido,
# porque o entregador "chegaria a I" sem cumprir as visitas obrigatórias.
OBRIGATORIOS = ("D", "F")


def sucessores_v2(estado):
    local, vd, vf = estado
    for viz in acoes(local):
        nd, nf = vd or viz == "D", vf or viz == "F"
        if viz == OBJETIVO and not (nd and nf):
            continue
        yield (viz, nd, nf), custo(local, viz)


def h_v2(estado):
    # Toda rota ainda precisa terminar em I, então h(n) original continua
    # sendo uma cota inferior: a heurística segue admissível no novo espaço.
    return H[estado[0]]


def busca_v2(usar_h, mostrar=True):
    ini = (INICIO, False, False)
    g, pais = {ini: 0}, {ini: None}
    fronteira = [(h_v2(ini) if usar_h else 0, ini)]
    fechados, expandidos = set(), []
    fmt = lambda s: f"{s[0]}{'D' if s[1] else '-'}{'F' if s[2] else '-'}"
    while fronteira:
        f, s = heapq.heappop(fronteira)
        if s in fechados:
            continue
        fechados.add(s)
        expandidos.append(s)
        if mostrar:
            print(f"  expande {fmt(s):<5} g={g[s]:>2} h={h_v2(s) if usar_h else 0:>2} f={f:>2}")
        if s == (OBJETIVO, True, True):
            rota = []
            while s is not None:
                rota.append(s)
                s = pais[s]
            return [x[0] for x in rota[::-1]], g[(OBJETIVO, True, True)], expandidos
        for t, c in sucessores_v2(s):
            ng = g[s] + c
            if t not in fechados and ng < g.get(t, float("inf")):
                g[t], pais[t] = ng, s
                heapq.heappush(fronteira, (ng + (h_v2(t) if usar_h else 0), t))
    return None, None, expandidos


def conferir_v2_por_permutacao():
    """Conferência independente: melhor ordem de visita usando distâncias reais."""
    dist = {n: distancias_reais(n) for n in GRAFO}
    melhores = []
    for ordem in permutations(OBRIGATORIOS):
        seq = (INICIO,) + ordem + (OBJETIVO,)
        melhores.append((sum(dist[a][b] for a, b in zip(seq, seq[1:])), seq))
    return min(melhores)


# ---------------------------------------------------------------------------
def main():
    print("=" * 72)
    print("FORMULAÇÃO")
    print("  Estados: {A, B, C, D, E, F, G, H, I} (localidade atual do entregador)")
    print("  Estado inicial: A    Teste de objetivo: estado == I")
    print("  Ações em s: ir para um vizinho de s;  Transição: Resultado(s, ir(v)) = v")
    print("  Custo do passo: minutos do trecho; custo do caminho: soma dos trechos")
    print("  Grafo:")
    for n in sorted(GRAFO):
        print("   ", n, "->", ", ".join(f"{v}({c})" for v, c in sorted(GRAFO[n].items())))

    resultados = {}
    print("=" * 72)
    rota, exp, ger = dfs()
    print("BUSCA EM PROFUNDIDADE (DFS)")
    print("  Ordem de expansão:", " ".join(exp))
    print("  Rota:", "-".join(rota), " Custo:", custo_rota(rota))
    resultados["DFS"] = (rota, exp, ger)

    print("=" * 72)
    rota, exp, ger = bfs()
    print("BUSCA EM LARGURA (BFS)")
    print("  Ordem de expansão:", " ".join(exp), "(I encontrado ao ser gerado a partir de",
          rota[-2] + ")")
    print("  Rota:", "-".join(rota), " Custo:", custo_rota(rota))
    resultados["BFS"] = (rota, exp, ger)

    print("=" * 72)
    print("BUSCA DE CUSTO UNIFORME (UCS) - prioridade g(n)")
    rota, exp, ger, _, _ = ucs()
    print("  Ordem de expansão:", " ".join(exp))
    print("  Rota:", "-".join(rota), " Custo:", custo_rota(rota))
    resultados["UCS"] = (rota, exp, ger)

    print("=" * 72)
    hstar = verificar_heuristica()
    print("-" * 72)
    print("A* - prioridade f(n) = g(n) + h(n)")
    rota, exp, ger, passos, _ = astar()
    print("  Nós expandidos, na ordem:")
    print("    nó   g(n)  h(n)  f(n)")
    for n, gn, hn, fn in passos:
        print(f"    {n:<3}  {gn:>4}  {hn:>4}  {fn:>4}")
    print("  Ordem de expansão:", " ".join(exp))
    print("  Rota:", "-".join(rota), " Custo:", custo_rota(rota))
    resultados["A*"] = (rota, exp, ger)

    print("=" * 72)
    print("COMPARAÇÃO")
    print(f"  {'Algoritmo':<9} {'Rota':<19} {'Custo':>5} {'Expandidos':>10} {'Gerados':>8}"
          f"  {'Completo':<9} {'Ótimo'}")
    props = {"DFS": ("sim*", "não"), "BFS": ("sim", "não**"),
             "UCS": ("sim", "sim"), "A*": ("sim", "sim***")}
    for nome, (rota, exp, ger) in resultados.items():
        comp, oti = props[nome]
        print(f"  {nome:<9} {'-'.join(rota):<19} {custo_rota(rota):>5} {len(exp):>10} {ger:>8}"
              f"  {comp:<9} {oti}")
    print("  *   em grafos finitos com controle de repetidos; não é completa em espaços infinitos")
    print("  **  ótima só quando todos os custos de passo são iguais")
    print("  *** com heurística admissível (busca em árvore) ou consistente (busca em grafo)")
    print(f"  Custo ótimo real de A até I (Dijkstra): {hstar[INICIO]}")

    print("=" * 72)
    print("VARIANTE: passar por D e F (qualquer ordem) antes de chegar a I")
    print("  Estado: (local, visitou_D, visitou_F); exibido como local + D/F visitados")
    print("-- UCS no espaço ampliado --")
    rota_u, custo_u, exp_u = busca_v2(usar_h=False)
    print("  Rota:", "-".join(rota_u), " Custo:", custo_u, " Expandidos:", len(exp_u))
    print("-- A* no espaço ampliado, h((n, d, f)) = h(n) --")
    rota_a, custo_a, exp_a = busca_v2(usar_h=True)
    print("  Rota:", "-".join(rota_a), " Custo:", custo_a, " Expandidos:", len(exp_a))
    c, seq = conferir_v2_por_permutacao()
    print("  Conferência por permutação das visitas obrigatórias:", " -> ".join(seq),
          "custo", c)


if __name__ == "__main__":
    main()
