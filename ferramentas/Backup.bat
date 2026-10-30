@echo off
setlocal
set "CPJ_BACKUP_SCRIPT=%~dp0backup.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$destino = Read-Host 'Pasta de destino do backup (vazio cancela)'; if ([string]::IsNullOrWhiteSpace($destino)) { Write-Host 'Backup cancelado. Nenhuma copia executada.'; exit }; if ((Read-Host 'Central, agentes, editores e TODOS os escritores foram parados? [S/N]') -ine 'S') { Write-Host 'Backup cancelado. Nenhuma copia executada.'; exit }; if ((Read-Host 'A midia esta autorizada e cifrada/protegida pelo orgao? [S/N]') -ine 'S') { Write-Host 'Backup cancelado. Nenhuma copia executada.'; exit }; & $env:CPJ_BACKUP_SCRIPT -Destino $destino -Offline -MidiaProtegida"
pause
endlocal
