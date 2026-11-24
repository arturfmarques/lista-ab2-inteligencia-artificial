#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 2 - Lista 2 de IA (2026.2)
K-vizinhos mais próximos (KNN) sobre a base de risco de crédito da Lista 1
(30 exemplos, 6 atributos categóricos, classe Risco = Baixo / Moderado / Alto).

O programa:
  1. implementa o KNN do zero (sem biblioteca de aprendizado);
  2. classifica um cliente novo passo a passo, mostrando as 30 distâncias,
     os k vizinhos e a votação;
  3. avalia k = 1, 3, 5, 7, 9 com validação leave-one-out (deixa um de fora);
  4. compara com o KNeighborsClassifier do scikit-learn, para conferir;
  5. salva o gráfico da acurácia por k (acuracia_por_k.png).

Distância: como os atributos são categóricos, usa-se a distância de Hamming
(número de atributos com valores diferentes). Variante ordinal: Renda e
Historia_Credito têm ordem natural; nela, a diferença entre categorias vizinhas
vale 0,5 e entre extremos vale 1 (ver DISTANCIA_ORDINAL).

Uso:
  python knn_credito.py                         # demonstração completa
  python knn_credito.py --k 5 --cliente "Boa,Alta,Nenhuma,15-35,Estavel,Jovem"
