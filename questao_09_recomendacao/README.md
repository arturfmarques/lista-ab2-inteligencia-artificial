# Questão 9: recomendação de atividades físicas com ontologia OWL 2

> Conteúdo educacional; não substitui orientação de profissional de saúde.

- [`ontologia_atividades.py`](ontologia_atividades.py): constrói a ontologia
  (24 classes, 21 propriedades, 2 regras SWRL, 35 indivíduos).
- [`recomendador.py`](recomendador.py): executa o raciocinador HermiT e gera as
  recomendações justificadas.
- [`atividades.owl`](atividades.owl): a ontologia em RDF/XML (abre no Protégé);
  [`atividades_inferido.owl`](atividades_inferido.owl): com as inferências gravadas.

```bash
python recomendador.py                    # usuários de exemplo, consulta SPARQL e teste de consistência
python recomendador.py --usuario Joao
python recomendador.py --novo Lia --objetivos ReduzirEstresse,GanharForca \
       --condicoes Asma --locais Casa,Academia --equipamentos Tapete --nivel intermediario
python recomendador.py --listar           # objetivos, condições, locais e equipamentos válidos
python recomendador.py --consistencia
```

Requer `owlready2` e Java 11 ou mais recente. Saída completa em
[`resultados.txt`](resultados.txt).

## Como a recomendação usa o raciocínio

1. O HermiT verifica a consistência e classifica atividades e usuários nas classes
   definidas (`AtividadeBaixoImpacto`, `UsuarioIniciante`, `UsuarioComRestricaoArticular`...).
2. Cadeias de propriedades descobrem relações implícitas:
   `temObjetivo ∘ eAtingidoPor ⊑ atividadeCandidata` e
   `temCondicao ∘ desaconselha ⊑ deveEvitar`.
3. Regras SWRL acrescentam `deveEvitar` para atividades de alto impacto (usuário com
   problema articular) e vigorosas (usuário iniciante).
4. O recomendador parte das candidatas, retira as que devem ser evitadas, confere local
   e equipamento, pontua e mostra o elemento da ontologia por trás de cada decisão.
