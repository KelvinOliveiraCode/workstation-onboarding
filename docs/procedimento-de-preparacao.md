# Procedimento de preparo de estacao

Checklist que um tecnico segue, na ordem, para preparar uma estacao
Windows do zero com este repositorio. Cada etapa tem o comando, a saida
esperada e a verificacao que confirma que a etapa passou. Nao pule etapas:
a verificacao final da etapa 5 relê os arquivos de configuracao e os
scripts, mas nao substitui a leitura de cada log.

Todo o fluxo roda em PowerShell. Nenhum comando deste procedimento precisa
de administrador no modo padrao (dry-run); o modo de execucao (`-Executar`)
pode exigir administracao conforme a etapa.

## 0. Posicao inicial

- Estacao ligada, logada com a conta do tecnico.
- Repositorio clonado (ou copiado) para um caminho sem espaco.
- Rede com acesso a pasta de software interna e ao servidor de impressao
  (nos testes deste repositorio, ambos sao ficticios: `\\srv-software` e
  `\\srv-printa-01`).

Verificacao: o repositorio tem `config/` com 3 arquivos, `scripts/` com 7
arquivos `.ps1` e `tests/` com testes Python.

## 1. Conferir a configuracao antes de tocar em qualquer estacao

```powershell
python -m workstation verificar
```

Saida esperada:

```
workstation-onboarding: validacao de configuracao
[ OK ] dicionario-software.yaml: 14 pacotes
[ OK ] perfis-usuario.yaml: 4 perfis
[ OK ] politicas.json: 6/6 politicas
[ OK ] coerencia: todos os pacotes referenciados existem no dicionario
RESUMO: 0 erro(s) | pacotes=14 perfis=4 politicas=6
```

Verificacao: `RESUMO: 0 erro(s)`. Se aparecer `[ ERRO]`, corrija o arquivo
de configuracao antes de seguir: onboarding com catalogo errado instala a
estacao inteira errada e a correcao vira reimplantacao.

## 2. Rodar o onboarding completo em dry-run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1
```

Saida esperada: 5 etapas, todas com `OK (codigo 0)`, cada acao logada com
o prefixo `[WhatIf]` e o relatorio final do verificador com
`RESULTADO: PASSOU`. Exemplo real em
`exemplos/exemplo-instalador-dryrun.txt`.

Verificacao:

- Numa linha de cada etapa, confirmar `OK (codigo 0)`.
- Nao pode existir nenhuma linha `EXECUTADO` nem `ERRO` nesta fase.
- O log em `logs\instalar-workstation.log` (e os logs das etapas) contem
  apenas linhas `[WhatIf]` para as acoes.

Por que o dry-run antes? O modo padrao nao altera nada, mas o log dele e o
mapa do que o `-Executar` vai executar. Conferir o mapa antes de executar
e a parte mais barata de se evitar uma estacao fora do padrao.

## 3. Executar o onboarding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Instalar-Workstation.ps1 -Executar
```

Saida esperada: as etapas trocam as linhas `[WhatIf]` por `EXECUTADO` (ou
`ERRO` com a mensagem da excecao), e a etapa 5/5 emite o relatorio do
verificador de novo.

Verificacao por etapa (leia os logs em `logs/`):

- `logs\configurar-rede.log`: DNS e fuso aplicados no adaptador primario;
  proxy em HKCU. Sem administracao, a definicao de DNS pode falhar - a
  linha `ERRO` aparece no log e a estacao segue com o restante da etapa.
- `logs\configurar-impressoras.log`: impressora `IMP-ESCR-001` cadastrada
  e definida como padrao. Se o share nao estiver acessivel, a linha fica
  `ERRO` e a estacao fica sem impressora padrao - resolver antes de
  entregar.
- `logs\instalar-software.log`: 14 pacotes. Pacote ja instalado com a
  mesma versao sai como `AVISO ... ja instalada, pulando`. Pacote com
  `silencioso: false` sai como `AVISO ... instalacao interativa nao e
  feita pelo onboarding` (ex.: `cliente-bancodados`).
- `logs\aplicar-politicas.log`: bloqueio de tela e execution policy
  aplicados direto (escopo de usuario); as quatro politicas que exigem
  HKLM ficam registradas em `HKCU:\Software\Politicas\Estacao` com a linha
  `AVISO ... requer administrador/GPO`.

Regra de seguranca: nenhuma acao destrutiva roda sem `-Executar`. A
limpeza de impressoras temporarias (`IMP-TMP-*`) so ocorre nesta fase e
dentro do filtro de nome - nunca por prefixo aberto.

## 4. Verificar a estacao

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Verificar-Workstation.ps1
```

Saida esperada: tabela `OK/FALHA/AVISO` com `RESULTADO: PASSOU` e codigo de
saida 0. Exemplo real em `exemplos/exemplo-de-saida.txt`.

Verificacao:

- `0 FALHA`. Qualquer `FALHA` impede a entrega; o detalhe da linha diz o
  que corrigir.
- `AVISO` nao impede a entrega: o aviso de administracao e esperado sem
  conta elevada; o aviso de execution policy do usuario indica que a
  aplicacao futura de politicas de maquina seguira o GPO.

## 5. Conferir os logs (rastreabilidade)

Cada script grava em `logs\<nome-da-etapa>.log` com timestamp na forma
`yyyy-MM-dd HH:mm:ss`. Para auditoria de uma implantacao, o conjunto de
logs das 5 etapas da estacao e o rastro completo do que rodou e em que
momento. Os logs ficam fora do versionamento (`.gitignore` cobre `*.log`).

## 6. Entregar

- Estacao com `RESULTADO: PASSOU` no passo 4.
- Logs das 5 etapas arquivados no chamado do chamado de implantacao.
- Politicas de HKLM pendentes (passo 3) documentadas no chamado como
  dependencia de GPO/administrador.

## O que eu aprendi com este procedimento

- **O dry-run gera o mapa, o `-Executar` so executa.** No primeiro round
  deste projeto, o script principal nao tinha separacao dos dois modos e
  uma execucao de teste alterou o fuso da estacao de trabalho. A separacao
  (`ShouldProcess` + `-Executar` explicito, nenhum efeito colateral fora do
  gate) nasceu desse incidente - e o teste `test_auditoria.py` existe para
  garantir que nenhum script perca o gate no futuro.
- **A checagem de PS nao substitui a checagem de schema.** O
  `Verificar-Workstation.ps1` confere estrutura (arquivos existem, campos
  estao presentes, JSON parseia); o schema completo (tipos, ranges,
  coerencia entre perfis e catalogo) vive em `tests/test_configuracao.py`.
  Conferir as duas e mais barato que descobrir um `silencioso: "sim"` na
  estacao 14.
- **Politicas de maquina honestas.** Em vez de fingir que firewall e
  politica de senha aplicam sem administrador, o script registra o estado
  desejado em HKCU e avisa. O resultado visivel no log vale mais que um
  `OK` enganoso.
