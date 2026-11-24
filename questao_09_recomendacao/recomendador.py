#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 9 - Lista 2 de IA (2026.2)
Sistema de recomendação de atividades físicas baseado em ontologia OWL 2.

Fluxo:
  1. constrói a ontologia (ontologia_atividades.py) e, se pedido, cria o usuário
     informado na linha de comando;
  2. executa o raciocinador HermiT, que
       - verifica a consistência da ontologia,
       - classifica indivíduos em classes definidas (AtividadeBaixoImpacto,
         UsuarioIniciante, UsuarioComRestricaoArticular, ...),
       - descobre relações implícitas: atividadeCandidata (cadeia
         temObjetivo o eAtingidoPor), deveEvitar (cadeia temCondicao o desaconselha
         e regras SWRL);
  3. consulta a ontologia inferida (Python e SPARQL) e monta a recomendação,
     mostrando os elementos usados em cada decisão.

Uso:
  python recomendador.py                    # usuários de exemplo (Joao, Maria, Pedro)
  python recomendador.py --usuario Joao
  python recomendador.py --novo Lia --objetivos ReduzirEstresse,GanharForca \\
         --condicoes Asma --locais Casa,Academia --equipamentos Tapete --nivel intermediario
  python recomendador.py --consistencia     # demonstra a detecção de inconsistência
  python recomendador.py --listar           # termos disponíveis
