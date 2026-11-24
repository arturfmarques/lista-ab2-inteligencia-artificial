# Questão 8: diagnóstico de dengue com rede bayesiana

> Modelo educacional. As probabilidades são plausíveis, não clínicas.

`python rede_dengue.py` imprime as tabelas de probabilidades condicionais, as
independências condicionais verificadas por d-separação, as probabilidades a
priori e quatro experimentos de inferência (eliminação de variáveis). Também gera:

- [`rede_dengue.png`](rede_dengue.png): o grafo da rede;
- [`rede_dengue.bif`](rede_dengue.bif) e [`rede_dengue.xmlbif`](rede_dengue.xmlbif):
  o modelo em formatos que outras ferramentas abrem (o XMLBIF abre, por exemplo, no
  GeNIe e no Weka).

Consulta com evidências livres:

```bash
python rede_dengue.py --evidencias Febre=Sim,ManchasPele=Sim,TesteNS1=Nao
```

Variáveis: `EpocaChuvosa`, `CasoVizinhanca`, `Dengue`, `Gripe`, `Febre`,
`DorRetroOrbital`, `ManchasPele`, `DorMuscular`, `Tosse`, `TesteNS1` (todas Sim/Nao).
Saída completa em [`resultados.txt`](resultados.txt).
