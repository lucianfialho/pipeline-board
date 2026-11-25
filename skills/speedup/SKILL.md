---
name: speedup
description: Finds why a pipeline is slow or failing and speeds it up in code (parallelism, skipping unchanged work, platform limits), with before and after measurements. Use when the user says a pipeline is slow, times out, should run in parallel, or costs too much.
---

# Acelerar sem quebrar

## 1. Medir antes de opinar
Some o tempo por etapa nas execuções reais. Ordene. Não proponha nada para o que não está no topo.

## 2. Para cada etapa lenta, ache o limite verdadeiro
- Quantos servidores diferentes ela contata? **Muitos:** linhas em paralelo ajudam muito. **Um só, com intervalo entre chamadas:** o intervalo é o piso (itens × intervalo), e paralelizar quase não ajuda. Faça essa conta antes de prometer ganho.
- Ela refaz o que não mudou (baixar de novo para comparar)?
- O limitador de chamadas aguenta várias linhas? Um intervalo guardado numa variável global **fura** com threads: reserve o próximo horário sob trava e durma fora dela. Escreva um teste.
- Os passos gravam no mesmo arquivo? Então não dá para rodá-los em paralelo sem separar as saídas.
- A rede pode ir em paralelo e a gravação continuar em fila, na mesma ordem. Teste que o resultado é idêntico ao de uma linha só.

## 3. Provar
Meça numa amostra com dados reais, sem gravar. Rode o paralelo primeiro, para o cache não favorecê-lo. Compare também a **qualidade** (quantos falharam). Depois, se der, rode a etapa inteira numa cópia descartável. Compare coisas iguais e diga o que torna a comparação injusta (outra máquina, menos trabalho a fazer). Projeção se chama projeção.

## 4. Falhas e limites
Leia a mensagem de erro e o limite na documentação atual, não de memória. Antes de remover arquivos de um site, observe num navegador o que ele realmente pede. Se destravar uma publicação, confira se não havia dado errado esperando para ir ao ar.

## 5. Entregar
Trabalhe num branch separado. Rode os testes e um build limpo. Nunca encadeie comandos de um jeito que continue depois de um teste falho. Não envie para a branch principal nem publique: mostre o comando e deixe a pessoa decidir. Diga as permissões novas que as rotinas passam a ter.
