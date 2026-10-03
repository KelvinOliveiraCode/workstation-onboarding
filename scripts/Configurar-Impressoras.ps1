<#
.SYNOPSIS
    Etapa de onboarding: cadastra e define a impressora padrao da estacao.
.DESCRIPTION
    Nenhuma mudanca e aplicada sem -Executar. O padrao e dry-run: cada acao
    passa por $PSCmdlet.ShouldProcess e sai no log com o prefixo [WhatIf].
    A impressora alvo e FICTICIA (nome e share nao existem fora deste
    repositorio); em ambiente real o tecnico troca os valores de destino.
    A limpeza de impressoras temporarias (prefixo IMP-TMP-) e a unica acao
    de remocao e so roda com -Executar, dentro do filtro de nome.
.PARAMETER Executar
    Quando presente, as acoes sao aplicadas de fato. Sem ele, o script so
    loga o que faria.
.PARAMETER WhatIf
    (comum) Simula as acoes; retornado por SupportsShouldProcess.
.PARAMETER Confirm
    (comum) Confirmacao por acao; ConfirmImpact=High.
.PARAMETER ConfigDir
    Pasta de configuracao. Padrao: ..\config relativo ao script.
.PARAMETER LogPath
    Arquivo de log com timestamp. Padrao: ..\logs\configurar-impressoras.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Configurar-Impressoras.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Configurar-Impressoras.ps1 -Executar
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\configurar-impressoras.log' }

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

function Aplicar-Acao {
    # Gate de seguranca: ShouldProcess + -Executar. Sem -Executar a acao NAO roda.
    param(
        [Parameter(Mandatory = $true)][string]$Descricao,
        [Parameter(Mandatory = $true)][scriptblock]$Acao
    )
    if ($PSCmdlet.ShouldProcess($Descricao)) {
        if ($Executar) {
            try {
                & $Acao
                Escrever-Log "EXECUTADO  $Descricao"
            }
            catch {
                $Script:falhas++
                Escrever-Log "ERRO       $Descricao :: $($_.Exception.Message)"
            }
        }
        else {
            Escrever-Log "[WhatIf]   $Descricao"
        }
    }
    else {
        Escrever-Log "[WhatIf]   $Descricao (suprimido por -WhatIf)"
    }
}

# Valores de destino (FICTICIOS).
$nomeImpressora = 'IMP-ESCR-001'
$shareImpressora = '\\srv-printa-01\imp-esc-001'
$prefixoTemporario = 'IMP-TMP-'

Escrever-Log "=== inicio Configurar-Impressoras (modo: $modo) ==="

Aplicar-Acao -Descricao "remover impressoras temporarias com prefixo $prefixoTemporario" -Acao {
    $tmp = Get-Printer | Where-Object { $_.Name -like "$prefixoTemporario*" }
    if ($tmp) {
        foreach ($p in $tmp) { Remove-Printer -Name $p.Name -ErrorAction Stop }
        Escrever-Log "INFO       $($tmp.Count) impressora(s) temporaria(s) removida(s)"
    }
}

Aplicar-Acao -Descricao "cadastrar impressora $nomeImpressora (share $shareImpressora)" -Acao {
    if (-not (Get-Printer | Where-Object { $_.Name -eq $nomeImpressora })) {
        Add-Printer -ConnectionName $shareImpressora -Name $nomeImpressora | Out-Null
    }
}

Aplicar-Acao -Descricao "definir $nomeImpressora como impressora padrao" -Acao {
    $alvo = Get-WmiObject -Class Win32_Printer -Filter "Name='$nomeImpressora'"
    if (-not $alvo) { throw "impressora $nomeImpressora nao encontrada nesta estacao" }
    $alvo.Default = $true
    $alvo.Put() | Out-Null
}

Escrever-Log "=== fim Configurar-Impressoras: $falhas falha(s) ==="
if ($falhas -gt 0) { exit 1 }
exit 0
