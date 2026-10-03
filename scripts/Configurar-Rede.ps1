<#
.SYNOPSIS
    Etapa de onboarding: configura a rede da estacao (DNS, fuso, proxy).
.DESCRIPTION
    Nenhuma mudanca e aplicada sem -Executar. O padrao e dry-run: cada acao
    passa por $PSCmdlet.ShouldProcess e sai no log com o prefixo [WhatIf].
    Os valores de destino sao FICTICIOS (servidores DNS em faixa privada,
    proxy interno) e ficam declarados no inicio do script; um ambiente real
    substitui pelo proprio -ConfigDir/catalogo local.
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
    Arquivo de log com timestamp. Padrao: ..\logs\configurar-rede.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Configurar-Rede.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Configurar-Rede.ps1 -Executar
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

# A confirmacao real e controlada pelo -Executar (e pela revisao do tecnico
# no log). Com ConfirmImpact=High e $ConfirmPreference=High o PowerShell
# faria prompt em cada acao e travaria o modo padrao, que e o mais usado.
$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\configurar-rede.log' }

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

# Valores de destino (FICTICIOS; trocar pelo catalogo local em ambiente real).
$dnsPrimario = '10.10.10.10'
$dnsSecundario = '10.10.10.11'
$fusoAlvo = 'America/Sao_Paulo'
$proxyAlvo = 'proxy.interno:8080'

Escrever-Log "=== inicio Configurar-Rede (modo: $modo) ==="

Aplicar-Acao -Descricao "definir servidores DNS $dnsPrimario e $dnsSecundario no adaptador primario" -Acao {
    $adaptador = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
    Set-DnsClientServerAddress -InterfaceIndex $adaptador.IfIndex -ServerAddresses @($dnsPrimario, $dnsSecundario)
}

Aplicar-Acao -Descricao "definir fuso horario $fusoAlvo" -Acao {
    Set-TimeZone -Id $fusoAlvo | Out-Null
}

Aplicar-Acao -Descricao "definir proxy corporativo $proxyAlvo (HKCU)" -Acao {
    $chave = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    Set-ItemProperty -Path $chave -Name 'ProxyServer' -Value $proxyAlvo
    Set-ItemProperty -Path $chave -Name 'ProxyEnable' -Value 1
}

Aplicar-Acao -Descricao "desativar auto-configuracao de proxy (AutoConfigURL)" -Acao {
    $chave = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    Set-ItemProperty -Path $chave -Name 'AutoConfigURL' -Value ''
}

Escrever-Log "=== fim Configurar-Rede: $falhas falha(s) ==="
if ($falhas -gt 0) { exit 1 }
exit 0
