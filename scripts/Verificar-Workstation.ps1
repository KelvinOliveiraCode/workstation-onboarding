<#
.SYNOPSIS
    Etapa final de onboarding: valida a estacao e emite um relatorio legivel.
.DESCRIPTION
    Rode apenas leitura e checagens: os arquivos de configuracao (schema
    basico em PowerShell; o schema completo e validado pelos testes Python),
    os seis scripts de etapa, a estrutura do repositorio e o ambiente
    (PowerShell, escrita na pasta de log, execution policy). O resultado e
    uma tabela OK/FALHA/AVISO, exibida no console e gravada em arquivo de
    log com timestamp. Sem -Executar? Este script ja e read-only: a unica
    "acao" (gravar o log) passa por $PSCmdlet.ShouldProcess; com -WhatIf a
    tabela e exibida mas o log nao e gravado. Saida de usuario: 0 se nao ha
    FALHA, 1 se ha. Obs.: a linha "Executado em" muda a cada execucao; o
    restante do conteudo e deterministico para a mesma estacao/repo. Este
    script e read-only: -Executar e aceito para a interface uniforme da
    pipeline, mas nao altera nada de diferente.
.PARAMETER Executar
    Aceito pela interface uniforme da pipeline; nao tem efeito extra, pois
    o script e somente leitura.
.PARAMETER WhatIf
    (comum) Exibe a tabela sem gravar o log.
.PARAMETER Confirm
    (comum) Confirmacao; ConfirmImpact=High.
.PARAMETER ConfigDir
    Pasta de configuracao. Padrao: ..\config relativo ao script.
.PARAMETER LogPath
    Arquivo de log com timestamp. Padrao: ..\logs\verificar-workstation.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Verificar-Workstation.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Verificar-Workstation.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\verificar-workstation.log' }

$Script:resultados = @()

function Adicionar-Resultado {
    param([string]$Status, [string]$Checagem, [string]$Detalhe)
    $Script:resultados += ,@($Status, $Checagem, $Detalhe)
}

function Escrever-Log {
    # Loga com timestamp no console e no arquivo (UTF-8 sem BOM).
    param([string]$Mensagem)
    $hora = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $linha = "[$hora] $Mensagem"
    Write-Host $linha
    $dir = Split-Path $LogPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $utf8SemBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($LogPath, $linha + [Environment]::NewLine, $utf8SemBom)
}

$raiz = Split-Path $PSScriptRoot -Parent
$horaExecucao = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$ehAdmin = [bool]([Security.Principal.WindowsIdentity]::GetCurrent().Groups | Where-Object { $_.Value -eq 'S-1-5-32-544' })

# --- checagem: diretorio de configuracao -------------------------------
if (Test-Path $ConfigDir) {
    Adicionar-Resultado 'OK' 'config: pasta de configuracao' "existe ($($ConfigDir.Split('\')[-1]))"
}
else {
    Adicionar-Resultado 'FALHA' 'config: pasta de configuracao' "nao encontrada"
}

# --- checagem: dicionario de software (schema basico em PS) -------------
if (Test-Path (Join-Path $ConfigDir 'dicionario-software.yaml')) {
    try {
        . (Join-Path $PSScriptRoot 'Parser-Catalogo.ps1')
        $doc = Converter-YamlDoCatalogo -Arquivo (Join-Path $ConfigDir 'dicionario-software.yaml')
        $pacotes = @($doc.pacotes)
        $faltando = @()
        foreach ($p in $pacotes) {
            foreach ($campo in @('id', 'nome', 'versao', 'categoria', 'silencioso', 'origem')) {
                if (-not $p.ContainsKey($campo)) { $faltando += "$($p.id):$campo" }
            }
        }
        if ($pacotes.Count -lt 12) {
            Adicionar-Resultado 'FALHA' 'config/dicionario-software.yaml' "$($pacotes.Count) pacotes; minimo esperado: 12"
        }
        elseif ($faltando.Count -gt 0) {
            Adicionar-Resultado 'FALHA' 'config/dicionario-software.yaml' "campos faltando: $($faltando[0])"
        }
        else {
            Adicionar-Resultado 'OK' 'config/dicionario-software.yaml' "$($pacotes.Count) pacotes, 6 campos por pacote"
        }
    }
    catch {
        Adicionar-Resultado 'FALHA' 'config/dicionario-software.yaml' "falha ao ler: $($_.Exception.Message)"
    }
}
else {
    Adicionar-Resultado 'FALHA' 'config/dicionario-software.yaml' 'arquivo nao encontrado'
}