Dependências: owlready2 e Java 11+.
"""

import argparse
import sys
import textwrap
from pathlib import Path

from owlready2 import OwlReadyInconsistentOntologyError, World, sync_reasoner

import ontologia_atividades as O

AQUI = Path(__file__).parent


def preparar(novo=None):
    mundo = World()
    onto = O.construir(mundo)
    if novo:
        O.adicionar_usuario(onto, **novo)
    onto.save(file=str(AQUI / "atividades.owl"), format="rdfxml")
    with onto:
        sync_reasoner(mundo, infer_property_values=True, debug=0)
    onto.save(file=str(AQUI / "atividades_inferido.owl"), format="rdfxml")
    return mundo, onto


def nomes(xs):
    return ", ".join(sorted(x.name for x in xs)) or "-"


def classes_inferidas(ind, onto):
    definidas = {"AtividadeBaixoImpacto", "AtividadeAltoImpacto", "AtividadeSemEquipamento",
                 "AtividadeEmCasa", "AtividadeVigorosa", "AtividadeParaEmagrecer",
                 "UsuarioComRestricaoArticular", "UsuarioComRestricaoCardiaca",
                 "UsuarioIniciante"}
    todas = {c.name for c in ind.INDIRECT_is_a if hasattr(c, "name")}
    return sorted(todas & definidas)


def motivo_evitar(u, a, onto):
    """Explica por que o raciocinador concluiu deveEvitar(u, a)."""
    motivos = []
    for c in u.temCondicao:
        if c in a.contraindicadaPara:
            motivos.append(f"contraindicada para {c.name} "
                           f"(cadeia temCondicao o desaconselha)")
        if onto.ProblemaArticular in c.is_a and a.impactoArticular == "alto":
            motivos.append(f"alto impacto e {c.name} é ProblemaArticular (regra SWRL 1)")
    if u.nivelCondicionamento == "iniciante" and a.temIntensidade == onto.Vigorosa:
        motivos.append("intensidade vigorosa para usuário iniciante (regra SWRL 2)")
    return "; ".join(motivos) or "inferido pelo raciocinador"


def recomendar(u, onto, n=3):
    candidatas = set(u.atividadeCandidata)        # inferido pela cadeia de propriedades
    evitar = set(u.deveEvitar)                    # inferido por cadeia + SWRL
    locais = set(u.temAcessoA)
    equip = set(u.possui)
    restr_art = onto.UsuarioComRestricaoArticular in u.INDIRECT_is_a

    aceitas, descartadas = [], []
    for a in sorted(candidatas, key=lambda x: x.name):
        if a in evitar:
            descartadas.append((a, "deve evitar: " + motivo_evitar(u, a, onto)))
            continue
        locais_ok = set(a.realizadaEm) & locais
        if not locais_ok:
            descartadas.append((a, f"realizada em {nomes(a.realizadaEm)}; "
                                   f"usuário tem acesso a {nomes(locais)}"))
            continue
        faltando = set(a.requer) - equip
        if faltando:
            descartadas.append((a, f"requer {nomes(faltando)}, que o usuário não possui"))
            continue
        objs = set(a.contribuiPara) & set(u.temObjetivo)
        pontos = 2 * len(objs)
        razoes = [f"atende a {nomes(objs)} (+{2 * len(objs)})"]
        if restr_art and onto.AtividadeBaixoImpacto in a.INDIRECT_is_a:
            pontos += 1
            razoes.append("baixo impacto, adequado à restrição articular (+1)")
        if onto.AtividadeSemEquipamento in a.INDIRECT_is_a:
            pontos += 0.5
            razoes.append("não exige equipamento (+0,5)")
        aceitas.append((pontos, a, razoes, locais_ok))
    aceitas.sort(key=lambda t: (-t[0], t[1].name))
    return aceitas[:n], aceitas[n:], descartadas


def relatorio(u, onto):
    print("=" * 84)
    print(f"Usuário: {u.name}  (nível {u.nivelCondicionamento}, {u.idade} anos)")
    print(f"  Objetivos: {nomes(u.temObjetivo)} | Condições: {nomes(u.temCondicao)}")
    print(f"  Acesso a: {nomes(u.temAcessoA)} | Equipamentos: {nomes(u.possui)}")
    print(f"  Classes inferidas: {', '.join(classes_inferidas(u, onto)) or '-'}")
    print(f"  Relações inferidas: atividadeCandidata = {nomes(u.atividadeCandidata)}")
    print(f"                      deveEvitar         = {nomes(u.deveEvitar)}")
    top, outras, descartadas = recomendar(u, onto)
    print("\n  RECOMENDAÇÕES")
    if not top:
        print("    Nenhuma atividade atende a todos os critérios.")
    for i, (p, a, razoes, locais_ok) in enumerate(top, 1):
        print(f"    {i}. {a.name}  (pontuação {p:g}; {a.duracaoSugerida} min; "
              f"~{a.gastoCaloricoHora} kcal/h; intensidade {a.temIntensidade.name})")
        print(f"       por quê: {'; '.join(razoes)}")
        print(f"       onde: {nomes(locais_ok)} | classes: "
              f"{', '.join(classes_inferidas(a, onto))}")
        sim = [s for s in a.similarA if s not in u.deveEvitar]
        if sim:
            print(f"       alternativa semelhante: {nomes(sim)}")
    if outras:
        print("  Também compatíveis: " + ", ".join(a.name for _, a, _, _ in outras))
    print("\n  DESCARTADAS (com o elemento da ontologia que motivou)")
    for a, motivo in descartadas:
        print(f"    - {a.name}: {motivo}")


def consulta_sparql(mundo):
    print("=" * 84)
    print("Consulta SPARQL sobre a ontologia inferida: atividades de baixo impacto, sem")
    print("equipamento, que contribuem para MelhorarCondicionamento")
    q = """
    PREFIX : <http://example.org/lista2/atividades.owl#>
    SELECT ?a WHERE {
        ?a a :AtividadeBaixoImpacto .
        ?a a :AtividadeSemEquipamento .
        ?a :contribuiPara :MelhorarCondicionamento .
    }"""
    print(textwrap.indent(textwrap.dedent(q).strip(), "  "))
    res = sorted(r[0].name for r in mundo.sparql(q))
    print("  Resultado:", ", ".join(res) or "-")


def demonstrar_inconsistencia():
    print("=" * 84)
    print("Verificação de consistência")
    print("  Declarando Corrida também como de impacto 'baixo' (impactoArticular é funcional,")
    print("  e AtividadeBaixoImpacto e AtividadeAltoImpacto são disjuntas)...")
    mundo = World()
    onto = O.construir(mundo)
    with onto:
        onto.Corrida.is_a.append(onto.AtividadeBaixoImpacto)
    try:
        with onto:
            sync_reasoner(mundo, debug=0)
        print("  Resultado: consistente")
    except OwlReadyInconsistentOntologyError:
        print("  Resultado: o HermiT detectou que a ontologia é INCONSISTENTE.")


def listar():
    mundo = World()
    onto = O.construir(mundo)
    for cls in ("Objetivo", "CondicaoSaude", "Local", "Equipamento"):
        c = getattr(onto, cls)
        print(f"{cls}: {', '.join(sorted(i.name for i in c.instances()))}")
    print("Níveis: iniciante, intermediario, avancado")


def main():
    p = argparse.ArgumentParser(description="Recomendação de atividades físicas com OWL 2")
    p.add_argument("--usuario")
    p.add_argument("--novo", help="nome de um novo usuário")
    p.add_argument("--objetivos", default="")
    p.add_argument("--condicoes", default="")
    p.add_argument("--locais", default="")
    p.add_argument("--equipamentos", default="")
    p.add_argument("--nivel", default="intermediario")
    p.add_argument("--idade", type=int, default=30)
    p.add_argument("--consistencia", action="store_true")
    p.add_argument("--listar", action="store_true")
    a = p.parse_args()
    lista = lambda s: [x for x in s.split(",") if x]

    if a.listar:
        return listar()
    if a.consistencia:
        return demonstrar_inconsistencia()

    novo = None
    if a.novo:
        novo = dict(nome_=a.novo, objetivos=lista(a.objetivos), condicoes=lista(a.condicoes),
                    locais=lista(a.locais), equipamentos=lista(a.equipamentos),
                    nivel=a.nivel, idade_=a.idade)
    mundo, onto = preparar(novo)
    print("Raciocinador HermiT executado: a ontologia é consistente.")
    print(f"Ontologia: {len(list(onto.classes()))} classes, "
          f"{len(list(onto.object_properties())) + len(list(onto.data_properties()))} "
          f"propriedades, {len(list(onto.individuals()))} indivíduos, "
          f"{len(list(onto.rules()))} regras SWRL")

    print("\nClassificação automática de atividades (classes definidas inferidas):")
    for at in sorted(onto.Atividade.instances(), key=lambda x: x.name):
        print(f"  {at.name:<24} {', '.join(classes_inferidas(at, onto))}")

    alvo = [a.novo] if a.novo else ([a.usuario] if a.usuario else ["Joao", "Maria", "Pedro"])
    for nome_ in alvo:
        u = onto.search_one(iri=O.IRI + nome_)
        if u is None:
            sys.exit(f"Usuário {nome_} não encontrado")
        relatorio(u, onto)
    if not a.usuario and not a.novo:
        consulta_sparql(mundo)
        demonstrar_inconsistencia()


if __name__ == "__main__":
    main()
