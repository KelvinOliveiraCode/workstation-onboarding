<div align="center">

<p>
  <img src="https://img.shields.io/badge/PowerShell-5.1%2B-blue?style=flat-square" alt="PowerShell">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/tests-52%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/coverage-89%25-yellowgreen-brightgreen?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/deps-PyYAML%20only-blue?style=flat-square" alt="Deps">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square" alt="Windows">
</p>

# workstation-onboarding

**Scripts PowerShell que preparam uma estacao Windows do zero: rede, impressoras, software, politicas e verificacao final  -  dry-run por padrao, mudanca so com `-Executar`.**

</div>

---

## PT-BR

### O que e

Seis scripts PowerShell que implantam uma estacao em 5 etapas (rede,
impressoras, software, politicas e verificacao final) lidas a partir de
tres arquivos de configuracao (YAML e JSON, 100% ficticios). O modo padrao
e dry-run: cada acao passa por `$PSCmdlet.ShouldProcess`, sai no log com o
prefixo `[WhatIf]` e nao toca na estacao. So o switch explicito
`-Executar` aplica algo. O `Verificar-Workstation.ps1` fecha o ciclo com
um relatorio `OK/FALHA/AVISO` legivel e com codigo de saida 0/1.

### Por que foi feito

Provisionamento de estacao que nao e executado literalmente na empresa,
todo dia, nao existe: o tecnico quer rodar o que leu no log de ontem e
ter resposta de "a estacao X esta pronta?" em menos de um minuto, sem
abrir 12 painéis. O valor aqui nao e fazer as mudancas (qualquer script
muda algo); e garantir que a mudanca so acontece com um switch explicito,
com cada acao rastreada em log com timestamp, e com a verificacao final
separada da execucao  -  a pessoa que executa pode ser a mesma que
verifica, mas o modo de cada uma e diferente e auditavel.

### Como rodar

```powershell
# 1. Dependencias (Python; os scripts PowerShell nao dependem de nada)
pip install -r requirements.txt

# 2. Validar (testes + auditoria de conteudo dos scripts .ps1)
python -m pytest tests/ -v
python -m workstation verificar
python -m workstation auditoria

# 3. Verificar a estacao (somente leitura, gera relatorio OK/FALHA/AVISO)
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1

# 4. Onboarding completo em dry-run (nao altera nada)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1

# 5. Onboarding de fato (aplica as mudancas; pode exigir administrador)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1 -Executar

# Gate unico: testes + cobertura + verificacao + dry-run
python tools\verificar_aceite.py
```

Saida real do passo 3 (executado neste host):

```
================================================================
 VERIFICACAO DE WORKSTATION - relatorio de validacao
================================================================
 Executado em : 2026-10-03 19:44:55  (timestamp; muda a cada execucao)
 Estacao      : DESKTOP-MQ2N9CF
 PowerShell   : 5.1.19041.6456
 Modo         : somente leitura (nao altera a estacao)

STATUS  CHECAGEM                            DETALHE
------  ----------------------------------  -------------------------------------------------------------
OK      config: pasta de configuracao       existe (config)
OK      config/dicionario-software.yaml     14 pacotes, 6 campos por pacote
OK      config/perfis-usuario.yaml          4 perfis com bloco de pacotes
OK      config/politicas.json               6 politicas obrigatorias presentes
OK      scripts/Instalar-Workstation.ps1    marcadores de seguranca presentes
OK      scripts/Configurar-Rede.ps1         marcadores de seguranca presentes
OK      scripts/Configurar-Impressoras.ps1  marcadores de seguranca presentes
OK      scripts/Instalar-Software.ps1       marcadores de seguranca presentes
OK      scripts/Aplicar-Politicas.ps1       marcadores de seguranca presentes
OK      scripts/Verificar-Workstation.ps1   marcadores de seguranca presentes
OK      estrutura do repositorio            2 docs, 2 exemplos, 4 testes Python
OK      logs: pasta gravavel                escrita e limpeza de probe OK
OK      PowerShell                          versao 5.1.19041.6456 (>= 5.1)
AVISO   administracao                       nao e administrador; dry-run nao exige, -Executar pode exigir
OK      execution policy (usuario)          RemoteSigned
------  ----------------------------------  -------------------------------------------------------------
 Total: 14 OK, 0 FALHA, 1 AVISO
 RESULTADO: PASSOU
================================================================
 Log gravado em: logs\verificar-workstation.log (caminho relativo a raiz do repo)
```

