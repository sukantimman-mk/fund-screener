@echo off
chcp 65001 >nul
title Finnomena Fund Screener
cd /d "%~dp0"

echo ========================================================
echo   Finnomena Fund Screener — กำลังเริ่มระบบ...
echo ========================================================

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ ไม่พบ Python ในเครื่องนี้
    echo กรุณาตรวจสอบว่าได้ติดตั้ง Python เรียบร้อยแล้ว
    pause
    exit /b 1
)

echo 🌐 กำลังเปิดเบราว์เซอร์ไปที่ http://localhost:8080/index.html ...
start "" "http://localhost:8080/index.html"

python server.py
pause
