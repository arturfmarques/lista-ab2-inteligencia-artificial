# Questão 15: ontologia OWL 2 acadêmica com raciocínio

Implementa a ontologia usada como exemplo na questão 1 (alunos, professores,
disciplinas, pré-requisitos) e executa o raciocinador **HermiT**, o mesmo que vem
no Protégé.

```bash
python ontologia_academica.py
```

O programa gera:

- [`academico.owl`](academico.owl): a ontologia declarada (RDF/XML);
- [`academico_inferido.owl`](academico_inferido.owl): a ontologia com as inferências gravadas;
- a saída em [`resultados.txt`](resultados.txt).

## Abrir no Protégé

1. *File → Open* e escolha `academico.owl`.
2. *Reasoner → HermiT* e depois *Reasoner → Start reasoner*.
3. Na aba *Individuals by class*, os indivíduos aparecem nas classes inferidas
   (em amarelo): Bruno em `Monitor`, ProfEvandro em `Orientador` e `DocenteDeIA`,
   ProfMarta em `Professor`.
4. Em *Object property assertions* de `AprendizadoDeMaquina`, `temPreRequisito`
   mostra Algoritmos e Programacao inferidos; em `Ana`, `deveCursarAntes` mostra o
   resultado das regras SWRL (aba *Rules* para vê-las).

Requer `owlready2` e Java 11 ou mais recente.
