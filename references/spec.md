# Descrição do quadro (spec.json)

Tudo o que o quadro mostra vem deste arquivo. O gerador (`scripts/build.py`) recusa ids repetidos e referências que não existem. Todo texto entra na página como texto puro.

```json
{
 "title": "nome", "subtitle": "de onde vem", "generated": "2026-11-25", "lang": "pt",
 "cards": [{
   "id": "ingest", "title": "Ingestão", "summary": "4 fontes · 6 min",
   "col": 0, "row": 0, "width": 320, "tone": "" ,
   "steps": [{
     "id": "orders", "name": "Pedidos", "icon": "database", "seconds": 95,
     "meta": "texto no bloco (sem ele, mostra o tempo)", "badge": "8x", "status": "failed",
     "writes": "onde grava", "file": "jobs/orders.py", "input": "o que entra", "output": "o que sai",
     "flow": ["passo", ["?", "pergunta?", "o que acontece no outro caminho"], ["L", "para cada item", ["passo"], 8]],
     "metrics": [{"when": "execução e data", "values": [["95 s", "tempo"]], "note": "como foi calculado"}],
     "case": {"name": "caso real", "rows": [["rótulo", "valor", "ok | bad | vazio"]], "note": ""},
     "records": {"title": "Últimos registros", "items": [["título", "detalhe", "data", "https://…"]]}
   }]
 }],
 "edges": [["ingest", "transform", "rótulo", "fail ou vazio"]],
 "runs": [{"label": "Diária", "steps": ["orders"], "seconds": [95], "breakAt": "orders", "note": "frase mostrada no fim"}],
 "limits": [{"name": "Minutos de CI", "used": 255, "limit": 2000, "unit": "min", "note": ""}],
 "findings": [{"title": "Lista para em 1.000", "status": "confirmed", "severity": "high", "step": "orders", "file": "jobs/orders.py:40", "detail": "o que acontece", "evidence": "o que foi visto", "fix": "correção sugerida"}],
 "ask": true,
 "labels": {"report": "Report"}
}
```

- `icon`: `bot database file globe learn news rss shield tag wand`.
- `col` e `row` posicionam o cartão no layout automático. Sem eles, os cartões vão em fila.
- `tone: "warn"` marca o cartão com borda laranja. Um cartão com falha confirmada fica laranja sozinho.
- `status` de etapa: `"failed"` ou ausente.
- Em `flow`, `["L", rótulo, [passos], 8]` é uma repetição; o número, opcional, é quantas rodam em paralelo.
- Em `edges`, o quarto campo é `"fail"` (seta tracejada, sem animação) ou vazio.
- `findings`: `status` é `confirmed` (exige `evidence`) ou `suspected`; `severity` é `high`, `medium` ou `low`; `step` é opcional. Problema achado na leitura vai aqui, não em `case`.
- Contagens que já estão nos dados do projeto podem ir em `metrics`, com a origem e a data em `when`.
- `ask: false` esconde a pergunta em linguagem natural. Ela só aparece quando a página é um artefato com a capacidade `sample`.

## Sem tempo medido

Etapa que veio só da leitura do código leva `"meta": "lido no código"` e nenhum `seconds`. Sem medição não há `runs`. Para medir, use `scripts/trace.py` (`run` grava, `spec --merge` junta).

## Regras de conteúdo

1. **Número só com origem.** Tempo, volume e taxa vêm de uma execução, de um log ou de um arquivo. Estimativa leva a palavra "estimativa" na nota. Sem dado, deixe de fora.
2. **Fluxo vem do código.** Escreva `flow` depois de ler a função. Se veio só do nome ou da documentação, diga isso na nota.
3. **Caso real é real.** Um registro de verdade, com o caminho que ele fez. Se um caso mostra um defeito, marque a linha como `bad` e diga o que não foi verificado.
4. **Nada sensível.** Sem chaves, e-mails, nomes de pessoas ou de clientes. `scripts/check.py` pega parte disso; o resto é leitura sua.
