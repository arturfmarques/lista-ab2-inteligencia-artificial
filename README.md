# Lista 2 de Inteligência Artificial (2026.2)

Código das questões da Lista 2 (Prof. Evandro Costa) que envolvem programação.
As respostas em texto ficam no documento de respostas; este repositório tem o
código e as saídas de cada execução.

| Questão | Pasta | Conteúdo |
|---|---|---|
| 2 | [`questao_02_knn`](questao_02_knn) | KNN sobre a base de 30 exemplos de risco de crédito da Lista 1 |
| 6 | [`questao_06_fuzzy`](questao_06_fuzzy) | Sistema fuzzy de Mamdani para irrigação (scikit-fuzzy) |
| 7 | [`questao_07_rbc`](questao_07_rbc) | Apoio ao diagnóstico médico por raciocínio baseado em casos |
| 8 | [`questao_08_bayes`](questao_08_bayes) | Diagnóstico de dengue com rede bayesiana (pgmpy) |
| 9 | [`questao_09_recomendacao`](questao_09_recomendacao) | Recomendação de atividades físicas com ontologia OWL 2 e HermiT |
| 10 | [`questao_10_busca`](questao_10_busca) | Rotas de entrega com DFS, BFS, custo uniforme e A* |
| 12 | [`questao_12_agente_llm`](questao_12_agente_llm) | Agente LLM de planejamento acadêmico com planejador e verificador |
| 15 | [`questao_15_ontologia`](questao_15_ontologia) | Ontologia OWL 2 acadêmica com raciocínio (HermiT e SWRL) |

## Como executar

Python 3.10 ou mais recente.

```bash
pip install -r requirements.txt

python questao_02_knn/knn_credito.py
python questao_06_fuzzy/fuzzy_irrigacao.py
python questao_07_rbc/rbc_diagnostico.py demo
python questao_08_bayes/rede_dengue.py
python questao_09_recomendacao/recomendador.py
python questao_10_busca/busca_rotas.py
python questao_12_agente_llm/agente.py --demo
python questao_15_ontologia/ontologia_academica.py
```

As questões 9 e 15 precisam de Java 11 ou mais recente (o Owlready2 já traz o
raciocinador HermiT). As questões 7 e 10 usam só a biblioteca padrão. Cada pasta tem um arquivo
`resultados*.txt` com a saída completa da execução e um README com os detalhes.
