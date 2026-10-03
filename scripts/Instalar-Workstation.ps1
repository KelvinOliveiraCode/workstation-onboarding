<#
.SYNOPSIS
    Script principal de onboarding: prepara uma estacao Windows do zero.
.DESCRIPTION
    Orquestra as quatro etapas de configuracao (rede, impressoras, software,
    politicas) e termina com a verificacao final do Verificar-Workstation.
    Secao de seguranca: cada etapa e uma acao passada por
    $PSCmdlet.ShouldProcess. Sem -Executar (modo padrao, dry-run) as etapas
    rodam apenas em dry-run e NAO alteram a estacao; o log registra cada
    acao com o prefixo [WhatIf] e timestamp. Com -Executar as etapas aplicam
    de fato. O codigo de saida e 1 se alguma etapa falhou ou se a
    verificacao final falhou, e 0 caso contrario.
.PARAMETER Executar
    Quando presente, as etapas aplicam mudancas de fato. Sem ele (padrao),
    tudo fica em dry-run.
.PARAMETER WhatIf
    (comum) NAO executa nenhuma etapa; so loga o que seria feito.
.PARAMETER Confirm
    (comum) Confirmacao por acao; ConfirmImpact=High.
.PARAMETER ConfigDir
    Pasta de configuracao passada as etapas. Padrao: ..\config relativo ao
    script.
.PARAMETER LogPath
    Arquivo de log com timestamp. Padrao: ..\logs\instalar-workstation.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Instalar-Workstation.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Instalar-Workstation.ps1 -Executar
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\instalar-workstation.log' }

$modo = 'dry-run'
if ($Executar) { $modo = 'execucao' }
$falhas = 0

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

# Argumentos passados as etapas: -ConfigDir sempre; -Executar/-WhatIf
# apenas quando pedidos. O padrao (sem os dois) deixa a etapa em dry-run.
# O verificador nao recebe -Executar: ele e read-only e o unico "parametro
# de acao" dele e o comum -WhatIf.
$paramsEtapa = @{ ConfigDir = $ConfigDir }
if ($Executar) { $paramsEtapa.Executar = $true }
if ($PSBoundParameters.ContainsKey('WhatIf')) { $paramsEtapa.WhatIf = $true }
$paramsVerificar = @{ ConfigDir = $ConfigDir }
if ($PSBoundParameters.ContainsKey('WhatIf')) { $paramsVerificar.WhatIf = $true }

$etapas = @(
    @{ Nome = 'Rede';        Script = 'Configurar-Rede.ps1' },
    @{ Nome = 'Impressoras'; Script = 'Configurar-Impressoras.ps1' },
    @{ Nome = 'Software';    Script = 'Instalar-Software.ps1' },
    @{ Nome = 'Politicas';   Script = 'Aplicar-Politicas.ps1' }
)

Escrever-Log "=== Instalar-Workstation: inicio (modo: $modo) ==="

$indice = 0
foreach ($etapa in $etapas) {
    $indice++
    $caminhoEtapa = Join-Path $PSScriptRoot $etapa.Script
    Escrever-Log "ETAPA $indice/5: $($etapa.Nome) ($($etapa.Script))"
    if ($PSCmdlet.ShouldProcess("executar etapa $($etapa.Nome) via $($etapa.Script)")) {
        & $caminhoEtapa @paramsEtapa
        $codigo = $LASTEXITCODE
        if ($codigo -eq 0) {
            Escrever-Log "ETAPA $indice/5: $($etapa.Nome) OK (codigo 0)"
        }
        else {
            $falhas++
            Escrever-Log "ETAPA $indice/5: $($etapa.Nome) FALHA (codigo $codigo)"
        }
    }
    else {
        Escrever-Log "[WhatIf]   executar etapa $($etapa.Nome) (suprimido por -WhatIf)"
    }
}

# --- etapa final: verificacao -------------------------------------------
$indice = 5
$caminhoVerificar = Join-Path $PSScriptRoot 'Verificar-Workstation.ps1'
Escrever-Log "ETAPA $indice/5: Verificacao final (Verificar-Workstation.ps1)"
if ($PSCmdlet.ShouldProcess('executar verificacao final (Verificar-Workstation.ps1)')) {
    & $caminhoVerificar @paramsVerificar
    $codigo = $LASTEXITCODE
    if ($codigo -eq 0) {
        Escrever-Log "ETAPA $indice/5: verificacao PASSOU (codigo 0)"
    }
    else {
        $falhas++
        Escrever-Log "ETAPA $indice/5: verificacao FALHOU (codigo $codigo)"
    }
}
else {
    Escrever-Log "[WhatIf]   executar verificacao final (suprimido por -WhatIf)"
}

Escrever-Log "=== fim Instalar-Workstation: $falhas etapa(s) com falha ==="
if ($falhas -gt 0) { exit 1 }
exit 0
