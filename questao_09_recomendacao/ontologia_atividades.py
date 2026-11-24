# -*- coding: utf-8 -*-
"""
Questão 9 - Lista 2 de IA (2026.2)
Ontologia OWL 2 de atividades físicas, usada pelo recomendador (recomendador.py).

Constrói a ontologia com Owlready2. Executar este arquivo diretamente salva
atividades.owl, que pode ser aberto no Protégé.

AVISO: conteúdo educacional; não substitui orientação de profissional de saúde.
"""

from pathlib import Path

from owlready2 import (AllDifferent, AllDisjoint, DataProperty, FunctionalProperty, Imp,
                       ObjectProperty, PropertyChain, SymmetricProperty, Thing, get_ontology)

AQUI = Path(__file__).parent
IRI = "http://example.org/lista2/atividades.owl#"


def construir(mundo=None):
    onto = (mundo.get_ontology(IRI) if mundo is not None else get_ontology(IRI))
    with onto:
        # ==============================================================
        # CLASSES E HIERARQUIA
        # ==============================================================
        class Atividade(Thing): pass
        class AtividadeAerobica(Atividade): pass
        class AtividadeAquatica(AtividadeAerobica): pass
        class AtividadeForca(Atividade): pass
        class AtividadeFlexibilidade(Atividade): pass
        class AtividadeMenteCorpo(AtividadeFlexibilidade): pass

        class Usuario(Thing): pass
        class Objetivo(Thing): pass
        class Local(Thing): pass
        class Equipamento(Thing): pass
        class NivelIntensidade(Thing): pass

        class CondicaoSaude(Thing): pass
        class ProblemaArticular(CondicaoSaude): pass
        class ProblemaCardiovascular(CondicaoSaude): pass
        class ProblemaRespiratorio(CondicaoSaude): pass

        AllDisjoint([Atividade, Usuario, Objetivo, Local, Equipamento, NivelIntensidade,
                     CondicaoSaude])

        # ==============================================================
        # PROPRIEDADES DE OBJETO
        # ==============================================================
        class contribuiPara(ObjectProperty):            # 1
            domain = [Atividade]; range = [Objetivo]
        class eAtingidoPor(ObjectProperty):             # 2 (inversa)
            inverse_property = contribuiPara
        class realizadaEm(ObjectProperty):              # 3
            domain = [Atividade]; range = [Local]
        class requer(ObjectProperty):                   # 4
            domain = [Atividade]; range = [Equipamento]
        class temIntensidade(ObjectProperty, FunctionalProperty):  # 5
            domain = [Atividade]; range = [NivelIntensidade]
        class contraindicadaPara(ObjectProperty):       # 6
            domain = [Atividade]; range = [CondicaoSaude]
        class desaconselha(ObjectProperty):             # 7 (inversa)
            inverse_property = contraindicadaPara
        class similarA(ObjectProperty, SymmetricProperty):  # 8
            domain = [Atividade]; range = [Atividade]
        class temObjetivo(ObjectProperty):              # 9
            domain = [Usuario]; range = [Objetivo]
        class temCondicao(ObjectProperty):              # 10
            domain = [Usuario]; range = [CondicaoSaude]
        class temAcessoA(ObjectProperty):               # 11
            domain = [Usuario]; range = [Local]
        class possui(ObjectProperty):                   # 12
            domain = [Usuario]; range = [Equipamento]
        # Relações implícitas, descobertas pelo raciocinador
        class atividadeCandidata(ObjectProperty):       # 13
            domain = [Usuario]; range = [Atividade]
        atividadeCandidata.property_chain.append(PropertyChain([temObjetivo, eAtingidoPor]))
        class deveEvitar(ObjectProperty):               # 14
            domain = [Usuario]; range = [Atividade]
        deveEvitar.property_chain.append(PropertyChain([temCondicao, desaconselha]))

        # ==============================================================
        # PROPRIEDADES DE DADOS
        # ==============================================================
        class impactoArticular(DataProperty, FunctionalProperty):  # 15 ("baixo" | "alto")
            domain = [Atividade]; range = [str]
        class requerEquipamento(DataProperty, FunctionalProperty):  # 16
            domain = [Atividade]; range = [bool]
        class gastoCaloricoHora(DataProperty, FunctionalProperty):  # 17 (kcal/h, aproximado)
            domain = [Atividade]; range = [int]
        class duracaoSugerida(DataProperty, FunctionalProperty):    # 18 (min)
            domain = [Atividade]; range = [int]
        class nivelCondicionamento(DataProperty, FunctionalProperty):  # 19
            domain = [Usuario]; range = [str]
        class idade(DataProperty, FunctionalProperty):              # 20
            domain = [Usuario]; range = [int]
        class nome(DataProperty, FunctionalProperty):               # 21
            range = [str]

        # ==============================================================
        # INDIVÍDUOS DE APOIO
        # ==============================================================
        perder = Objetivo("PerderPeso")
        forca = Objetivo("GanharForca")
        flex = Objetivo("MelhorarFlexibilidade")
        estresse = Objetivo("ReduzirEstresse")
        cond = Objetivo("MelhorarCondicionamento")
        casa, academia, ar, piscina = (Local("Casa"), Local("Academia"),
                                       Local("ArLivre"), Local("Piscina"))
        tapete, halteres, bicicleta, corda = (Equipamento("Tapete"), Equipamento("Halteres"),
                                              Equipamento("Bicicleta"), Equipamento("Corda"))
        leve, moderada, vigorosa = (NivelIntensidade("Leve"), NivelIntensidade("Moderada"),
                                    NivelIntensidade("Vigorosa"))
        joelho = ProblemaArticular("LesaoNoJoelho")
        artrose = ProblemaArticular("Artrose")
        hipertensao = ProblemaCardiovascular("Hipertensao")
        asma = ProblemaRespiratorio("Asma")
        AllDifferent([perder, forca, flex, estresse, cond])
        AllDifferent([casa, academia, ar, piscina])
        AllDifferent([leve, moderada, vigorosa])

        # ==============================================================
        # CLASSES DEFINIDAS (o raciocinador classifica os indivíduos nelas)
        # ==============================================================
        class AtividadeBaixoImpacto(Thing):
            equivalent_to = [Atividade & impactoArticular.value("baixo")]
        class AtividadeAltoImpacto(Thing):
            equivalent_to = [Atividade & impactoArticular.value("alto")]
        AllDisjoint([AtividadeBaixoImpacto, AtividadeAltoImpacto])
        class AtividadeSemEquipamento(Thing):
            equivalent_to = [Atividade & requerEquipamento.value(False)]
        class AtividadeEmCasa(Thing):
            equivalent_to = [Atividade & realizadaEm.value(casa)]
        class AtividadeVigorosa(Thing):
            equivalent_to = [Atividade & temIntensidade.value(vigorosa)]
        class AtividadeParaEmagrecer(Thing):
            equivalent_to = [Atividade & contribuiPara.value(perder)]
        class UsuarioComRestricaoArticular(Thing):
            equivalent_to = [Usuario & temCondicao.some(ProblemaArticular)]
        class UsuarioComRestricaoCardiaca(Thing):
            equivalent_to = [Usuario & temCondicao.some(ProblemaCardiovascular)]
        class UsuarioIniciante(Thing):
            equivalent_to = [Usuario & nivelCondicionamento.value("iniciante")]

        # ==============================================================
        # ATIVIDADES
        # ==============================================================
        def atividade(nome_, classe, impacto, equip, intens, locais, objetivos, kcal, minutos,
                      requer_=(), contra=()):
            a = classe(nome_, impactoArticular=impacto, requerEquipamento=equip,
                       temIntensidade=intens, gastoCaloricoHora=kcal, duracaoSugerida=minutos)
            a.realizadaEm = list(locais)
            a.contribuiPara = list(objetivos)
            a.requer = list(requer_)
            a.contraindicadaPara = list(contra)
            return a

        caminhada = atividade("Caminhada", AtividadeAerobica, "baixo", False, leve,
                              [ar], [perder, cond, estresse], 250, 40)
        corrida = atividade("Corrida", AtividadeAerobica, "alto", False, vigorosa,
                            [ar], [perder, cond], 600, 30)
        natacao = atividade("Natacao", AtividadeAquatica, "baixo", False, moderada,
                            [piscina], [perder, cond, forca], 450, 40, contra=[])
        hidro = atividade("Hidroginastica", AtividadeAquatica, "baixo", False, leve,
                          [piscina], [cond, flex], 250, 45)
        ciclismo = atividade("Ciclismo", AtividadeAerobica, "baixo", True, moderada,
                             [ar], [perder, cond], 450, 45, requer_=[bicicleta])
        musculacao = atividade("Musculacao", AtividadeForca, "baixo", True, moderada,
                               [academia], [forca, perder], 300, 50, requer_=[halteres])
        funcional = atividade("TreinoFuncionalComPeso", AtividadeForca, "alto", True, moderada,
                              [casa, academia], [forca, cond], 400, 30, requer_=[halteres])
        pilates = atividade("PilatesSolo", AtividadeMenteCorpo, "baixo", True, leve,
                            [casa, academia], [flex, forca], 200, 40, requer_=[tapete])
        yoga = atividade("Yoga", AtividadeMenteCorpo, "baixo", True, leve,
                         [casa, academia], [flex, estresse], 180, 40, requer_=[tapete])
        alongamento = atividade("Alongamento", AtividadeFlexibilidade, "baixo", False, leve,
                                [casa, academia, ar], [flex, estresse], 120, 20)
        hiit = atividade("HIIT", AtividadeAerobica, "alto", False, vigorosa,
                         [casa, academia], [perder, cond], 650, 20, contra=[hipertensao])
        pular_corda = atividade("PularCorda", AtividadeAerobica, "alto", True, vigorosa,
                                [casa, ar], [perder, cond], 700, 15, requer_=[corda],
                                contra=[hipertensao, asma])
        AllDifferent(list(Atividade.instances()))
        caminhada.similarA = [ciclismo]
        corrida.similarA = [pular_corda]
        yoga.similarA = [pilates]
        natacao.similarA = [hidro]

        # ==============================================================
        # REGRAS SWRL
        # ==============================================================
        # Problema articular -> evitar toda atividade de alto impacto (regra por classe,
        # sem precisar listar a contraindicação em cada atividade).
        Imp().set_as_rule("Usuario(?u), temCondicao(?u, ?c), ProblemaArticular(?c), "
                          "Atividade(?a), impactoArticular(?a, \"alto\") -> deveEvitar(?u, ?a)")
        # Iniciante -> evitar atividades vigorosas.
        Imp().set_as_rule("Usuario(?u), nivelCondicionamento(?u, \"iniciante\"), "
                          "temIntensidade(?a, Vigorosa) -> deveEvitar(?u, ?a)")

        # ==============================================================
        # USUÁRIOS DE EXEMPLO
        # ==============================================================
        def usuario(nome_, objetivos, condicoes, locais, equipamentos, nivel, idade_):
            u = Usuario(nome_, nivelCondicionamento=nivel, idade=idade_)
            u.temObjetivo = list(objetivos)
            u.temCondicao = list(condicoes)
            u.temAcessoA = list(locais)
            u.possui = list(equipamentos)
            return u

        usuario("Joao", [perder], [joelho], [casa, ar, piscina], [tapete], "iniciante", 45)
        usuario("Maria", [forca, cond], [], [casa, academia], [halteres, tapete],
                "intermediario", 29)
        usuario("Pedro", [estresse, flex], [hipertensao], [casa, ar], [], "iniciante", 58)
    return onto


def adicionar_usuario(onto, nome_, objetivos, condicoes, locais, equipamentos, nivel, idade_):
    """Cria um usuário a partir de nomes de indivíduos já existentes na ontologia."""
    def busca(n):
        ind = onto.search_one(iri=IRI + n)
        if ind is None:
            raise ValueError(f"'{n}' não existe na ontologia")
        return ind
    with onto:
        u = onto.Usuario(nome_, nivelCondicionamento=nivel, idade=idade_)
        u.temObjetivo = [busca(x) for x in objetivos]
        u.temCondicao = [busca(x) for x in condicoes]
        u.temAcessoA = [busca(x) for x in locais]
        u.possui = [busca(x) for x in equipamentos]
    return u


if __name__ == "__main__":
    o = construir()
    o.save(file=str(AQUI / "atividades.owl"), format="rdfxml")
    print("atividades.owl salvo")
