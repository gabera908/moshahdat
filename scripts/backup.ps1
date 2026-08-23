# PostgreSQL backup for Windows hosts (plan §35)
# Usage: .\backup.ps1 [-BackupDir ..\backups]
param(
    [string]$BackupDir = "..\backups",
    [int]$KeepDays = 14
)

$ErrorActionPreference = "Stop"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$File = Join-Path $BackupDir "video_platform_$Stamp.sql.gz"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Load .env from repo root
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$") {
            Set-Item -Path "env:$($Matches[1])" -Value $Matches[2]
        }
    }
}

$User = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "video_user" }
$Db   = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { "video_platform" }

Write-Host "Backing up to $File ..."
docker compose exec -T postgres pg_dump -U $User -d $Db --no-owner --clean | gzip > $File
Write-Host "Done."

Get-ChildItem $BackupDir -Filter "video_platform_*.sql.gz" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
    Remove-Item -Force
Write-Host "Backups older than $KeepDays days removed."
