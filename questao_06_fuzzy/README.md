# Questão 6: sistema fuzzy de Mamdani para irrigação

Entradas: umidade do solo (0 a 100 %) e temperatura do ar (0 a 45 °C).
Saída: tempo de irrigação (0 a 60 min). Nove regras, inferência de Mamdani
(E = mínimo, implicação = mínimo, agregação = máximo) e defuzzificação pelo
centroide.

```bash
python fuzzy_irrigacao.py                         # caso de exemplo: 33 %, 31 °C
python fuzzy_irrigacao.py --umidade 60 --temperatura 22
```

O programa calcula a inferência à mão, etapa por etapa, e confere o resultado
com o `ControlSystem` do scikit-fuzzy. Saída completa em
[`resultados.txt`](resultados.txt).

Figuras:

- [`figuras/funcoes_pertinencia.png`](figuras/funcoes_pertinencia.png)
- [`figuras/agregacao_e_centroide.png`](figuras/agregacao_e_centroide.png)
- [`figuras/superficie_controle.png`](figuras/superficie_controle.png)
