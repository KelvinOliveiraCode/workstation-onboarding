"""CLI de validacao: confere config/ e os scripts PowerShell.
Validation CLI: checks config/ and the PowerShell scripts.

Uso:
    python -m workstation verificar [diretorio-config]
    python -m workstation auditoria [diretorio-scripts]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .auditoria import SCRIPTS_OBRIGATORIOS, auditar_diretorio
from .schema import POLITICAS_OBRIGATORIAS, validar_configuracoes


def _raiz_projeto() -> Path:
    """Raiz do repositorio (dois niveis acima de src/workstation).
    Repository root (two levels above src/workstation)."""
    return Path(__file__).resolve().parents[2]


def _verificar(diretorio: Path) -> int:
    """Valida os arquivos de configuracao e imprime o relatorio.
    Validate the config files and print the report."""
    resultado = validar_configuracoes(diretorio)
    resumo = resultado["resumo"]
    print("workstation-onboarding: validacao de configuracao")
    if not resultado["erros"]:
        print(
            f"[ OK ] dicionario-software.yaml: {resumo['pacotes']} pacotes"
        )
        print(f"[ OK ] perfis-usuario.yaml: {resumo['perfis']} perfis")
        print(
            f"[ OK ] politicas.json: "
            f"{resumo['politicas']}/{len(POLITICAS_OBRIGATORIAS)} politicas"
        )
        print(
            "[ OK ] coerencia: todos os pacotes referenciados existem "
            "no dicionario"
        )
    for erro in resultado["erros"]:
        print(f"[ ERRO] {erro}")
    print(
        "RESUMO: "
        f"{len(resultado['erros'])} erro(s) | "
        f"pacotes={resumo['pacotes']} perfis={resumo['perfis']} "
        f"politicas={resumo['politicas']}"
    )
    return 0 if resultado["ok"] else 1


def _auditoria(diretorio: Path) -> int:
    """Audita os scripts obrigatorios e imprime o relatorio.
    Audit the required scripts and print the report."""
    resultado = auditar_diretorio(diretorio)
    print("workstation-onboarding: auditoria de scripts")
    erros_por_script = {nome: [] for nome in SCRIPTS_OBRIGATORIOS}
    for erro in resultado["erros"]:
        chave = erro.split(":", 1)[0]
        if chave in erros_por_script:
            erros_por_script[chave].append(erro)
        else:
            print(f"[ ERRO] {erro}")
    for nome in SCRIPTS_OBRIGATORIOS:
        if erros_por_script[nome]:
            print(f"[ ERRO ] {nome}")
            for erro in erros_por_script[nome]:
                print(f"         {erro}")
        else:
            print(f"[ OK ] {nome}")
    print(
        "RESUMO: "
        f"{resultado['presentes']}/{len(SCRIPTS_OBRIGATORIOS)} scripts "
        f"presentes, {len(resultado['erros'])} violacao(oes)"
    )
    return 0 if resultado["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.
    CLI entry point. Retorna o codigo de saida (0 = ok)."""
    parser = argparse.ArgumentParser(
        prog="workstation",
        description=(
            "Valida a configuracao e os scripts do onboarding de estacao."
        ),
    )
    parser.add_argument(
        "comando",
        choices=("verificar", "auditoria"),
        help=(
            "verificar: confere config/; auditoria: confere scripts/"
        ),
    )
    parser.add_argument(
        "diretorio",
        nargs="?",
        default=None,
        help=(
            "diretorio alternativo (padrao: config/ ou scripts/ da raiz "
            "do projeto)"
        ),
    )
    args = parser.parse_args(argv)
    raiz = _raiz_projeto()
    diretorio = Path(args.diretorio) if args.diretorio else (
        raiz / "config" if args.comando == "verificar" else raiz / "scripts"
    )
    if args.comando == "verificar":
        return _verificar(diretorio)
    return _auditoria(diretorio)


if __name__ == "__main__":
    raise SystemExit(main())
