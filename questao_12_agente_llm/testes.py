# -*- coding: utf-8 -*-
"""Testes sem rede: planejador, verificador e os dois backends reais com clientes falsos.

Os clientes falsos devolvem objetos no mesmo formato das bibliotecas openai e anthropic,
seguindo o roteiro consultar_agenda -> planejar_atividades -> verificar_plano -> resposta.
Uso: python testes.py
"""
import json
from types import SimpleNamespace as NS

import ferramentas as F
import planejador as P
from agente import Agente, PEDIDO_Q11
import llm

TAREFAS = [
    dict(id="A", nome="Preparar aula", duracao_min=90, prioridade="alta", prazo="hoje"),
    dict(id="B", nome="Corrigir", duracao_min=120, prioridade="media", prazo="amanha",
         divisivel=True),
    dict(id="C", nome="Reunião", duracao_min=60, prioridade="alta", prazo="hoje",
         inicio_fixo="16:00"),
    dict(id="D", nome="Artigo", duracao_min=60, prioridade="baixa", prazo="semana"),
]
ROTEIRO = [
    ("consultar_agenda", {"data": "hoje"}),
    ("planejar_atividades", {"tarefas": TAREFAS, "inicio": "14:00", "fim": "18:00"}),
    ("verificar_plano", {"plano": [{"inicio": "14:00", "fim": "15:30", "tarefa": "A"},
                                   {"inicio": "16:00", "fim": "17:00", "tarefa": "C"},
                                   {"inicio": "17:00", "fim": "18:00", "tarefa": "D"}],
                         "tarefas": TAREFAS, "inicio": "14:00", "fim": "18:00"}),
]


def teste_planejador():
    r = P.planejar(TAREFAS)
    assert [b["tarefa"] for b in r["plano"]] == ["A", "C", "D"], r["plano"]
    assert r["nao_realizadas"] == ["B"]
    assert P.verificar([{k: b[k] for k in ("inicio", "fim", "tarefa")} for b in r["plano"]],
                       TAREFAS)["valido"]
    r2 = P.planejar(TAREFAS, permitir_divisao=True)
    assert r2["parciais"] == {"B": 90} and r2["nao_realizadas"] == ["D"]
    ruim = [{"inicio": "15:00", "fim": "16:30", "tarefa": "A"},
            {"inicio": "16:00", "fim": "17:00", "tarefa": "C"}]
    v = P.verificar(ruim, TAREFAS)
    assert not v["valido"] and any("sobreposição" in x for x in v["violacoes"])
    print("ok planejador e verificador")


class FakeOpenAI:
    def __init__(self):
        self.passo = 0
        self.recebidas = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, model, messages, tools):
        self.recebidas.append(json.loads(json.dumps(messages, default=str)))
        if self.passo < len(ROTEIRO):
            nome, args = ROTEIRO[self.passo]
            self.passo += 1
            call = NS(id=f"c{self.passo}", function=NS(name=nome, arguments=json.dumps(args)))
            msg = NS(content=None, tool_calls=[call])
        else:
            msg = NS(content="Plano pronto.", tool_calls=None)
        return NS(choices=[NS(message=msg)])


def teste_openai():
    ag = Agente("simulado")
    fake = FakeOpenAI()
    ag.llm = llm.OpenAICompativelBackend("sistema", F.DEFINICOES, modelo="x", cliente=fake)
    resp = ag.responder(PEDIDO_Q11)
    assert "Plano pronto." in resp and "plano válido" in resp, resp
    ultima = fake.recebidas[-1]
    papeis = [m["role"] for m in ultima]
    assert papeis == ["system", "user", "assistant", "tool", "assistant", "tool",
                      "assistant", "tool"], papeis
    assert ultima[3]["tool_call_id"] == "c1"
    print("ok backend OpenAI (formato das mensagens)")


class Bloco(NS):
    pass


class FakeAnthropic:
    def __init__(self):
        self.passo = 0
        self.recebidas = []
        self.messages = NS(create=self._create)

    def _create(self, model, max_tokens, system, tools, messages):
        self.recebidas.append(list(messages))
        assert all("input_schema" in t for t in tools)
        if self.passo < len(ROTEIRO):
            nome, args = ROTEIRO[self.passo]
            self.passo += 1
            content = [Bloco(type="text", text="Vou consultar."),
                       Bloco(type="tool_use", id=f"t{self.passo}", name=nome, input=args)]
        else:
            content = [Bloco(type="text", text="Plano pronto.")]
        return NS(content=content)


def teste_anthropic():
    ag = Agente("simulado")
    b = llm.AnthropicBackend.__new__(llm.AnthropicBackend)
    b.cliente, b.modelo, b.sistema, b.mensagens = FakeAnthropic(), "x", "s", []
    b.tools = [{"name": f["nome"], "description": f["descricao"],
                "input_schema": f["parametros"]} for f in F.DEFINICOES]
    ag.llm = b
    resp = ag.responder(PEDIDO_Q11)
    assert "Plano pronto." in resp
    msgs = b.cliente.recebidas[-1]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant", "user",
                                         "assistant", "user"]
    assert msgs[2]["content"][0]["type"] == "tool_result"
    assert msgs[2]["content"][0]["tool_use_id"] == "t1"
    print("ok backend Anthropic (formato das mensagens)")


def teste_verificacao_automatica():
    """Se o LLM não chamar o verificador, o agente verifica sozinho."""
    ag = Agente("simulado")
    fake = FakeOpenAI()
    global ROTEIRO
    original = ROTEIRO
    ROTEIRO = original[:2]
    try:
        ag.llm = llm.OpenAICompativelBackend("s", F.DEFINICOES, modelo="x", cliente=fake)
        resp = ag.responder(PEDIDO_Q11)
    finally:
        ROTEIRO = original
    assert "plano válido" in resp
    assert any(i[0] == "agente" for i in ag.rastro)
    print("ok verificação automática quando o LLM esquece o verificador")


if __name__ == "__main__":
    teste_planejador()
    teste_openai()
    teste_anthropic()
    teste_verificacao_automatica()
    print("todos os testes passaram")
