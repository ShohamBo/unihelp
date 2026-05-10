# Usage: .\scripts\db_backup.ps1
# Dumps the Docker Postgres DB to backups/<timestamp>.sql.gz
# Run from the project root.

$BackupDir = Join-Path $PSScriptRoot "..\backups"
if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutFile = Join-Path (Resolve-Path $BackupDir) "$Timestamp.sql.gz"

Write-Host "Backing up to $OutFile ..."

docker exec infra-db-1 bash -c "pg_dump -U maslul maslul | gzip > /tmp/maslul_backup.sql.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "pg_dump failed"; exit 1 }

docker cp "infra-db-1:/tmp/maslul_backup.sql.gz" $OutFile
if ($LASTEXITCODE -ne 0) { Write-Host "docker cp failed"; exit 1 }

docker exec infra-db-1 rm /tmp/maslul_backup.sql.gz

Write-Host "Done: $OutFile"

# Keep only the 10 most recent backups
Get-ChildItem $BackupDir -Filter "*.sql.gz" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 10 |
    Remove-Item -Force
