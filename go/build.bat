@echo off
echo Building httpz_bridge.dll...
cd /d "%~dp0"
set CGO_ENABLED=1
go build -buildmode=c-shared -o "..\httpz\_libs\httpz_bridge.dll" .
if %errorlevel% neq 0 (
    echo Build FAILED!
    exit /b 1
)
echo Build OK: httpz\_libs\httpz_bridge.dll
