# workstation-onboarding

<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/PowerShell-5.1%2B-blue?style=flat-square" alt="PowerShell">
<img src="https://img.shields.io/badge/tests-52%20passing-brightgreen?style=flat-square" alt="Tests">
<img src="https://img.shields.io/badge/coverage-89%25-yellowgreen-brightgreen?style=flat-square" alt="Coverage">
<img src="https://img.shields.io/badge/deps-PyYAML%20only-blue?style=flat-square" alt="Deps">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
<img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">

PowerShell scripts that prepare a Windows workstation from scratch: network, printers, software, policies, and final verification. Dry-run by default; changes nothing unless `-Executar` is passed.

## Problem / Why it exists

Provisioning a Windows workstation requires repeating the same sequence: configure network, map printers, install packages, apply policies, and check that it came out right. When that flow is not executed every day, the technician forgets the order, tests on the wrong machine, or changes something by accident. The bigger risk is applying a change before verifying it is needed.

This project solves that by separating verification from execution and requiring an explicit switch (`-Executar`) for any change. The default mode is dry-run: every action appears in the log with a `[WhatIf]` prefix and nothing touches the workstation.

## What it does

Six PowerShell scripts run five steps read from three configuration files (YAML and JSON, fictional data):

- `Configurar-Rede.ps1` - DNS, time zone, proxy
- `Configurar-Impressoras.ps1` - registration and default printer
- `Instalar-Software.ps1` - packages from the catalog (local YAML parser, no module)
- `Aplicar-Politicas.ps1` - user policy and desired state in `HKCU:\Software\Politicas\Estacao`
- `Verificar-Workstation.ps1` - `OK/FAIL/WARNING` report, read-only, exit code 0/1
- `Instalar-Workstation.ps1` - orchestrator that calls the previous steps in order

The catalog holds 14 fictional packages split into 5 categories (office, security, data, productivity, network, system). There are 4 user profiles (accounting, designer, reception, IT) and 6 mandatory policies (screen lock, PowerShell execution policy, Windows Update, firewall, minimum password, audit).

## Stack

- PowerShell 5.1+ (scripts; no external dependency)
- Python 3.10+ (CLI, configuration validation, script audit, tests)
- PyYAML >= 6.0 (only Python dependency, used by tests and the CLI)
- pytest >= 7.4 and pytest-cov >= 4.1 (dev)

## How it works

Every script uses `SupportsShouldProcess = $true` and `ConfirmImpact = 'High'`, with the parameter `[switch]$Executar`. Every action goes through `Aplicar-Acao`, which calls `$PSCmdlet.ShouldProcess(...)`. Without `-Executar`, the action becomes a `[WhatIf]` line in the log and nothing changes. With `-Executar`, the action runs for real and may require administrator rights.

`Verificar-Workstation.ps1` closes the loop: it checks config, scripts, structure, logs, and environment, prints an `OK/FAIL/WARNING` table, and returns 0 or 1.

The Python side does three things:

1. `python -m workstation verificar` - validates `dicionario-software.yaml`, `perfis-usuario.yaml`, and `politicas.json` against the schema and crosses profiles with the catalog (every referenced package must exist)
2. `python -m workstation auditoria` - checks that no script lost `SupportsShouldProcess`, `$PSCmdlet.ShouldProcess`, or `[switch]$Executar`, and that none contains `Remove-Item -Recurse -Force` without a guard, `curl | iex`, CMD downloading something, or a real vendor name
3. Python tests - 52 tests (schema, audit, CLI, PowerShell parser x PyYAML crossover)

Measured coverage: 89% total (required floor: 70%).

## How to run

```powershell
# 1. Python dependencies
pip install -r requirements.txt

# 2. Validate configuration and scripts
python -m workstation verificar
python -m workstation auditoria

# 3. Verify the workstation (read-only, generates OK/FAIL/WARNING report)
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1

# 4. Full onboarding in dry-run (changes nothing)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1

# 5. Real onboarding (applies changes; may require administrator)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1 -Executar

# Single acceptance gate: tests + coverage + verification + dry-run
python tools\verificar_aceite.py
```

Real output of step 3 (run on this host):

