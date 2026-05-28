@echo off
set PATH=C:\Program Files\Go\bin;C:\msys64\mingw64\bin;%PATH%
set CGO_ENABLED=1
cd /d D:\httpz\go
echo Building...
go build -buildmode=c-shared -o D:\httpz\httpz\_libs\httpz_bridge.dll . 2>&1
if %ERRORLEVEL% EQU 0 (
    echo BUILD SUCCESS
) else (
    echo BUILD FAILED with code %ERRORLEVEL%
)