A saida completa esta em [`exemplos/exemplo-de-saida.txt`](exemplos/exemplo-de-saida.txt)
e o dry-run completo do instalador em
[`exemplos/exemplo-instalador-dryrun.txt`](exemplos/exemplo-instalador-dryrun.txt).
A linha `Executado em` muda a cada execucao (timestamp): a saida nao e
byte-identica entre rodadas, mas o conteudo e deterministico para a mesma
estacao e versao do repositorio.

Outros comandos uteis:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1 -WhatIf  # tabela sem gravar log
powershell -ExecutionPolicy Bypass -File scripts\Configurar-Rede.ps1 -WhatIf         # simulacao padrao do PowerShell
python -m pytest --cov=workstation --cov-report=term-missing                         # cobertura medida
```

### O padrao de seguranca (secao obrigatoria da spec)

Todos os scripts usam:

```powershell
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,   # padrao: ..\config relativo ao script
    [string]$LogPath      # padrao: ..\logs\<etapa>.log
)
```

- Cada acao e chamada por `Aplicar-Acao`, que chama
  `$PSCmdlet.ShouldProcess(...)` e so executa o scriptblock quando
  `-Executar` estiver presente. Sem ele, a acao vira uma linha `[WhatIf]`
  no log (console + arquivo com timestamp `yyyy-MM-dd HH:mm:ss`).
- `-WhatIf` (comum) nao executa acao nenhuma e tambem nao grava o log do
  verificador; o proprio PowerShell emite as linhas "What if:".
- Nenhuma mudanca destrutiva sem confirmacao: a unica remocao do fluxo
  (impressoras temporarias `IMP-TMP-*`) roda so com `-Executar`, dentro do
  filtro de nome.
- Dry-run nao exige administrador; `-Executar` pode exigir (os logs dizem
  quando a falha e privilegio).

A auditoria de conteudo (rodada pelos testes Python e pelo verificador)
confere que nenhum script perdeu `SupportsShouldProcess`,
`$PSCmdlet.ShouldProcess` ou `[switch]$Executar`, e que nenhum contem
`Remove-Item -Recurse -Force` sem guarda de `if`, `curl | iex`/CMD com
download, ou nome real de fabricante.

### O que aprendi

- **`-f` tem precedencia maior que `+` no PowerShell.** A primeira versao
  do relatorio montava o template alinhando strings e aplicando `-f` sem
  parenteses; o operador aplicou no ultimo fragmento e a tabela quebrou
  com `FormatException` (o `}` literal sobrou). O fix foi envolver o
  template completo em parenteses. A Armadilha foi achada na primeira
  execucao real, nao no teste - por isso o exemplo em `exemplos/` e da
  versao corrigida.
- **`@($lista)` falha com `ArgumentException` no PowerShell 5.1 quando a
  lista e `List[object]`.** O parser local do catalogo devolvia a
  subexpressao de array e o verificador acusou `falha ao ler` sem mais
  detalhe. Trocar por `.ToArray()` resolveu; a linha de comentario no
  `Parser-Catalogo.ps1` documenta o motivo para quem for refactorizar.
- **`exit N` dentro de um script chamado com `&` nao mata o parent e
  preenche `$LASTEXITCODE`** (comportamento medido neste host, PowerShell
  5.1.19041.6456). Foi essa mediacao que permitiu o orquestrador ler o
  codigo de saida de cada etapa sem processo filho nem pipe.
- **`ConfirmImpact='High'` sem tratamento faz prompt em cada acao.** Com
  `$ConfirmPreference` padrao (High), o `ShouldProcess` de cada etapa
  pedia confirmacao interativa e o modo padrao travava. O script define
  `$ConfirmPreference = 'None'` no proprio scope e move a confirmacao
  explicita para o `-Executar`; a secao "documente o padrao" ficou no
  help de cada script.
- **O teste de crossover segura o parser PS.** O PowerShell 5.1 nao tem
  YAML embutido e o projeto nao quer modulo; por isso o teste
  `TestParserPowerShell` roda o parser real via subprocess e compara
  campo a campo com o `yaml.safe_load` do PyYAML. Sem esse teste, um
  ajuste "inocente" no parser muda o catalogo inteiro em producao sem
  sinal.

### Limitacoes

O que este projeto **nao** faz, honestamente:

- **Nao aplica GPO nem politicas de dominio.** As quatro politicas que
  exigem HKLM (atualizacao, firewall, senha, auditoria) registram o estado
  desejado em `HKCU:\Software\Politicas\Estacao` e avisam no log que a
  aplicacao efetiva e de GPO/administrador.
- **Nao e parser de YAML generico.** O `Parser-Catalogo.ps1` cobre o
  schema fixo do catalogo (lista plana de escalares); listas aninhadas,
  multi-linha e alias nao sao suportados por escolha.
- **O verificador confere o disco, nao o sistema.** Ele valida
  config/scripts/estrutura/ambiente; o que de fato mudou (DNS, impressora,
  pacotes) fica nos logs das etapas.
- **`-Executar` sem acesso a `\\srv-software` falha com elegancia**: a
  linha vira `ERRO` no log e a estacao segue sem o pacote - nada e
  instalado a meio.
- **Nao desinstala nem faz rollback** do software ja instalado.
- **A saida nao e byte-identica entre execucoes** (timestamp, nome do
  host); o conteudo comparavel e o resultado de cada checagem.

### Licenca

MIT. Ver [LICENSE](LICENSE).

---

## EN

### What it is

Six PowerShell scripts that provision a Windows workstation in five stages
(network, printers, software, policies, final verification), reading three
config files (YAML and JSON, 100% fictional). The default mode is
dry-run: every action goes through `$PSCmdlet.ShouldProcess`, lands in the
log with the `[WhatIf]` prefix, and touches nothing on the machine. Only
the explicit `-Executar` switch applies anything.
`Verificar-Workstation.ps1` closes the loop with a readable
`OK/FALHA/AVISO` report and exit code 0/1.

### Why it was built

Workstation provisioning that is not literally run at work, every day,
does not exist: the technician wants to run what was in yesterday's log
and get a "is workstation X ready?" answer in under a minute, without
opening 12 panels. The value here is not making the changes (any script
changes something); it is guaranteeing that a change only happens with an
explicit switch, that every action is traced to a timestamped log, and
that final verification is separated from execution  -  the same person can
execute and verify, but each one's mode is different and auditable.

### How to run

```powershell
# 1. Dependencies (Python; the PowerShell scripts depend on nothing)
pip install -r requirements.txt

