"""Roda os gates de aceite do projeto e resume o resultado.
Runs the project acceptance gates and summarizes the results.

Uso:
    python tools/verificar_aceite.py

Os gates sao exatamente os do GATE FINAL do repositorio: pytest -v,
cobertura, Verificar-Workstation.ps1 (leitura) e
Instalar-Workstation.ps1 (dry-run, nao pode alterar nada). Sai com 0
so quando todos passam.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASS = "PASS"
FAIL = "FAIL"


def rodar(rotulo: str, comando: list[str], timeout: int = 300) -> tuple[str, str]:
    """Executa um comando e devolve (PASS/FAIL, saida).
    Run one command, return (PASS/FAIL, output)."""
    try:
        processo = subprocess.run(
            comando,
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return FAIL, f"timeout apos {timeout}s: {exc}"
    saida = (processo.stdout or "") + (processo.stderr or "")
    status = PASS if processo.returncode == 0 else FAIL
    return status, saida


def ultima_linha_nao_vazia(saida: str) -> str:
    for linha in reversed(saida.splitlines()):
        if linha.strip():
            return linha.strip()
    return ""


def main() -> int:
    """Roda os quatro gates e imprime o resumo.
    Run the four gates and print the summary. 0 = todos passaram."""
    print(f"gates de aceite em: {RAIZ}")
    gates: list[tuple[str, list[str]]] = [
        (
            "testes (pytest -v)",
            [sys.executable, "-m", "pytest", "tests/", "-v"],
        ),
        (
            "cobertura (--cov=workstation)",
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=workstation",
                "--cov-report=term-missing",
            ],
        ),
        (
            "verificacao da estacao (read-only)",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts\\Verificar-Workstation.ps1",
            ],
        ),
        (
            "instalador em dry-run (nao altera nada)",
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts\\Instalar-Workstation.ps1",
            ],
        ),
    ]
    falhas = 0
    for rotulo, comando in gates:
        status, saida = rodar(rotulo, comando)
        if status == FAIL:
            falhas += 1
        print(f"[{status}] {rotulo}")
        print(f"       {ultima_linha_nao_vazia(saida)}")
        if status == FAIL:
            print("       --- saida final ---")
            for linha in saida.splitlines()[-15:]:
                print(f"       {linha}")
    print(f"resumo: {len(gates) - falhas}/{len(gates)} gates passaram")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
