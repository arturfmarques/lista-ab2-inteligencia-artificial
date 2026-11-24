# -*- coding: utf-8 -*-
"""Ferramentas que o agente LLM pode chamar (descrição + implementação)."""

import json
from pathlib import Path

import planejador

AQUI = Path(__file__).parent
AGENDA = AQUI / "agenda.json"

_TAREFA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "identificador curto, ex.: A"},
        "nome": {"type": "string"},
        "duracao_min": {"type": "integer"},
        "prioridade": {"type": "string", "enum": ["alta", "media", "baixa"]},
        "prazo": {"type": "string", "description": "hoje, amanha ou outro texto (ex.: semana)"},
        "inicio_fixo": {"type": "string", "description": "HH:MM, só para compromissos fixos"},
        "divisivel": {"type": "boolean", "description": "pode ser feita em partes"},
    },
    "required": ["id", "nome", "duracao_min", "prioridade", "prazo"],
}

DEFINICOES = [
    {
        "nome": "consultar_agenda",
        "descricao": ("Retorna a janela de tempo disponível do professor na data, os "
                      "compromissos fixos e as tarefas pendentes cadastradas (com duração "
                      "estimada, prioridade padrão e prazo)."),
        "parametros": {"type": "object",
                       "properties": {"data": {"type": "string",
                                               "description": "hoje, amanha ou AAAA-MM-DD"}},
                       "required": ["data"]},
    },
    {
        "nome": "planejar_atividades",
        "descricao": ("Planejador clássico: encontra o plano de maior utilidade que respeita "
                      "a janela, os compromissos fixos e a não sobreposição. Devolve o plano, "
                      "a utilidade e uma justificativa para cada tarefa. Use SEMPRE esta "
                      "ferramenta para montar horários; não calcule horários por conta própria."),
        "parametros": {"type": "object",
                       "properties": {"tarefas": {"type": "array", "items": _TAREFA},
                                      "inicio": {"type": "string", "description": "HH:MM"},
                                      "fim": {"type": "string", "description": "HH:MM"},
                                      "permitir_divisao": {"type": "boolean"}},
                       "required": ["tarefas", "inicio", "fim"]},
    },
    {
        "nome": "verificar_plano",
        "descricao": ("Verificador: confere se um plano respeita as restrições (janela, "
                      "compromissos fixos, sobreposição, divisão de tarefas) e lista "
                      "violações e avisos. Use antes de apresentar qualquer plano."),
        "parametros": {"type": "object",
                       "properties": {
                           "plano": {"type": "array", "items": {
                               "type": "object",
                               "properties": {"inicio": {"type": "string"},
                                              "fim": {"type": "string"},
                                              "tarefa": {"type": "string"}},
                               "required": ["inicio", "fim", "tarefa"]}},
                           "tarefas": {"type": "array", "items": _TAREFA},
                           "inicio": {"type": "string"}, "fim": {"type": "string"}},
                       "required": ["plano", "tarefas", "inicio", "fim"]},
    },
]


def consultar_agenda(data="hoje"):
    agenda = json.loads(AGENDA.read_text(encoding="utf-8"))
    dia = agenda["dias"].get(data) or agenda["dias"]["hoje"]
    return {"data": data, **dia, "tarefas_pendentes": agenda["tarefas_pendentes"]}


def planejar_atividades(tarefas, inicio, fim, permitir_divisao=False):
    return planejador.planejar(tarefas, inicio, fim, permitir_divisao)


def verificar_plano(plano, tarefas, inicio, fim):
    return planejador.verificar(plano, tarefas, inicio, fim)


IMPLEMENTACOES = {
    "consultar_agenda": consultar_agenda,
    "planejar_atividades": planejar_atividades,
    "verificar_plano": verificar_plano,
}


def executar(nome, argumentos):
    if nome not in IMPLEMENTACOES:
        return {"erro": f"ferramenta desconhecida: {nome}"}
    try:
        return IMPLEMENTACOES[nome](**argumentos)
    except Exception as e:  # o erro volta para o LLM, que pode corrigir a chamada
        return {"erro": f"{type(e).__name__}: {e}"}
