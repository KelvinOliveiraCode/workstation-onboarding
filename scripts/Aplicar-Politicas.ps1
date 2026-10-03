<#
.SYNOPSIS
    Etapa de onboarding: aplica as politicas de workstation do config/politicas.json.
.DESCRIPTION
    Nenhuma mudanca e aplicada sem -Executar. O padrao e dry-run: cada
    politica passa por $PSCmdlet.ShouldProcess e sai no log com [WhatIf].
    Politicas de escopo de usuario (bloqueio de tela, execution policy) sao
    aplicadas direto; politicas que exigem HKLM/administrador (atualizacao,
    firewall, senha minima, auditoria) registram o estado desejado em
    HKCU:\Software\Politicas\Estacao e o log indica que a aplicacao efetiva
    fica por conta de GPO/administrador. Nada disso muda em dry-run.
.PARAMETER Executar
    Quando presente, as acoes sao aplicadas de fato.
.PARAMETER WhatIf
    (comum) Simula as acoes; retornado por SupportsShouldProcess.
.PARAMETER Confirm
    (comum) Confirmacao por acao; ConfirmImpact=High.
.PARAMETER ConfigDir
    Pasta de configuracao. Padrao: ..\config relativo ao script.
.PARAMETER LogPath
    Arquivo de log com timestamp. Padrao: ..\logs\aplicar-politicas.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Aplicar-Politicas.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Aplicar-Politicas.ps1 -Executar
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\aplicar-politicas.log' }

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

function Registrar-EstadoDesejado {
    # Grava em HKCU o estado desejado de politica que exige HKLM/admin.
    param([string]$Politica, [string]$Descricao)
    $base = 'HKCU:\Software\Politicas\Estacao'
    if (-not (Test-Path $base)) { New-Item -Path $base -Force | Out-Null }
    Set-ItemProperty -Path $base -Name $Politica -Value $Descricao
    Escrever-Log "AVISO      $($Politica): estado desejado registrado; aplicacao efetiva requer administrador/GPO"
}

$caminhoPoliticas = Join-Path $ConfigDir 'politicas.json'
Escrever-Log "=== inicio Aplicar-Politicas (modo: $modo) ==="

if (-not (Test-Path $caminhoPoliticas)) {
    Escrever-Log "ERRO       arquivo de politicas nao encontrado: politicas.json em $ConfigDir"
    exit 1
}

$politicas = Get-Content -Path $caminhoPoliticas -Raw -Encoding UTF8 | ConvertFrom-Json

Aplicar-Acao -Descricao "definir bloqueio de tela em $($politicas.bloqueio_tela.minutos) minutos" -Acao {
    $chave = 'HKCU:\Control Panel\Desktop'
    Set-ItemProperty -Path $chave -Name 'ScreenSaveTimeout' -Value ($politicas.bloqueio_tela.minutos * 60000)
}

Aplicar-Acao -Descricao "definir execution policy do PowerShell para $($politicas.execution_policy_powershell.valor) (escopo usuario)" -Acao {
    Set-ExecutionPolicy -Scope CurrentUser -Force -ExecutionPolicy $politicas.execution_policy_powershell.valor | Out-Null
}

Aplicar-Acao -Descricao "definir janela de atualizacao do sistema $($politicas.windows_update.janela_inicio):00 a $($politicas.windows_update.janela_fim):00 (modo $($politicas.windows_update.modo))" -Acao {
    Registrar-EstadoDesejado -Politica 'windows_update' -Descricao "$($politicas.windows_update.modo); janela $($politicas.windows_update.janela_inicio)-$($politicas.windows_update.janela_fim)"
}

Aplicar-Acao -Descricao "definir perfil de firewall padrao: $($politicas.firewall.perfil_padrao)" -Acao {
    Registrar-EstadoDesejado -Politica 'firewall' -Descricao "$($politicas.firewall.perfil_padrao)"
}

Aplicar-Acao -Descricao "definir politica de senha minima: $($politicas.senha_minima.comprimento) caracteres, expira em $($politicas.senha_minima.expira_dias) dias" -Acao {
    Registrar-EstadoDesejado -Politica 'senha_minima' -Descricao "comprimento=$($politicas.senha_minima.comprimento); expira_dias=$($politicas.senha_minima.expira_dias)"
}

Aplicar-Acao -Descricao "habilitar auditoria de eventos: $($politicas.auditoria.eventos -join ', ')" -Acao {
    Registrar-EstadoDesejado -Politica 'auditoria' -Descricao ($politicas.auditoria.eventos -join ',')
}

Escrever-Log "=== fim Aplicar-Politicas: $falhas falha(s) ==="
if ($falhas -gt 0) { exit 1 }
exit 0
