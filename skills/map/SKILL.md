---
name: map
description: Turns any project into an interactive board (infinite canvas, clickable steps, replay of recorded runs, search) and publishes it as a private Claude artifact. Works with GitHub Actions, cron, Makefiles, shell and Python scripts, other CI providers, orchestrators, and also apps, bots and agents. Use when the user wants to see, draw, diagram, map or explain their pipeline, data jobs, workflows, cron jobs, or how requests and data flow through their project.
---

# Montar o quadro de um projeto

Responda no idioma da pessoa. O objetivo é ela terminar com o quadro funcionando **no artefato dela**, sem precisar rodar nada.

Leia `${CLAUDE_PLUGIN_ROOT}/references/spec.md` antes de escrever a descrição.

## 1. Descobrir o que o projeto é
Olhe o repositório, sem rodar nada: arquivos de CI, `Makefile`, `package.json`, `pyproject.toml`, scripts, crontab, DAGs, `Dockerfile`, compose, pontos de entrada do app. Diga em uma frase o que achou e quais fluxos dá para desenhar. Se houver mais de um e o pedido não deixar claro, pergunte qual.

## 2. De onde vêm as etapas e os tempos
Use o primeiro caminho que servir. Eles podem se somar.

**A. GitHub Actions.** Etapas, tempos e falhas vêm das execuções:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect.py" dono/repo -o <pasta temporária>/spec.json
```

**B. Leitura do código (qualquer projeto).** Escreva a descrição à mão a partir do orquestrador ou do ponto de entrada. Siga as chamadas até onde cada etapa lê e grava.
- **Pipeline:** um cartão por fase, na ordem em que roda.
- **App, API, bot ou agente:** um cartão por camada (entrada, regra, dados, serviços externos). Cada fluxo (um pedido, um comando, um evento) vira etapas ligadas. Diga no `subtitle` que o quadro mostra a estrutura.
- Etapa sem tempo medido recebe `"meta": "lido no código"` e não recebe `seconds`. Sem medição, não escreva `runs`: não há o que repetir.
- Chamada decidida só em execução (plugin, injeção de dependência, fila, ferramenta escolhida por modelo) o código não garante. Marque como não confirmada.

**C. Tempos reais para o que roda por comando.** O gravador cronometra qualquer comando, em qualquer linguagem ou CI:
```bash
export PIPELINE_RUN=$(date +%Y-%m-%dT%H:%M:%S)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/trace.py" run "baixar dados" --group "Coleta" -- python3 baixar.py
```
Depois junte os tempos à descrição escrita no caminho B, sem perder o que veio do código. Para a junção achar a etapa, use o mesmo nome (e o título do cartão em `--group`):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/trace.py" spec trace.jsonl -o spec.json --merge spec.json
```
Cuidados:
- **Pergunte antes de rodar comandos do projeto.** Eles podem enviar, publicar, apagar, cobrar ou gravar em produção. Mostre a lista. Para só experimentar, escolha comandos que apenas leem ou constroem.
- Para gravar sempre (no cron, no Makefile ou no CI), mostre a mudança e deixe a pessoa decidir. O gravador precisa existir naquela máquina: copie `trace.py` para o repositório e ponha `trace.jsonl` no `.gitignore`. Em CI a máquina é descartada: o registro precisa ser guardado como artefato da execução.
- O gravador não guarda argumentos nem saída. **O nome e o grupo são gravados:** não ponha segredo neles.
- Ele mede comandos. Fases dentro de um mesmo processo só aparecem separadas se forem separadas em comandos ou marcadas no código.
- O replay passa as etapas uma de cada vez, mesmo as que rodaram juntas, e o relógio dele soma os tempos. Se houve paralelismo, diga isso.

## 3. Organizar para um humano entender
- 4 a 8 cartões, com `col` e `row` no sentido do fluxo;
- junte passos de preparação que não explicam nada;
- dê nomes que um colega novo entenda;
- acrescente um cartão de fontes e um de destinos quando der para saber pelo código;
- ligue os cartões com `edges` curtas.

Ao renomear uma etapa já gravada, renomeie também no comando do gravador, ou a próxima junção cria uma etapa nova.

Para fluxo interno, casos reais e registros, use a skill `explain` do mesmo plugin. Faça isso nas etapas que a pessoa apontar ou nas três mais lentas ou que falham.

## 4. Montar e olhar
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check.py" spec.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build.py" spec.json -o board.html
```
Abra `board.html` num navegador sem janela, capture uma tela e **olhe**: cartões sobrepostos, setas atravessando, texto cortado. Corrija `col`, `row` e `width`.

## 5. Publicar no artefato
1. Se `check.py` achou algo, pare e mostre à pessoa.
2. Gere a versão de artefato: `build.py spec.json -o board-artifact.html --artifact`.
3. Carregue a skill `artifact-design` e, se for usar a pergunta em linguagem natural, a `artifact-capabilities`. Publique com `capabilities: {"sample": {}}` para a pergunta funcionar, ou ponha `"ask": false` na descrição.
4. O artefato nasce privado. Diga isso, e diga o que está exposto se a pessoa compartilhar: nomes de rotinas, arquivos, falhas e registros. Leia o compartilhamento no resultado de **cada** publicação: ele pode ter mudado.
5. Para atualizar, publique o mesmo arquivo de novo (mesmo endereço).

Se não houver como publicar artefato, entregue o `board.html`, que abre em qualquer navegador.

## O que dizer no fim
O endereço, **o que foi medido** e **o que foi lido no código**, e o que você não testou (clique, celular, tema claro).
