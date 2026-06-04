# Manual daily ingest wrapper (not scheduled — use GitHub Actions for 10:00 IST).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m src.ingest --manifest corpus/urls.yaml --no-save-raw @args
