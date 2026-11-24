#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Questão 12 - Lista 2 de IA (2026.2)
Agente baseado em LLM para planejar as atividades de um professor.

Componentes:
  - Interface em linguagem natural: conversa no terminal (pedidos e perguntas livres).
  - Inferência: o LLM interpreta o pedido e decide quais ferramentas chamar; o
    planejador clássico (planejador.py) calcula o plano de maior utilidade e o
    verificador confere as restrições. É a ideia LLM-Modulo: o LLM propõe e
    traduz, mecanismos explícitos garantem a correção.
  - Explicabilidade:
      * rastro de raciocínio: cada chamada de ferramenta, argumentos e resultado (/explicar);
      * justificativa por tarefa, gerada pelo planejador e não pelo LLM (/porque A);
      * explicação contrastiva: o que aconteceria se a tarefa omitida fosse incluída;
      * bloco "Base da decisão" anexado à resposta, sempre conferido pelo verificador.

Uso:
  python agente.py                       # conversa (backend simulado, sem chave de API)
  python agente.py --backend anthropic   # usa a API da Anthropic (ANTHROPIC_API_KEY)
  python agente.py --backend openai      # API no formato OpenAI (OPENAI_API_KEY, OPENAI_BASE_URL)
  python agente.py --demo                # roteiro da demonstração
Comandos na conversa: /explicar, /porque <ID>, /plano, /sair
"""

import argparse
import json
import sys

import ferramentas as F
import planejador
from llm import BACKENDS

SISTEMA = """Você é um assistente que organiza as atividades acadêmicas de um professor.
Regras:
1. Primeiro consulte a agenda com consultar_agenda para obter a janela disponível, os
   compromissos fixos e as tarefas pendentes cadastradas.
2. Relacione o pedido do professor às tarefas cadastradas. Ajuste prioridade e prazo
   conforme o que ele disser ("urgente" = prioridade alta). Se faltar a duração de uma
   tarefa nova, pergunte antes de planejar.
3. Monte o horário SEMPRE com planejar_atividades; nunca invente horários.
4. Verifique o plano com verificar_plano antes de responder.
5. Responda em português, de forma curta: o plano, o que ficou de fora e por quê, usando
   as justificativas devolvidas pelo planejador. Não altere os números.
