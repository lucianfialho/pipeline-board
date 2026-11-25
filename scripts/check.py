#!/usr/bin/env python3
"""Procura, na descrição do quadro, o que não deveria sair da máquina. Rode antes de publicar.

  python3 check.py spec.json

Sai com erro se achar chave, token, referência de cofre, e-mail ou caminho de pasta pessoal. Não é auditoria completa:
nomes de pessoas, de clientes e detalhes internos só uma leitura humana pega.
"""
import json
import pathlib
import re
import sys

PADROES = {
    "chave ou token": r"\b(sk-[A-Za-z0-9_-]*?[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,})",
    "token em cabeçalho": r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}",
    "chave privada": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "endereço com senha": r"[a-z][a-z0-9+.-]*://[^/\s:\"]+:[^@\s\"]+@",
    "referência de cofre": r"op://[^\s\"]+",
    # "logo@2x.png" é nome de imagem, não e-mail
    "e-mail": r"[A-Za-z0-9._%+-]+@(?!\dx\.(?:png|jpe?g|webp|gif|svg)\b)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+",
    # "site.br/modulo/home/index.php" é endereço, não pasta: antes da barra não pode vir letra nem número
    "pasta pessoal": r"(?<![A-Za-z0-9])(/Users|/home)/[A-Za-z0-9._-]+",
}


def procurar(texto):
    """[(tipo, trecho encurtado)] sem repetir. O trecho vai cortado para o relatório não repetir o segredo."""
    achados = []
    for tipo, padrao in PADROES.items():
        for m in re.finditer(padrao, texto):
            item = (tipo, m.group(0)[:6] + "…")
            if item not in achados:
                achados.append(item)
    return achados


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        sys.exit("uso: check.py spec.json")
    achados = procurar(json.dumps(json.loads(pathlib.Path(args[0]).read_text()), ensure_ascii=False))
    for tipo, trecho in achados:
        print(f"ACHEI {tipo}: começa com {trecho}")
    if achados:
        sys.exit(1)
    print("nada nos padrões conferidos. Leia a descrição antes de publicar: nomes e detalhes internos não são detectados.")


if __name__ == "__main__":
    main()
