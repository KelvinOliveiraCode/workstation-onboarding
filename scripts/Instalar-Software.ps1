<#
.SYNOPSIS
    Etapa de onboarding: instala os pacotes do catalogo de software.
.DESCRIPTION
    Le config/dicionario-software.yaml com o parser local (Parser-Catalogo,
    dot-sourced; o PowerShell 5.1 nao tem YAML embutido e o projeto nao
    depende de modulo). Nenhuma instalacao e iniciada sem -Executar: o
    padrao e dry-run, com cada pacote logado como [WhatIf]. Com -Executar,
    o script confere a versao ja registrada em HKCU:\Software\CatalogoInterno
    e so tenta instalar o que falta; pacotes com silencioso=false exigem
    instalacao interativa e apenas sao avisados no log.
    Todos os pacotes do catalogo sao FICTICIOS: os caminhos de origem
    apontam para a pasta de rede ficticia \\srv-software.
.PARAMETER Executar
    Quando presente, as instalacoes sao iniciadas de fato.
.PARAMETER WhatIf
    (comum) Simula as acoes; retornado por SupportsShouldProcess.
.PARAMETER Confirm
    (comum) Confirmacao por acao; ConfirmImpact=High.
.PARAMETER ConfigDir
    Pasta de configuracao. Padrao: ..\config relativo ao script.
.PARAMETER LogPath
    Arquivo de log com timestamp. Padrao: ..\logs\instalar-software.log.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Instalar-Software.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Instalar-Software.ps1 -Executar
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Executar,
    [string]$ConfigDir,
    [string]$LogPath
)

$ConfirmPreference = 'None'

if ([string]::IsNullOrWhiteSpace($ConfigDir)) { $ConfigDir = Join-Path $PSScriptRoot '..\config' }
if ([string]::IsNullOrWhiteSpace($LogPath))   { $LogPath   = Join-Path $PSScriptRoot '..\logs\instalar-software.log' }

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

function VersaoInstalada {
    # Devolve a versao registrada no inventario local, ou $null.
    param([string]$Id)
    $chave = "HKCU:\Software\CatalogoInterno\$Id"
    if (Test-Path $chave) {
        return (Get-ItemProperty -Path $chave).VersaoInstalada
    }
    return $null
}

# Parser local do catalogo (dot-sourced; nao e uma etapa, nao muda nada).
. (Join-Path $PSScriptRoot 'Parser-Catalogo.ps1')

$caminhoCatalogo = Join-Path $ConfigDir 'dicionario-software.yaml'
Escrever-Log "=== inicio Instalar-Software (modo: $modo) ==="

if (-not (Test-Path $caminhoCatalogo)) {
    Escrever-Log "ERRO       catalogo nao encontrado: dicionario-software.yaml em $ConfigDir"
    exit 1
}

$catalogo = Converter-YamlDoCatalogo -Arquivo $caminhoCatalogo
$pacotes = @($catalogo.pacotes)
Escrever-Log "INFO       catalogo v$($catalogo.versao_catalogo) com $($pacotes.Count) pacote(s)"

foreach ($pacote in $pacotes) {
    $descricao = "instalar $($pacote.id) v$($pacote.versao) (categoria: $($pacote.categoria))"
    Aplicar-Acao -Descricao $descricao -Acao {
        if (-not $pacote.silencioso) {
            Escrever-Log "AVISO      $($pacote.id): silencioso=false, instalacao interativa nao e feita pelo onboarding"
            return
        }
        $atual = VersaoInstalada -Id $pacote.id
        if ($atual -eq $pacote.versao) {
            Escrever-Log "AVISO      $($pacote.id): versao $($pacote.versao) ja instalada, pulando"
            return
        }
        Write-Host "          executando instalador de $($pacote.id) ($($pacote.origem) /S)"
        $proc = Start-Process -FilePath $pacote.origem -ArgumentList '/S' -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            throw "instalador de $($pacote.id) terminou com codigo $($proc.ExitCode)"
        }
        $chave = "HKCU:\Software\CatalogoInterno\$($pacote.id)"
        if (-not (Test-Path $chave)) {
            New-Item -Path $chave -Force | Out-Null
        }
        Set-ItemProperty -Path $chave -Name 'VersaoInstalada' -Value $pacote.versao
    }
}

Escrever-Log "=== fim Instalar-Software: $falhas falha(s) ==="
if ($falhas -gt 0) { exit 1 }
exit 0
