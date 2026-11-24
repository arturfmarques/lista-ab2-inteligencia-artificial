#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 6 - Lista 2 de IA (2026.2)
Sistema fuzzy de Mamdani para irrigação: decide por quantos minutos ligar a
irrigação de um canteiro a partir da umidade do solo e da temperatura do ar.

O programa:
  1. define as variáveis linguísticas, seus universos e funções de pertinência;
  2. define a base de 9 regras SE...ENTÃO;
  3. faz a inferência de Mamdani "à mão" com numpy, mostrando cada etapa
     (fuzzificação, ativação das regras, implicação, agregação, defuzzificação);
  4. repete a inferência com o scikit-fuzzy (ControlSystem) e confere que o
     resultado é o mesmo;
  5. compara métodos de defuzzificação e gera os gráficos em ./figuras.

Mamdani: E = mínimo, OU = máximo, implicação = mínimo (corte),
agregação = máximo, defuzzificação = centroide.

Uso:
  python fuzzy_irrigacao.py                        # caso de exemplo (33 %, 31 °C)
  python fuzzy_irrigacao.py --umidade 60 --temperatura 22
Dependências: numpy, scikit-fuzzy, matplotlib.
"""

import argparse
from pathlib import Path

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

FIG = Path(__file__).parent / "figuras"

# ---------------------------------------------------------------------------
# 1. Variáveis linguísticas e universos de discurso
# ---------------------------------------------------------------------------
U_UMIDADE = np.arange(0, 100.01, 0.1)      # umidade do solo, % (0 a 100)
U_TEMPERATURA = np.arange(0, 45.01, 0.05)  # temperatura do ar, °C (0 a 45)
U_TEMPO = np.arange(0, 60.01, 0.05)        # tempo de irrigação, min (0 a 60)

# Funções de pertinência: trapmf [a, b, c, d] e trimf [a, b, c]
MF = {
    "umidade": {
        "seco":   ("trap", [0, 0, 20, 40]),
        "ideal":  ("tri",  [30, 50, 70]),
        "umido":  ("trap", [60, 80, 100, 100]),
    },
    "temperatura": {
        "baixa":  ("trap", [0, 0, 15, 22]),
        "media":  ("tri",  [18, 25, 32]),
        "alta":   ("trap", [28, 35, 45, 45]),
    },
    "tempo": {
        "nulo":   ("tri",  [0, 0, 8]),
        "curto":  ("tri",  [5, 15, 25]),
        "medio":  ("tri",  [20, 30, 40]),
        "longo":  ("trap", [35, 45, 60, 60]),
    },
}
UNIVERSOS = {"umidade": U_UMIDADE, "temperatura": U_TEMPERATURA, "tempo": U_TEMPO}

# ---------------------------------------------------------------------------
# 2. Base de regras: SE umidade = X E temperatura = Y ENTÃO tempo = Z
# ---------------------------------------------------------------------------
REGRAS = [
    ("seco",  "baixa", "medio"),
    ("seco",  "media", "longo"),
    ("seco",  "alta",  "longo"),
    ("ideal", "baixa", "nulo"),
    ("ideal", "media", "curto"),
    ("ideal", "alta",  "medio"),
    ("umido", "baixa", "nulo"),
    ("umido", "media", "nulo"),
    ("umido", "alta",  "curto"),
]


def curva(variavel, termo, universo=None):
    tipo, p = MF[variavel][termo]
    x = UNIVERSOS[variavel] if universo is None else universo
    return fuzz.trapmf(x, p) if tipo == "trap" else fuzz.trimf(x, p)


def grau(variavel, termo, valor):
    """Grau de pertinência de um valor nítido (crisp) em um termo."""
    return float(fuzz.interp_membership(UNIVERSOS[variavel], curva(variavel, termo), valor))


# ---------------------------------------------------------------------------
# 3. Inferência de Mamdani passo a passo
# ---------------------------------------------------------------------------
def mamdani_manual(umidade, temperatura, mostrar=True):
    # Etapa 1: fuzzificação
    mu_u = {t: grau("umidade", t, umidade) for t in MF["umidade"]}
    mu_t = {t: grau("temperatura", t, temperatura) for t in MF["temperatura"]}
    if mostrar:
        print(f"Entradas: umidade = {umidade} %, temperatura = {temperatura} °C")
        print("\nEtapa 1 - Fuzzificação")
        print("  umidade:     " + ", ".join(f"{t} = {v:.3f}" for t, v in mu_u.items()))
        print("  temperatura: " + ", ".join(f"{t} = {v:.3f}" for t, v in mu_t.items()))

    # Etapa 2: ativação de cada regra (E = mínimo)
    # Etapa 3: implicação de Mamdani (corta a saída na altura da ativação)
    cortes = []
    if mostrar:
        print("\nEtapa 2 - Ativação das regras (E = mínimo)")
    for n, (tu, tt, ts) in enumerate(REGRAS, 1):
        alfa = min(mu_u[tu], mu_t[tt])
        cortes.append((ts, alfa))
        if mostrar and alfa > 0:
            print(f"  R{n}: SE umidade é {tu} ({mu_u[tu]:.3f}) E temperatura é {tt} "
                  f"({mu_t[tt]:.3f}) ENTÃO tempo é {ts}  ->  alfa = {alfa:.3f}")
    if mostrar:
        inativas = [f"R{n}" for n, (_, a) in enumerate(cortes, 1) if a == 0]
        print(f"  Regras com ativação 0: {', '.join(inativas)}")

    # Etapa 4: agregação (máximo das saídas cortadas)
    saida = np.zeros_like(U_TEMPO)
    por_termo = {}
    for ts, alfa in cortes:
        por_termo[ts] = max(por_termo.get(ts, 0.0), alfa)
        saida = np.fmax(saida, np.fmin(alfa, curva("tempo", ts)))
    if mostrar:
        print("\nEtapa 3 - Implicação (mínimo) e Etapa 4 - Agregação (máximo)")
        for ts in MF["tempo"]:
            print(f"  tempo é {ts:<5}: cortado na altura {por_termo.get(ts, 0.0):.3f}")

    # Etapa 5: defuzzificação pelo centroide
    if saida.sum() == 0:
        raise ValueError("Nenhuma regra foi ativada para essas entradas.")
    centroide = float(np.sum(U_TEMPO * saida) / np.sum(saida))
    if mostrar:
        print("\nEtapa 5 - Defuzzificação pelo centroide: "
              "z* = soma(z * mu(z)) / soma(mu(z))")
        print(f"  Tempo de irrigação = {centroide:.2f} min")
    return centroide, saida


# ---------------------------------------------------------------------------
# 4. A mesma solução com o scikit-fuzzy
# ---------------------------------------------------------------------------
def construir_sistema():
    umidade = ctrl.Antecedent(U_UMIDADE, "umidade")
    temperatura = ctrl.Antecedent(U_TEMPERATURA, "temperatura")
    tempo = ctrl.Consequent(U_TEMPO, "tempo", defuzzify_method="centroid")
    for var, nome in ((umidade, "umidade"), (temperatura, "temperatura"), (tempo, "tempo")):
        for termo in MF[nome]:
            var[termo] = curva(nome, termo)
    regras = [ctrl.Rule(umidade[u] & temperatura[t], tempo[s]) for u, t, s in REGRAS]
    return ctrl.ControlSystem(regras)


def mamdani_skfuzzy(sistema, umidade, temperatura):
    sim = ctrl.ControlSystemSimulation(sistema)
    sim.input["umidade"] = umidade
    sim.input["temperatura"] = temperatura
    sim.compute()
    return float(sim.output["tempo"])


# ---------------------------------------------------------------------------
# 5. Gráficos
# ---------------------------------------------------------------------------
def graficos(umidade, temperatura, saida, centroide, sistema):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(exist_ok=True)

    fig, eixos = plt.subplots(3, 1, figsize=(7, 8))
    titulos = {"umidade": "Umidade do solo (%)", "temperatura": "Temperatura do ar (°C)",
               "tempo": "Tempo de irrigação (min)"}
    for ax, nome in zip(eixos, ("umidade", "temperatura", "tempo")):
        for termo in MF[nome]:
            ax.plot(UNIVERSOS[nome], curva(nome, termo), label=termo)
        ax.set_title(titulos[nome])
        ax.set_ylabel("pertinência")
        ax.set_ylim(-0.02, 1.05)
        ax.legend(loc="center right", fontsize=8)
        ax.grid(alpha=0.3)
    eixos[0].axvline(umidade, color="k", ls="--", lw=1)
    eixos[1].axvline(temperatura, color="k", ls="--", lw=1)
    fig.tight_layout()
    fig.savefig(FIG / "funcoes_pertinencia.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.4))
    for termo in MF["tempo"]:
        ax.plot(U_TEMPO, curva("tempo", termo), lw=0.8, ls=":", color="gray")
    ax.fill_between(U_TEMPO, saida, alpha=0.5, label="saída agregada")
    ax.axvline(centroide, color="k", lw=1.5, label=f"centroide = {centroide:.2f} min")
    ax.set_xlabel("Tempo de irrigação (min)")
    ax.set_ylabel("pertinência")
    ax.set_title(f"Agregação para umidade = {umidade} % e temperatura = {temperatura} °C")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "agregacao_e_centroide.png", dpi=150)
    plt.close(fig)

    xs = np.linspace(0, 100, 41)
    ys = np.linspace(0, 45, 37)
    Z = np.array([[mamdani_manual(x, y, mostrar=False)[0] for x in xs] for y in ys])
    X, Y = np.meshgrid(xs, ys)
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="none")
    ax.set_xlabel("Umidade (%)")
    ax.set_ylabel("Temperatura (°C)")
    ax.set_zlabel("Tempo (min)")
    ax.set_title("Superfície de controle")
    ax.view_init(28, -130)
    fig.tight_layout()
    fig.savefig(FIG / "superficie_controle.png", dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--umidade", type=float, default=33.0)
    p.add_argument("--temperatura", type=float, default=31.0)
    args = p.parse_args()

    print("=" * 74)
    print("Base de regras")
    for n, (u, t, s) in enumerate(REGRAS, 1):
        print(f"  R{n}: SE umidade é {u} E temperatura é {t} ENTÃO tempo é {s}")
    print("=" * 74)
    centroide, saida = mamdani_manual(args.umidade, args.temperatura)

    sistema = construir_sistema()
    via_lib = mamdani_skfuzzy(sistema, args.umidade, args.temperatura)
    print(f"\nConferência com scikit-fuzzy: {via_lib:.2f} min "
          f"(diferença {abs(via_lib - centroide):.4f})")

    print("\nOutros métodos de defuzzificação sobre a mesma saída agregada:")
    for m, nome in (("centroid", "centroide"), ("bisector", "bissetriz"),
                    ("mom", "média dos máximos"), ("som", "menor dos máximos"),
                    ("lom", "maior dos máximos")):
        print(f"  {nome:<18} {fuzz.defuzz(U_TEMPO, saida, m):6.2f} min")

    print("=" * 74)
    print("Outros cenários (centroide):")
    print("  umidade  temperatura   tempo (manual)   tempo (scikit-fuzzy)")
    for u, t in ((10, 35), (20, 18), (45, 25), (50, 38), (65, 30), (90, 40)):
        m, _ = mamdani_manual(u, t, mostrar=False)
        print(f"  {u:>6} %   {t:>7} °C   {m:12.2f} min   {mamdani_skfuzzy(sistema, u, t):12.2f} min")

    graficos(args.umidade, args.temperatura, saida, centroide, sistema)
    print("\nFiguras salvas em ./figuras")


if __name__ == "__main__":
    main()
