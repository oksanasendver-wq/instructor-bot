param([switch]$TestPreview)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Создайте .venv и установите backend/requirements-dev.txt по QUICKSTART.md.' }
$vitePath = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $vitePath)) { throw 'Сначала выполните npm ci из корня проекта.' }
foreach ($port in @(8010, 5173, 5174)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Порт $port занят. Остановите предыдущий локальный запуск." }
}
$logRoot = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$processes = @()
$previousProxy = $env:VITE_BACKEND_PROXY
$previousPreview = $env:VITE_LOCAL_PREVIEW
try {
    $backendArguments = if ($TestPreview) { 'scripts/local_preview.py' } else { '-m uvicorn app.main:app --host 127.0.0.1 --port 8010' }
    $processes += Start-Process -FilePath $pythonPath -ArgumentList $backendArguments -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot 'backend.log') -RedirectStandardError (Join-Path $logRoot 'backend-error.log')
    $env:VITE_BACKEND_PROXY = 'http://127.0.0.1:8010'
    $env:VITE_LOCAL_PREVIEW = if ($TestPreview) { 'true' } else { 'false' }
    foreach ($entry in @(@('frontend-miniapp', 5173), @('frontend-admin', 5174))) {
        $processes += Start-Process -FilePath (Get-Command node).Source -ArgumentList @(('"' + $vitePath + '"'), '--port', $entry[1]) -WorkingDirectory (Join-Path $projectRoot $entry[0]) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot ($entry[0] + '.log')) -RedirectStandardError (Join-Path $logRoot ($entry[0] + '-error.log'))
    }
    Write-Host 'Miniapp: http://127.0.0.1:5173 | Admin: http://127.0.0.1:5174'
    if ($TestPreview) { Write-Host 'Изолированный тестовый режим. Admin: local-admin / instructor-local.' }
    else { Write-Host 'Рабочий режим: данные и вход из backend/.env. Миниап требует вход через Telegram.' }
    Write-Host 'Логи: .local. Остановка: Ctrl+C.'
    while ($true) {
        foreach ($process in $processes) { if ($process.HasExited) { throw "Процесс $($process.Id) завершился. Проверьте логи .local." } }
        Start-Sleep -Seconds 2
    }
} finally {
    foreach ($process in $processes) { if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() } }
    $env:VITE_BACKEND_PROXY = $previousProxy
    $env:VITE_LOCAL_PREVIEW = $previousPreview
}
