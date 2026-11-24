# Questão 7: apoio ao diagnóstico médico baseado em casos

> Protótipo educacional. Os casos são fictícios e o sistema não substitui
> avaliação médica.

Base inicial: [`casos_iniciais.json`](casos_iniciais.json), 20 casos de 7
doenças (gripe, resfriado comum, dengue, COVID-19, enxaqueca, gastroenterite e
sinusite). Na primeira execução o programa copia essa base para `casos.json`,
que é a base de trabalho onde os casos novos são retidos.

## Comandos

```bash
python rbc_diagnostico.py demo          # 6 consultas de exemplo + avaliação (não altera a base)
python rbc_diagnostico.py interativo    # menu: consulta, revisão e retenção
python rbc_diagnostico.py consultar --sintomas febre,tosse,perda_olfato --temperatura 38.2 --dias 3
python rbc_diagnostico.py consultar --sintomas ... --confirmar
python rbc_diagnostico.py consultar --sintomas ... --corrigir "Sinusite" --tratamento "..."
python rbc_diagnostico.py listar
python rbc_diagnostico.py avaliar       # leave-one-out
python rbc_diagnostico.py reiniciar     # volta para a base inicial
```

Saída da demonstração em [`resultados_demo.txt`](resultados_demo.txt).

## Ciclo de RBC

1. **Recuperação**: similaridade global entre a consulta e cada caso, e os k = 3 mais semelhantes.
2. **Reutilização**: votam os casos recuperados com similaridade de pelo menos 85 %
   da do mais parecido; o diagnóstico com maior soma de similaridades é sugerido,
   com o tratamento do caso mais parecido que tem esse diagnóstico.
3. **Revisão**: o profissional confirma ou corrige o diagnóstico e o tratamento.
4. **Retenção**: o caso revisado é gravado; um caso idêntico a outro já existente
   com o mesmo diagnóstico não é gravado.

## Similaridade

```
sim = 0,70 * sim_sintomas + 0,20 * sim_temperatura + 0,10 * sim_duracao
sim_sintomas    = Jaccard ponderado (sintomas específicos pesam mais)
sim_temperatura = 1 - |t1 - t2| / 5
sim_duracao     = 1 - |d1 - d2| / 14
```

Quando a consulta não tem temperatura ou duração, o peso desse atributo sai da
conta e os outros são renormalizados.
