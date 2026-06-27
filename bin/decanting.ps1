#!/usr/bin/env pwsh
# Wrapper de conveniência (Windows PowerShell).
# Uso: decanting <subcomando> [args]
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Entry = Join-Path $ScriptDir "..\scripts\decanting.py"
$py = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $py $Entry @args
