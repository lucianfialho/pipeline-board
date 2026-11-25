#!/usr/bin/env python3
"""Monta o quadro: um HTML único e autocontido a partir de um arquivo de descrição (references/spec.md).

  python3 build.py spec.json -o board.html

Só usa a biblioteca padrão. Recusa descrição incoerente (etapa repetida, seta para cartão que não existe, execução que
cita etapa desconhecida) em vez de gerar um quadro que mente por omissão.
"""
import argparse
import base64
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def conferir(spec):
    """Lista de problemas na descrição. Vazia quer dizer que dá para montar."""
    erros, cartoes, etapas = [], [], []
    if not isinstance(spec, dict) or not isinstance(spec.get("cards"), list) or not spec["cards"]:
        return ["a descrição precisa de 'cards', uma lista não vazia"]
    for c in spec["cards"]:
        if not c.get("id") or not c.get("title") or not isinstance(c.get("steps"), list):
            erros.append(f"cartão sem id, title ou steps: {str(c)[:80]}")
            continue
        cartoes.append(c["id"])
        for s in c["steps"]:
            if not s.get("id") or not s.get("name"):
                erros.append(f"etapa sem id ou name no cartão {c['id']}")
                continue
            etapas.append(s["id"])
    for nome, ids in (("cartão", cartoes), ("etapa", etapas)):
        erros += [f"{nome} com id repetido: {i}" for i in sorted({x for x in ids if ids.count(x) > 1})]
    for e in spec.get("edges", []):
        erros += [f"seta para cartão que não existe: {i}" for i in e[:2] if i not in cartoes]
    for r in spec.get("runs", []):
        if not r.get("label") or not isinstance(r.get("steps"), list):
            erros.append("execução sem label ou steps")
            continue
        erros += [f"execução '{r['label']}' cita etapa que não existe: {i}" for i in r["steps"] + ([r["breakAt"]] if r.get("breakAt") else []) if i not in etapas]
        if r.get("seconds") and len(r["seconds"]) != len(r["steps"]):
            erros.append(f"execução '{r['label']}': 'seconds' precisa ter um valor por etapa")
    return erros


def seguro(dado):
    """JSON que pode ir dentro de <script>: um '</script>' vindo de um log não fecha a página."""
    return json.dumps(dado, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def montar(spec, raiz=RAIZ, artefato=False):
    erros = conferir(spec)
    if erros:
        raise ValueError("\n".join(erros))
    icones = {p.stem: "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode() for p in sorted((raiz / "assets" / "icons").glob("*.svg"))}
    usados = {s.get("icon") for c in spec["cards"] for s in c["steps"]} | {"file"}
    js = (raiz / "assets" / "board.js").read_text()
    # os ícones entram antes: assim um texto da descrição nunca é tratado como marcador
    js = js.replace("__ICONS__", seguro({k: v for k, v in icones.items() if k in usados}), 1).replace("__SPEC__", seguro(spec), 1)
    titulo = str(spec.get("title") or "Pipeline").replace("&", "&amp;").replace("<", "&lt;")
    estilo = (raiz / "assets" / "board.css").read_text()
    if artefato:
        # a ferramenta de artefatos do Claude embrulha a página: vai só o conteúdo, com título e estilo no topo
        return f'<title>{titulo}</title>\n<style>\n{estilo}</style>\n<script>\n{js}</script>\n'
    return (f'<!doctype html>\n<html lang="{ "en" if spec.get("lang") == "en" else "pt-BR"}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{titulo}</title>\n'
            f'<style>\n{estilo}</style></head>\n<body>\n<script>\n{js}</script>\n</body></html>\n')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec")
    p.add_argument("-o", "--saida", default="board.html")
    p.add_argument("--artifact", action="store_true", help="formato para publicar como artefato do Claude")
    a = p.parse_args(argv)
    try:
        spec = json.loads(pathlib.Path(a.spec).read_text())
        html = montar(spec, artefato=a.artifact)
    except (OSError, ValueError) as erro:
        sys.exit(f"Não montei o quadro:\n{erro}")
    pathlib.Path(a.saida).write_text(html)
    n = sum(len(c["steps"]) for c in spec["cards"])
    print(f"{a.saida}: {len(spec['cards'])} cartões, {n} etapas, {len(spec.get('runs', []))} execuções, {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
