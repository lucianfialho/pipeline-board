#!/usr/bin/env python3
"""Cronometra qualquer comando e transforma o registro no quadro. Serve para cron, Makefile, scripts e qualquer CI.

  python3 trace.py run "baixar dados" [--group "Coleta"] -- python3 baixar.py
  python3 trace.py spec trace.jsonl -o spec.json [--merge spec.json] [--title nome]

`run` repassa a saída e o código de saída do comando e anota só: execução, grupo, nome, início, duração e código.
Os argumentos e a saída do comando NÃO são gravados, porque podem ter segredo.
Passos com o mesmo PIPELINE_RUN são a mesma execução; sem a variável, vale o dia.
O arquivo é PIPELINE_TRACE, ou trace.jsonl na pasta atual.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

GRUPO = "Etapas"
LIDO = "lido no código"


def anotar(arquivo, registro):
    # uma escrita só, em modo de acréscimo: etapas paralelas não se misturam na mesma linha
    with open(arquivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def rodar(nome, comando, grupo=GRUPO, arquivo=None, execucao=None):
    arquivo = arquivo or os.environ.get("PIPELINE_TRACE") or "trace.jsonl"
    inicio = datetime.datetime.now(datetime.timezone.utc)
    execucao = execucao or os.environ.get("PIPELINE_RUN") or inicio.astimezone().date().isoformat()
    relogio, codigo = time.monotonic(), 130
    try:
        codigo = subprocess.run(comando).returncode
        if codigo < 0:  # morto por sinal: mesma convenção do shell
            codigo = 128 - codigo
    except FileNotFoundError:
        print(f"trace: comando não encontrado: {comando[0]}", file=sys.stderr)
        codigo = 127
    except PermissionError:
        print(f"trace: sem permissão para executar: {comando[0]}", file=sys.stderr)
        codigo = 126
    finally:
        # grava também quando interrompem a execução; se o registro falhar, o resultado do comando não muda
        try:
            anotar(arquivo, {"run": execucao, "group": grupo, "name": nome, "start": inicio.isoformat(), "seconds": round(time.monotonic() - relogio, 3), "exit": codigo})
        except OSError as erro:
            print(f"trace: não consegui gravar em {arquivo}: {erro}", file=sys.stderr)
    return codigo


def ler(texto):
    """Registros válidos e quantas linhas foram ignoradas (uma escrita cortada não derruba o resto)."""
    bons, ruins = [], 0
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        try:
            r = json.loads(linha)
            bons.append({"run": str(r["run"]), "group": str(r.get("group") or GRUPO), "name": str(r["name"]), "start": str(r["start"]), "seconds": float(r["seconds"]), "exit": int(r["exit"])})
        except (ValueError, KeyError, TypeError, AttributeError):
            ruins += 1
    return sorted(bons, key=lambda r: r["start"]), ruins


def slug(texto, usados):
    base = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:40] or "etapa"
    nome, n = base, 2
    while nome in usados:
        nome, n = f"{base}-{n}", n + 1
    usados.add(nome)
    return nome


def execucoes(registros):
    """{execução: {(grupo, nome): resumo}}, na ordem em que apareceram. Repetição soma o tempo; vale o último resultado."""
    saida = {}
    for r in registros:
        etapa = saida.setdefault(r["run"], {}).setdefault((r["group"], r["name"]), {"seconds": 0.0, "tries": 0})
        etapa["seconds"] = round(etapa["seconds"] + r["seconds"], 3)
        etapa["tries"] += 1
        etapa["exit"] = r["exit"]
    return saida


def montar_spec(registros, base=None, titulo=None, hoje=None):
    """Sem `base`, um cartão por grupo. Com `base` (descrição já escrita), só acrescenta tempos e execuções."""
    if not registros:
        raise ValueError("o registro não tem nenhuma etapa")
    spec = json.loads(json.dumps(base)) if base else {"title": titulo or "pipeline", "subtitle": "tempos gravados com trace.py", "cards": [], "edges": []}
    if titulo:
        spec["title"] = titulo
    cartoes = spec.setdefault("cards", [])
    usados = {c["id"] for c in cartoes} | {s["id"] for c in cartoes for s in c["steps"]}
    todas, ids, novos = execucoes(registros), {}, []
    ultima = {}  # (grupo, nome) -> (execução, resumo) mais recente
    for nome_exec, etapas in todas.items():
        for chave, resumo in etapas.items():
            ultima[chave] = (nome_exec, resumo)
    escritas = {s["id"] for c in cartoes for s in c["steps"]}  # as que já vieram prontas em `base`
    nomes_gravados = [nome for _, nome in ultima]
    for (grupo, nome), (nome_exec, resumo) in ultima.items():
        iguais = [(c, s) for c in cartoes for s in c["steps"] if s["id"] in escritas and nome in (s["name"], s["id"])]
        do_grupo = [(c, s) for c, s in iguais if grupo in (c["title"], c["id"])]
        # só pelo nome, quando não há dúvida: uma etapa escrita e um grupo gravado com esse nome
        achou = do_grupo or (iguais if len(iguais) == 1 and nomes_gravados.count(nome) == 1 else [])
        if achou:
            etapa = achou[0][1]
        else:
            cartao = next((c for c in cartoes if grupo in (c["title"], c["id"])), None)
            if not cartao:
                cartao = {"id": slug("c-" + grupo, usados), "title": grupo, "steps": []}
                cartoes.append(cartao)
                novos.append(cartao)
            etapa = {"id": slug(nome, usados), "name": nome, "icon": "file"}
            cartao["steps"].append(etapa)
        ids[(grupo, nome)] = etapa["id"]
        falhou = resumo["exit"] != 0
        etapa["seconds"] = resumo["seconds"]
        etapa["status"] = "failed" if falhou else None
        if etapa.get("meta") == LIDO:
            del etapa["meta"]
        medida = {"when": f"medido com trace.py · execução {nome_exec}", "values": [[f"{resumo['seconds']:.1f} s", "duração"], [str(resumo["exit"]), "código de saída"]]}
        if resumo["tries"] > 1:
            medida["note"] = f"{resumo['tries']} tentativas: o tempo é a soma e o código é o da última."
        etapa["metrics"] = [medida] + [m for m in etapa.get("metrics", []) if not str(m.get("when", "")).startswith("medido com trace.py")]
    if not base:
        spec["edges"] = [[a["id"], b["id"], ""] for a, b in zip(cartoes, cartoes[1:])]
    for c in cartoes:
        if c in novos:
            c["width"] = 560 if len(c["steps"]) > 6 else 320
        c["tone"] = "warn" if any(s.get("status") == "failed" for s in c["steps"]) else ""
    nomes = {s["id"]: s["name"] for c in cartoes for s in c["steps"]}
    corridas = []
    for nome_exec, etapas in reversed(list(todas.items())[-4:]):
        passos = [ids[chave] for chave in etapas]
        quebrou = next((ids[chave] for chave, r in etapas.items() if r["exit"] != 0), None)
        corridas.append({"label": nome_exec, "steps": passos, "seconds": [r["seconds"] for r in etapas.values()], "breakAt": None,
                         "note": f"Falhou em “{nomes[quebrou]}”." if quebrou else "Nenhuma etapa gravada falhou."})
        # o replay para no erro só quando nada rodou depois dele; senão a execução seguiu e a nota registra a falha
        if quebrou and passos[-1] == quebrou:
            corridas[-1]["breakAt"] = quebrou
    spec["runs"] = corridas
    spec["generated"] = (hoje or datetime.date.today()).isoformat()
    return spec


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    comando = []
    if "--" in argv:  # tudo depois de -- é do comando, inclusive opções com o mesmo nome das nossas
        i = argv.index("--")
        argv, comando = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="acao", required=True)
    r = sub.add_parser("run", help="roda e cronometra um comando")
    r.add_argument("nome")
    r.add_argument("--group", default=GRUPO)
    r.add_argument("--trace")
    r.add_argument("--run-id")
    s = sub.add_parser("spec", help="transforma o registro na descrição do quadro")
    s.add_argument("registro")
    s.add_argument("-o", "--saida", default="spec.json")
    s.add_argument("--merge", help="descrição já escrita, que recebe os tempos")
    s.add_argument("--title")
    a = p.parse_args(argv)
    if a.acao == "run":
        if not comando:
            p.error("faltou o comando depois de --")
        sys.exit(rodar(a.nome, comando, a.group, a.trace, a.run_id))
    try:
        registros, ruins = ler(pathlib.Path(a.registro).read_text(encoding="utf-8"))
        base = json.loads(pathlib.Path(a.merge).read_text()) if a.merge else None
        spec = montar_spec(registros, base, a.title)
    except (OSError, ValueError) as erro:
        sys.exit(f"Não montei a descrição: {erro}")
    pathlib.Path(a.saida).write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(f"{a.saida}: {sum(len(c['steps']) for c in spec['cards'])} etapas, {len(spec['runs'])} execuções" + (f". Ignorei {ruins} linhas ilegíveis." if ruins else ""))


if __name__ == "__main__":
    main()
