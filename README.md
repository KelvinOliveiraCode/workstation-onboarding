# workstation-onboarding

<img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/PowerShell-5.1%2B-blue?style=flat-square" alt="PowerShell">
<img src="https://img.shields.io/badge/testes-52%20passando-brightgreen?style=flat-square" alt="Testes">
<img src="https://img.shields.io/badge/cobertura-89%25-yellowgreen-brightgreen?style=flat-square" alt="Cobertura">
<img src="https://img.shields.io/badge/deps-PyYAML%20apenas-blue?style=flat-square" alt="Dep">
<img src="https://img.shields.io/badge/licenca-MIT-yellow?style=flat-square" alt="Licenca">
<img src="https://img.shields.io/badge/plataforma-Windows-blue?style=flat-square" alt="Windows">

Scripts PowerShell que preparam uma estacao Windows do zero: rede, impressoras, software, politicas e verificacao final. Modo dry-run por padrao; so muda alguma coisa com `-Executar`.

## Problema / Por que existe

Provisionar uma estacao Windows exige repetir a mesma sequencia: configurar rede, mapear impressoras, instalar pacotes, aplicar politicas e conferir se ficou correto. Quando esse fluxo nao e executado todo dia, o tecnico esquece a ordem, testa na maquina errada ou altera algo sem querer. O risco maior e aplicar uma mudanca antes de verificar se ela e necessaria.

Este projeto resolve isso separando verificacao de execucao e exigindo um switch explicito (`-Executar`) para qualquer alteracao. O modo padrao e dry-run: cada acao aparece no log com o prefixo `[WhatIf]` e nao toca na estacao.

## O que faz

Seis scripts PowerShell executam cinco etapas lidas de tres arquivos de configuracao (YAML e JSON, dados ficticios):

- `Configurar-Rede.ps1` - DNS, fuso horario, proxy
- `Configurar-Impressoras.ps1` - cadastro e impressora padrao
- `Instalar-Software.ps1` - pacotes do catalogo (parser YAML local, sem modulo)
- `Aplicar-Politicas.ps1` - politica de usuario e estado desejado em `HKCU:\Software\Politicas\Estacao`
- `Verificar-Workstation.ps1` - relatorio `OK/FALHA/AVISO`, somente leitura, codigo de saida 0/1
- `Instalar-Workstation.ps1` - orquestrador que chama as etapas anteriores em ordem

O catalogo contem 14 pacotes ficticios divididos em 5 categorias (oficio, seguranca, dados, produtividade, rede, sistema). Ha 4 perfis de usuario (contabilidade, projetista, recepcao, ti) e 6 politicas obrigatorias (bloqueio de tela, execution policy do PowerShell, Windows Update, firewall, senha minima, auditoria).

## Stack

- PowerShell 5.1+ (scripts; nenhuma dependencia externa)
- Python 3.10+ (CLI, validacao de configuracao, auditoria de scripts, testes)
- PyYAML >= 6.0 (unica dependencia Python, usada pelos testes e pela CLI)
- pytest >= 7.4 e pytest-cov >= 4.1 (dev)

## Como funciona

Cada script usa `SupportsShouldProcess = $true` e `ConfirmImpact = 'High'`, com o parametro `[switch]$Executar`. Toda acao passa por `Aplicar-Acao`, que chama `$PSCmdlet.ShouldProcess(...)`. Sem `-Executar`, a acao vira uma linha `[WhatIf]` no log e nada e alterado. Com `-Executar`, a acao e executada de verdade e pode exigir administrador.

O `Verificar-Workstation.ps1` fecha o ciclo: checa config, scripts, estrutura, logs e ambiente, imprime uma tabela `OK/FALHA/AVISO` e retorna 0 ou 1.

A validacao do lado Python faz tres coisas:

1. `python -m workstation verificar` - valida `dicionario-software.yaml`, `perfis-usuario.yaml` e `politicas.json` contra o esquema e cruza perfis com o catalogo (todo pacote referenciado deve existir)
2. `python -m workstation auditoria` - confere que nenhum script perdeu `SupportsShouldProcess`, `$PSCmdlet.ShouldProcess` ou `[switch]$Executar`, e que nenhum contem `Remove-Item -Recurse -Force` sem guarda, `curl | iex`, CMD baixando algo ou nome real de fabricante
3. Testes Python - 52 testes (schema, auditoria, CLI, crossover parser PowerShell x PyYAML)

Cobertura medida: 89% total (limite exigido: 70%).

## Como rodar

```powershell
# 1. Dependencias Python
pip install -r requirements.txt

# 2. Validar configuracao e scripts
python -m workstation verificar
python -m workstation auditoria

# 3. Verificar a estacao (somente leitura, gera relatorio OK/FALHA/AVISO)
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1

# 4. Onboarding completo em dry-run (nao altera nada)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1

# 5. Onboarding de fato (aplica as mudancas; pode exigir administrador)
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1 -Executar

# Gate unico de aceitacao: testes + cobertura + verificacao + dry-run
python tools\verificar_aceite.py
```

