# -*- coding: utf-8 -*-
"""
Backends de LLM com chamada de ferramentas (tool calling).

Todos têm a mesma interface, usada pelo agente:
    b = Backend(sistema, ferramentas)
    b.adicionar_usuario(texto)
    r = b.passo()      -> {"texto": str, "chamadas": [{"id", "nome", "argumentos"}]}
    b.adicionar_resultados([(id, nome, resultado_dict), ...])

  - AnthropicBackend: API da Anthropic (variável ANTHROPIC_API_KEY).
  - OpenAICompativelBackend: qualquer API no formato da OpenAI (OpenAI, Ollama local,
    Groq, Gemini etc.), configurada por OPENAI_API_KEY e OPENAI_BASE_URL.
  - SimuladoBackend: imita um LLM com regras simples, sem rede nem chave. Serve para
    demonstrar e testar o ciclo do agente; não entende linguagem natural de verdade.
"""

import json
import os
import re
import unicodedata


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
class AnthropicBackend:
    def __init__(self, sistema, ferramentas, modelo=None):
        import anthropic
        self.cliente = anthropic.Anthropic()
        self.modelo = modelo or os.environ.get("LLM_MODELO", "claude-haiku-5-5")
        self.sistema = sistema
        self.tools = [{"name": f["nome"], "description": f["descricao"],
                       "input_schema": f["parametros"]} for f in ferramentas]
        self.mensagens = []

    def adicionar_usuario(self, texto):
        self.mensagens.append({"role": "user", "content": texto})

    def passo(self):
        resp = self.cliente.messages.create(model=self.modelo, max_tokens=2000,
                                            system=self.sistema, tools=self.tools,
                                            messages=self.mensagens)
        self.mensagens.append({"role": "assistant", "content": resp.content})
        texto = "".join(b.text for b in resp.content if b.type == "text")
        chamadas = [{"id": b.id, "nome": b.name, "argumentos": b.input}
                    for b in resp.content if b.type == "tool_use"]
        return {"texto": texto, "chamadas": chamadas}

    def adicionar_resultados(self, resultados):
        self.mensagens.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": i, "content": json.dumps(r, ensure_ascii=False)}
            for i, _, r in resultados]})


# ---------------------------------------------------------------------------
# Formato OpenAI (chat completions)
# ---------------------------------------------------------------------------
class OpenAICompativelBackend:
    def __init__(self, sistema, ferramentas, modelo=None, cliente=None):
        if cliente is None:
            from openai import OpenAI
            cliente = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None,
                             api_key=os.environ.get("OPENAI_API_KEY", "nao-usada"))
        self.cliente = cliente
        self.modelo = modelo or os.environ.get("LLM_MODELO", "gpt-4o-mini")
        self.tools = [{"type": "function", "function": {
            "name": f["nome"], "description": f["descricao"], "parameters": f["parametros"]}}
            for f in ferramentas]
        self.mensagens = [{"role": "system", "content": sistema}]

    def adicionar_usuario(self, texto):
        self.mensagens.append({"role": "user", "content": texto})

    def passo(self):
        resp = self.cliente.chat.completions.create(model=self.modelo, messages=self.mensagens,
                                                    tools=self.tools)
        msg = resp.choices[0].message
        chamadas = []
        registro = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            registro["tool_calls"] = []
            for c in msg.tool_calls:
                registro["tool_calls"].append({"id": c.id, "type": "function", "function": {
                    "name": c.function.name, "arguments": c.function.arguments}})
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"_erro": "argumentos não são JSON válido"}
                chamadas.append({"id": c.id, "nome": c.function.name, "argumentos": args})
        self.mensagens.append(registro)
        return {"texto": msg.content or "", "chamadas": chamadas}

    def adicionar_resultados(self, resultados):
        for i, _, r in resultados:
            self.mensagens.append({"role": "tool", "tool_call_id": i,
                                   "content": json.dumps(r, ensure_ascii=False)})


# ---------------------------------------------------------------------------
# Simulado (sem rede)
# ---------------------------------------------------------------------------
def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


