#!/usr/bin/env python3
"""Lê as execuções do GitHub Actions de um repositório e escreve o primeiro rascunho da descrição do quadro.

  python3 collect.py dono/repo -o spec.json [--workflow "Nome"] [--runs 20]

Só leitura, pela CLI `gh` já autenticada. Cada rotina vira um cartão com as etapas da execução mais recente: nome,
tempo medido e resultado. O que não dá para saber pela API (fluxo interno, o que entra e sai, casos reais) fica vazio,
para ser preenchido a partir do código. Nada é inventado.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

# passos que o GitHub acrescenta sozinho: não dizem nada sobre o pipeline
RUIDO = re.compile(r"^(Set up job|Complete job|Post |Run actions/(checkout|setup-[a-z]+|cache)@)")
ICONES = (("test|lint|check|confere|valida", "shield"), ("build|compil", "wand"), ("deploy|publi|release", "globe"),
          ("data|dado|db|migrat|export", "database"), ("crawl|scrap|coleta|collect|fetch|sync", "bot"), ("model|llm|classif|embed", "tag"), ("news|rss|blog|feed", "rss"))


def gh(caminho):
    r = subprocess.run(["gh", "api", caminho], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr.strip().splitlines() or ["falha no gh"])[-1])
    return json.loads(r.stdout)


def segundos(a, b):
    if not a or not b:
        return None
    f = lambda t: datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
    return max(0, (f(b) - f(a)).total_seconds())


def slug(texto, usados):
    base = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:40] or "etapa"
    nome, n = base, 2
    while nome in usados:
        nome, n = f"{base}-{n}", n + 1
    usados.add(nome)
    return nome


def icone(nome):
    return next((i for padrao, i in ICONES if re.search(padrao, nome, re.I)), "file")


def rascunho(repo, execucoes, jobs_de, filtro=None, hoje=None):
    """`execucoes` vem da API, da mais nova para a mais antiga; `jobs_de(id)` devolve os jobs de uma execução."""
    por_rotina = {}
    for e in execucoes:
        if e.get("status") == "completed" and (not filtro or e["name"] == filtro):
            por_rotina.setdefault(e["name"], []).append(e)
    ids, cartoes, corridas, limites = set(), [], [], []
    for linha, (nome, lista) in enumerate(por_rotina.items()):
        ultima = lista[0]
        jobs = jobs_de(ultima["id"])
        falhas = sum(e.get("conclusion") != "success" for e in lista)
        for coluna, job in enumerate(jobs):
            etapas, sequencia, quebrou = [], [], None
            for s in job.get("steps", []):
                if RUIDO.search(s["name"]) or s.get("conclusion") == "skipped":
                    continue
                sid = slug(f"{job['name']}-{s['name']}" if len(jobs) > 1 else s["name"], ids)
                t = segundos(s.get("started_at"), s.get("completed_at"))
                ruim = s.get("conclusion") in ("failure", "cancelled", "timed_out")
                etapas.append({"id": sid, "name": s["name"], "icon": icone(s["name"]), "seconds": t, "status": "failed" if ruim else None,
                               "metrics": [{"when": f"{ultima['run_started_at'][:10]} · {s.get('conclusion')}", "values": [[f"{t:.0f} s" if t is not None else "—", "duração"]]}]})
                sequencia.append(sid)
                if ruim and not quebrou:
                    quebrou = sid
                    break
            if not etapas:
                continue
            total = sum(s["seconds"] or 0 for s in etapas)
            cid = slug(f"{nome}-{job['name']}", ids)
            cartoes.append({"id": cid, "title": nome if len(jobs) == 1 else f"{nome}: {job['name']}", "col": coluna, "row": linha,
                            "summary": f"{total / 60:.1f} min · {falhas} de {len(lista)} execuções recentes sem sucesso", "tone": "warn" if quebrou else "",
                            "width": 560 if len(etapas) > 6 else 320, "steps": etapas})
            corridas.append({"label": nome if len(jobs) == 1 else f"{nome}: {job['name']}", "steps": sequencia, "breakAt": quebrou,
                             "note": f"Quebrou em “{next(s['name'] for s in etapas if s['id'] == quebrou)}”." if quebrou else "Terminou sem erro."})
    setas = [[a["id"], b["id"], ""] for a, b in zip(cartoes, cartoes[1:]) if a["row"] == b["row"]]
    return {"title": repo.split("/")[-1], "subtitle": f"GitHub Actions de {repo}", "generated": (hoje or datetime.date.today()).isoformat(),
            "cards": cartoes, "edges": setas, "runs": corridas, "limits": limites}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="dono/repositorio")
    p.add_argument("-o", "--saida", default="spec.json")
    p.add_argument("--workflow", help="só esta rotina (nome exato)")
    p.add_argument("--runs", type=int, default=30, help="quantas execuções recentes olhar (até 100)")
    a = p.parse_args(argv)
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", a.repo):
        sys.exit("repositório inválido: use dono/nome")
    try:
        execucoes = gh(f"repos/{a.repo}/actions/runs?per_page={max(1, min(a.runs, 100))}")["workflow_runs"]
        spec = rascunho(a.repo, execucoes, lambda i: gh(f"repos/{a.repo}/actions/runs/{i}/jobs?per_page=50")["jobs"], a.workflow)
    except (RuntimeError, KeyError) as erro:
        sys.exit(f"Não consegui ler o GitHub Actions de {a.repo}: {erro}")
    if not spec["cards"]:
        sys.exit("Nenhuma execução concluída encontrada.")
    pathlib.Path(a.saida).write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(f"{a.saida}: {len(spec['cards'])} cartões, {sum(len(c['steps']) for c in spec['cards'])} etapas. Falta preencher fluxo, entradas, saídas e casos a partir do código.")


if __name__ == "__main__":
    main()
