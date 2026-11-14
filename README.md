# workstation-onboarding

[English](README.en.md) · **Português (Brasil)**

[![Python 3](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#) [![PyYAML](https://img.shields.io/badge/PyYAML-%C3%BAnica%20dep-3776AB?style=flat-square)](#) [![pytest](https://img.shields.io/badge/pytest-52%20testes-0A9EDC?style=flat-square&logo=pytest)](#) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

## O que é

**Onboarding de estações de trabalho via configuração declarativa**: perfis e políticas de setup definidos em **YAML/JSON**, com **validação de schema e coerência** entre arquivos e uma **auditoria estática dos scripts de setup** (detecta padrões perigosos antes de executar). É um laboratório educacional de automação de Suporte TI.

## Status

Laboratório educacional funcional e testado (52 testes).

## Funcionalidades

- **Validação de configurações** (`schema.py`): `carregar_yaml`/`carregar_json`, `validar_perfis`, `validar_politicas`, `checar_coerencia` (perfis ↔ dicionário) e `validar_configuracoes` agregando tudo.
- **Auditoria de scripts** (`auditoria.py`): `auditar_script`/`auditar_diretorio` — verificação estática dos scripts (regras + fabricantes), antes de rodar nada na máquina.
- **CLI** (`workstation`): `verificar <dir>` e `auditoria <dir>`.

## Arquitetura

Pacote `workstation` com `schema.py` (YAML/JSON + regras), `auditoria.py` (análise estática de scripts) e `cli.py`.

```mermaid
flowchart LR
    CFG[dados/*.yaml|json perfis/políticas] --> V[schema.py - validar + coerência]
    SCR[scripts de setup] --> AUD[auditoria.py - análise estática]
    V --> CLI[workstation verificar]
    AUD --> CLI[workstation auditoria]
```

## Stack

- Python ≥ 3.10
- PyYAML ≥ 6.0 (única dependência)
- pytest (dev)

## Estrutura do repositório

```
workstation-onboarding/
├── pyproject.toml · BRIEF.md
├── src/workstation/
│   ├── schema.py       # validação YAML/JSON + coerência
│   ├── auditoria.py    # auditoria estática de scripts
│   └── cli.py
├── dados/ · scripts/   # exemplos de perfis e scripts setup
├── tests/              # 52 testes
└── LICENSE             # MIT
```

## Pré-requisitos e instalação

```bash
pip install -e .
```

## Como executar

```bash
workstation verificar dados/
workstation auditoria scripts/
```

## Testes e qualidade

Comando real (verificado pelo agente):

```bash
PYTHONPATH=src python -m pytest tests/
# 52 passed
```

## Decisões técnicas e trade-offs

- **Configuração declarativa (YAML)**: perfis revisáveis em revisão de código, executados por outro motor.
- **Auditoria estática antes de executar**: risco pego na revisão, não só na máquina.
- **Coerência perfis ↔ dicionário**: evita perfis referenciando coisas inexistentes.

## Limitações conhecidas e roadmap

- Este repo **valida e audita** os scripts — não executa a configuração (sem motor de aplicação).
- Auditoria por regras simples, sem parser completo de PowerShell.

## Processo de desenvolvimento

Projeto individual de Kelvin Oliveira, construído com agentes de IA orquestrados e revisado pelo autor.

## Licença e autor

MIT — Copyright (c) 2026 Kelvin Rebelo de Oliveira. Autor: [Kelvin Oliveira](https://github.com/KelvinOliveiraCode) · [Portfólio](https://kelvinoliveiracode.github.io/portfolio/)