Dependências: pandas, numpy, scikit-learn, matplotlib.
"""

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).parent
ATRIBUTOS = ["Historia_Credito", "Divida", "Garantia", "Renda", "Emprego", "Idade"]
CLASSE = "Risco"

# Ordem natural de atributos ordinais (usada só na variante ordinal)
ORDENS = {
    "Renda": ["0-15", "15-35", "35+"],
    "Historia_Credito": ["Ruim", "Desconhecida", "Boa"],
}


def carregar_base():
    return pd.read_csv(AQUI / "dados_credito.csv")


# ---------------------------------------------------------------------------
# Distâncias
# ---------------------------------------------------------------------------
def distancia_hamming(a, b):
    """Número de atributos em que os dois exemplos diferem (0 a 6)."""
    return sum(1 for atr in ATRIBUTOS if a[atr] != b[atr])


def distancia_ordinal(a, b):
    """Hamming, mas Renda e História contam a distância na escala ordenada."""
    d = 0.0
    for atr in ATRIBUTOS:
        if atr in ORDENS:
            ordem = ORDENS[atr]
            d += abs(ordem.index(a[atr]) - ordem.index(b[atr])) / (len(ordem) - 1)
        else:
            d += a[atr] != b[atr]
    return d


# ---------------------------------------------------------------------------
# KNN
# ---------------------------------------------------------------------------
def vizinhos(base, consulta, k, distancia=distancia_hamming, excluir=None):
    """Retorna os k vizinhos mais próximos: lista de (distância, índice).

    Empates de distância são resolvidos pela ordem na base (E1 antes de E2).
    """
    dist = [(distancia(consulta, linha), i) for i, linha in base.iterrows() if i != excluir]
    dist.sort(key=lambda t: (t[0], t[1]))
    return dist[:k], dist


def votar(base, viz):
    """Voto da maioria; empate entre classes -> classe do vizinho mais próximo."""
    votos = Counter(base.loc[i, CLASSE] for _, i in viz)
    maior = max(votos.values())
    empatadas = {c for c, v in votos.items() if v == maior}
    if len(empatadas) == 1:
        return empatadas.pop(), votos
    for _, i in viz:  # viz está ordenado por distância
        if base.loc[i, CLASSE] in empatadas:
            return base.loc[i, CLASSE], votos


def classificar(base, consulta, k, distancia=distancia_hamming, excluir=None):
    viz, _ = vizinhos(base, consulta, k, distancia, excluir)
    classe, votos = votar(base, viz)
    return classe, viz, votos


def leave_one_out(base, k, distancia=distancia_hamming):
    acertos, previsoes = 0, []
    for i, linha in base.iterrows():
        prevista, _, _ = classificar(base, linha, k, distancia, excluir=i)
        previsoes.append(prevista)
        acertos += prevista == linha[CLASSE]
    return acertos / len(base), previsoes


# ---------------------------------------------------------------------------
# Demonstração
# ---------------------------------------------------------------------------
def demonstrar_passo_a_passo(base, consulta, k):
    print("Cliente novo:", ", ".join(f"{a}={consulta[a]}" for a in ATRIBUTOS))
    print(f"\nPasso 1. Distância de Hamming do cliente a cada um dos {len(base)} exemplos")
    _, todas = vizinhos(base, consulta, k)
    print("  Exemplo  " + "  ".join(f"{a[:12]:<12}" for a in ATRIBUTOS) + "  Risco      d")
    for d, i in sorted(todas, key=lambda t: t[1]):
        linha = base.loc[i]
        marcas = "  ".join(
            f"{(linha[a] if linha[a] == consulta[a] else '*' + linha[a])[:12]:<12}"
            for a in ATRIBUTOS)
        print(f"  {linha['Exemplo']:<7}  {marcas}  {linha[CLASSE]:<9} {d}")
    print("  (* marca o atributo que difere do cliente; cada * soma 1 à distância)")

    print(f"\nPasso 2. Ordenar pela distância e pegar os k = {k} mais próximos")
    classe, viz, votos = classificar(base, consulta, k)
    for pos, (d, i) in enumerate(viz, 1):
        print(f"  {pos}º  {base.loc[i, 'Exemplo']:<4} d = {d}  Risco = {base.loc[i, CLASSE]}")
    dk = viz[-1][0]
    empatados = [base.loc[i, "Exemplo"] for d, i in todas if d == dk]
    if len(empatados) > sum(1 for d, _ in viz if d == dk):
        print(f"  Obs.: {len(empatados)} exemplos estão à distância {dk} ({', '.join(empatados)});"
              " o desempate segue a ordem da base.")

    print("\nPasso 3. Votação")
    for c, v in votos.most_common():
        print(f"  {c}: {v} voto(s)")
    print(f"  Classe prevista: Risco = {classe}")
    return classe


def avaliar(base):
    print("\nAvaliação leave-one-out (cada exemplo é classificado pelos outros 29)")
    print("   k   Hamming   Ordinal   scikit-learn (Hamming)")
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.model_selection import LeaveOneOut, cross_val_predict
    from sklearn.preprocessing import OrdinalEncoder

    X = OrdinalEncoder().fit_transform(base[ATRIBUTOS])
    y = base[CLASSE].values
    linhas = []
    for k in (1, 3, 5, 7, 9):
        acc_h, _ = leave_one_out(base, k, distancia_hamming)
        acc_o, _ = leave_one_out(base, k, distancia_ordinal)
        knn = KNeighborsClassifier(n_neighbors=k, metric="hamming", algorithm="brute")
        pred = cross_val_predict(knn, X, y, cv=LeaveOneOut())
        acc_sk = (pred == y).mean()
        linhas.append((k, acc_h, acc_o, acc_sk))
        print(f"  {k:>2}   {acc_h:7.3f}   {acc_o:7.3f}   {acc_sk:7.3f}")
    print("  Obs.: com Hamming a distância só assume 7 valores (0 a 6) e há muitos empates.")
    print("  O scikit-learn escolhe de outro modo entre exemplos empatados na k-ésima distância")
    print("  e desempata votos pela ordem alfabética das classes; daí as pequenas diferenças.")
    return linhas


def matriz_confusao(base, k):
    _, prev = leave_one_out(base, k)
    classes = ["Baixo", "Moderado", "Alto"]
    tab = pd.crosstab(pd.Series(base[CLASSE], name="Real"),
                      pd.Series(prev, name="Previsto")).reindex(index=classes,
                                                                 columns=classes, fill_value=0)
    print(f"\nMatriz de confusão (leave-one-out, Hamming, k = {k})")
    print(tab.to_string())
    erros = [base.loc[i, "Exemplo"] for i in range(len(base)) if prev[i] != base.loc[i, CLASSE]]
    print("Exemplos classificados errado:", ", ".join(erros) if erros else "nenhum")


def grafico(linhas):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ks = [l[0] for l in linhas]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(ks, [l[1] for l in linhas], marker="o", label="Hamming")
    ax.plot(ks, [l[2] for l in linhas], marker="s", label="Ordinal")
    ax.set_xlabel("k")
    ax.set_ylabel("Acurácia (leave-one-out)")
    ax.set_xticks(ks)
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("KNN na base de risco de crédito (30 exemplos)")
    fig.tight_layout()
    fig.savefig(AQUI / "acuracia_por_k.png", dpi=150)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, default=3)
    p.add_argument("--cliente", default="Desconhecida,Alta,Adequada,15-35,Estavel,Adulto",
                   help="valores na ordem: " + ",".join(ATRIBUTOS))
    args = p.parse_args()
    base = carregar_base()
    consulta = pd.Series(dict(zip(ATRIBUTOS, args.cliente.split(","))))
    print("=" * 78)
    demonstrar_passo_a_passo(base, consulta, args.k)
    print("=" * 78)
    linhas = avaliar(base)
    matriz_confusao(base, args.k)
    grafico(linhas)
    print("\nGráfico salvo em acuracia_por_k.png")


if __name__ == "__main__":
    main()
