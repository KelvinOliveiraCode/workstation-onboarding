# workstation-onboarding

**English** · [Português (Brasil)](README.md)

[![Python 3](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#) [![PyYAML](https://img.shields.io/badge/PyYAML-only%20dep-3776AB?style=flat-square)](#) [![pytest](https://img.shields.io/badge/pytest-52%20tests-0A9EDC?style=flat-square&logo=pytest)](#) [![MIT License](https://img.shields.io/badge/License-MIT-f4c430?style=flat-square)](LICENSE)

## What it is

**Workstation onboarding via declarative configuration**: setup profiles and policies defined in **YAML/JSON**, with **schema and cross-file consistency validation** plus a **static audit of the setup scripts** (flags dangerous patterns before anything runs). It is an educational IT-support automation lab.

## Status

An educational lab, working and tested (52 tests).

## Features

- **Configuration validation** (`schema.py`): `carregar_yaml`/`carregar_json`, `validar_perfis`, `validar_politicas`, `checar_coerencia` (profiles ↔ dictionary) and `validar_configuracoes` aggregating everything.
- **Script audit** (`auditoria.py`): `auditar_script`/`auditar_diretorio` — static checks of the scripts (rules + vendors) before running anything on the machine.
- **CLI** (`workstation`): `verificar <dir>` and `auditoria <dir>`.

## Architecture

A `workstation` package with `schema.py` (YAML/JSON + rules), `auditoria.py` (static script analysis) and `cli.py`.

```mermaid
flowchart LR
    CFG[dados/*.yaml|json profiles/policies] --> V[schema.py - validate + consistency]
    SCR[setup scripts] --> AUD[auditoria.py - static analysis]
    V --> CLI[workstation verificar]
    AUD --> CLI[workstation auditoria]
```

## Stack

- Python ≥ 3.10
- PyYAML ≥ 6.0 (only dependency)
- pytest (dev)

## Repository layout

```
workstation-onboarding/
├── pyproject.toml · BRIEF.md
├── src/workstation/
│   ├── schema.py       # YAML/JSON validation + consistency
│   ├── auditoria.py    # static script audit
│   └── cli.py
├── dados/ · scripts/   # sample profiles and setup scripts
├── tests/              # 52 tests
└── LICENSE             # MIT
```

## Prerequisites and installation

```bash
pip install -e .
```

## How to run

```bash
workstation verificar dados/
workstation auditoria scripts/
```

## Tests and quality

Real command (verified by the agent):

```bash
PYTHONPATH=src python -m pytest tests/
# 52 passed
```

## Technical decisions and trade-offs

- **Declarative configuration (YAML)**: profiles reviewable in code review, executed by a separate engine.
- **Static audit before running**: risk caught in review, not on the machine.
- **Profile ↔ dictionary consistency**: prevents profiles referencing non-existent items.

## Known limitations and roadmap

- This repo **validates and audits** the scripts — it does not apply the configuration (no application engine).
- Audit relies on simple rules, not a full PowerShell parser.

## Development process

An individual project by Kelvin Oliveira, built with orchestrated AI agents and reviewed by the author.

## License and author

MIT — Copyright (c) 2026 Kelvin Rebelo de Oliveira. Author: [Kelvin Oliveira](https://github.com/KelvinOliveiraCode) · [Portfolio](https://kelvinoliveiracode.github.io/portfolio/)
