---
name: explain
description: Fills a pipeline board with what happens inside each step, read from the code, plus real example records, latest results and metrics. Use when the user wants to understand what a step does, see a real case, the latest items found, throughput, costs or which models a step calls.
---

# Explicar uma etapa

Edite o `spec.json` do quadro (formato em `${CLAUDE_PLUGIN_ROOT}/references/spec.md`). Para cada etapa pedida:

1. **Fluxo.** Leia a função que a etapa chama, não só o nome do passo. Escreva em `flow` os passos, as repetições (`["L", ...]`, com o número de chamadas em paralelo se houver) e as decisões, com o que acontece quando falha. Preencha `file`, `input`, `output` e `writes`.
2. **Medidas.** Pegue contagens dos logs da execução (`gh run view <id> --log`) e calcule itens por segundo. "Links por segundo" só se o código contar requisições; senão diga que não há contagem.
3. **Caso real.** Um registro dos dados do projeto que passou por ali, com entrada, decisão e saída. Prefira um que mostre uma regra em ação. Procure também um caso que pareça errado: se achar, meça o tamanho do problema, marque como `bad` e **conte à pessoa na hora**.
4. **Últimos registros.** Até 10 itens recentes em `records`, com data e endereço de origem. Diga que é um retrato e de que dia.
5. **Modelos e custo.** Se a etapa chama um modelo, diga qual, se é local ou por API, e o preço consultado na hora. Custo por tamanho de texto é estimativa.

Antes de publicar de novo, rode `scripts/check.py` e confira que nenhum registro traz nome de pessoa, e-mail ou dado de cliente.
