---
name: map
description: Turns a repository's pipeline into an interactive board (infinite canvas, clickable steps, replay of real runs, search) and publishes it as a private Claude artifact. Use when the user wants to see, draw, diagram, map or explain their pipeline, CI/CD, data jobs, GitHub Actions workflows or cron jobs.
---

# Montar o quadro do pipeline

Responda no idioma da pessoa. O objetivo é ela terminar com o quadro funcionando **no artefato dela**, sem precisar rodar nada.

## 1. Rascunho a partir das execuções reais
Descubra o repositório (`git remote get-url origin`) e rode:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect.py" dono/repo -o <pasta temporária>/spec.json
```

Se o projeto não usa GitHub Actions, escreva a descrição à mão seguindo `${CLAUDE_PLUGIN_ROOT}/references/spec.md`, a partir do orquestrador que ele usa (Makefile, crontab, DAG, scripts), e diga que não há tempos medidos.

## 2. Organizar para um humano entender
Leia `${CLAUDE_PLUGIN_ROOT}/references/spec.md`. Depois ajuste o rascunho:
- agrupe as etapas em 4 a 8 cartões por fase (de onde vem, processar, conferir, publicar), com `col` e `row` no sentido do fluxo;
- junte passos de preparação que não explicam nada;
- dê nomes que um colega novo entenda;
- acrescente um cartão de fontes e um de destinos quando der para saber pelo código;
- ligue os cartões com `edges` curtas.

Para fluxo interno, casos reais e registros, use a skill `explain` do mesmo plugin. Faça isso nas etapas que a pessoa apontar ou nas três mais lentas ou que falham.

## 3. Montar e olhar
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" spec.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build.py" spec.json -o board.html
```
Abra `board.html` num navegador sem janela, capture uma tela e **olhe**: cartões sobrepostos, setas atravessando, texto cortado. Corrija `col`, `row` e `width`.

## 4. Publicar no artefato
1. Se `check.py` achou algo, pare e mostre à pessoa.
2. Gere a versão de artefato: `build.py spec.json -o board-artifact.html --artifact`.
3. Carregue a skill `artifact-design` e, se for usar a pergunta em linguagem natural, a `artifact-capabilities`. Publique com `capabilities: {"sample": {}}` para a pergunta funcionar, ou ponha `"ask": false` na descrição.
4. O artefato nasce privado. Diga isso, e diga o que está exposto se a pessoa compartilhar: nomes de rotinas, arquivos, falhas e registros. Leia o compartilhamento no resultado de **cada** publicação: ele pode ter mudado.
5. Para atualizar, publique o mesmo arquivo de novo (mesmo endereço).

## O que dizer no fim
O endereço, o que veio de medição, o que foi escrito por leitura do código, e o que você não testou (clique, celular, tema claro).