Saida real do passo 3 (executado neste host):

```
==================================================================
 VERIFICACAO DE WORKSTATION - relatorio de validacao
==================================================================
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
==================================================================
 Log gravado em: logs\verificar-workstation.log
```

A linha `Executado em` muda a cada execucao (timestamp): a saida nao e byte-identica entre rodadas, mas o conteudo e deterministico para a mesma estacao e versao do repositorio. A saida completa esta em `exemplos/exemplo-de-saida.txt` e o dry-run completo do instalador em `exemplos/exemplo-instalador-dryrun.txt`.

## Estrutura do projeto

```
config/
  dicionario-software.yaml   catalogo ficticio (14 pacotes, 6 campos cada)
  perfis-usuario.yaml        4 perfis (contabilidade, projetista, recepcao, ti)
  politicas.json             6 politicas de workstation
scripts/
  Instalar-Workstation.ps1   orquestrador das 5 etapas
  Configurar-Rede.ps1        DNS, fuso horario, proxy
  Configurar-Impressoras.ps1 cadastro e impressora padrao
  Instalar-Software.ps1      pacotes do catalogo (parser YAML local)
  Aplicar-Politicas.ps1      politicas de usuario e estado desejado em HKCU
  Verificar-Workstation.ps1  relatorio OK/FALHA/AVISO (somente leitura)
  Parser-Catalogo.ps1        auxiliar: parser minimal do schema do catalogo
dados/                      exemplos invalidos de proposito (usados pelos testes)
docs/
  procedimento-de-preparacao.md checklist do tecnico, etapa por etapa
  como-verificar-uma-estacao.md leitura do relatorio e da tabela
exemplos/
  exemplo-de-saida.txt           saida real do Verificar-Workstation
  exemplo-instalador-dryrun.txt  saida real do dry-run completo
src/workstation/            schema, auditoria de conteudo, CLI (modulo Python)
tests/                      52 testes (schema, auditoria, CLI, parser PS x PyYAML)
tools/
  verificar_encoding.py      checagem BOM/CJK/U+FFFD antes do commit
  verificar_aceite.py        gate unico: testes + cobertura + verificacao + dry-run
```

Cobertura medida com `python -m pytest --cov=workstation --cov-report=term-missing` (o modulo validado vive em `src/workstation`).

## Trade-offs e decisoes

- **Dry-run por padrao com `-Executar` para aplicar.** Custo: o tecnico tem que lembrar do switch. Ganho: impossibilidade de alterar a estacao por acidente, e cada acao fica registrada no log com timestamp.
- **Parser YAML local em PowerShell 5.1.** PowerShell 5.1 nao tem YAML embutido e o projeto nao quer instalar modulo. Ganho: zero dependencias nos scripts. Custo: so suporta o schema fixo do catalogo (lista plana de escalares); listas aninhadas, multi-linha e alias nao sao suportados.
- **Politicas gravadas em `HKCU`, não GPO.** As quatro politicas que exigem HKLM registram o estado desejado em `HKCU:\Software\Politicas\Estacao` e avisam no log que a aplicacao efetiva e de GPO/administrador. Ganho: funciona sem direitos de dominio. Custo: nao aplica politica de dominio de verdade.
- **Verificacao separada da execucao.** O verificador confere o disco, não o sistema: valida config/scripts/estrutura/ambiente. O que de fato mudou (DNS, impressora, pacotes) fica nos logs das etapas. Ganho: auditoria independente de quem executou. Custo: nao diz se o DNS esta resolvendo de verdade, apenas se o script foi executado.
- **Saida nao e byte-identica entre execucoes** (timestamp, nome do host). O conteudo comparavel e o resultado de cada checagem. Ganho: rastreabilidade por execucao. Custo: nao e possivel diff de saidas direto.

## Limitações conhecidas

- Nao aplica GPO nem politicas de dominio. As politicas que exigem HKLM registram o estado desejado em `HKCU:\Software\Politicas\Estacao` e avisam no log que a aplicacao efetiva e de GPO/administrador.
- Nao e parser de YAML generico. O `Parser-Catalogo.ps1` cobre o schema fixo do catalogo (lista plana de escalares); listas aninhadas, multi-linha e alias nao sao suportados por escolha.
- O verificador confere o disco, nao o sistema. Ele valida config/scripts/estrutura/ambiente; o que de fato mudou (DNS, impressora, pacotes) fica nos logs das etapas.
- `-Executar` sem acesso a `\\srv-software` falha com elegancia: a linha vira `ERRO` no log e a estacao segue sem o pacote - nada e instalado a meio.
- Nao desinstala nem faz rollback do software ja instalado.
- A saida nao e byte-identica entre execucoes (timestamp, nome do host); o conteudo comparavel e o resultado de cada checagem.

## Licenca

MIT. Ver [LICENSE](LICENSE).

## Autor

Kelvin Oliveira - https://github.com/KelvinOliveiraCode - https://kelvinoliveiracode.github.io/portfolio/
