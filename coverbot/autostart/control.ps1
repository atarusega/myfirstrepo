# Управление ботом в фоне:  .\autostart\control.ps1 status | start | stop | restart | install | uninstall
param([ValidateSet('status', 'start', 'stop', 'restart', 'install', 'uninstall')][string]$Action = 'status')

$Root = Split-Path $PSScriptRoot -Parent
$Pythonw = Join-Path $Root '.venv\Scripts\pythonw.exe'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Supervisor = Join-Path $PSScriptRoot 'supervisor.pyw'
$Log = Join-Path $Root 'logs\bot.log'
$Shortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'CoverBot.lnk'

function Get-BotProcesses {
    # supervisor (pythonw ... supervisor.pyw) и сам бот (python -m app.main из .venv этой папки)
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object {
        $_.CommandLine -and ($_.CommandLine -like "*$Supervisor*" -or
            ($_.CommandLine -like '*-m app.main*' -and $_.ExecutablePath -like "$Root\*"))
    }
}

function Start-Bot {
    if (Get-BotProcesses) { Write-Host 'Уже запущен'; return }
    Start-Process -FilePath $Pythonw -ArgumentList "`"$Supervisor`"" -WorkingDirectory $Root
    Write-Host 'Запущен в фоне'
}

function Stop-Bot {
    $procs = Get-BotProcesses
    if (-not $procs) { Write-Host 'Не запущен'; return }
    $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Остановлен ($(@($procs).Count) процесс.)"
}

switch ($Action) {
    'start' { Start-Bot }
    'stop' { Stop-Bot }
    'restart' { Stop-Bot; Start-Sleep 2; Start-Bot }
    'install' {
        $ws = New-Object -ComObject WScript.Shell
        $lnk = $ws.CreateShortcut($Shortcut)
        $lnk.TargetPath = $Pythonw
        $lnk.Arguments = "`"$Supervisor`""
        $lnk.WorkingDirectory = $Root
        $lnk.Description = 'CoverBot: Telegram-бот подбора кавер-групп'
        $lnk.Save()
        Write-Host "Автозапуск включён: $Shortcut"
    }
    'uninstall' {
        if (Test-Path $Shortcut) { Remove-Item $Shortcut; Write-Host 'Автозапуск выключен' } else { Write-Host 'Ярлыка автозапуска нет' }
    }
    'status' {
        $procs = Get-BotProcesses
        Write-Host "Автозапуск: $(if (Test-Path $Shortcut) { 'включён' } else { 'выключен' })"
        Write-Host "Процессы:   $(if ($procs) { ($procs | ForEach-Object { "$($_.Name)#$($_.ProcessId)" }) -join ', ' } else { 'не запущен' })"
        # getMe: токен читается из .env внутри Python и не печатается
        Push-Location $Root
        & $Python -c "import asyncio; from aiogram import Bot; from app.config import settings`nasync def m():`n  b=Bot(settings.bot_token)`n  try: print('Telegram:   @'+(await b.get_me()).username+' отвечает')`n  finally: await b.session.close()`ntry: asyncio.run(m())`nexcept Exception as e: print('Telegram:   ошибка', type(e).__name__, e)"
        Pop-Location
        if (Test-Path $Log) { Write-Host "`n--- последние строки $Log ---"; Get-Content $Log -Tail 15 -Encoding utf8 }
    }
}
