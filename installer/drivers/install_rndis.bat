
@echo off
:: Install RNDIS driver silently using pnputil (built into Windows 10/11)
:: Called by the NSIS installer with admin rights
set DRIVER_DIR=%~dp0
pnputil /add-driver "%DRIVER_DIR%mod-duo-rndis.inf" /install >nul 2>&1
exit /b 0
