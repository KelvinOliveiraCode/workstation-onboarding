<#
.SYNOPSIS
    Parser minimal de YAML para o catalogo de software (schema fixo).
.DESCRIPTION
    O PowerShell 5.1 nao tem parser de YAML embutido, e este projeto nao
    depende de modulo externo. Converter-YamlDoCatalogo le o schema FIXO de
    config/dicionario-software.yaml: chaves de raiz em coluna zero e uma
    lista 'pacotes:' com entradas planas (id, nome, versao, categoria,
    silencioso, origem). Nao e um parser de YAML generico: listas aninhadas,
    multi-linha e aliases nao sao suportados de proposito.

    O teste Python tests/test_configuracao.py confere que a saida deste
    parser bate campo a campo com a do PyYAML no arquivo real. Isso segura a
    fidelidade do parser sem depender de nenhum modulo aqui.

    Este arquivo e um AUXILIAR (dot-sourced). Ele nao e um script de etapa
    e nao precisa de -WhatIf/-Executar: so le arquivo e devolve objetos.
#>

function Converter-EscalaoYaml {
    # Converte um valor escalar do YAML (tipo que o schema usa).
    # Entre aspas simples: literal (apenas '' vira ').
    # 'true'/'false': booleano. Demais: string.
    param([string]$bruto)
    if ($bruto.StartsWith("'") -and $bruto.EndsWith("'") -and $bruto.Length -ge 2) {
        $interno = $bruto.Substring(1, $bruto.Length - 2)
        return ($interno -replace "''", "'")
    }
    if ($bruto.StartsWith('"') -and $bruto.EndsWith('"') -and $bruto.Length -ge 2) {
        # Entre aspas duplas o YAML usa escapes; \\ vira \.
        $interno = $bruto.Substring(1, $bruto.Length - 2)
        return ($interno -replace '\\\\', '\')
    }
    if ($bruto -eq 'true') { return $true }
    if ($bruto -eq 'false') { return $false }
    return $bruto
}

function Converter-YamlDoCatalogo {
    # Le o catalogo de software e devolve @{ versao_catalogo; pacotes }.
    # pacotes e um array de hashtables com as 6 chaves do schema.
    param([Parameter(Mandatory = $true)][string]$Arquivo)
    $linhas = [System.IO.File]::ReadAllLines($Arquivo, [System.Text.Encoding]::UTF8)
    $raiz = @{}
    $pacotes = New-Object System.Collections.Generic.List[object]
    $pacoteAtual = $null
    foreach ($linhaBruta in $linhas) {
        $linha = $linhaBruta.TrimEnd()
        if ([string]::IsNullOrWhiteSpace($linha)) { continue }
        $trim = $linha.TrimStart()
        if ($trim.StartsWith('#')) { continue }
        if ($trim -eq 'pacotes:') { continue }
        if ($trim.StartsWith('- ')) {
            # Inicio de uma nova entrada da lista de pacotes.
            $par = $trim.Substring(2)
            $idx = $par.IndexOf(':')
            if ($idx -lt 0) { continue }
            $chave = $par.Substring(0, $idx).Trim()
            $valor = $par.Substring($idx + 1).Trim()
            $pacoteAtual = @{}
            $pacoteAtual[$chave] = Converter-EscalaoYaml $valor
            $pacotes.Add($pacoteAtual) | Out-Null
        }
        elseif ($pacoteAtual -ne $null -and $trim.Contains(':')) {
            # Continuacao da entrada atual (chave: valor).
            $idx = $trim.IndexOf(':')
            $chave = $trim.Substring(0, $idx).Trim()
            $valor = $trim.Substring($idx + 1).Trim()
            $pacoteAtual[$chave] = Converter-EscalaoYaml $valor
        }
        elseif ($trim.Contains(':')) {
            # Chave de raiz, ex.: versao_catalogo.
            $idx = $trim.IndexOf(':')
            $chave = $trim.Substring(0, $idx).Trim()
            $valor = $trim.Substring($idx + 1).Trim()
            $raiz[$chave] = Converter-EscalaoYaml $valor
        }
    }
    # ToArray() em vez de @($pacotes): no PowerShell 5.1 a subexpressao de
    # array @() falha com ArgumentException ao enumerar List[object].
    return @{ versao_catalogo = $raiz['versao_catalogo']; pacotes = $pacotes.ToArray() }
}
