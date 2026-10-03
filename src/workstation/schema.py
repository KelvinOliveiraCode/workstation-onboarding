"""Validacao do esquema dos arquivos de configuracao do onboarding.
Schema validation for the workstation onboarding config files.

O esquema e o contrato entre os scripts PowerShell e os perfis: um campo
faltando aqui vira um onboarding errado la. Os validadores retornam listas
de erros (vazia = valido) em vez de excecao, para o relatorio conseguir
listar todos os problemas de uma vez em vez de parar no primeiro.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

__all__ = [
    "CAMPOS_PACOTE",
    "CAMPOS_PERFIL",
    "POLITICAS_OBRIGATORIAS",
    "EXECUTION_POLICIES_VALIDAS",
    "ARQUIVOS_CONFIG",
    "ErroDeConfiguracao",
    "carregar_yaml",
    "carregar_json",
    "validar_dicionario",
    "validar_perfis",
    "validar_politicas",
    "checar_coerencia",
    "validar_configuracoes",
]

CAMPOS_PACOTE = ("id", "nome", "versao", "categoria", "silencioso", "origem")
CAMPOS_PERFIL = (
    "id",
    "descricao",
    "grupo-dominio",
    "impressora-padrao",
    "pode-instalar-software",
    "pacotes",
)
POLITICAS_OBRIGATORIAS = (
    "bloqueio_tela",
    "execution_policy_powershell",
    "windows_update",
    "firewall",
    "senha_minima",
    "auditoria",
)
EXECUTION_POLICIES_VALIDAS = (
    "Restricted",
    "AllSigned",
    "RemoteSigned",
    "Unrestricted",
    "System",
    "Machine",
    "User",
    "Inheritance",
)
ARQUIVOS_CONFIG = (
    "dicionario-software.yaml",
    "perfis-usuario.yaml",
    "politicas.json",
)

_ID_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ErroDeConfiguracao(Exception):
    """Arquivo ausente ou com sintaxe invalida.
    File missing, unreadable, or with invalid syntax."""


def carregar_yaml(caminho: Path) -> object:
    """Carrega um arquivo YAML com safe_load.
    Load a YAML file with safe_load."""
    p = Path(caminho)
    if not p.is_file():
        raise ErroDeConfiguracao(f"arquivo nao encontrado: {p.name}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ErroDeConfiguracao(
            f"sintaxe YAML invalida em {p.name}: {exc}"
        ) from exc


def carregar_json(caminho: Path) -> object:
    """Carrega um arquivo JSON.
    Load a JSON file."""
    p = Path(caminho)
    if not p.is_file():
        raise ErroDeConfiguracao(f"arquivo nao encontrado: {p.name}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErroDeConfiguracao(
            f"sintaxe JSON invalida em {p.name}: linha {exc.lineno}"
        ) from exc


def validar_dicionario(data: object) -> list[str]:
    """Valida o esquema de config/dicionario-software.yaml.
    Validate the software catalog schema.
    Retorna uma lista de erros; vazia quando o documento e valido."""
    if not isinstance(data, dict):
        return ["dicionario: a raiz deve ser um mapeamento"]
    pacotes = data.get("pacotes")
    if not isinstance(pacotes, list) or len(pacotes) == 0:
        return ["dicionario: campo 'pacotes' ausente ou vazio"]
    erros: list[str] = []
    ids_vistos: set[str] = set()
    for i, pacote in enumerate(pacotes):
        rotulo = f"dicionario: pacotes[{i}]"
        if not isinstance(pacote, dict):
            erros.append(f"{rotulo}: entrada deve ser um mapeamento")
            continue
        for campo in CAMPOS_PACOTE:
            valor = pacote.get(campo)
            if campo not in pacote:
                erros.append(f"{rotulo}: campo obrigatorio '{campo}' ausente")
            elif isinstance(valor, str) and valor.strip() == "":
                erros.append(f"{rotulo}: campo '{campo}' esta vazio")
        pid = pacote.get("id")
        if isinstance(pid, str) and pid:
            if not _ID_KEBAB.match(pid):
                erros.append(
                    f"{rotulo}: id '{pid}' deve ser kebab-case (minussulas, "
                    "numeros e tracos)"
                )
            if pid in ids_vistos:
                erros.append(f"{rotulo}: id '{pid}' duplicado no catalogo")
            ids_vistos.add(pid)
        silencioso = pacote.get("silencioso")
        if silencioso is not None and not isinstance(silencioso, bool):
            erros.append(
                f"{rotulo}: 'silencioso' deve ser booleano, nao "
                f"{type(silencioso).__name__}"
            )
        origem = pacote.get("origem")
        if isinstance(origem, str) and origem:
            if not origem.startswith("\\\\"):
                erros.append(
                    f"{rotulo}: 'origem' deve apontar para pasta de rede "
                    "ficticia (\\\\srv-...)"
                )
    return erros


def validar_perfis(data: object) -> list[str]:
    """Valida o esquema de config/perfis-usuario.yaml.
    Validate the user profiles schema.
    Retorna uma lista de erros; vazia quando o documento e valido."""
    if not isinstance(data, dict):
        return ["perfis: a raiz deve ser um mapeamento"]
    perfis = data.get("perfis")
    if not isinstance(perfis, list) or len(perfis) == 0:
        return ["perfis: campo 'perfis' ausente ou vazio"]
    erros: list[str] = []
    ids_vistos: set[str] = set()
    for i, perfil in enumerate(perfis):
        rotulo = f"perfis: perfis[{i}]"
        if not isinstance(perfil, dict):
            erros.append(f"{rotulo}: entrada deve ser um mapeamento")
            continue
        for campo in CAMPOS_PERFIL:
            if campo not in perfil or perfil.get(campo) in (None, ""):
                erros.append(f"{rotulo}: campo obrigatorio '{campo}' ausente")
        pid = perfil.get("id")
        if isinstance(pid, str) and pid:
            if not _ID_KEBAB.match(pid):
                erros.append(f"{rotulo}: id '{pid}' deve ser kebab-case")
            if pid in ids_vistos:
                erros.append(f"{rotulo}: id '{pid}' duplicado")
            ids_vistos.add(pid)
        flag = perfil.get("pode-instalar-software")
        if flag is not None and not isinstance(flag, bool):
            erros.append(
                f"{rotulo}: 'pode-instalar-software' deve ser booleano"
            )
        pacotes = perfil.get("pacotes")
        if pacotes is not None:
            if not isinstance(pacotes, list) or len(pacotes) == 0:
                erros.append(f"{rotulo}: 'pacotes' deve ser lista nao vazia")
            elif not all(isinstance(x, str) and x for x in pacotes):
                erros.append(
                    f"{rotulo}: 'pacotes' deve conter apenas ids (strings)"
                )
    return erros


def validar_politicas(data: object) -> list[str]:
    """Valida o esquema de config/politicas.json.
    Validate the workstation policies schema.
    Retorna uma lista de erros; vazia quando o documento e valido."""
    if not isinstance(data, dict):
        return ["politicas: a raiz deve ser um objeto JSON"]
    erros: list[str] = []
    for chave in POLITICAS_OBRIGATORIAS:
        if chave not in data:
            erros.append(f"politicas: politica obrigatoria '{chave}' ausente")
    if "bloqueio_tela" in data:
        seg = data["bloqueio_tela"]
        if not isinstance(seg, dict):
            erros.append("politicas: 'bloqueio_tela' deve ser um objeto")
        else:
            minutos = seg.get("minutos")
            if not isinstance(minutos, int) or isinstance(minutos, bool) \
                    or not 0 < minutos <= 1440:
                erros.append(
                    "politicas: 'bloqueio_tela.minutos' deve ser inteiro "
                    "entre 1 e 1440"
                )
    if "execution_policy_powershell" in data:
        seg = data["execution_policy_powershell"]
        if not isinstance(seg, dict):
            erros.append(
                "politicas: 'execution_policy_powershell' deve ser um objeto"
            )
        else:
            valor = seg.get("valor")
            if valor not in EXECUTION_POLICIES_VALIDAS:
                erros.append(
                    f"politicas: 'execution_policy_powershell.valor' "
                    f"'{valor}' nao e uma execution policy valida"
                )
            if seg.get("escopo") not in ("usuario", "maquina"):
                erros.append(
                    "politicas: 'execution_policy_powershell.escopo' deve "
                    "ser 'usuario' ou 'maquina'"
                )
    if "windows_update" in data:
        seg = data["windows_update"]
        if not isinstance(seg, dict):
            erros.append("politicas: 'windows_update' deve ser um objeto")
        else:
            if seg.get("modo") not in ("automatico", "manual"):
                erros.append(
                    "politicas: 'windows_update.modo' deve ser "
                    "'automatico' ou 'manual'"
                )
            inicio = seg.get("janela_inicio")
            fim = seg.get("janela_fim")
            if not (isinstance(inicio, int) and isinstance(fim, int)
                    and not isinstance(inicio, bool)
                    and not isinstance(fim, bool)
                    and 0 <= inicio < fim <= 24):
                erros.append(
                    "politicas: 'windows_update' exige janela_inicio < "
                    "janela_fim dentro de 0..24"
                )
    if "firewall" in data:
        seg = data["firewall"]
        if not isinstance(seg, dict):
            erros.append("politicas: 'firewall' deve ser um objeto")
        else:
            if seg.get("perfil_padrao") not in ("dominio", "privada", "publica"):
                erros.append(
                    "politicas: 'firewall.perfil_padrao' deve ser "
                    "'dominio', 'privada' ou 'publica'"
                )
    if "senha_minima" in data:
        seg = data["senha_minima"]
        if not isinstance(seg, dict):
            erros.append("politicas: 'senha_minima' deve ser um objeto")
        else:
            comp = seg.get("comprimento")
            if not isinstance(comp, int) or isinstance(comp, bool) \
                    or not 8 <= comp <= 64:
                erros.append(
                    "politicas: 'senha_minima.comprimento' deve ser inteiro "
                    "entre 8 e 64"
                )
            expira = seg.get("expira_dias")
            if not isinstance(expira, int) or isinstance(expira, bool) \
                    or not 1 <= expira <= 730:
                erros.append(
                    "politicas: 'senha_minima.expira_dias' deve ser inteiro "
                    "entre 1 e 730"
                )
    if "auditoria" in data:
        seg = data["auditoria"]
        if not isinstance(seg, dict):
            erros.append("politicas: 'auditoria' deve ser um objeto")
        else:
            if not isinstance(seg.get("habilitada"), bool):
                erros.append(
                    "politicas: 'auditoria.habilitada' deve ser booleano"
                )
            eventos = seg.get("eventos")
            if not isinstance(eventos, list) \
                    or not all(isinstance(e, str) and e for e in eventos):
                erros.append(
                    "politicas: 'auditoria.eventos' deve ser lista de "
                    "nomes de evento"
                )
    return erros


def checar_coerencia(perfis: object, dicionario: object) -> list[str]:
    """Cruza perfis com dicionario: todo pacote referenciado existe.
    Cross-check profiles against the catalog: every referenced package id
    must exist.
    Retorna uma lista de erros; vazia quando a coerencia se manteve."""
    if not isinstance(perfis, dict) or not isinstance(dicionario, dict):
        return ["coerencia: perfis e dicionario devem ser mapeamentos"]
    pacotes = dicionario.get("pacotes") or []
    ids = {
        p.get("id") for p in pacotes
        if isinstance(p, dict) and isinstance(p.get("id"), str)
    }
    erros: list[str] = []
    for perfil in perfis.get("perfis") or []:
        if not isinstance(perfil, dict):
            continue
        pid = perfil.get("id")
        pacotes_ref = perfil.get("pacotes") or []
        if not isinstance(pacotes_ref, list):
            continue
        for ref in pacotes_ref:
            if isinstance(ref, str) and ref not in ids:
                erros.append(
                    f"coerencia: perfil '{pid}' referencia pacote "
                    f"'{ref}' que nao existe no dicionario"
                )
    return erros


def validar_configuracoes(config_dir: object) -> dict:
    """Valida os tres arquivos de configuracao + coerencia entre eles.
    Validate the three config files plus their cross-consistency.
    Retorna {'erros': list, 'resumo': dict, 'ok': bool}."""
    raiz = Path(config_dir)
    erros: list[str] = []
    resumo = {"pacotes": 0, "perfis": 0, "politicas": 0}
    documentos: dict[str, object] = {}
    for nome in ARQUIVOS_CONFIG:
        loader = carregar_yaml if nome.endswith(".yaml") else carregar_json
        try:
            documentos[nome] = loader(raiz / nome)
        except ErroDeConfiguracao as exc:
            erros.append(f"{nome}: {exc}")
    dicionario = documentos.get("dicionario-software.yaml")
    perfis = documentos.get("perfis-usuario.yaml")
    politicas = documentos.get("politicas.json")
    if isinstance(dicionario, dict):
        pacotes = dicionario.get("pacotes")
        resumo["pacotes"] = len(pacotes) if isinstance(pacotes, list) else 0
        erros.extend(validar_dicionario(dicionario))
    if isinstance(perfis, dict):
        lista = perfis.get("perfis")
        resumo["perfis"] = len(lista) if isinstance(lista, list) else 0
        erros.extend(validar_perfis(perfis))
    if isinstance(politicas, dict):
        resumo["politicas"] = sum(
            1 for chave in POLITICAS_OBRIGATORIAS if chave in politicas
        )
        erros.extend(validar_politicas(politicas))
    if isinstance(dicionario, dict) and isinstance(perfis, dict):
        erros.extend(checar_coerencia(perfis, dicionario))
    return {"erros": erros, "resumo": resumo, "ok": not erros}
