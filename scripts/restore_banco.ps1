<#
.SYNOPSIS
    Restaura o dump SQL em um banco PostgreSQL (novo ou existente).

.DESCRIPTION
    Lê DATABASE_URL do .env para obter host/porta/usuário/senha.
    Cria o banco destino se ele não existir.
    Restaura o arquivo SQL gerado por dump_banco.ps1.

.PARAMETER Input
    Arquivo SQL a restaurar. Padrão: data/dump_logistica.sql

.PARAMETER TargetDb
    Nome do banco destino. Padrão: nome do banco no .env (ou DATABASE_URL).

.PARAMETER DbUrl
    DATABASE_URL completo. Se omitido, lê do .env.

.PARAMETER Force
    Se informado, dropa e recria o banco destino antes de restaurar.

.EXAMPLE
    .\scripts\restore_banco.ps1
    .\scripts\restore_banco.ps1 -TargetDb logistica_staging
    .\scripts\restore_banco.ps1 -Input data\backup_20241201.sql -TargetDb logistica_novo
    .\scripts\restore_banco.ps1 -Force
#>

param(
    [string]$Input    = "",
    [string]$TargetDb = "",
    [string]$DbUrl    = "",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Raiz do projeto ───────────────────────────────────────────────────────────
$Root = (Resolve-Path "$PSScriptRoot\..").Path

# ── Arquivo de dump padrão ────────────────────────────────────────────────────
if (-not $Input) {
    $Input = Join-Path $Root "data\dump_logistica.sql"
}

if (-not (Test-Path $Input)) {
    Write-Error "Arquivo de dump nao encontrado: $Input`nGere-o primeiro com: .\scripts\dump_banco.ps1"
    exit 1
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
    Write-Error "DATABASE_URL nao encontrado. Crie o arquivo .env ou passe -DbUrl."
    exit 1
}

# ── Parseia a URL ─────────────────────────────────────────────────────────────
$clean = $DbUrl -replace '^postgresql(\+\w+)?://', ''

if ($clean -match '^(?:([^:@]+)(?::([^@]*))?@)?([^:/]+)(?::(\d+))?/(.+)$') {
    $PgUser       = if ($Matches[1]) { $Matches[1] } else { "postgres" }
    $PgPass       = $Matches[2]
    $PgHost       = if ($Matches[3]) { $Matches[3] } else { "localhost" }
    $PgPort       = if ($Matches[4]) { $Matches[4] } else { "5432" }
    $PgDbOriginal = $Matches[5]
} else {
    Write-Error "Nao foi possivel interpretar a DATABASE_URL: $DbUrl"
    exit 1
}

if (-not $TargetDb) { $TargetDb = $PgDbOriginal }

# ── Localiza psql e createdb ──────────────────────────────────────────────────
function Find-PgTool([string]$Tool) {
    $cmd = Get-Command $Tool -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = Get-ChildItem "C:\Program Files\PostgreSQL" -ErrorAction SilentlyContinue |
                  Sort-Object Name -Descending |
                  ForEach-Object { "$($_.FullName)\bin\$Tool.exe" } |
                  Where-Object { Test-Path $_ }
    if ($candidates) { return $candidates | Select-Object -First 1 }
    Write-Error "$Tool nao encontrado. Adicione o bin do PostgreSQL ao PATH."
    exit 1
}

$Psql     = Find-PgTool "psql"
$Createdb = Find-PgTool "createdb"
$Dropdb   = Find-PgTool "dropdb"

$env:PGPASSWORD = $PgPass
$ConnArgs = @("--host=$PgHost", "--port=$PgPort", "--username=$PgUser")

# ── Verifica se o banco destino já existe ─────────────────────────────────────
$DbExists = & $Psql @ConnArgs --dbname=postgres --tuples-only --no-align `
    --command="SELECT 1 FROM pg_database WHERE datname='$TargetDb'" 2>$null
$DbExists = ($DbExists -match '1')

if ($DbExists -and $Force) {
    Write-Host "[-Force] Dropando banco existente '$TargetDb' ..." -ForegroundColor Yellow
    & $Dropdb @ConnArgs $TargetDb
    if ($LASTEXITCODE -ne 0) { Write-Error "Falha ao dropar '$TargetDb'."; exit 1 }
    $DbExists = $false
}

if (-not $DbExists) {
    Write-Host "Criando banco '$TargetDb' ..."
    & $Createdb @ConnArgs $TargetDb
    if ($LASTEXITCODE -ne 0) { Write-Error "Falha ao criar '$TargetDb'."; exit 1 }
} else {
    Write-Host "Banco '$TargetDb' ja existe — restaurando sobre ele." -ForegroundColor Yellow
    Write-Host "(Use -Force para dropar e recriar do zero.)"
}

# ── Restaura o dump ───────────────────────────────────────────────────────────
$InputSize = [math]::Round((Get-Item $Input).Length / 1KB, 1)
Write-Host "Restaurando $Input ($InputSize KB) em $PgHost`:$PgPort/$TargetDb ..."

& $Psql @ConnArgs --dbname=$TargetDb --file=$Input --echo-errors

$ExitCode = $LASTEXITCODE
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

if ($ExitCode -ne 0) {
    Write-Error "psql finalizou com codigo $ExitCode. Verifique os erros acima."
    exit $ExitCode
}

Write-Host "Restauracao concluida: banco '$TargetDb' pronto." -ForegroundColor Green
