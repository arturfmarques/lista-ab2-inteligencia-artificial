#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 15 - Lista 2 de IA (2026.2)
Ontologia OWL 2 de um assistente acadêmico, com raciocínio automático.

É a ontologia usada como exemplo na questão 1, agora implementada e executada.
O programa constrói a ontologia com Owlready2, salva em academico.owl (RDF/XML,
abre no Protégé) e executa o raciocinador HermiT, o mesmo que o Protégé traz no
menu Reasoner. Depois mostra o que foi inferido:

  1. classificação de indivíduos em classes definidas (Monitor, Orientador, ...);
  2. classificação de classes (hierarquia inferida);
  3. tipos inferidos pelo domínio de uma propriedade;
  4. propriedades inferidas por transitividade, cadeia de propriedades e regra SWRL;
  5. verificação de consistência com um indivíduo que viola uma disjunção.

Obs.: as propriedades inversas (ministra/ministradaPor, orienta/orientadoPor) o
Owlready2 já preenche ao criar o fato, antes do raciocinador.

Uso:  python ontologia_academica.py
Dependências: owlready2 e Java 11 ou mais recente (o Owlready2 já traz o HermiT).
"""

from pathlib import Path

from owlready2 import (AllDisjoint, PropertyChain, FunctionalProperty, Imp, ObjectProperty, DataProperty,
                       OwlReadyInconsistentOntologyError, Thing, TransitiveProperty,
                       get_ontology, sync_reasoner)

AQUI = Path(__file__).parent
IRI = "http://example.org/lista2/academico.owl#"


def construir():
    onto = get_ontology(IRI)
    with onto:
        # ------------------------------------------------------------------
        # Classes e hierarquia
        # ------------------------------------------------------------------
        class Pessoa(Thing): pass
        class Aluno(Pessoa): pass
        class AlunoGraduacao(Aluno): pass
        class AlunoPosGraduacao(Aluno): pass
        class Professor(Pessoa): pass
        class Disciplina(Thing): pass
        class Curso(Thing): pass
        class AreaConhecimento(Thing): pass
        AllDisjoint([Aluno, Professor])
        AllDisjoint([Pessoa, Disciplina, Curso, AreaConhecimento])

        # ------------------------------------------------------------------
        # Propriedades de objeto
        # ------------------------------------------------------------------
        class matriculadoEm(ObjectProperty):
            domain = [Aluno]; range = [Disciplina]
        class ministra(ObjectProperty):
            domain = [Professor]; range = [Disciplina]
        class ministradaPor(ObjectProperty):
            domain = [Disciplina]; range = [Professor]
            inverse_property = ministra
        class auxilia(ObjectProperty):
            domain = [Aluno]; range = [Disciplina]
        class orienta(ObjectProperty):
            range = [Aluno]
        class orientadoPor(ObjectProperty):
            inverse_property = orienta
        class temPreRequisito(ObjectProperty, TransitiveProperty):
            domain = [Disciplina]; range = [Disciplina]
        class pertenceA(ObjectProperty):
            domain = [Disciplina]; range = [AreaConhecimento]
        class temInteresseEm(ObjectProperty):
            domain = [Pessoa]; range = [AreaConhecimento]
        class cursa(ObjectProperty, FunctionalProperty):
            domain = [Aluno]; range = [Curso]
        # cadeia de propriedades (OWL 2): ministra o pertenceA -> pesquisaEm
        class pesquisaEm(ObjectProperty):
            range = [AreaConhecimento]
        pesquisaEm.property_chain.append(PropertyChain([ministra, pertenceA]))
        # usada pela regra SWRL
        class deveCursarAntes(ObjectProperty):
            domain = [Aluno]; range = [Disciplina]

        # Propriedades de dados
        class cargaHoraria(DataProperty, FunctionalProperty):
            domain = [Disciplina]; range = [int]
        class nome(DataProperty, FunctionalProperty):
            range = [str]

        # ------------------------------------------------------------------
        # Classes definidas (condições necessárias e suficientes)
        # ------------------------------------------------------------------
        class Monitor(Thing):
            equivalent_to = [Aluno & auxilia.some(Disciplina)]
        class Orientador(Thing):
            equivalent_to = [Professor & orienta.some(Aluno)]
        class DisciplinaAvancada(Thing):
            equivalent_to = [Disciplina & temPreRequisito.some(Disciplina)]

        # ------------------------------------------------------------------
        # Indivíduos (fatos declarados)
        # ------------------------------------------------------------------
        ia_area = AreaConhecimento("InteligenciaArtificial")
        fund = AreaConhecimento("FundamentosDaComputacao")

        class DisciplinaDeIA(Thing):
            equivalent_to = [Disciplina & pertenceA.value(ia_area)]
        class DocenteDeIA(Thing):
            equivalent_to = [Professor & ministra.some(DisciplinaDeIA)]

        cc = Curso("CienciaDaComputacao")
        prog = Disciplina("Programacao", cargaHoraria=60)
        alg = Disciplina("Algoritmos", cargaHoraria=60, temPreRequisito=[prog])
        ia = Disciplina("IA", cargaHoraria=60, temPreRequisito=[alg])
        ml = Disciplina("AprendizadoDeMaquina", cargaHoraria=60, temPreRequisito=[ia])
        for d in (prog, alg):
            d.pertenceA = [fund]
        for d in (ia, ml):
            d.pertenceA = [ia_area]

        evandro = Professor("ProfEvandro", nome="Evandro Costa")
        evandro.ministra = [ia, ml]          # ministradaPor será inferida
        marta = Pessoa("ProfMarta", nome="Marta")
        marta.ministra = [prog]               # Professor será inferido pelo domínio
        ana = Aluno("Ana", nome="Ana", cursa=cc)
        ana.matriculadoEm = [ml]
        bruno = AlunoGraduacao("Bruno", nome="Bruno", cursa=cc)
        bruno.matriculadoEm = [ia]
        bruno.auxilia = [alg]                 # Monitor será inferido
        carla = AlunoPosGraduacao("Carla", nome="Carla")
        carla.orientadoPor = [evandro]        # orienta será inferida pela inversa
        carla.temInteresseEm = [ia_area]

        # ------------------------------------------------------------------
        # Regras SWRL: um aluno deve cursar antes todos os pré-requisitos
        # (diretos e transitivos) das disciplinas em que está matriculado.
        # ------------------------------------------------------------------
        # Como as regras SWRL são "DL-safe" (aplicadas sobre os fatos dos indivíduos
        # nomeados), a segunda regra propaga a obrigação ao longo da cadeia.
        Imp().set_as_rule("Aluno(?a), matriculadoEm(?a, ?d), temPreRequisito(?d, ?p) "
                          "-> deveCursarAntes(?a, ?p)")
        Imp().set_as_rule("deveCursarAntes(?a, ?d), temPreRequisito(?d, ?p) "
                          "-> deveCursarAntes(?a, ?p)")
    return onto


def nomes(lista):
    return ", ".join(sorted(x.name for x in lista)) or "-"


def classes_diretas(ind, onto):
    return sorted(c.name for c in ind.is_a if hasattr(c, "name") and c.namespace == onto)


def relatar(onto, titulo):
    print(f"\n{titulo}")
    for ind in sorted(onto.individuals(), key=lambda i: i.name):
        print(f"  {ind.name:<24} é: {', '.join(classes_diretas(ind, onto))}")


def main():
    onto = construir()
    onto.save(file=str(AQUI / "academico.owl"), format="rdfxml")
    print("Ontologia salva em academico.owl")
    print(f"  {len(list(onto.classes()))} classes, {len(list(onto.object_properties()))} "
          f"propriedades de objeto, {len(list(onto.data_properties()))} propriedades de dados, "
          f"{len(list(onto.individuals()))} indivíduos, {len(list(onto.rules()))} regras SWRL")

    relatar(onto, "ANTES do raciocínio (classes declaradas):")
    antes = {
        "temPreRequisito(AprendizadoDeMaquina)": nomes(onto.AprendizadoDeMaquina.temPreRequisito),
        "pesquisaEm(ProfEvandro)": nomes(onto.ProfEvandro.pesquisaEm),
        "deveCursarAntes(Ana)": nomes(onto.Ana.deveCursarAntes),
    }

    # --------------------------------------------------------------
    print("\n" + "=" * 76)
    print("RACIOCÍNIO: HermiT (classificação, domínio, transitividade, cadeia de propriedades,")
    print("            regra SWRL)")
    with onto:
        sync_reasoner(infer_property_values=True, debug=0)
    relatar(onto, "DEPOIS do HermiT (classes inferidas):")
    print("\nHierarquia de classes inferida (classes definidas):")
    for c in (onto.Monitor, onto.Orientador, onto.DisciplinaAvancada, onto.DocenteDeIA):
        sup = [s.name for s in c.is_a if hasattr(s, "name")]
        print(f"  {c.name:<20} subclasse de: {', '.join(sup) or '-'}   "
              f"instâncias: {nomes(c.instances())}")

    print("\nPropriedades: declarado  ->  depois do raciocínio")
    depois = {
        "temPreRequisito(AprendizadoDeMaquina)": nomes(onto.AprendizadoDeMaquina.temPreRequisito),
        "pesquisaEm(ProfEvandro)": nomes(onto.ProfEvandro.pesquisaEm),
        "deveCursarAntes(Ana)": nomes(onto.Ana.deveCursarAntes),
    }
    for k in antes:
        print(f"  {k:<40} {antes[k]:<22} ->  {depois[k]}")

    onto.save(file=str(AQUI / "academico_inferido.owl"), format="rdfxml")

    # --------------------------------------------------------------
    print("\n" + "=" * 76)
    print("VERIFICAÇÃO DE CONSISTÊNCIA")
    print("  Declarando ProfEvandro também como Aluno (Aluno e Professor são disjuntas)...")
    mundo, teste = construir_inconsistente()
    try:
        with teste:
            sync_reasoner(mundo, debug=0)
        print("  Resultado: consistente")
    except OwlReadyInconsistentOntologyError:
        print("  Resultado: o HermiT detectou que a ontologia é INCONSISTENTE.")
    print("\nArquivos: academico.owl (declarado) e academico_inferido.owl (com inferências)")


def construir_inconsistente():
    from owlready2 import World
    mundo = World()
    onto = mundo.get_ontology("file://" + str(AQUI / "academico.owl")).load()
    with onto:
        onto.ProfEvandro.is_a.append(onto.Aluno)
    return mundo, onto


if __name__ == "__main__":
    main()
