@echo off
set PATH=C:\Program Files\Go\bin;C:\msys64\mingw64\bin;%PATH%
set CGO_ENABLED=1
cd /d D:\httpz\go
echo Building... > D:\httpz\build_output.txt 2>&1
go build -buildmode=c-shared -o D:\httpz\httpz\_libs\httpz_bridge.dll . >> D:\httpz\build_output.txt 2>&1
echo Exit code: %ERRORLEVEL% >> D:\httpz\build_output.txt 2>&1
