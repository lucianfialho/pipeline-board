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
import re
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
    erros += conferir_falhas(spec.get("findings", []), etapas)
    erros += conferir_extras(spec)
    return erros


def conferir_extras(spec):
    erros = []
    cat = spec.get("catalog")
    if cat is not None:
        itens = cat.get("items") if isinstance(cat, dict) else None
        if not isinstance(itens, list) or not all(isinstance(i, list) and len(i) in (4, 5) and all(isinstance(x, str) for x in i) for i in itens):
            erros.append("catalog.items precisa ser uma lista de [tipo, dono, id do dono, valor, endereço opcional], tudo texto")
        form = cat.get("form") if isinstance(cat, dict) else None
        if form and not (re.fullmatch(r"[\w.-]+/[\w.-]+", str(form.get("repo", ""))) and isinstance(form.get("types"), dict) and form["types"]
                         and all(isinstance(v, list) and v for v in form["types"].values())):
            erros.append("catalog.form precisa de 'repo' (dono/nome) e 'types' {tipo: [rótulo, exemplo]}")
    for nome, dado in (spec.get("icons") or {}).items():
        if not re.fullmatch(r"data:image/(svg\+xml|png);base64,[A-Za-z0-9+/=]+", str(dado)):
            erros.append(f"ícone '{nome}': use data:image/svg+xml;base64 ou data:image/png;base64")
    return erros


SITUACOES, GRAVIDADES = ("confirmed", "suspected"), ("high", "medium", "low")


def conferir_falhas(falhas, etapas):
    erros = []
    for f in falhas:
        nome = f.get("title")
        if not nome:
            erros.append("falha sem title")
            continue
        if f.get("status") not in SITUACOES:
            erros.append(f"falha '{nome}': status precisa ser {' ou '.join(SITUACOES)}")
        if f.get("severity") not in GRAVIDADES:
            erros.append(f"falha '{nome}': severity precisa ser {', '.join(GRAVIDADES)}")
        if f.get("step") and f["step"] not in etapas:
            erros.append(f"falha '{nome}' cita etapa que não existe: {f['step']}")
        if f.get("status") == "confirmed" and not str(f.get("evidence") or "").strip():
            erros.append(f"falha '{nome}': 'confirmed' exige 'evidence' (o que foi visto e onde). Sem isso é 'suspected'")
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
    icones.update(spec.get("icons") or {})
    spec = {k: v for k, v in spec.items() if k != "icons"}
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
