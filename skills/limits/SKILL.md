---
name: limits
description: Measures how close a pipeline is to its limits (GitHub Actions usage, job timeout, cache, files per deploy) and shows them on the board. Use when the user asks about quotas, limits, monitoring, cost of CI, or why a deploy or job was cancelled.
---

# Limites

O script abaixo só lê o GitHub Actions. Em projeto sem ele, não rode o script: escreva `limits` à mão.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/limits.py" dono/repo --spec spec.json --timeouts .github/workflows
```
Acrescente `--site <pasta do build> --max-files N` quando a publicação tiver limite de arquivos.

- Antes de citar um teto, **confira o plano da conta e a documentação atual**, e passe os valores por `--included-usd` e `--usd-per-minute`.
- Limite de outro serviço: acrescente à mão em `limits`, com a fonte na nota. Sem acesso, deixe `used` vazio: aparece como "não medido".
- Segredo para ler um limite só por cofre ou segredo da plataforma. Não peça para a pessoa colar token na conversa.
- Projeção do mês: cuidado quando as rotinas começaram no meio do mês.
- Para acompanhar todo dia, ofereça um passo no fim da rotina com `if: always()`, e avise que ele exige `actions: read`.

Depois monte e publique o quadro de novo (skill `map`).