# --- checagem: perfis de usuario (contagem basica; schema completo em Python) ---
if (Test-Path (Join-Path $ConfigDir 'perfis-usuario.yaml')) {
    $textoPerfis = Get-Content -Path (Join-Path $ConfigDir 'perfis-usuario.yaml') -Raw
    $nPerfis = ([regex]::Matches($textoPerfis, '(?m)^\s*-\s+id:\s+\S+')).Count
    $nBlocoPacotes = ([regex]::Matches($textoPerfis, '(?m)^\s*pacotes:\s*$')).Count
    if ($nPerfis -ge 4 -and $nBlocoPacotes -ge 4) {
        Adicionar-Resultado 'OK' 'config/perfis-usuario.yaml' "$nPerfis perfis com bloco de pacotes"
    }
    else {
        Adicionar-Resultado 'FALHA' 'config/perfis-usuario.yaml' "$nPerfis perfis, $nBlocoPacotes blocos de pacotes (esperado >= 4 de cada)"
    }
}
else {
    Adicionar-Resultado 'FALHA' 'config/perfis-usuario.yaml' 'arquivo nao encontrado'
}

# --- checagem: politicas (JSON nativo do PowerShell) --------------------
if (Test-Path (Join-Path $ConfigDir 'politicas.json')) {
    try {
        $politicas = Get-Content -Path (Join-Path $ConfigDir 'politicas.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $faltandoPol = @()
        foreach ($chave in @('bloqueio_tela', 'execution_policy_powershell', 'windows_update', 'firewall', 'senha_minima', 'auditoria')) {
            if (-not $politicas.PSObject.Properties.Name.Contains($chave)) { $faltandoPol += $chave }
        }
        if ($faltandoPol.Count -gt 0) {
            Adicionar-Resultado 'FALHA' 'config/politicas.json' "chaves faltando: $($faltandoPol -join ', ')"
        }
        else {
            Adicionar-Resultado 'OK' 'config/politicas.json' '6 politicas obrigatorias presentes'
        }
    }
    catch {
        Adicionar-Resultado 'FALHA' 'config/politicas.json' "JSON invalido: $($_.Exception.Message)"
    }
}
else {
    Adicionar-Resultado 'FALHA' 'config/politicas.json' 'arquivo nao encontrado'
}

# --- checagem: os seis scripts de etapa ---------------------------------
$scriptsObrigatorios = @(
    'Instalar-Workstation.ps1',
    'Configurar-Rede.ps1',
    'Configurar-Impressoras.ps1',
    'Instalar-Software.ps1',
    'Aplicar-Politicas.ps1',
    'Verificar-Workstation.ps1'
)
foreach ($nome in $scriptsObrigatorios) {
    $caminho = Join-Path $PSScriptRoot $nome
    if (-not (Test-Path $caminho)) {
        Adicionar-Resultado 'FALHA' "scripts/$nome" 'arquivo nao encontrado'
        continue
    }
    $conteudo = Get-Content -Path $caminho -Raw
    $faltam = @()
    if ($conteudo -notmatch 'SupportsShouldProcess') { $faltam += 'SupportsShouldProcess' }
    if ($conteudo -notmatch [regex]::Escape('$PSCmdlet.ShouldProcess')) { $faltam += 'ShouldProcess' }
    if ($conteudo -notmatch 'Executar') { $faltam += 'Executar' }
    if ($faltam.Count -gt 0) {
        Adicionar-Resultado 'FALHA' "scripts/$nome" "sem marcador: $($faltam -join ', ')"
    }
    else {
        Adicionar-Resultado 'OK' "scripts/$nome" 'marcadores de seguranca presentes'
    }
}

# --- checagem: estrutura do repositorio ----------------------------------
$nDocs = @(Get-ChildItem -Path (Join-Path $raiz 'docs') -Filter '*.md' -File -ErrorAction SilentlyContinue).Count
$nExemplos = @(Get-ChildItem -Path (Join-Path $raiz 'exemplos') -Filter '*.txt' -File -ErrorAction SilentlyContinue).Count
$nTestes = @(Get-ChildItem -Path (Join-Path $raiz 'tests') -Filter '*.py' -File -ErrorAction SilentlyContinue).Count
if ($nDocs -ge 2 -and $nExemplos -ge 1 -and $nTestes -ge 1 -and (Test-Path (Join-Path $raiz 'README.md')) -and (Test-Path (Join-Path $raiz 'LICENSE'))) {
    Adicionar-Resultado 'OK' 'estrutura do repositorio' "$nDocs docs, $nExemplos exemplos, $nTestes testes Python"
}
else {
    Adicionar-Resultado 'AVISO' 'estrutura do repositorio' "$nDocs docs, $nExemplos exemplos, $nTestes testes (verifique se docs/exemplos/tests estao presentes)"
}

# --- checagem: pasta de log gravavel -------------------------------------
$dirLog = Split-Path $LogPath -Parent
if (-not (Test-Path $dirLog)) { New-Item -ItemType Directory -Path $dirLog -Force | Out-Null }
$probe = Join-Path $dirLog "probe-$([guid]::NewGuid().ToString('N')).tmp"
try {
    [System.IO.File]::WriteAllText($probe, 'ok', (New-Object System.Text.UTF8Encoding($false)))
    if (Test-Path $probe) {
        # File.Delete em vez de Remove-Item: em -WhatIf o cmdlet e suprimido
        # e a probe ficaria para tras; a limpeza da propria probe faz parte
        # da checagem e nao e uma acao de onboarding.
        [System.IO.File]::Delete($probe)
        Adicionar-Resultado 'OK' 'logs: pasta gravavel' "escrita e limpeza de probe OK"
    }
    else {
        Adicionar-Resultado 'FALHA' 'logs: pasta gravavel' 'probe nao apareceu apos escrita'
    }
}
catch {
    Adicionar-Resultado 'FALHA' 'logs: pasta gravavel' "falha de escrita: $($_.Exception.Message)"
}

# --- checagem: versao do PowerShell --------------------------------------
$versaoPS = $PSVersionTable.PSVersion
if ($versaoPS -ge [version]'5.1.0') {
    Adicionar-Resultado 'OK' 'PowerShell' "versao $versaoPS (>= 5.1)"
}
else {
    Adicionar-Resultado 'FALHA' 'PowerShell' "versao $versaoPS e menor que 5.1"
}

# --- checagem: privileges de administracao (contexto, nao requisito) ------
if ($ehAdmin) {
    Adicionar-Resultado 'OK' 'administracao' 'usuario atual e administrador'
}
else {
    Adicionar-Resultado 'AVISO' 'administracao' 'nao e administrador; dry-run nao exige, -Executar pode exigir'
}

# --- checagem: execution policy do usuario --------------------------------
$polUsr = Get-ExecutionPolicy -Scope CurrentUser
if ($polUsr -in @('Restricted', 'AllSigned', 'Undefined')) {
    Adicionar-Resultado 'AVISO' 'execution policy (usuario)' "$polUsr; os scripts deste repo rodam com -ExecutionPolicy Bypass"
}
else {
    Adicionar-Resultado 'OK' 'execution policy (usuario)' $polUsr
}

# --- relatorio ------------------------------------------------------------
$linhasRelatorio = @()
$linhasRelatorio += '================================================================'
$linhasRelatorio += ' VERIFICACAO DE WORKSTATION - relatorio de validacao'
$linhasRelatorio += '================================================================'
$linhasRelatorio += " Executado em : $horaExecucao  (timestamp; muda a cada execucao)"
$linhasRelatorio += " Estacao      : $env:COMPUTERNAME"
$linhasRelatorio += " PowerShell   : $versaoPS"
$linhasRelatorio += ' Modo         : somente leitura (nao altera a estacao)'
$linhasRelatorio += ''

$larguraStatus = 6
$larguraChecagem = 0
$larguraDetalhe = 0
foreach ($r in $Script:resultados) {
    if ($r[1].Length -gt $larguraChecagem) { $larguraChecagem = $r[1].Length }
    if ($r[2].Length -gt $larguraDetalhe) { $larguraDetalhe = $r[2].Length }
}
$linhasRelatorio += ('{0,-6}  {1,-' + $larguraChecagem + '}  {2}') -f 'STATUS', 'CHECAGEM', 'DETALHE'
$linhasRelatorio += ('-' * $larguraStatus) + '  ' + ('-' * $larguraChecagem) + '  ' + ('-' * $larguraDetalhe)
foreach ($r in $Script:resultados) {
    $linhasRelatorio += ('{0,-6}  {1,-' + $larguraChecagem + '}  {2}') -f $r[0], $r[1], $r[2]
}
$linhasRelatorio += ('-' * $larguraStatus) + '  ' + ('-' * $larguraChecagem) + '  ' + ('-' * $larguraDetalhe)

$nOk = @($Script:resultados | Where-Object { $_[0] -eq 'OK' }).Count
$nFalha = @($Script:resultados | Where-Object { $_[0] -eq 'FALHA' }).Count
$nAviso = @($Script:resultados | Where-Object { $_[0] -eq 'AVISO' }).Count
$linhasRelatorio += " Total: $nOk OK, $nFalha FALHA, $nAviso AVISO"
if ($nFalha -eq 0) { $veredicto = 'PASSOU' } else { $veredicto = 'FALHOU' }
$linhasRelatorio += " RESULTADO: $veredicto"
$linhasRelatorio += '================================================================'

foreach ($linha in $linhasRelatorio) { Write-Host $linha }

if ($PSCmdlet.ShouldProcess('gravar relatorio em arquivo de log')) {
    $dirLog2 = Split-Path $LogPath -Parent
    if (-not (Test-Path $dirLog2)) { New-Item -ItemType Directory -Path $dirLog2 -Force | Out-Null }
    $utf8SemBom = New-Object System.Text.UTF8Encoding($false)
    $conteudo = @()
    foreach ($linha in $linhasRelatorio) {
        $conteudo += "[$horaExecucao] $linha"
    }
    [System.IO.File]::AppendAllText($LogPath, ($conteudo -join [Environment]::NewLine) + [Environment]::NewLine, $utf8SemBom)
    Write-Host " Log gravado em: logs\verificar-workstation.log (caminho relativo a raiz do repo)"
}
else {
    Write-Host " Log NAO gravado (modo -WhatIf). Use -ConfigDir/-LogPath para onde gravar."
}

if ($nFalha -gt 0) { exit 1 }
exit 0