# 2. Validate (tests + content audit of the .ps1 scripts)
python -m pytest tests/ -v
python -m workstation verificar
python -m workstation auditoria

# 3. Verify the workstation (read-only, prints the OK/FALHA/AVISO report)
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1

# 4. Full onboarding in dry-run (changes nothing)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1

# 5. Onboarding for real (applies changes; may need an admin account)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1 -Executar

# Single gate: tests + coverage + verification + dry-run
python tools\verificar_aceite.py
```

Real output of step 3 (run on this host):

```
================================================================
 VERIFICACAO DE WORKSTATION - relatorio de validacao
================================================================
 Executado em : 2026-10-03 19:40:26  (timestamp; muda a cada execucao)
 Estacao      : DESKTOP-MQ2N9CF
 PowerShell   : 5.1.19041.6456
 Modo         : somente leitura (nao altera a estacao)

STATUS  CHECAGEM                            DETALHE
------  ----------------------------------  -------------------------------------------------------------------------------
OK      config: pasta de configuracao       existe (config)
OK      config/dicionario-software.yaml     14 pacotes, 6 campos por pacote
OK      config/perfis-usuario.yaml          4 perfis com bloco de pacotes
OK      config/politicas.json               6 politicas obrigatorias presentes
OK      scripts/Instalar-Workstation.ps1    marcadores de seguranca presentes
OK      scripts/Configurar-Rede.ps1         marcadores de seguranca presentes
OK      scripts/Configurar-Impressoras.ps1  marcadores de seguranca presentes
OK      scripts/Instalar-Software.ps1       marcadores de seguranca presentes
OK      scripts/Aplicar-Politicas.ps1       marcadores de seguranca presentes
OK      scripts/Verificar-Workstation.ps1   marcadores de seguranca presentes
AVISO   estrutura do repositorio            2 docs, 2 exemplos, 4 testes (verifique se docs/exemplos/tests estao presentes)
OK      logs: pasta gravavel                escrita e limpeza de probe OK
OK      PowerShell                          versao 5.1.19041.6456 (>= 5.1)
AVISO   administracao                       nao e administrador; dry-run nao exige, -Executar pode exigir
OK      execution policy (usuario)          RemoteSigned
------  ----------------------------------  -------------------------------------------------------------------------------
 Total: 13 OK, 0 FALHA, 2 AVISO
 RESULTADO: PASSOU
