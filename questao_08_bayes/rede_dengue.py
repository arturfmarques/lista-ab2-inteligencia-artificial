#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 8 - Lista 2 de IA (2026.2)
Diagnóstico de dengue com rede bayesiana (pgmpy).

AVISO: modelo educacional. As probabilidades foram definidas de forma
plausível para ilustrar o raciocínio sob incerteza; não servem para uso clínico.

Variáveis (todas binárias):
  EpocaChuvosa    fator ambiental: período de chuvas (mais mosquitos)
  CasoVizinhanca  há caso confirmado de dengue na vizinhança
  Dengue          doença principal a diagnosticar
  Gripe           diagnóstico concorrente (causa alternativa de febre e dor)
  Febre, DorRetroOrbital, ManchasPele, DorMuscular, Tosse   sintomas observáveis
  TesteNS1        resultado do teste rápido de antígeno NS1

Estrutura (pai -> filho):
  EpocaChuvosa -> CasoVizinhanca
  EpocaChuvosa, CasoVizinhanca -> Dengue
  Dengue, Gripe -> Febre
  Dengue, Gripe -> DorMuscular
  Dengue -> DorRetroOrbital, ManchasPele, TesteNS1
  Gripe -> Tosse

O programa imprime as CPTs, as independências condicionais, executa os
experimentos de inferência (eliminação de variáveis), salva o grafo em
rede_dengue.png e o modelo em rede_dengue.bif e rede_dengue.xmlbif.

Uso:  python rede_dengue.py
      python rede_dengue.py --evidencias Febre=Sim,DorRetroOrbital=Sim
