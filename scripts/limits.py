#!/usr/bin/env python3
"""Mede quanto falta para estourar limites e grava o resultado na descrição do quadro (campo "limits").

  python3 limits.py dono/repo --spec spec.json [--timeouts .github/workflows] [--site dist --max-files 100000]
                    [--included-usd 12 --usd-per-minute 0.006]

O que não dá para ler fica "não medido", com o motivo: número ausente não é número zero. Os valores do plano são os do
GitHub Free para organizações em 11/2026; confira os do seu plano e passe pelos parâmetros.
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess


def gh(caminho):
    r = subprocess.run(["gh", "api", caminho], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError((r.stderr.strip().splitlines() or ["sem acesso"])[-1][:160])
    return json.loads(r.stdout)


def segundos(a, b):
    f = lambda t: datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
    return (f(b) - f(a)).total_seconds()


def item(nome, usado, limite, unidade, nota=""):
    return {"name": nome, "used": None if usado is None else round(usado, 3), "limit": limite, "unit": unidade, "note": nota}


def medir(repo, a, chamar=gh, hoje=None):
    hoje, itens = hoje or datetime.date.today(), []
    try:
        execs = [e for e in chamar(f"repos/{repo}/actions/runs?per_page=100&created=%3E%3D{hoje.replace(day=1).isoformat()}")["workflow_runs"] if e.get("status") == "completed" and e.get("run_started_at")]
    except (RuntimeError, KeyError) as erro:
        return [item("GitHub Actions no mês", None, a.included_usd, "US$", str(erro))]
    try:
        uso = chamar(f"organizations/{repo.split('/')[0]}/settings/billing/usage?year={hoje.year}&month={hoje.month}")["usageItems"]
        usd, fonte = sum(u["grossAmount"] for u in uso if u.get("product", "").lower() == "actions" and u.get("unitType") == "Minutes"), "cobrança da organização"
    except (RuntimeError, KeyError):
        usd, fonte = sum(-(-segundos(e["run_started_at"], e["updated_at"]) // 60) for e in execs) * a.usd_per_minute, "estimativa pela duração das últimas 100 execuções deste repositório"
    itens.append(item("GitHub Actions no mês", usd, a.included_usd, "US$", fonte))
    if a.timeouts:
        for arq in sorted(pathlib.Path(a.timeouts).glob("*.y*ml")):
            texto = arq.read_text()
            nome, teto = re.search(r"^name:\s*(.+)$", texto, re.M), re.search(r"timeout-minutes:\s*(\d+)", texto)
            if not nome:
                continue
            dela = sorted((e for e in execs if e["name"] == nome.group(1).strip()), key=lambda e: e["run_started_at"])
            if dela:
                itens.append(item(f"Tempo da rotina {nome.group(1).strip()}", segundos(dela[-1]["run_started_at"], dela[-1]["updated_at"]) / 60, int(teto.group(1)) if teto else 360, "min",
                                  f"última execução: {dela[-1].get('conclusion')}" + ("" if teto else " · sem timeout-minutes, vale o teto de 6 h do GitHub")))
    try:
        itens.append(item("Cache do Actions", chamar(f"repos/{repo}/actions/cache/usage")["active_caches_size_in_bytes"] / 1e9, 10, "GB"))
    except (RuntimeError, KeyError) as erro:
        itens.append(item("Cache do Actions", None, 10, "GB", str(erro)))
    if a.site:
        pasta = pathlib.Path(a.site)
        itens.append(item("Arquivos do site", sum(p.is_file() for p in pasta.rglob("*")) if pasta.is_dir() else None, a.max_files, "arquivos", "" if pasta.is_dir() else "a pasta não existe"))
    return itens


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo")
    p.add_argument("--spec", required=True)
    p.add_argument("--timeouts", help="pasta das rotinas, para ler timeout-minutes")
    p.add_argument("--site")
    p.add_argument("--max-files", type=int, default=100_000)
    p.add_argument("--included-usd", type=float, default=12.0)
    p.add_argument("--usd-per-minute", type=float, default=0.006)
    a = p.parse_args(argv)
    caminho = pathlib.Path(a.spec)
    spec = json.loads(caminho.read_text())
    spec["limits"] = medir(a.repo, a)
    caminho.write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    for i in spec["limits"]:
        pct = f"{100 * i['used'] / i['limit']:.0f}%" if i["used"] is not None and i["limit"] else "não medido"
        print(f"{pct:>11}  {i['name']}  {i['note']}")


if __name__ == "__main__":
    main()