6. Só divida uma tarefa se o professor permitir."""


class Agente:
    def __init__(self, backend="simulado", modelo=None, max_passos=8, saida=print):
        self.llm = BACKENDS[backend](SISTEMA, F.DEFINICOES, modelo=modelo)
        self.max_passos = max_passos
        self.rastro = []
        self.ultimo = {}          # último planejamento: resultado, tarefas, janela, verificação
        self.saida = saida

    # ------------------------------------------------------------------
    def responder(self, texto):
        self.rastro = [("usuario", texto)]
        self.llm.adicionar_usuario(texto)
        resposta = ""
        for _ in range(self.max_passos):
            r = self.llm.passo()
            if r["texto"]:
                self.rastro.append(("llm", r["texto"]))
            if not r["chamadas"]:
                resposta = r["texto"]
                break
            resultados = []
            for c in r["chamadas"]:
                res = F.executar(c["nome"], c["argumentos"])
                self.rastro.append(("ferramenta", c["nome"], c["argumentos"], res))
                self._registrar(c["nome"], c["argumentos"], res)
                resultados.append((c["id"], c["nome"], res))
            self.llm.adicionar_resultados(resultados)
        else:
            resposta = "Não consegui concluir em um número razoável de passos."
        return resposta + self._base_da_decisao()

    def _registrar(self, nome, args, res):
        if nome == "planejar_atividades" and "plano" in res:
            self.ultimo = {"resultado": res, "tarefas": args["tarefas"],
                           "janela": (args["inicio"], args["fim"]), "verificacao": None,
                           "novo": True}
        elif nome == "verificar_plano" and self.ultimo and "valido" in res:
            self.ultimo["verificacao"] = res

    def _base_da_decisao(self):
        u = self.ultimo
        if not u or not u.get("novo"):
            return ""
        u["novo"] = False
        if u["verificacao"] is None:  # o LLM não verificou: o agente verifica por conta própria
            plano = [{k: b[k] for k in ("inicio", "fim", "tarefa")} for b in u["resultado"]["plano"]]
            u["verificacao"] = planejador.verificar(plano, u["tarefas"], *u["janela"])
            self.rastro.append(("agente", "verificação automática (o LLM não chamou o verificador)"))
        r, v = u["resultado"], u["verificacao"]
        nomes = {t["id"]: t["nome"] for t in u["tarefas"]}
        linhas = ["", "", "── Base da decisão (planejador e verificador, não o LLM) ──"]
        for b in r["plano"]:
            linhas.append(f"  {b['inicio']}-{b['fim']}  {b['tarefa']}  {b['nome']}")
        linhas.append(f"  Utilidade: {r['utilidade_total']:g} de {r['utilidade_maxima_possivel']:g}"
                      f" possíveis. Critério: {r['criterio']}.")
        if r["tempo_livre"]:
            linhas.append(f"  Tempo livre: {', '.join(r['tempo_livre'])}")
        for i, j in r["justificativas"].items():
            linhas.append(f"  {i} ({nomes.get(i, i)}): {j}")
        if v["valido"]:
            linhas.append("  Verificação: plano válido (sem sobreposição, dentro da janela, "
                          "compromissos fixos respeitados).")
        else:
            linhas.append("  Verificação: PLANO INVÁLIDO -> " + "; ".join(v["violacoes"]))
        for a in v["avisos"]:
            linhas.append(f"  Aviso: {a}")
        return "\n".join(linhas)

    # ------------------------------------------------------------------
    def explicar(self):
        linhas = ["Rastro do último pedido:"]
        n = 0
        for item in self.rastro:
            if item[0] == "usuario":
                linhas.append(f"  [usuário] {item[1]}")
            elif item[0] == "llm":
                linhas.append(f"  [LLM] {item[1][:300]}")
            elif item[0] == "agente":
                linhas.append(f"  [agente] {item[1]}")
            else:
                n += 1
                _, nome, args, res = item
                arg_txt = json.dumps(args, ensure_ascii=False)
                linhas.append(f"  [{n}] LLM chamou {nome}({arg_txt[:220]}"
                              f"{'...' if len(arg_txt) > 220 else ''})")
                linhas.append(f"      resultado: {self._resumo(nome, res)}")
        return "\n".join(linhas)

    @staticmethod
    def _resumo(nome, res):
        if "erro" in res:
            return "ERRO " + res["erro"]
        if nome == "consultar_agenda":
            j = res["janela_disponivel"]
            return (f"janela {j['inicio']}-{j['fim']}; fixos: "
                    f"{', '.join(c['nome'] for c in res['compromissos_fixos'])}; "
                    f"{len(res['tarefas_pendentes'])} tarefas pendentes")
        if nome == "planejar_atividades":
            return (f"{len(res['plano'])} blocos, utilidade {res['utilidade_total']:g}, "
                    f"não realizadas: {', '.join(res['nao_realizadas']) or '-'}")
        if nome == "verificar_plano":
            return "válido" if res["valido"] else "inválido: " + "; ".join(res["violacoes"])
        return str(res)[:200]

    def porque(self, ident):
        if not self.ultimo:
            return "Ainda não há plano."
        r = self.ultimo["resultado"]
        j = r["justificativas"].get(ident.upper())
        return (f"{ident.upper()}: {j}\nCritério: {r['criterio']}" if j
                else f"Tarefa {ident} não está no último plano.")


# ----------------------------------------------------------------------
PEDIDO_Q11 = ("Preciso preparar uma aula de Inteligência Artificial, corrigir trabalhos de alunos "
              "e participar de uma reunião de pesquisa. Tenho apenas quatro horas disponíveis "
              "hoje. A preparação da aula é urgente, mas a correção dos trabalhos precisa ser "
              "concluída até amanhã. Organize minhas atividades da melhor maneira possível.")


def demo(backend, modelo):
    ag = Agente(backend, modelo)
    roteiro = [
        PEDIDO_Q11,
        "/explicar",
        "Quero aproveitar o resto da tarde para revisar o artigo também. Organize de novo, "
        "incluindo a revisão do artigo.",
        "E se eu puder dividir a correção dos trabalhos em partes?",
        "Por que a revisão do artigo ficou de fora?",
        "/porque B",
    ]
    for msg in roteiro:
        print("=" * 90)
        print("Professor:", msg)
        print("-" * 90)
        print(executar_comando(ag, msg))


def executar_comando(ag, msg):
    if msg.startswith("/explicar"):
        return ag.explicar()
    if msg.startswith("/porque"):
        partes = msg.split()
        return ag.porque(partes[1]) if len(partes) > 1 else "Use /porque <ID da tarefa>"
    if msg.startswith("/plano"):
        return json.dumps(ag.ultimo.get("resultado", {}), ensure_ascii=False, indent=1)
    return "Assistente: " + ag.responder(msg)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=list(BACKENDS), default="simulado")
    p.add_argument("--modelo")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--pergunta")
    a = p.parse_args()
    if a.demo:
        return demo(a.backend, a.modelo)
    ag = Agente(a.backend, a.modelo)
    if a.pergunta:
        print(executar_comando(ag, a.pergunta))
        return
    print(f"Assistente de planejamento acadêmico (backend: {a.backend}). "
          "Comandos: /explicar, /porque <ID>, /plano, /sair")
    while True:
        try:
            msg = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.startswith("/sair"):
            break
        print(executar_comando(ag, msg))


if __name__ == "__main__":
    sys.exit(main())