Dependências: pgmpy, networkx, matplotlib.
"""

import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

from pgmpy.inference import VariableElimination
from pgmpy.factors.discrete import TabularCPD
try:
    from pgmpy.models import DiscreteBayesianNetwork as BN
except ImportError:  # versões antigas do pgmpy
    from pgmpy.models import BayesianNetwork as BN

AQUI = Path(__file__).parent
S = ["Sim", "Nao"]

ARESTAS = [
    ("EpocaChuvosa", "CasoVizinhanca"),
    ("EpocaChuvosa", "Dengue"), ("CasoVizinhanca", "Dengue"),
    ("Dengue", "Febre"), ("Gripe", "Febre"),
    ("Dengue", "DorMuscular"), ("Gripe", "DorMuscular"),
    ("Dengue", "DorRetroOrbital"), ("Dengue", "ManchasPele"),
    ("Dengue", "TesteNS1"), ("Gripe", "Tosse"),
]


def binaria(var, p_sim, pais=None):
    """CPD binária a partir da lista P(var=Sim | combinação dos pais).

    A ordem das combinações segue o pgmpy: o primeiro pai varia mais devagar,
    e cada pai assume Sim antes de Nao.
    """
    pais = pais or []
    p_sim = p_sim if isinstance(p_sim, list) else [p_sim]
    return TabularCPD(var, 2, [p_sim, [1 - p for p in p_sim]],
                      evidence=pais or None, evidence_card=[2] * len(pais) or None,
                      state_names={var: S, **{p: S for p in pais}})


def construir_rede():
    rede = BN(ARESTAS)
    cpds = [
        binaria("EpocaChuvosa", 0.40),
        binaria("CasoVizinhanca", [0.30, 0.08], ["EpocaChuvosa"]),
        # P(Dengue=Sim | EpocaChuvosa, CasoVizinhanca): (S,S) (S,N) (N,S) (N,N)
        binaria("Dengue", [0.20, 0.05, 0.08, 0.01], ["EpocaChuvosa", "CasoVizinhanca"]),
        binaria("Gripe", 0.10),
        # P(Febre=Sim | Dengue, Gripe): (S,S) (S,N) (N,S) (N,N)
        binaria("Febre", [0.98, 0.95, 0.85, 0.10], ["Dengue", "Gripe"]),
        binaria("DorMuscular", [0.95, 0.85, 0.75, 0.10], ["Dengue", "Gripe"]),
        binaria("DorRetroOrbital", [0.60, 0.05], ["Dengue"]),
        binaria("ManchasPele", [0.45, 0.03], ["Dengue"]),
        # NS1: sensibilidade 0,80 e especificidade 0,97 (P(+|sem dengue) = 0,03)
        binaria("TesteNS1", [0.80, 0.03], ["Dengue"]),
        binaria("Tosse", [0.80, 0.10], ["Gripe"]),
    ]
    rede.add_cpds(*cpds)
    assert rede.check_model()
    return rede


def p_sim(inf, var, evid):
    return float(inf.query([var], evidence=evid, show_progress=False).values[0])


def fmt_evid(evid):
    return ", ".join(f"{k}={v}" for k, v in evid.items()) or "(nenhuma)"


def imprimir_cpds(rede):
    print("TABELAS DE PROBABILIDADES CONDICIONAIS")
    for cpd in rede.get_cpds():
        print(f"\n{cpd.variable}")
        print(cpd)


def independencias(rede):
    print("\nINDEPENDÊNCIAS CONDICIONAIS (d-separação) verificadas na rede")
    testes = [
        ("DorRetroOrbital", "Febre", ["Dengue"]),
        ("ManchasPele", "TesteNS1", ["Dengue"]),
        ("EpocaChuvosa", "Febre", ["Dengue"]),
        ("Tosse", "Dengue", []),
        ("Tosse", "Dengue", ["Febre"]),
        ("Gripe", "Dengue", []),
        ("Gripe", "Dengue", ["Febre"]),
        ("CasoVizinhanca", "ManchasPele", ["Dengue"]),
    ]
    for x, y, z in testes:
        ind = not rede.is_dconnected(x, y, observed=z)
        cond = f" | {', '.join(z)}" if z else ""
        print(f"  {x} ⟂ {y}{cond}: {'sim' if ind else 'NÃO (dependentes)'}")


def experimento_sequencial(inf, titulo, passos, alvos=("Dengue",)):
    print("\n" + "=" * 78)
    print(titulo)
    print("-" * 78)
    evid = {}
    linhas = []
    cab = "  " + f"{'Evidências acumuladas':<90}" + "".join(f"P({a}=Sim)  " for a in alvos)
    print(cab)
    for k, v in [(None, None)] + passos:
        if k:
            evid[k] = v
        vals = [p_sim(inf, a, evid) for a in alvos]
        linhas.append((dict(evid), vals))
        print(f"  {fmt_evid(evid):<90}" + "".join(f"{x:>14.4f}" for x in vals))
    return linhas


def influencia_individual(inf):
    print("\n" + "=" * 78)
    print("Influência de cada evidência isolada sobre P(Dengue=Sim)")
    print("-" * 78)
    base = p_sim(inf, "Dengue", {})
    print(f"  A priori: {base:.4f}")
    print(f"  {'Evidência':<26}{'P(Dengue|Sim)':>15}{'P(Dengue|Nao)':>15}{'razão Sim/priori':>18}")
    for v in ("Febre", "DorMuscular", "DorRetroOrbital", "ManchasPele", "Tosse",
              "TesteNS1", "CasoVizinhanca", "EpocaChuvosa"):
        ps = p_sim(inf, "Dengue", {v: "Sim"})
        pn = p_sim(inf, "Dengue", {v: "Nao"})
        print(f"  {v:<26}{ps:>15.4f}{pn:>15.4f}{ps / base:>18.2f}")


def salvar(rede):
    from pgmpy.readwrite import BIFWriter, XMLBIFWriter
    for cls, nome, antigo in ((BIFWriter, "rede_dengue.bif", "write_bif"),
                              (XMLBIFWriter, "rede_dengue.xmlbif", "write_xmlbif")):
        w = cls(rede)
        getattr(w, "write" if hasattr(w, "write") else antigo)(str(AQUI / nome))


def desenhar(rede):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pos = {
        "EpocaChuvosa": (0, 3), "CasoVizinhanca": (2, 3), "Gripe": (5.5, 2),
        "Dengue": (1, 2),
        "DorRetroOrbital": (-1.6, 0.6), "ManchasPele": (0, 0.6), "TesteNS1": (1.6, 0.6),
        "Febre": (3.2, 0.6), "DorMuscular": (4.8, 0.6), "Tosse": (6.4, 0.6),
    }
    cores = {"EpocaChuvosa": "#d9e8f5", "CasoVizinhanca": "#d9e8f5",
             "Dengue": "#f7c6c5", "Gripe": "#fbe3c3", "TesteNS1": "#e3d7f2"}
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.set_xlim(-2.6, 7.4)
    ax.set_ylim(0, 3.6)
    textos = {n: ax.text(*pos[n], n, ha="center", va="center", fontsize=9, zorder=3,
                         bbox=dict(boxstyle="round,pad=0.5", fc=cores.get(n, "#dff0d8"),
                                   ec="#444"))
              for n in rede.nodes()}
    fig.canvas.draw()
    for u, v in rede.edges():
        ax.annotate("", xy=pos[v], xytext=pos[u], zorder=2,
                    arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.3, mutation_scale=16,
                                    patchA=textos[u].get_bbox_patch(),
                                    patchB=textos[v].get_bbox_patch(), shrinkA=1, shrinkB=1))
    ax.set_title("Rede bayesiana para diagnóstico de dengue\n"
                 "azul: fatores de contexto; vermelho: doença principal; laranja: doença "
                 "concorrente; verde: sintomas; roxo: exame", fontsize=10)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(AQUI / "rede_dengue.png", dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidencias", help="ex.: Febre=Sim,DorRetroOrbital=Sim,TesteNS1=Nao")
    args = p.parse_args()
    rede = construir_rede()
    inf = VariableElimination(rede)

    if args.evidencias:
        evid = dict(item.split("=") for item in args.evidencias.split(","))
        print("Evidências:", fmt_evid(evid))
        for alvo in ("Dengue", "Gripe"):
            print(f"  P({alvo}=Sim) a priori = {p_sim(inf, alvo, {}):.4f}   "
                  f"a posteriori = {p_sim(inf, alvo, evid):.4f}")
        return

    print(f"Rede com {len(rede.nodes())} variáveis e {len(rede.edges())} arcos.")
    imprimir_cpds(rede)
    independencias(rede)

    print("\nPROBABILIDADES A PRIORI (sem evidências)")
    for v in ("EpocaChuvosa", "CasoVizinhanca", "Dengue", "Gripe", "Febre", "TesteNS1"):
        print(f"  P({v}=Sim) = {p_sim(inf, v, {}):.4f}")

    experimento_sequencial(
        inf, "Experimento 1: diagnóstico com inclusão sucessiva de sintomas",
        [("Febre", "Sim"), ("DorMuscular", "Sim"), ("DorRetroOrbital", "Sim"),
         ("ManchasPele", "Sim")], alvos=("Dengue", "Gripe"))

    experimento_sequencial(
        inf, "Experimento 2: explicação alternativa (explaining away) com tosse",
        [("Febre", "Sim"), ("DorMuscular", "Sim"), ("Tosse", "Sim")],
        alvos=("Dengue", "Gripe"))

    experimento_sequencial(
        inf, "Experimento 3: contexto epidemiológico e teste NS1 positivo",
        [("Febre", "Sim"), ("DorRetroOrbital", "Sim"), ("EpocaChuvosa", "Sim"),
         ("CasoVizinhanca", "Sim"), ("TesteNS1", "Sim")])

    print("\n" + "=" * 78)
    print("Experimento 4: comparação de conjuntos de evidências")
    print("-" * 78)
    conjuntos = [
        {"Febre": "Sim", "DorRetroOrbital": "Sim", "ManchasPele": "Sim"},
        {"Febre": "Sim", "DorRetroOrbital": "Sim", "ManchasPele": "Sim", "TesteNS1": "Nao"},
        {"Febre": "Sim", "DorRetroOrbital": "Sim", "ManchasPele": "Sim", "EpocaChuvosa": "Nao"},
        {"Febre": "Sim", "DorMuscular": "Sim", "Tosse": "Sim", "TesteNS1": "Nao"},
        {"Febre": "Nao", "DorMuscular": "Sim"},
    ]
    print(f"  {'Evidências':<70}{'P(Dengue)':>10}{'P(Gripe)':>10}")
    for e in conjuntos:
        print(f"  {fmt_evid(e):<70}{p_sim(inf, 'Dengue', e):>10.4f}{p_sim(inf, 'Gripe', e):>10.4f}")

    influencia_individual(inf)
    salvar(rede)
    desenhar(rede)
    print("\nArquivos gerados: rede_dengue.bif, rede_dengue.xmlbif, rede_dengue.png")


if __name__ == "__main__":
    main()
