@echo off
chcp 65001 >nul
title อัพเดทข้อมูลกองทุน Finnomena
cd /d "%~dp0"

echo ========================================================
echo   Finnomena Fund Screener — ระบบอัพเดทข้อมูลล่าสุด
echo ========================================================
echo.
echo กำลังเชื่อมต่อ Finnomena API และอัพเดทข้อมูล...
echo กรุณารอสักครู่ (ใช้เวลาประมาณ 10-20 วินาที)
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ❌ ไม่พบ Python ในเครื่องนี้
    pause
    exit /b 1
)

python update_data.py
echo.
echo ========================================================
echo ดำเนินการเสร็จสิ้น สามารถเปิดดูใน index.html ได้ทันที
echo ========================================================
pause
