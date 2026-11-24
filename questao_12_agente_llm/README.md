# Questão 12: agente baseado em LLM para planejamento acadêmico

Assistente que organiza as atividades de um professor (o cenário da questão 11).
O LLM conversa em linguagem natural e decide quais ferramentas chamar; um
planejador clássico calcula o plano e um verificador confere as restrições.

| Arquivo | Papel |
|---|---|
| [`agente.py`](agente.py) | ciclo do agente, interface de conversa e explicações |
| [`llm.py`](llm.py) | backends: Anthropic, formato OpenAI (OpenAI, Ollama, Groq...) e simulado |
| [`ferramentas.py`](ferramentas.py) | ferramentas que o LLM pode chamar |
| [`planejador.py`](planejador.py) | planejador por utilidade e verificador de restrições |
| [`agenda.json`](agenda.json) | agenda e tarefas pendentes do professor |
| [`testes.py`](testes.py) | testes sem rede, inclusive dos dois backends reais com clientes falsos |

## Executar

```bash
python agente.py --demo                  # roteiro da demonstração (sem chave de API)
python agente.py                         # conversa no terminal, backend simulado

export ANTHROPIC_API_KEY=...             # com um LLM de verdade
python agente.py --backend anthropic

export OPENAI_BASE_URL=http://localhost:11434/v1   # Ollama local, por exemplo
export LLM_MODELO=qwen2.5:7b
python agente.py --backend openai

python testes.py
```

Na conversa: `/explicar` mostra o rastro do último pedido (cada ferramenta chamada,
com argumentos e resultado), `/porque A` mostra a justificativa do planejador para a
tarefa A, `/plano` mostra o último plano completo e `/sair` encerra.

O backend `simulado` imita as decisões de um LLM com regras fixas para que a
demonstração rode sem chave de API; ele só entende pedidos parecidos com os do
roteiro. Os backends reais foram testados com clientes falsos (`testes.py`), não com
chamadas reais à API.

Saída da demonstração em [`resultados_demo.txt`](resultados_demo.txt).
