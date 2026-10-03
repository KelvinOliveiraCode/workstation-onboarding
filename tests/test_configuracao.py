"""Testes da validacao dos arquivos de configuracao.
Tests for the config file validation.

Cobre os tres arquivos reais do projeto (dicionario, perfis, politicas), a
coerencia entre perfis e dicionario, e os casos de falha: campo faltando,
id duplicado, tipo errado, arquivo ausente, JSON invalido e pacote
referenciado que nao existe no catalogo.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from workstation.schema import (
    ErroDeConfiguracao,
    checar_coerencia,
    carregar_json,
    carregar_yaml,
    validar_configuracoes,
    validar_dicionario,
    validar_perfis,
    validar_politicas,
)


def _dicionario_real(config_dir: Path) -> dict:
    return carregar_yaml(config_dir / "dicionario-software.yaml")


def _perfis_reais(config_dir: Path) -> dict:
    return carregar_yaml(config_dir / "perfis-usuario.yaml")


def _politicas_reais(config_dir: Path) -> dict:
    return carregar_json(config_dir / "politicas.json")


class TestArquivosReais:
    """Os tres arquivos do repo passam no proprio esquema."""

    def test_dicionario_real_passa(self, config_dir: Path) -> None:
        assert validar_dicionario(_dicionario_real(config_dir)) == []

    def test_perfis_reais_passam(self, config_dir: Path) -> None:
        assert validar_perfis(_perfis_reais(config_dir)) == []

    def test_politicas_reais_passam(self, config_dir: Path) -> None:
        assert validar_politicas(_politicas_reais(config_dir)) == []

    def test_coerencia_reais(self, config_dir: Path) -> None:
        erros = checar_coerencia(
            _perfis_reais(config_dir), _dicionario_real(config_dir)
        )
        assert erros == []

    def test_dicionario_real_tem_minimo_de_doze_pacotes(
        self, config_dir: Path
    ) -> None:
        pacotes = _dicionario_real(config_dir)["pacotes"]
        assert len(pacotes) >= 12

    def test_perfis_reais_incluem_os_quatro_obrigatorios(
        self, config_dir: Path
    ) -> None:
        ids = [p["id"] for p in _perfis_reais(config_dir)["perfis"]]
        assert len(ids) >= 4
        for esperado in ("contabilidade", "projetista", "recepcao", "ti"):
            assert esperado in ids

    def test_validar_configuracoes_real_ok(self, config_dir: Path) -> None:
        resultado = validar_configuracoes(config_dir)
        assert resultado["ok"] is True
        assert resultado["erros"] == []
        assert resultado["resumo"]["pacotes"] >= 12
        assert resultado["resumo"]["perfis"] >= 4
        assert resultado["resumo"]["politicas"] == 6


class TestFalhasDicionario:
    """Casos de falha do dicionario de software."""

    def _pacote_ok(self, **mudancas) -> dict:
        base = {
            "id": "pacote-x",
            "nome": "Pacote X",
            "versao": "1.0.0",
            "categoria": "oficio",
            "silencioso": True,
            "origem": "\\\\srv-software\\share\\pacote-x\\setup.exe",
        }
        base.update(mudancas)
        return base

    def test_raiz_que_nao_e_mapeamento(self) -> None:
        assert validar_dicionario(["a", "b"]) != []
        assert validar_dicionario(None) != []

    def test_sem_pacotes_gera_erro(self) -> None:
        erros = validar_dicionario({"pacotes": []})
        assert any("vazio" in e for e in erros)
        erros = validar_dicionario({"versao_catalogo": "1"})
        assert any("ausente ou vazio" in e for e in erros)

    def test_campo_faltando_gera_erro(self) -> None:
        pacote = self._pacote_ok()
        del pacote["versao"]
        erros = validar_dicionario({"pacotes": [pacote]})
        assert any("'versao' ausente" in e for e in erros)

    def test_id_duplicado_gera_erro(self) -> None:
        erros = validar_dicionario(
            {"pacotes": [self._pacote_ok(), self._pacote_ok()]}
        )
        assert any("duplicado" in e for e in erros)

    def test_silencioso_nao_bool_gera_erro(self) -> None:
        erros = validar_dicionario(
            {"pacotes": [self._pacote_ok(silencioso="sim")]}
        )
        assert any("'silencioso' deve ser booleano" in e for e in erros)

    def test_id_fora_do_kebab_case_gera_erro(self) -> None:
        erros = validar_dicionario(
            {"pacotes": [self._pacote_ok(id="Pacote X 1")]}
        )
        assert any("kebab-case" in e for e in erros)

    def test_origem_fora_de_share_gera_erro(self) -> None:
        erros = validar_dicionario(
            {"pacotes": [self._pacote_ok(origem="C:\\temp\\setup.exe")]}
        )
        assert any("origem" in e for e in erros)


class TestFalhasPerfis:
    """Casos de falha dos perfis de usuario."""

    def _perfil_ok(self, **mudancas) -> dict:
        base = {
            "id": "ti",
            "descricao": "Estacao TI",
            "grupo-dominio": "ESCR-TI",
            "impressora-padrao": "IMP-TECNICO-01",
            "pode-instalar-software": True,
            "pacotes": ["pacote-x"],
        }
        base.update(mudancas)
        return base

    def test_campo_faltando_gera_erro(self) -> None:
        perfil = self._perfil_ok()
        del perfil["grupo-dominio"]
        erros = validar_perfis({"perfis": [perfil]})
        assert any("'grupo-dominio' ausente" in e for e in erros)

    def test_pode_instalar_nao_bool_gera_erro(self) -> None:
        perfil = self._perfil_ok()
        perfil["pode-instalar-software"] = "nao"
        erros = validar_perfis({"perfis": [perfil]})
        assert any("'pode-instalar-software' deve ser booleano" in e
                   for e in erros)

    def test_id_duplicado_gera_erro(self) -> None:
        erros = validar_perfis(
            {"perfis": [self._perfil_ok(), self._perfil_ok()]}
        )
        assert any("duplicado" in e for e in erros)

    def test_pacotes_com_entrada_nao_string_gera_erro(self) -> None:
        erros = validar_perfis(
            {"perfis": [self._perfil_ok(pacotes=["ok", 42])]}
        )
        assert any("apenas ids (strings)" in e for e in erros)


class TestFalhasPoliticas:
    """Casos de falha das politicas de workstation."""

    def _politica_ok(self, **mudancas) -> dict:
        base = {
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
        base.update(mudancas)
        return base

    def test_politica_obrigatoria_ausente_gera_erro(self) -> None:
        politica = self._politica_ok()
        del politica["auditoria"]
        erros = validar_politicas(politica)
        assert any("'auditoria' ausente" in e for e in erros)

    def test_execution_policy_invalida_gera_erro(self) -> None:
        erros = validar_politicas(
            self._politica_ok(
                execution_policy_powershell={"escopo": "usuario",
                                             "valor": "Banana"}
            )
        )
        assert any("nao e uma execution policy valida" in e for e in erros)

    def test_bloqueio_tela_zero_gera_erro(self) -> None:
        erros = validar_politicas(
            self._politica_ok(bloqueio_tela={"minutos": 0})
        )
        assert any("bloqueio_tela.minutos" in e for e in erros)

    def test_janela_incoerente_gera_erro(self) -> None:
        erros = validar_politicas(
            self._politica_ok(
                windows_update={"modo": "automatico",
                                "janela_inicio": 5,
                                "janela_fim": 4}
            )
        )
        assert any("janela_inicio" in e for e in erros)

    def test_comprimento_de_senha_curto_gera_erro(self) -> None:
        erros = validar_politicas(
            self._politica_ok(senha_minima={"comprimento": 4,
                                            "expira_dias": 60})
        )
        assert any("senha_minima.comprimento" in e for e in erros)

    def test_auditoria_habilitada_nao_bool_gera_erro(self) -> None:
        erros = validar_politicas(
            self._politica_ok(
                auditoria={"habilitada": "sim", "eventos": ["login"]}
            )
        )
        assert any("auditoria.habilitada" in e for e in erros)


class TestCoerencia:
    """Cruza perfis com dicionario."""

    def _catalogo(self) -> dict:
        return {
            "pacotes": [
                {"id": "pacote-a", "nome": "A", "versao": "1.0.0",
                 "categoria": "oficio", "silencioso": True,
                 "origem": "\\\\srv-software\\share\\a\\setup.exe"},
            ]
        }

    def test_pacote_inexistente_gera_erro(self) -> None:
        perfis = {
            "perfis": [
                {
                    "id": "ti",
                    "descricao": "x",
                    "grupo-dominio": "g",
                    "impressora-padrao": "i",
                    "pode-instalar-software": True,
                    "pacotes": ["pacote-z"],
                }
            ]
        }
        erros = checar_coerencia(perfis, self._catalogo())
        assert any("pacote-z" in e for e in erros)

    def test_coferencia_valida_nao_gera_erro(self) -> None:
        perfis = {
            "perfis": [
                {
                    "id": "ti",
                    "descricao": "x",
                    "grupo-dominio": "g",
                    "impressora-padrao": "i",
                    "pode-instalar-software": True,
                    "pacotes": ["pacote-a"],
                }
            ]
        }
        assert checar_coerencia(perfis, self._catalogo()) == []


class TestCarregamento:
    """Arquivo ausente, sintaxe invalida, validacao de pasta invalida."""

    def test_yaml_ausente_gera_erro(self, tmp_path: Path) -> None:
        with pytest.raises(ErroDeConfiguracao, match="nao encontrado"):
            carregar_yaml(tmp_path / "nao-existe.yaml")

    def test_json_invalido_gera_erro(self, tmp_path: Path) -> None:
        ruim = tmp_path / "ruim.json"
        ruim.write_text("{ nao e json", encoding="utf-8")
        with pytest.raises(ErroDeConfiguracao, match="sintaxe JSON"):
            carregar_json(ruim)

    def test_yaml_invalido_gera_erro(self, tmp_path: Path) -> None:
        ruim = tmp_path / "ruim.yaml"
        ruim.write_text("a:\n- b\n c: [incompleto", encoding="utf-8")
        with pytest.raises(ErroDeConfiguracao, match="sintaxe YAML"):
            carregar_yaml(ruim)

    def test_pasta_invalida_gera_erros(self, tmp_path: Path) -> None:
        (tmp_path / "politicas.json").write_text(
            '{"bloqueio_tela": {"minutos": 0}}', encoding="utf-8"
        )
        resultado = validar_configuracoes(tmp_path)
        assert resultado["ok"] is False
        texto = " | ".join(resultado["erros"])
        assert "dicionario-software.yaml" in texto
        assert "perfis-usuario.yaml" in texto
        assert "minutos" in texto

    def test_dados_invalidos_do_repo_nao_passam(self, raiz: Path) -> None:
        dicionario = carregar_yaml(
            raiz / "dados" / "exemplo-dicionario-invalido.yaml"
        )
        erros = validar_dicionario(dicionario)
        assert any("duplicado" in e for e in erros)
        assert any("'versao' ausente" in e for e in erros)
        assert any("'silencioso' deve ser booleano" in e for e in erros)
        politicas = carregar_json(
            raiz / "dados" / "exemplo-politicas-invalida.json"
        )
        erros_p = validar_politicas(politicas)
        assert len(erros_p) >= 3
        assert any("execution policy" in e for e in erros_p)


class TestParserPowerShell:
    """O parser de YAML dos scripts bate com o PyYAML no catalogo real."""

    def test_parser_ps_bate_com_pyyaml(self, raiz: Path) -> None:
        if shutil.which("powershell") is None:
            pytest.skip("powershell indisponivel neste host")
        comando = (
            ". .\\scripts\\Parser-Catalogo.ps1; "
            "$doc = Converter-YamlDoCatalogo "
            "-Arquivo 'config\\dicionario-software.yaml'; "
            "$doc | ConvertTo-Json -Depth 5"
        )
        processo = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", comando],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert processo.returncode == 0, processo.stderr
        doc_ps = json.loads(processo.stdout)
        esperado = yaml.safe_load(
            (raiz / "config" / "dicionario-software.yaml")
            .read_text(encoding="utf-8")
        )
        assert doc_ps["versao_catalogo"] == esperado["versao_catalogo"]
        ids_ps = [p["id"] for p in doc_ps["pacotes"]]
        ids_ys = [p["id"] for p in esperado["pacotes"]]
        assert ids_ps == ids_ys
        for pacote_ps, pacote_ys in zip(doc_ps["pacotes"],
                                        esperado["pacotes"]):
            assert pacote_ps["nome"] == pacote_ys["nome"]
            assert pacote_ps["versao"] == pacote_ys["versao"]
            assert pacote_ps["categoria"] == pacote_ys["categoria"]
            assert pacote_ps["silencioso"] is pacote_ys["silencioso"]
            assert pacote_ps["origem"] == pacote_ys["origem"]
