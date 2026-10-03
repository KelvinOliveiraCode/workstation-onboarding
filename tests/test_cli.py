"""Testes da CLI (python -m workstation).
Tests for the CLI (python -m workstation).

Cobre os dois comandos com diretorio valido e invalido, o codigo de saida
e o comportamento sem comando (uso/ajuda).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workstation.cli import main


def _config_valido(tmp_path: Path) -> None:
    (tmp_path / "dicionario-software.yaml").write_text(
        "versao_catalogo: '1.0.0'\n"
        "pacotes:\n"
        "  - id: pacote-a\n"
        "    nome: 'Pacote A'\n"
        "    versao: '1.0.0'\n"
        "    categoria: 'oficio'\n"
        "    silencioso: true\n"
        "    origem: '\\\\srv-software\\share\\a\\setup.exe'\n",
        encoding="utf-8",
    )
    (tmp_path / "perfis-usuario.yaml").write_text(
        "perfis:\n"
        "  - id: ti\n"
        "    descricao: 'Estacao TI'\n"
        "    grupo-dominio: 'ESCR-TI'\n"
        "    impressora-padrao: 'IMP-TI-01'\n"
        "    pode-instalar-software: true\n"
        "    pacotes:\n"
        "      - pacote-a\n",
        encoding="utf-8",
    )
    (tmp_path / "politicas.json").write_text(
        json.dumps(
            {
                "bloqueio_tela": {"minutos": 10},
                "execution_policy_powershell": {
                    "escopo": "usuario",
                    "valor": "RemoteSigned",
                },
                "windows_update": {
                    "modo": "automatico",
                    "janela_inicio": 3,
                    "janela_fim": 4,
                },
                "firewall": {"perfil_padrao": "dominio"},
                "senha_minima": {"comprimento": 12, "expira_dias": 60},
                "auditoria": {"habilitada": True, "eventos": ["login"]},
            }
        ),
        encoding="utf-8",
    )


class TestVerificar:
    """Comando 'verificar'."""

    def test_diretorio_valido_retorna_zero(self, tmp_path: Path,
                                          capsys: pytest.CaptureFixture) -> None:
        _config_valido(tmp_path)
        codigo = main(["verificar", str(tmp_path)])
        saida = capsys.readouterr().out
        assert codigo == 0
        assert "RESUMO: 0 erro(s)" in saida
        assert "1 pacotes" in saida

    def test_diretorio_invalido_retorna_um(self, tmp_path: Path,
                                           capsys: pytest.CaptureFixture) -> None:
        (tmp_path / "politicas.json").write_text(
            '{"bloqueio_tela": {"minutos": 0}}', encoding="utf-8"
        )
        codigo = main(["verificar", str(tmp_path)])
        saida = capsys.readouterr().out
        assert codigo == 1
        assert "ERRO" in saida
        assert "minutos" in saida

    def test_config_real_do_repo_passa(self, raiz: Path,
                                       capsys: pytest.CaptureFixture) -> None:
        codigo = main(["verificar", str(raiz / "config")])
        saida = capsys.readouterr().out
        assert codigo == 0
        assert "RESUMO: 0 erro(s)" in saida

    def test_auditoria_de_scripts_reais(self, raiz: Path,
                                       capsys: pytest.CaptureFixture) -> None:
        codigo = main(["auditoria", str(raiz / "scripts")])
        saida = capsys.readouterr().out
        assert codigo == 0
        assert "6/6 scripts" in saida
        assert "0 violacao(oes)" in saida

    def test_auditoria_de_pasta_invalida(self, tmp_path: Path,
                                         capsys: pytest.CaptureFixture) -> None:
        codigo = main(["auditoria", str(tmp_path)])
        saida = capsys.readouterr().out
        assert codigo == 1
        assert "arquivo ausente" in saida

    def test_sem_comando_exibe_ajuda(self) -> None:
        with pytest.raises(SystemExit) as capturo:
            main([])
        assert capturo.value.code == 2
