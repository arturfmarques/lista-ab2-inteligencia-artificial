# Questão 2: KNN sobre a base da Lista 1

Base: [`dados_credito.csv`](dados_credito.csv), os 30 exemplos de risco de
crédito (6 atributos categóricos) usados na Lista 1.

`python knn_credito.py` executa:

1. a classificação passo a passo de um cliente novo (distâncias aos 30
   exemplos, k vizinhos, votação);
2. a avaliação leave-one-out para k = 1, 3, 5, 7, 9, com distância de Hamming e
   com uma variante ordinal (Renda e História de Crédito ordenadas);
3. a conferência com o `KNeighborsClassifier` do scikit-learn;
4. a matriz de confusão e o gráfico [`acuracia_por_k.png`](acuracia_por_k.png).

Outro cliente e outro k:

```bash
python knn_credito.py --k 5 --cliente "Boa,Alta,Nenhuma,15-35,Estavel,Jovem"
```

Ordem dos valores: Historia_Credito, Divida, Garantia, Renda, Emprego, Idade.
Saída completa em [`resultados.txt`](resultados.txt).
