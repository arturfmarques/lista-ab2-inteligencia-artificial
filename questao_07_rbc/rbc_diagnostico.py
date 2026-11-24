#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 7 - Lista 2 de IA (2026.2)
Sistema de Apoio ao Diagnóstico Médico Baseado em Casos (RBC / CBR).

AVISO: protótipo educacional. Os casos são fictícios e o sistema não
substitui avaliação médica.

Ciclo de RBC implementado (Aamodt e Plaza, 1994):
  1. Recuperação (Retrieve): calcula a similaridade da consulta com cada caso
     e devolve os k mais semelhantes;
  2. Reutilização (Reuse): soma as similaridades dos k casos por diagnóstico,
     propõe o diagnóstico de maior soma e o tratamento do caso mais parecido
     que tem esse diagnóstico;
  3. Revisão (Revise): o profissional confirma ou corrige diagnóstico e tratamento;
  4. Retenção (Retain): o caso revisado é gravado na base (casos.json).

Representação de um caso:
  {"id", "idade", "sintomas": [...], "temperatura" (°C), "duracao_dias",
   "diagnostico", "tratamento", "origem"}

Similaridade global (média ponderada de similaridades locais):
  sim = 0,70 * sim_sintomas + 0,20 * sim_temperatura + 0,10 * sim_duracao
  - sim_sintomas: Jaccard ponderado = soma dos pesos dos sintomas em comum /
    soma dos pesos dos sintomas presentes em pelo menos um dos dois casos.
    Sintomas mais específicos (dor atrás dos olhos, perda de olfato...) pesam mais.
  - sim_temperatura = 1 - |t1 - t2| / 5   (limitada a [0, 1])
  - sim_duracao     = 1 - |d1 - d2| / 14  (limitada a [0, 1])
  Se a consulta (ou o caso) não tem temperatura ou duração, o peso desse
  atributo é retirado e os demais são renormalizados.

Reutilização: entre os k recuperados, só votam os casos com similaridade de pelo
menos 85 % da do mais parecido (MARGEM_VOTO). Assim um caso quase idêntico não é
vencido por dois casos medianos de outra doença.

Uso:
  python rbc_diagnostico.py listar
  python rbc_diagnostico.py consultar --sintomas febre,tosse,perda_olfato --temperatura 38 --dias 3
  python rbc_diagnostico.py consultar ... --confirmar          (revisão: aceita a sugestão e retém)
  python rbc_diagnostico.py consultar ... --corrigir "Dengue" --tratamento "..."
  python rbc_diagnostico.py interativo                        (menu com revisão e retenção)
  python rbc_diagnostico.py avaliar                           (validação leave-one-out)
  python rbc_diagnostico.py demo                              (exemplos do relatório)
  python rbc_diagnostico.py reiniciar                         (restaura a base inicial)
