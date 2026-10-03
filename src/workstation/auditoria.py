"""Auditoria de conteudo dos scripts PowerShell do projeto.
Content audit for the project's PowerShell scripts.

Os testes nao executam os scripts (cada um exigiria Windows); eles auditam
as regras de seguranca estaticas que so podem ser checadas lendo o texto:
SupportsShouldProcess, o switch -Executar, o uso de $PSCmdlet.ShouldProcess
por acao, e a ausencia de Remove-Item -Recurse -Force sem guarda, de CMD
executando curl|iex, e de nome real de fabricante.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "SCRIPTS_OBRIGATORIOS",
    "FABRICANTES_PROIBIDOS",
    "auditar_script",
    "auditar_diretorio",
]

SCRIPTS_OBRIGATORIOS = (
    "Instalar-Workstation.ps1",
    "Configurar-Rede.ps1",
    "Configurar-Impressoras.ps1",
    "Instalar-Software.ps1",
    "Aplicar-Politicas.ps1",
    "Verificar-Workstation.ps1",
)

# Nomes reais de fabricante/produto que nao podem aparecer em linha de
# codigo dos scripts (comentarios ficam de fora da checagem).
# Real vendor/product names that must not appear in code lines.
FABRICANTES_PROIBIDOS = (
    "adobe",
    "oracle",
    "sap",
    "canon",
    "epson",
    "brother",
    "lexmark",
    "ricoh",
    "xerox",
    "skype",
    "chrome",
    "firefox",
    "photoshop",
)

_RE_REMOVE_PERIGOSO = re.compile(r"Remove-Item\b.*-Recurse.*-Force", re.IGNORECASE)
_RE_GUARDA_IF = re.compile(r"\bif\s*\(", re.IGNORECASE)


def _dentro_de_if(linhas: list[str], indice: int) -> bool:
    """Diz se a linha 'indice' fica dentro de um bloco 'if ( ... )'.
    Say whether the line sits inside an 'if (...) { }' block.
    Regra: sobe ate a linha mais proxima que abriu um bloco que ainda esta
    aberto na linha dada; se essa linha tem 'if (' conta como guarda.
    Presupoe chaves bem formadas (um bloco por linha), o que vale para os
    scripts deste repositorio."""
    if _RE_GUARDA_IF.search(linhas[indice]):
        return True
    diferenca = 0
    for j in range(indice - 1, -1, -1):
        diferenca += linhas[j].count("{") - linhas[j].count("}")
        if diferenca > 0:
            return bool(_RE_GUARDA_IF.search(linhas[j]))
    return False
_RE_CURL_PIPE = re.compile(r"\bcurl\b.*\|\s*(iex|powershell|pwsh)\b", re.IGNORECASE)
_RE_CMD = re.compile(r"\bcmd(\.exe)?\b", re.IGNORECASE)
_RE_BAIXADA = re.compile(
    r"\b(curl|wget)\b|\biex\b|Invoke-WebRequest|Invoke-RestMethod",
    re.IGNORECASE,
)


def _fabricante_na_linha(linha: str) -> str | None:
    """Retorna o nome de fabricante presente, ou None.
    Return the vendor name found on the line, or None."""
    for nome in FABRICANTES_PROIBIDOS:
        if re.search(rf"\b{re.escape(nome)}\b", linha, re.IGNORECASE):
            return nome
    return None


def auditar_script(nome: str, texto: str) -> list[str]:
    """Audita um script PowerShell e lista as violacoes.
    Audit one PowerShell script and list the violations (empty = ok)."""
    erros: list[str] = []
    if "SupportsShouldProcess" not in texto:
        erros.append(
            f"{nome}: falta SupportsShouldProcess=$true no CmdletBinding"
        )
    if "$PSCmdlet.ShouldProcess" not in texto:
        erros.append(f"{nome}: nenhuma acao usa $PSCmdlet.ShouldProcess")
    if not re.search(r"\[switch\]\s*\$Executar", texto):
        erros.append(f"{nome}: falta o parametro [switch]$Executar")
    linhas = texto.splitlines()
    for numero, linha in enumerate(linhas):
        s = linha.strip()
        if not s or s.startswith("#") or s.startswith("<#"):
            continue
        if _RE_REMOVE_PERIGOSO.search(s) and not _dentro_de_if(linhas, numero):
            erros.append(
                f"{nome}:{numero}: Remove-Item -Recurse -Force sem guarda de if"
            )
        if _RE_CURL_PIPE.search(s):
            erros.append(
                f"{nome}:{numero}: pipe de curl para interpretador de comandos"
            )
        if _RE_CMD.search(s) and _RE_BAIXADA.search(s):
            erros.append(
                f"{nome}:{numero}: CMD executando download ou execucao remota"
            )
        fabricante = _fabricante_na_linha(s)
        if fabricante is not None:
            erros.append(
                f"{nome}:{numero}: nome real de fabricante '{fabricante}' "
                "presente"
            )
    return erros


def auditar_diretorio(diretorio: object) -> dict:
    """Audita os scripts obrigatorios de um diretorio.
    Audit the required scripts of a directory.
    Retorna {'erros': list, 'presentes': int, 'ok': bool}."""
    erros: list[str] = []
    presentes = 0
    for nome in SCRIPTS_OBRIGATORIOS:
        caminho = Path(diretorio) / nome
        if not caminho.is_file():
            erros.append(f"{nome}: arquivo ausente")
            continue
        presentes += 1
        erros.extend(auditar_script(nome, caminho.read_text(encoding="utf-8")))
    return {"erros": erros, "presentes": presentes, "ok": not erros}
