#!/usr/bin/env python3
"""Conta o que há nos arquivos JSON e JSONL do projeto e aponta tamanhos redondos, que costumam ser corte.

  python3 profile.py pasta [pasta...]

Só leitura. Mostra caminhos de campos, números e o dono que aparece no id, nunca o resto dos registros. Tamanho redondo é indício, não prova.
"""
import collections
import json
import pathlib
import re
import sys

REDONDOS = {100, 200, 250, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000}
MAX_BYTES = 60_000_000


def listas(valor, caminho=""):
    """(caminho genérico, tamanho, chave de origem) de cada lista. A chave de um mapa grande vira '*'."""
    if isinstance(valor, list):
        yield caminho or "(raiz)", len(valor), None
        for x in valor:
            if isinstance(x, (dict, list)):
                yield from listas(x, caminho + "[]")
    elif isinstance(valor, dict):
        mapa = len(valor) > 30 and all(isinstance(v, (dict, list)) for v in valor.values())
        for k, v in valor.items():
            for c, n, origem in listas(v, f"{caminho}.{'*' if mapa else k}"):
                yield c, n, origem or (k if mapa else None)


def por_origem(itens):
    """Itens com id 'dono/nome', contados por dono: o corte é por consulta, e uma soma de donos o esconde."""
    donos = [x["id"].split("/")[0] for x in itens if isinstance(x, dict) and isinstance(x.get("id"), str) and "/" in x["id"]]
    return collections.Counter(donos)


def nome_seguro(dono):
    """O dono vem do id público da conta; corta o que não parece nome, para um dado estranho não virar texto na saída."""
    return dono if re.fullmatch(r"[\w.-]{1,60}", dono) else "(dono com nome incomum)"


def analisar(dado):
    achados, tamanhos = [], collections.defaultdict(list)

    def andar(v, onde):
        if isinstance(v, list):
            for dono, n in por_origem(v).items():
                if n in REDONDOS:
                    achados.append(f"{onde}: {n} itens de '{nome_seguro(dono)}' (tamanho redondo)")
            for x in v:
                if isinstance(x, (dict, list)):
                    andar(x, onde + "[]")
        elif isinstance(v, dict):
            mapa = len(v) > 30 and all(isinstance(x, (dict, list)) for x in v.values())
            for k, x in v.items():
                andar(x, f"{onde}.{'*' if mapa else k}")

    andar(dado, "")
    for caminho, n, _ in listas(dado):
        tamanhos[caminho].append(n)
    for caminho, ns in tamanhos.items():
        contagem = collections.Counter(ns)
        maior = max(ns)
        if maior in REDONDOS:
            achados.append(f"{caminho}: o maior tamanho é {maior}, em {contagem[maior]} de {len(ns)} listas")
    return sorted(collections.Counter(achados).items()), {c: (len(n), min(n), max(n)) for c, n in tamanhos.items()}


def ler(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    if arquivo.suffix == ".jsonl":
        return [json.loads(l) for l in texto.splitlines() if l.strip()]
    return json.loads(texto)


def main(argv=None):
    pastas = sys.argv[1:] if argv is None else argv
    if not pastas:
        sys.exit("uso: profile.py pasta [pasta...]")
    arquivos = sorted({a for p in pastas for a in pathlib.Path(p).rglob("*") if a.suffix in (".json", ".jsonl") and "node_modules" not in a.parts and not a.is_symlink()})
    for arq in arquivos:
        try:
            if arq.stat().st_size > MAX_BYTES:
                print(f"{arq}: grande demais, não li")
                continue
            dado = ler(arq)
        except (OSError, ValueError):
            print(f"{arq}: não consegui ler")
            continue
        achados, _ = analisar(dado)
        registros = f", {len(dado)} registros" if isinstance(dado, list) else ""
        print(f"{arq} ({arq.stat().st_size // 1024} KB{registros})")
        for texto, vezes in achados[:15]:
            print(f"  ! {texto}" + (f" [x{vezes}]" if vezes > 1 else ""))


if __name__ == "__main__":
    main()
