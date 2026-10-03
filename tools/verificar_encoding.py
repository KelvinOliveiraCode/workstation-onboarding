"""Verifica BOM, CJK e U+FFFD nos arquivos de texto do projeto.
Checks for BOM, CJK ranges, and U+FFFD in the project's text files.

Uso:
    python tools/verificar_encoding.py [diretorio]

Sem diretorio, varre a raiz do repositorio. Sai com 0 quando tudo e limpo
e 1 quando encontra problema. Esta e a checagem de encoding que o projeto
roda antes de cada commit (o CI nao a cobre).
"""

from __future__ import annotations

import sys
from pathlib import Path

EXTENSOES = (".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".ps1")


def raiz_projeto() -> Path:
    """Raiz do repositorio.
    Repository root."""
    return Path(__file__).resolve().parents[1]


def checar_arquivo(caminho: Path) -> list[str]:
    """Retorna os problemas de encoding de um arquivo.
    Return the encoding problems of one file (empty = clean)."""
    problemas = []
    bruto = caminho.read_bytes()
    if len(bruto) >= 3 and bruto[0:3] == b"\xef\xbb\xbf":
        problemas.append("BOM UTF-8 presente")
    texto = bruto.decode("utf-8", errors="replace")
    for char in texto:
        codigo = ord(char)
        if 0x3000 <= codigo <= 0x9FFF:
            problemas.append(
                f"CJK: U+{codigo:04X} (possivel corrupcao de encoding)"
            )
            break
        if codigo == 0xFFFD:
            problemas.append("U+FFFD (substitucao de caractere invalido)")
            break
    return problemas


def main() -> int:
    """Varre os arquivos e imprime os problemas.
    Scan the files and print the problems. Retorna 0 se tudo e limpo."""
    alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else raiz_projeto()
    if not alvo.is_dir():
        print(f"diretorio nao encontrado: {alvo.name}")
        return 1
    problemas_total = 0
    verificados = 0
    for caminho in sorted(alvo.rglob("*")):
        if caminho.name.startswith(".git") or caminho.is_dir():
            continue
        if caminho.suffix.lower() not in EXTENSOES:
            continue
        verificados += 1
        for problema in checar_arquivo(caminho):
            problemas_total += 1
            relativo = caminho.relative_to(alvo)
            print(f"[ERRO] {relativo}: {problema}")
    print(f"verificados: {verificados} arquivo(s)")
    if problemas_total == 0:
        print("encoding limpo: sem BOM, sem CJK, sem U+FFFD")
        return 0
    print(f"problemas: {problemas_total}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
