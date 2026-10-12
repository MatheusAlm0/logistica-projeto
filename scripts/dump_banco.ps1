<#
.SYNOPSIS
    Exporta o banco PostgreSQL para data/dump_logistica.sql (schema + dados).

.DESCRIPTION
    Lê DATABASE_URL do arquivo .env na raiz do projeto.
    Aceita parâmetros para sobrescrever qualquer parte da conexão.

.PARAMETER Output
    Caminho do arquivo SQL gerado. Padrão: data/dump_logistica.sql

.PARAMETER DbUrl
    DATABASE_URL completo. Se omitido, lê do .env.

.EXAMPLE
    .\scripts\dump_banco.ps1
    .\scripts\dump_banco.ps1 -Output "data\backup_20241201.sql"
    .\scripts\dump_banco.ps1 -DbUrl "postgresql+psycopg2://user:pass@host:5432/db"
#>

param(
    [string]$Output = "",
    [string]$DbUrl  = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Raiz do projeto (um nível acima de scripts/) ─────────────────────────────
$Root = (Resolve-Path "$PSScriptRoot\..").Path

# ── Saída padrão ─────────────────────────────────────────────────────────────
if (-not $Output) {
    $Output = Join-Path $Root "data\dump_logistica.sql"
}

# ── Lê .env se DATABASE_URL não foi passado ───────────────────────────────────
if (-not $DbUrl) {
    $EnvFile = Join-Path $Root ".env"
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match '^\s*DATABASE_URL\s*=\s*(.+)$') {
                $DbUrl = $Matches[1].Trim()
                break
            }
        }
    }
}

if (-not $DbUrl) {
    Write-Error "DATABASE_URL não encontrado. Crie o arquivo .env ou passe -DbUrl."
    exit 1
}

# ── Parseia a URL ─────────────────────────────────────────────────────────────
# Formato: postgresql+psycopg2://user:password@host:port/dbname
$clean = $DbUrl -replace '^[^:]+\+[^:]+://', ''   # remove "postgresql+psycopg2://"
$clean = $DbUrl -replace '^postgresql(\+\w+)?://',  ''

if ($clean -match '^(?:([^:@]+)(?::([^@]*))?@)?([^:/]+)(?::(\d+))?/(.+)$') {
    $PgUser   = if ($Matches[1]) { $Matches[1] } else { "postgres" }
    $PgPass   = $Matches[2]
    $PgHost   = if ($Matches[3]) { $Matches[3] } else { "localhost" }
    $PgPort   = if ($Matches[4]) { $Matches[4] } else { "5432" }
    $PgDbName = $Matches[5]
} else {
    Write-Error "Não foi possível interpretar a DATABASE_URL: $DbUrl"
    exit 1
}

# ── Localiza pg_dump ──────────────────────────────────────────────────────────
$PgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $PgDump) {
    # Tenta os diretórios padrão de instalação do PostgreSQL no Windows
    $candidates = Get-ChildItem "C:\Program Files\PostgreSQL" -ErrorAction SilentlyContinue |
                  Sort-Object Name -Descending |
                  ForEach-Object { "$($_.FullName)\bin\pg_dump.exe" } |
                  Where-Object { Test-Path $_ }
    if ($candidates) {
        $PgDump = $candidates | Select-Object -First 1
    } else {
        Write-Error "pg_dump não encontrado. Adicione o bin do PostgreSQL ao PATH."
        exit 1
    }
} else {
    $PgDump = $PgDump.Source
}

# ── Garante que o diretório de saída existe ───────────────────────────────────
$OutputDir = Split-Path $Output -Parent
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force $OutputDir | Out-Null
}

# ── Executa pg_dump ───────────────────────────────────────────────────────────
Write-Host "Conectando em $PgHost`:$PgPort/$PgDbName como $PgUser ..."
Write-Host "Salvando em:  $Output"

$env:PGPASSWORD = $PgPass

& $PgDump `
    --host=$PgHost `
    --port=$PgPort `
    --username=$PgUser `
    --dbname=$PgDbName `
    --format=plain `
    --no-owner `
    --no-acl `
    --file=$Output

$ExitCode = $LASTEXITCODE
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

if ($ExitCode -ne 0) {
    Write-Error "pg_dump falhou com código $ExitCode."
    exit $ExitCode
}

$Size = [math]::Round((Get-Item $Output).Length / 1KB, 1)
Write-Host "Dump concluido: $Output ($Size KB)" -ForegroundColor Green
