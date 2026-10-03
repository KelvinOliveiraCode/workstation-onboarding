# Como verificar uma estacao

Guia de leitura do `scripts\Verificar-Workstation.ps1`: o que ele checa,
o que cada status significa, como interpretar o resultado e quando
reexecutar.

## O comando

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1
```

O script e somente leitura: nada na estacao e modificado. A unica escrita e
o proprio relatorio, em `logs\verificar-workstation.log` (com timestamp em
cada linha). O param `-WhatIf` exibe a tabela sem gravar o log. Os
parametros `-ConfigDir` e `-LogPath` permitem trocar a pasta de
configuracao e o destino do log; os padroes sao relativos ao script
(`..\config` e `..\logs\verificar-workstation.log`).

Codigo de saida: `0` quando nao ha `FALHA`, `1` quando ha. Isso permite
encadear em pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1
if ($LASTEXITCODE -ne 0) { Write-Error "estacao nao verificada" }
```

## O que cada status significa

| Status | Significado | O que fazer |
|--------|-------------|-------------|
| `OK` | A checagem passou. | Nada. |
| `AVISO` | Contexto que nao impede a entrega. | Ler o detalhe; agir se for da sua execucao. |
| `FALHA` | A checagem nao passou; a estacao ou o repo estao incompletos. | Corrigir e reexecutar; nao entregar. |

As checagens em ordem de saida:

1. **pasta de configuracao** - existe a `config/` (ou o `-ConfigDir` dado).
2. **dicionario-software.yaml** - lido com o parser local
   (`Parser-Catalogo.ps1`); exige 12+ pacotes e os 6 campos por pacote.
   Falha aqui costuma ser typo de indentacao no YAML.
3. **perfis-usuario.yaml** - contagem basica: 4+ perfis e 4+ blocos de
   `pacotes:`. O schema completo (tipos, campos obrigatorios, ids unicos,
   coerencia com o catalogo) e validado pelos testes Python, nao aqui.
4. **politicas.json** - parseado com `ConvertFrom-Json` nativo; as 6
   chaves obrigatorias precisam estar presentes.
5. **seis scripts de etapa** - existem e contem os marcadores de seguranca
   (`SupportsShouldProcess`, `$PSCmdlet.ShouldProcess`, `Executar`). Esta
   checagem protege contra a edicao manual de um script de campo que
   apaga o gate de seguranca.
6. **estrutura do repositorio** - docs, exemplos e testes presentes
   (aparece como `AVISO` se faltar, porque repositorio parcial e comum em
   clone local; `FALHA` so se o teste/infra critica sumir).
7. **pasta de log gravavel** - escreve e limpa um arquivo de probe.
8. **PowerShell >= 5.1** - os scripts usam `CmdletBinding` avancado.
9. **administracao** - contexto: dry-run nao exige; `-Executar` pode.
10. **execution policy do usuario** - `AVISO` quando restritiva, com a
    observacao que os scripts rodam com `-ExecutionPolicy Bypass`.

## Lendo um resultado real

Fragmento de `exemplos/exemplo-de-saida.txt` (saida real deste host):

```
 Executado em : 2026-10-03 19:35:13  (timestamp; muda a cada execucao)
 Estacao      : DESKTOP-MQ2N9CF
 PowerShell   : 5.1.19041.6456
 Modo         : somente leitura (nao altera a estacao)

STATUS  CHECAGEM                            DETALHE
------  ----------------------------------  -------------------------------------------------------------------------------
OK      config: pasta de configuracao       existe (config)
OK      config/dicionario-software.yaml     14 pacotes, 6 campos por pacote
...
AVISO   estrutura do repositorio            0 docs, 0 exemplos, 4 testes (verifique se docs/exemplos/tests estao presentes)
...
 Total: 13 OK, 0 FALHA, 2 AVISO
 RESULTADO: PASSOU
```

Duas observacoes sobre comparacao entre execucoes:

- A linha `Executado em` **muda a cada execucao** (timestamp do momento).
  O restante do conteudo e deterministico para a mesma estacao e a mesma
  versao do repositorio: duas rodadas seguidas diferem apenas no
  timestamp. Por isso a saida nao e byte-identica entre execucoes, mas o
  resultado comparavel e.
- O nome da estacao (`Estacao`) e o nome do host; em outra maquina a linha
  muda, e isso e esperado, nao e divergencia de resultado.

## Quando reexecutar

- Depois de qualquer correcao de configuracao (o verificador relê os 3
  arquivos a cada execucao).
- Depois de clonar o repositorio em outra estacao (a checagem de estrutura
  e a de scripts dependem do checkout estar completo).
- Antes de cada execucao com `-Executar`: a checagem de scripts garante
  que o gate de seguranca segue inteiro na copia local.

## O que o verificador nao confere

- O estado real do sistema (DNS aplicado, impressora cadastrada, pacotes
  instalados, politicas ativas). Isso fica no log das etapas de
  execucao: `logs\*.log`. O verificador confere o que esta em disco
  (repo + config + ambiente) e o ambiente minimo; o log confere o que
  mudou.
- O schema completo dos YAML: tipos e ranges sao dominio dos testes
  Python (`tests/test_configuracao.py`), rodados com
  `python -m pytest tests/ -v`.
- Politicas de dominio: se a estacao estiver em dominio, o GPO pode
  sobrescrever o que o script escreveu; o log da etapa 4 mostra quais
  politicas ficaram apenas registradas em HKCU.

## Decisao que este design tomou (e a consequencia)

O verificador so valida os 6 scripts obrigatorios, e nao qualquer `.ps1`
da pasta. O motivo: `Parser-Catalogo.ps1` e um auxiliar sem gate de
seguranca por natureza (nao muda nada) e nao deveria ser penalizado por
nao ter `[switch]$Executar`. A consequencia: um script de etapa novo
precisa ser adicionado a `SCRIPTS_OBRIGATORIOS` (em
`src/workstation/auditoria.py`) e a lista embutida no proprio
`Verificar-Workstation.ps1`. O teste de auditoria cobre esse par de
listas: se um script sumir do repo, o teste falha antes do verificador.
