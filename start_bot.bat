@echo off
echo ========================================
echo   maimai-wechat-bot — WeChatAuto bridge
echo ========================================
echo.
echo [1] Launch .NET bridge ...
start "WeChatAuto Bridge" dotnet run --project wabridge
timeout /t 3 /nobreak >nul
echo [2] Launch Python bot ...
python -m app.main
pause