Dependências: somente a biblioteca padrão do Python 3.
"""

import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
BASE_INICIAL = AQUI / "casos_iniciais.json"
BASE = AQUI / "casos.json"

PESOS_ATRIBUTOS = {"sintomas": 0.70, "temperatura": 0.20, "duracao_dias": 0.10}
FAIXA = {"temperatura": 5.0, "duracao_dias": 14.0}
K_PADRAO = 3
MARGEM_VOTO = 0.85
LIMIAR_CONFIANCA = 0.50  # abaixo disso, o sistema avisa que nenhum caso é parecido

# Peso de cada sintoma na similaridade (padrão = 1)
PESO_SINTOMA = defaultdict(lambda: 1.0, {
    "dor_atras_olhos": 3, "manchas_pele": 3, "perda_olfato": 3, "perda_paladar": 3,
    "sensibilidade_luz": 3, "sensibilidade_som": 2, "dor_face": 3, "secrecao_espessa": 2,
    "diarreia": 3, "dor_abdominal": 2, "falta_ar": 2, "dor_articular": 2,
    "espirros": 2, "congestao_nasal": 2, "visao_turva": 2, "calafrios": 1.5,
})


# ---------------------------------------------------------------------------
# Base de casos
# ---------------------------------------------------------------------------
def carregar(caminho=BASE):
    if not caminho.exists():
        shutil.copy(BASE_INICIAL, caminho)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def salvar(casos, caminho=BASE):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(casos, f, ensure_ascii=False, indent=1)


def vocabulario(casos):
    return sorted({s for c in casos for s in c["sintomas"]})


# ---------------------------------------------------------------------------
# Similaridade
# ---------------------------------------------------------------------------
def sim_sintomas(a, b):
    a, b = set(a), set(b)
    uniao = a | b
    if not uniao:
        return 1.0
    return sum(PESO_SINTOMA[s] for s in a & b) / sum(PESO_SINTOMA[s] for s in uniao)


def sim_numerica(x, y, faixa):
    return max(0.0, 1.0 - abs(x - y) / faixa)


def similaridade(consulta, caso):
    """Retorna (similaridade global, dicionário com as similaridades locais)."""
    locais = {"sintomas": sim_sintomas(consulta["sintomas"], caso["sintomas"])}
    for atr in ("temperatura", "duracao_dias"):
        if consulta.get(atr) is not None and caso.get(atr) is not None:
            locais[atr] = sim_numerica(consulta[atr], caso[atr], FAIXA[atr])
    peso_total = sum(PESOS_ATRIBUTOS[a] for a in locais)
    global_ = sum(PESOS_ATRIBUTOS[a] * v for a, v in locais.items()) / peso_total
    return global_, locais


# ---------------------------------------------------------------------------
# Ciclo 4R
# ---------------------------------------------------------------------------
def recuperar(casos, consulta, k=K_PADRAO, excluir_id=None):
    ranking = []
    for caso in casos:
        if caso["id"] == excluir_id:
            continue
        s, locais = similaridade(consulta, caso)
        ranking.append((s, locais, caso))
    ranking.sort(key=lambda t: (-t[0], t[2]["id"]))
    return ranking[:k]


def reutilizar(recuperados):
    corte = MARGEM_VOTO * recuperados[0][0]
    votantes = [r for r in recuperados if r[0] >= corte]
    pontos = defaultdict(float)
    for s, _, caso in votantes:
        pontos[caso["diagnostico"]] += s
    diagnostico = max(pontos, key=lambda d: (pontos[d], -min(
        i for i, (_, _, c) in enumerate(recuperados) if c["diagnostico"] == d)))
    confianca = pontos[diagnostico] / sum(pontos.values())
    base = next(c for _, _, c in recuperados if c["diagnostico"] == diagnostico)
    return {
        "diagnostico": diagnostico,
        "tratamento": base["tratamento"],
        "confianca": confianca,
        "caso_base": base["id"],
        "similaridade_max": recuperados[0][0],
        "pontos": dict(pontos),
        "ignorados": [c["id"] for s, _, c in recuperados if s < corte],
        "corte": corte,
    }


def revisar(sugestao, confirmar=False, corrigir=None, tratamento=None, interativo=False):
    """Devolve (diagnóstico final, tratamento final, revisado_por) ou None se não retiver."""
    if interativo:
        r = input("\nO diagnóstico sugerido está correto? [s/n/ignorar] ").strip().lower()
        if r.startswith("s"):
            return sugestao["diagnostico"], sugestao["tratamento"], "confirmado"
        if r.startswith("n"):
            dx = input("Diagnóstico correto: ").strip()
            tt = input("Tratamento recomendado (Enter para manter o sugerido): ").strip()
            return dx, tt or sugestao["tratamento"], "corrigido"
        return None
    if corrigir:
        return corrigir, tratamento or sugestao["tratamento"], "corrigido"
    if confirmar:
        return sugestao["diagnostico"], tratamento or sugestao["tratamento"], "confirmado"
    return None


def reter(casos, consulta, diagnostico, tratamento, revisao, caminho=BASE):
    # Política de retenção: não grava um caso idêntico a outro já existente
    # com o mesmo diagnóstico, pois ele não traria conhecimento novo.
    for c in casos:
        s, _ = similaridade(consulta, c)
        if s >= 0.999 and c["diagnostico"] == diagnostico:
            return None, c["id"]
    novo_id = f"C{max(int(c['id'][1:]) for c in casos) + 1:02d}"
    casos.append({
        "id": novo_id,
        "idade": consulta.get("idade"),
        "sintomas": sorted(consulta["sintomas"]),
        "temperatura": consulta.get("temperatura"),
        "duracao_dias": consulta.get("duracao_dias"),
        "diagnostico": diagnostico,
        "tratamento": tratamento,
        "origem": f"retido após revisão ({revisao})",
    })
    salvar(casos, caminho)
    return novo_id, None


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------
def mostrar_consulta(consulta):
    partes = ["sintomas = " + ", ".join(consulta["sintomas"])]
    if consulta.get("temperatura") is not None:
        partes.append(f"temperatura = {consulta['temperatura']} °C")
    if consulta.get("duracao_dias") is not None:
        partes.append(f"duração = {consulta['duracao_dias']} dia(s)")
    if consulta.get("idade") is not None:
        partes.append(f"idade = {consulta['idade']}")
    print("Consulta: " + "; ".join(partes))


def mostrar_recuperados(recuperados):
    print("\n[Recuperação] Casos mais semelhantes")
    print("  Caso  Sim.   sintomas  temp.  duração  Diagnóstico         Sintomas do caso")
    for s, loc, c in recuperados:
        t = f"{loc['temperatura']:.2f}" if "temperatura" in loc else "  -  "
        d = f"{loc['duracao_dias']:.2f}" if "duracao_dias" in loc else "  -  "
        print(f"  {c['id']:<4}  {s:.3f}  {loc['sintomas']:.3f}     {t}   {d}     "
              f"{c['diagnostico']:<19} {', '.join(c['sintomas'])}")


def mostrar_sugestao(sug):
    print(f"\n[Reutilização] Votam os casos com similaridade >= {sug['corte']:.3f} "
          f"({MARGEM_VOTO:.0%} da maior)" +
          (f"; fora da margem: {', '.join(sug['ignorados'])}" if sug['ignorados'] else ""))
    print("  Pontuação por diagnóstico (soma das similaridades):")
    for d, p in sorted(sug["pontos"].items(), key=lambda t: -t[1]):
        print(f"  {d:<19} {p:.3f}")
    print(f"  Diagnóstico sugerido: {sug['diagnostico']} "
          f"(confiança {sug['confianca']:.0%}, baseado no caso {sug['caso_base']})")
    print(f"  Tratamento associado: {sug['tratamento']}")
    if sug["similaridade_max"] < LIMIAR_CONFIANCA:
        print(f"  ATENÇÃO: o caso mais parecido tem similaridade {sug['similaridade_max']:.2f}, "
              f"abaixo de {LIMIAR_CONFIANCA}. A sugestão é fraca e a revisão é obrigatória.")


def montar_consulta(sintomas, temperatura=None, dias=None, idade=None):
    return {"sintomas": [s.strip() for s in sintomas.split(",") if s.strip()],
            "temperatura": temperatura, "duracao_dias": dias, "idade": idade}


def executar_consulta(casos, consulta, k, caminho=BASE, **revisao):
    mostrar_consulta(consulta)
    desconhecidos = set(consulta["sintomas"]) - set(vocabulario(casos))
    if desconhecidos:
        print("  Obs.: sintomas sem registro na base:", ", ".join(sorted(desconhecidos)))
    rec = recuperar(casos, consulta, k)
    mostrar_recuperados(rec)
    sug = reutilizar(rec)
    mostrar_sugestao(sug)
    final = revisar(sug, **revisao)
    if final is None:
        print("\n[Revisão] Sugestão não revisada; o caso não foi retido.")
        return sug, None
    dx, tt, como = final
    print(f"\n[Revisão] Diagnóstico {como}: {dx}")
    novo, igual = reter(casos, consulta, dx, tt, como, caminho)
    if novo:
        print(f"[Retenção] Caso gravado na base como {novo}. A base tem agora {len(casos)} casos.")
    else:
        print(f"[Retenção] Caso idêntico ao {igual}; nada foi gravado.")
    return sug, novo


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def cmd_listar(casos):
    print(f"{len(casos)} casos; {len({c['diagnostico'] for c in casos})} diagnósticos\n")
    for c in casos:
        print(f"{c['id']}  {c['diagnostico']:<19} idade {c['idade']!s:>3}  "
              f"{c['temperatura']} °C  {c['duracao_dias']} d  {', '.join(c['sintomas'])}")


def cmd_avaliar(casos, k):
    """Leave-one-out: cada caso é tratado como consulta e comparado aos demais."""
    acertos, erros = 0, []
    for c in casos:
        q = {a: c[a] for a in ("sintomas", "temperatura", "duracao_dias", "idade")}
        sug = reutilizar(recuperar(casos, q, k, excluir_id=c["id"]))
        if sug["diagnostico"] == c["diagnostico"]:
            acertos += 1
        else:
            erros.append(f"{c['id']} ({c['diagnostico']} -> {sug['diagnostico']})")
    print(f"Leave-one-out com k = {k}: {acertos}/{len(casos)} corretos "
          f"({acertos / len(casos):.0%})")
    if erros:
        print("Erros:", "; ".join(erros))


def cmd_interativo(casos, k):
    vocab = vocabulario(casos)
    print("Sintomas conhecidos:", ", ".join(vocab))
    while True:
        print("\n1) Nova consulta   2) Listar casos   3) Sair")
        op = input("> ").strip()
        if op == "1":
            s = input("Sintomas (separados por vírgula): ")
            t = input("Temperatura em °C (Enter se não medida): ").strip()
            d = input("Há quantos dias (Enter se não souber): ").strip()
            i = input("Idade (Enter para omitir): ").strip()
            q = montar_consulta(s, float(t) if t else None, int(d) if d else None,
                                int(i) if i else None)
            print()
            executar_consulta(casos, q, k, interativo=True)
        elif op == "2":
            cmd_listar(casos)
        elif op == "3":
            break


def cmd_demo(k):
    """Exemplos do relatório, rodados sobre uma cópia temporária da base."""
    tmp = AQUI / "casos_demo.json"
    shutil.copy(BASE_INICIAL, tmp)
    casos = carregar(tmp)
    exemplos = [
        ("Exemplo 1: quadro típico, sugestão confirmada e retida",
         montar_consulta("febre,dor_atras_olhos,dor_muscular,dor_cabeca,manchas_pele",
                         39.1, 3, 26), {"confirmar": True}),
        ("Exemplo 2: sintomas compartilhados por várias doenças",
         montar_consulta("febre,tosse,fadiga,dor_cabeca", 38.4, 3, 40), {}),
        ("Exemplo 3: mesma consulta, agora com perda de olfato (sintoma discriminante)",
         montar_consulta("febre,tosse,fadiga,dor_cabeca,perda_olfato", 38.4, 3, 40),
         {"confirmar": True}),
        ("Exemplo 4: sem temperatura medida (peso renormalizado)",
         montar_consulta("diarreia,nausea,dor_abdominal"), {"confirmar": True}),
        ("Exemplo 5: sugestão errada, corrigida pelo profissional e retida",
         montar_consulta("dor_cabeca,congestao_nasal,coriza", 37.2, 10, 35),
         {"corrigir": "Sinusite",
          "tratamento": "Lavagem nasal com soro, hidratação, analgésico; reavaliar em 7 dias."}),
        ("Exemplo 6: a mesma consulta do exemplo 5 depois da retenção",
         montar_consulta("dor_cabeca,congestao_nasal,coriza", 37.2, 10, 35), {}),
    ]
    for titulo, q, rev in exemplos:
        print("=" * 100)
        print(titulo)
        print("-" * 100)
        executar_consulta(casos, q, k, caminho=tmp, **rev)
    print("=" * 100)
    cmd_avaliar(carregar(BASE_INICIAL), k)
    tmp.unlink()


def main():
    p = argparse.ArgumentParser(description="RBC para apoio ao diagnóstico (educacional)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar")
    c = sub.add_parser("consultar")
    c.add_argument("--sintomas", required=True)
    c.add_argument("--temperatura", type=float)
    c.add_argument("--dias", type=int)
    c.add_argument("--idade", type=int)
    c.add_argument("--confirmar", action="store_true")
    c.add_argument("--corrigir")
    c.add_argument("--tratamento")
    for nome in ("interativo", "avaliar", "demo", "reiniciar"):
        sub.add_parser(nome)
    p.add_argument("-k", type=int, default=K_PADRAO)
    a = p.parse_args()

    if a.cmd == "reiniciar":
        shutil.copy(BASE_INICIAL, BASE)
        print("Base restaurada para os casos iniciais.")
    elif a.cmd == "demo":
        cmd_demo(a.k)
    else:
        casos = carregar()
        if a.cmd == "listar":
            cmd_listar(casos)
        elif a.cmd == "avaliar":
            cmd_avaliar(casos, a.k)
        elif a.cmd == "interativo":
            cmd_interativo(casos, a.k)
        elif a.cmd == "consultar":
            q = montar_consulta(a.sintomas, a.temperatura, a.dias, a.idade)
            executar_consulta(casos, q, a.k, confirmar=a.confirmar,
                              corrigir=a.corrigir, tratamento=a.tratamento)


if __name__ == "__main__":
    sys.exit(main())