================================================================
 Log gravado em: logs\verificar-workstation.log (caminho relativo a raiz do repo)
```

The full output is in [`exemplos/exemplo-de-saida.txt`](exemplos/exemplo-de-saida.txt)
and the installer's full dry-run in
[`exemplos/exemplo-instalador-dryrun.txt`](exemplos/exemplo-instalador-dryrun.txt).
The `Executado em` line changes on every run (timestamp): output is not
byte-identical across runs, but the content is deterministic for the same
machine and repository version.

Other useful commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1 -WhatIf  # table without writing the log
powershell -ExecutionPolicy Bypass -File scripts\Configurar-Rede.ps1 -WhatIf         # PowerShell's standard simulation
python -m pytest --cov=workstation --cov-report=term-missing                         # measured coverage
```

### The safety pattern (mandatory section of the spec)

All scripts use:

```powershell
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,   # default: ..\config relative to the script
    [string]$LogPath      # default: ..\logs\<stage>.log
)
```

- Each action is invoked through `Aplicar-Acao`, which calls
  `$PSCmdlet.ShouldProcess(...)` and only runs the scriptblock when
  `-Executar` is present. Without it, the action becomes a `[WhatIf]`
  line in the log (console + file with `yyyy-MM-dd HH:mm:ss` timestamp).
- `-WhatIf` (common) executes no action and also skips the verifier's
  log write; PowerShell itself prints the "What if:" lines.
- No destructive change without confirmation: the only removal in the
  flow (temporary printers `IMP-TMP-*`) runs only with `-Executar`,
  inside the name filter.
- Dry-run needs no administrator; `-Executar` may (the logs say when a
  failure is a privilege one).

The content audit (run by the Python tests and by the verifier) checks
that no script lost `SupportsShouldProcess`, `$PSCmdlet.ShouldProcess`
or `[switch]$Executar`, and that none contains
`Remove-Item -Recurse -Force` without an `if` guard, `curl | iex`/CMD
downloading, or a real vendor name.

### What I learned

- **`-f` binds tighter than `+` in PowerShell.** The first version of the
  report built its aligned template by concatenating strings and applying
  `-f` without parentheses; the operator applied to the last fragment and
  the table broke with `FormatException` (a literal `}` was left over).
  The fix was wrapping the full template in parentheses. The trap was
  found on the first real run, not in the tests  -  that is why the example
  in `exemplos/` is from the fixed version.
- **`@($list)` fails with `ArgumentException` in PowerShell 5.1 when the
  list is `List[object]`.** The local catalog parser returned the array
  subexpression and the verifier reported `falha ao ler` with no detail.
  Switching to `.ToArray()` fixed it; the comment line in
  `Parser-Catalogo.ps1` documents the reason for whoever refactors.