```
==================================================================
 WORKSTATION VERIFICATION - validation report
==================================================================
 Executed at : 2026-10-03 19:44:55  (timestamp; changes every run)
 Station      : DESKTOP-MQ2N9CF
 PowerShell   : 5.1.19041.6456
 Mode         : read-only (does not change the station)

STATUS  CHECK                                 DETAIL
------  ----------------------------------  -------------------------------------------------------------
OK      config: configuration folder          exists (config)
OK      config/dicionario-software.yaml       14 packages, 6 fields per package
OK      config/perfis-usuario.yaml            4 profiles with package block
OK      config/politicas.json                 6 mandatory policies present
OK      scripts/Instalar-Workstation.ps1      security markers present
OK      scripts/Configurar-Rede.ps1           security markers present
OK      scripts/Configurar-Impressoras.ps1    security markers present
OK      scripts/Instalar-Software.ps1         security markers present
OK      scripts/Aplicar-Politicas.ps1         security markers present
OK      scripts/Verificar-Workstation.ps1     security markers present
OK      repository structure                  2 docs, 2 examples, 4 Python tests
OK      logs: writable folder                 probe write and cleanup OK
OK      PowerShell                           version 5.1.19041.6456 (>= 5.1)
WARNING administration                       not an administrator; dry-run does not require it, -Executar may
OK      execution policy (user)               RemoteSigned
------  ----------------------------------  -------------------------------------------------------------
 Total: 14 OK, 0 FAIL, 1 WARNING
 RESULT: PASSED
==================================================================
 Log written to: logs\verificar-workstation.log
```

The `Executed at` line changes every run (timestamp): the output is not byte-identical between runs, but the content is deterministic for the same station and repository version. The full output is in `exemplos/exemplo-de-saida.txt` and the full installer dry-run in `exemplos/exemplo-instalador-dryrun.txt`.

## Project structure

```
config/
  dicionario-software.yaml   fictional catalog (14 packages, 6 fields each)
  perfis-usuario.yaml        4 profiles (accounting, designer, reception, IT)
  politicas.json             6 workstation policies
scripts/
  Instalar-Workstation.ps1   orchestrator of the 5 steps
  Configurar-Rede.ps1        DNS, time zone, proxy
  Configurar-Impressoras.ps1 registration and default printer
  Instalar-Software.ps1      packages from the catalog (local YAML parser)
  Aplicar-Politicas.ps1      user policies and desired state in HKCU
  Verificar-Workstation.ps1  OK/FAIL/WARNING report (read-only)
  Parser-Catalogo.ps1        helper: minimal parser for the catalog schema
dados/                      intentionally invalid examples (used by tests)
docs/
  procedimento-de-preparacao.md technician checklist, step by step
  como-verificar-uma-estacao.md how to read the report and the table
exemplos/
  exemplo-de-saida.txt           real output of Verificar-Workstation
  exemplo-instalador-dryrun.txt  real output of the full dry-run
src/workstation/            schema, content audit, CLI (Python module)
tests/                      52 tests (schema, audit, CLI, PS parser x PyYAML)
tools/
  verificar_encoding.py      BOM/CJK/U+FFFD check before commit
  verificar_aceite.py        single gate: tests + coverage + verification + dry-run
```

Measured coverage with `python -m pytest --cov=workstation --cov-report=term-missing` (the validated module lives in `src/workstation`).

## Trade-offs and decisions

- **Dry-run by default with `-Executar` to apply.** Cost: the technician has to remember the switch. Gain: impossibility of changing the station by accident, and every action is logged with a timestamp.
- **Local YAML parser in PowerShell 5.1.** PowerShell 5.1 has no built-in YAML and the project does not want to install a module. Gain: zero dependencies in the scripts. Cost: only the fixed catalog schema (flat list of scalars); nested lists, multi-line, and aliases are not supported.
- **Policies written to `HKCU`, not GPO.** The four policies that require HKLM record the desired state in `HKCU:\Software\Politicas\Estacao` and warn in the log that effective application is up to GPO/administrator. Gain: works without domain rights. Cost: does not apply real domain policy.
- **Verification separate from execution.** The verifier checks the disk, not the system: it validates config/scripts/structure/environment. What actually changed (DNS, printer, packages) stays in the step logs. Gain: independent audit of whoever executed. Cost: it does not say whether DNS is really resolving, only whether the script ran.
- **Output is not byte-identical between runs** (timestamp, host name). The comparable content is the result of each check. Gain: traceability per run. Cost: direct diff of outputs is not possible.

## Known limitations

- Does not apply GPO or domain policies. The policies that require HKLM record the desired state in `HKCU:\Software\Politicas\Estacao` and warn in the log that effective application is up to GPO/administrator.
- Not a generic YAML parser. `Parser-Catalogo.ps1` covers the fixed catalog schema (flat list of scalars); nested lists, multi-line, and aliases are not supported by choice.
- The verifier checks the disk, not the system. It validates config/scripts/structure/environment; what actually changed (DNS, printer, packages) stays in the step logs.
- `-Executar` without access to `\\srv-software` fails gracefully: the line becomes `ERRO` in the log and the station continues without the package — nothing is installed halfway.
- Does not uninstall or roll back already installed software.
- Output is not byte-identical between runs (timestamp, host name); the comparable content is the result of each check.

## License

MIT. See [LICENSE](LICENSE).

## Author

Kelvin Oliveira - https://github.com/KelvinOliveiraCode - https://kelvinoliveiracode.github.io/portfolio/