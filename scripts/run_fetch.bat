@echo off
chcp 65001 >nul
echo ========================================
echo ETF净值爬取任务
echo 时间: %date% %time%
echo ========================================

:: 切换到项目目录
cd /d "%~dp0\.."

:: 激活虚拟环境（如果有）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: 运行脚本
python scripts\fetch_daily_quotes.py

echo ========================================
echo 任务完成
echo ========================================

:: 暂停查看结果（调试时开启）
:: pause
