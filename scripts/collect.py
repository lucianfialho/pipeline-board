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

SEP = " :: "  # liga uma etapa do quadro ao passo da rotina: "Rotina :: Nome do passo"
LIDO, NAO_RODOU = "lido no código", "não rodou na última execução"

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
    ids, cartoes, corridas, limites, origem = set(), [], [], [], {}
    for linha, (nome, lista) in enumerate(por_rotina.items()):
        ultima = lista[0]
        jobs = jobs_de(ultima["id"])
        origem[nome] = {"id": ultima["id"], "date": ultima["run_started_at"][:10], "at": ultima["run_started_at"]}
        falhas = sum(e.get("conclusion") != "success" for e in lista)
        for coluna, job in enumerate(jobs):
            etapas, sequencia, quebrou = [], [], None
            for s in job.get("steps", []):
                if RUIDO.search(s["name"]) or s.get("conclusion") == "skipped":
                    continue
                sid = slug(f"{job['name']}-{s['name']}" if len(jobs) > 1 else s["name"], ids)
                t = segundos(s.get("started_at"), s.get("completed_at"))
                ruim = s.get("conclusion") in ("failure", "cancelled", "timed_out")
                etapas.append({"id": sid, "ci": [f"{nome}{SEP}{s['name']}"], "name": s["name"], "icon": icone(s["name"]), "seconds": t, "status": "failed" if ruim else None,
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
            corridas.append({"label": nome if len(jobs) == 1 else f"{nome}: {job['name']}", "auto": nome, "steps": sequencia, "breakAt": quebrou,
                             "note": f"Quebrou em “{next(s['name'] for s in etapas if s['id'] == quebrou)}”." if quebrou else "Terminou sem erro."})
    setas = [[a["id"], b["id"], ""] for a, b in zip(cartoes, cartoes[1:]) if a["row"] == b["row"]]
    return {"title": repo.split("/")[-1], "subtitle": f"GitHub Actions de {repo}", "generated": (hoje or datetime.date.today()).isoformat(),
            "cards": cartoes, "edges": setas, "runs": corridas, "limits": limites, "source": {"repo": repo, "runs": origem}}


def etapas_de(spec):
    return [s for c in spec.get("cards", []) for s in c.get("steps", [])]


def sem_aviso(meta):
    """A anotação escrita à mão, sem os avisos que a própria junção torna falsos ("lido no código · pode falhar" → "pode falhar")."""
    return " · ".join(p for p in str(meta or "").split(" · ") if p not in (LIDO, NAO_RODOU))


def ligar_pelo_nome(base, chaves):
    """Etapa escrita à mão sem 'ci' ganha a ligação quando o nome é igual ao de um passo e não há dúvida dos dois lados."""
    ligadas = {k for s in etapas_de(base) for k in s.get("ci", [])}
    nomes = [s["name"] for s in etapas_de(base)]
    for s in etapas_de(base):
        if s.get("ci") or nomes.count(s["name"]) != 1:
            continue
        iguais = [k for k in chaves if k.split(SEP, 1)[1] == s["name"] and k not in ligadas]
        if iguais and len({k.split(SEP, 1)[1] for k in iguais}) == 1:
            s["ci"] = sorted(iguais)  # o mesmo passo em duas rotinas: vale a execução mais nova
            ligadas.update(iguais)


def fundir(base, novo, hoje=None):
    """Atualiza em `base` só o que a execução diz: tempo, resultado e replay. Cartões, fluxos, casos, falhas, registros,
    setas e limites ficam como estão. Devolve (descrição, passos do GitHub que não têm lugar no quadro)."""
    spec = json.loads(json.dumps(base))
    medidos = {k: s for s in etapas_de(novo) for k in s["ci"]}
    ligar_pelo_nome(spec, medidos)
    origem = novo["source"]["runs"]
    for s in etapas_de(spec):
        chaves = s.get("ci", [])
        achadas = [k for k in chaves if k in medidos]
        resto = [m for m in s.get("metrics", []) if not m.get("auto")]
        if achadas:
            rotina = max({k.split(SEP, 1)[0] for k in achadas}, key=lambda n: origem[n]["at"])
            dela = [medidos[k] for k in achadas if k.split(SEP, 1)[0] == rotina]
            tempo = sum(m["seconds"] or 0 for m in dela)
            ruim = any(m["status"] == "failed" for m in dela)
            s["seconds"], s["status"] = tempo, "failed" if ruim else None
            s["metrics"] = [{"auto": True, "when": f"execução de {origem[rotina]['date']} · {rotina}",
                             "values": [[f"{tempo:.0f} s", "duração"], ["falhou" if ruim else "sem erro", "resultado"]]}] + resto
            anotacao = sem_aviso(s.get("meta"))
            if anotacao:
                s["meta"] = anotacao
            else:
                s.pop("meta", None)
        elif any(k.split(SEP, 1)[0] in origem for k in chaves):  # a rotina dela foi lida e o passo não veio
            s.pop("seconds", None)
            s["status"], s["meta"] = None, " · ".join(x for x in (NAO_RODOU, sem_aviso(s.get("meta"))) if x)
            s["metrics"] = resto
    dono = {}
    for s in etapas_de(spec):
        for k in s.get("ci", []):
            dono.setdefault(k, s["id"])
    de_novo = {s["id"]: dono.get(s["ci"][0]) for s in etapas_de(novo)}
    nomes = {s["id"]: s["name"] for s in etapas_de(spec)}
    replays = []
    for r in novo.get("runs", []):
        tempos = {}
        for sid, passo in ((i, next(s for s in etapas_de(novo) if s["id"] == i)) for i in r["steps"]):
            if de_novo[sid]:
                tempos[de_novo[sid]] = tempos.get(de_novo[sid], 0) + (passo["seconds"] or 0)
        if not tempos:
            continue
        quebrou = de_novo.get(r["breakAt"]) if r.get("breakAt") else None
        nota = f"Quebrou em “{nomes[quebrou]}”." if quebrou else ("Quebrou num passo que não está no quadro." if r.get("breakAt") else "Terminou sem erro.")
        replays.append({"label": r["label"], "auto": r["auto"], "steps": list(tempos), "seconds": list(tempos.values()), "breakAt": quebrou, "note": nota})
    spec["runs"] = replays + [r for r in spec.get("runs", []) if r.get("auto") not in origem]
    for c in spec["cards"]:
        quebrado = any(s.get("status") == "failed" for s in c["steps"])
        if quebrado and not c.get("tone"):
            c["tone"], c["toneAuto"] = "warn", True
        elif not quebrado and c.pop("toneAuto", False):
            c["tone"] = ""
    spec["source"] = {"repo": novo["source"]["repo"], "runs": {**spec.get("source", {}).get("runs", {}), **origem}}
    spec["generated"] = (hoje or datetime.date.today()).isoformat()
    return spec, sorted(k for k in medidos if k not in dono)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="dono/repositorio")
    p.add_argument("-o", "--saida", default="spec.json")
    p.add_argument("--workflow", help="só esta rotina (nome exato)")
    p.add_argument("--runs", type=int, default=30, help="quantas execuções recentes olhar (até 100)")
    p.add_argument("--merge", help="quadro já escrito: atualiza só tempos, resultados e replays, preservando o resto")
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
    sem_lugar = []
    if a.merge:
        try:
            spec, sem_lugar = fundir(json.loads(pathlib.Path(a.merge).read_text()), spec)
        except (OSError, ValueError, KeyError) as erro:
            sys.exit(f"Não consegui juntar com {a.merge}: {erro}")
    pathlib.Path(a.saida).write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    if a.merge:
        print(f"{a.saida}: atualizado. {len(sem_lugar)} passos do GitHub sem lugar no quadro" + (":" if sem_lugar else "."))
        for k in sem_lugar:
            print("  " + k)
        return
    print(f"{a.saida}: {len(spec['cards'])} cartões, {sum(len(c['steps']) for c in spec['cards'])} etapas. Falta preencher fluxo, entradas, saídas e casos a partir do código.")


if __name__ == "__main__":
    main()