class SimuladoBackend:
    """Imita as decisões de um LLM com regras fixas, para rodar sem chave de API."""

    def __init__(self, sistema, ferramentas, modelo=None):
        self.historico = []  # ("usuario", texto) | ("chamada", nome, args) | ("resultado", nome, r)
        self.n = 0
        self.tarefas, self.janela = None, None

    def adicionar_usuario(self, texto):
        self.historico.append(("usuario", texto))

    def adicionar_resultados(self, resultados):
        for _, nome, r in resultados:
            self.historico.append(("resultado", nome, r))

    def _chamar(self, nome, args):
        self.n += 1
        self.historico.append(("chamada", nome, args))
        return {"texto": "", "chamadas": [{"id": f"sim{self.n}", "nome": nome,
                                           "argumentos": args}]}

    def _ultimo(self, tipo, nome=None):
        for h in reversed(self.historico):
            if h[0] == tipo and (nome is None or h[1] == nome):
                return h
        return None

    def passo(self):
        idx_usuario = max(i for i, h in enumerate(self.historico) if h[0] == "usuario")
        pergunta = self.historico[idx_usuario][1]
        p = _sem_acento(pergunta)
        depois = self.historico[idx_usuario + 1:]
        ultimo = depois[-1] if depois else None

        if ultimo is None:
            if re.search(r"\bpor ?que\b", p) and self._ultimo("resultado", "planejar_atividades"):
                return {"texto": self._explicar(p), "chamadas": []}
            if self.tarefas and re.search(r"dividi|em partes|fracion", p):
                return self._chamar("planejar_atividades", {
                    "tarefas": self.tarefas, **self.janela, "permitir_divisao": True})
            return self._chamar("consultar_agenda", {"data": "hoje"})

        if ultimo[0] == "resultado" and ultimo[1] == "consultar_agenda":
            agenda = ultimo[2]
            textos = " ".join(_sem_acento(h[1]) for h in self.historico if h[0] == "usuario")
            frases = re.split(r"[.;!?]", textos)
            tarefas = []
            for t in agenda["tarefas_pendentes"]:
                if not any(_sem_acento(k) in textos for k in t["palavras"]):
                    continue
                t = {k: v for k, v in t.items() if k != "palavras"}
                for f in frases:
                    if any(_sem_acento(k) in f for k in ("aula", "preparar")) and t["id"] == "A" \
                            and "urgente" in f:
                        t["prioridade"] = "alta"
                    if "amanha" in f and any(_sem_acento(k) in f for k in ("corre", "trabalho")) \
                            and t["id"] == "B":
                        t["prazo"] = "amanha"
                tarefas.append(t)
            if not tarefas:
                return {"texto": "Não identifiquei tarefas no pedido. Quais atividades você "
                                 "precisa encaixar e quanto tempo cada uma leva?",
                        "chamadas": []}
            jan = agenda["janela_disponivel"]
            self.tarefas, self.janela = tarefas, {"inicio": jan["inicio"], "fim": jan["fim"]}
            dividir = bool(re.search(r"dividi|em partes", p))
            return self._chamar("planejar_atividades", {"tarefas": tarefas, **self.janela,
                                                        "permitir_divisao": dividir})

        if ultimo[0] == "resultado" and ultimo[1] == "planejar_atividades":
            plano = [{k: b[k] for k in ("inicio", "fim", "tarefa")} for b in ultimo[2]["plano"]]
            return self._chamar("verificar_plano", {"plano": plano, "tarefas": self.tarefas,
                                                    **self.janela})

        if ultimo[0] == "resultado" and ultimo[1] == "verificar_plano":
            r = self._ultimo("resultado", "planejar_atividades")[2]
            v = ultimo[2]
            linhas = ["Organizei suas atividades assim:"]
            for b in r["plano"]:
                linhas.append(f"- {b['inicio']}–{b['fim']}: {b['nome']}")
            nomes = {t["id"]: t["nome"] for t in self.tarefas}
            for i in r["nao_realizadas"]:
                linhas.append(f"Ficou de fora: {nomes[i]} ({r['justificativas'][i]}).")
            for i, m in r["parciais"].items():
                linhas.append(f"{nomes[i]} foi feita em parte ({m} min); o restante fica "
                              "para depois.")
            linhas.append("O plano passou na verificação de restrições." if v["valido"]
                          else "Atenção: o verificador encontrou problemas no plano.")
            return {"texto": "\n".join(linhas), "chamadas": []}

        return {"texto": "Não consegui concluir o pedido.", "chamadas": []}

    def _explicar(self, p):
        r = self._ultimo("resultado", "planejar_atividades")[2]
        alvo = None
        for t in self.tarefas or []:
            if any(_sem_acento(k) in p for k in t.get("palavras", [])) or \
                    _sem_acento(t["nome"]) in p:
                alvo = t
        if alvo is None:
            for t in self.tarefas:
                for palavra in _sem_acento(t["nome"]).split():
                    if len(palavra) > 4 and palavra in p:
                        alvo = t
        if alvo is None:
            return "Critério usado: " + r["criterio"] + "."
        return f"{alvo['nome']}: {r['justificativas'][alvo['id']]}. Critério: {r['criterio']}."


BACKENDS = {"anthropic": AnthropicBackend, "openai": OpenAICompativelBackend,
            "simulado": SimuladoBackend}