- **`exit N` inside a script called with `&` does not kill the parent and
  fills `$LASTEXITCODE`** (behavior measured on this host, PowerShell
  5.1.19041.6456). That measurement is what let the orchestrator read
  each stage's exit code without child processes or pipes.
- **`ConfirmImpact='High'` unhandled prompts on every action.** With the
  default `$ConfirmPreference` (High), every stage's `ShouldProcess`
  asked for interactive confirmation and the default mode hung. The
  scripts set `$ConfirmPreference = 'None'` in their own scope and move
  the explicit confirmation to `-Executar`; the "document the pattern"
  part lives in each script's help block.
- **The crossover test guards the PS parser.** PowerShell 5.1 has no
  built-in YAML and the project wants no module; so the
  `TestParserPowerShell` test runs the real parser via subprocess and
  compares field by field with PyYAML's `yaml.safe_load`. Without that
  test, an "innocent" parser tweak would change the whole catalog in
  production with no signal.

### Limitations

What this project does **not** do, honestly:

- **No GPO or domain policies.** The four policies that need HKLM
  (update, firewall, password, audit) record the desired state in
  `HKCU:\Software\Politicas\Estacao` and log that the effective
  application is GPO/administrator's.
- **Not a generic YAML parser.** `Parser-Catalogo.ps1` covers the
  catalog's fixed schema (flat list of scalars); nested lists,
  multi-line values and aliases are intentionally unsupported.
- **The verifier checks the disk, not the system.** It validates
  config/scripts/structure/environment; what actually changed (DNS,
  printer, packages) is in the stage logs.
- **`-Executar` without access to `\\srv-software` fails gracefully**:
  the line becomes `ERRO` in the log and the machine goes on without
  the package  -  nothing is installed halfway.
- **No uninstall or rollback** of software already installed.
- **Output is not byte-identical across runs** (timestamp, host name);
  the comparable content is each check's result.

### License

MIT. See [LICENSE](LICENSE).

---

## Estrutura / Structure

```
config/
  dicionario-software.yaml   catalogo ficticio (14 pacotes)
  perfis-usuario.yaml        4 perfis (contabilidade, projetista, recepcao, ti)
  politicas.json             6 politicas de workstation
scripts/
  Instalar-Workstation.ps1   orquestrador das 5 etapas
  Configurar-Rede.ps1        DNS, fuso, proxy
  Configurar-Impressoras.ps1 cadastro e padrao da impressora
  Instalar-Software.ps1      pacotes do catalogo (parser local de YAML)
  Aplicar-Politicas.ps1      politicas de usuario e estado desejado em HKCU
  Verificar-Workstation.ps1  relatorio OK/FALHA/AVISO (read-only)
  Parser-Catalogo.ps1        auxiliar: parser minimal do schema do catalogo
dados/                      exemplos invalidos de proposito (usados pelos testes)
docs/
  procedimento-de-preparacao.md   checklist do tecnico, etapa por etapa
  como-verificar-uma-estacao.md   leitura do relatorio e da tabela
exemplos/
  exemplo-de-saida.txt             saida real do Verificar-Workstation
  exemplo-instalador-dryrun.txt    saida real do dry-run completo
src/workstation/           schema, auditoria de conteudo, CLI
tests/                     52 testes (schema, auditoria, CLI, parser PS x PyYAML)
tools/
  verificar_encoding.py      checagem BOM/CJK/U+FFFD antes do commit
  verificar_aceite.py        gate unico: testes + cobertura + verificacao + dry-run
```

Cobertura: medida com `python -m pytest --cov=workstation --cov-report=term-missing`
(o modulo validado vive em `src/workstation`, por isso `--cov=workstation`
e nao `--cov=tests`). Ultimo gate: 89% de cobertura total.

---

<div align="center">
  <sub>Por <a href="https://github.com/KelvinOliveiraCode">Kelvin Oliveira</a> &middot;
  <a href="https://kelvinoliveiracode.github.io/portfolio/">portfolio</a></sub>
</div>
