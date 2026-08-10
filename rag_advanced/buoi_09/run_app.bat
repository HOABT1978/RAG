@echo off
title RAG Foundation Launcher - Buoi 09
chcp 65001 > nul

echo ========================================================
echo   KHOI CHAY STREAMLIT DASHBOARD (BUOI 09)
echo ========================================================
echo.
echo [*] Đang mở trình duyệt giao diện khởi động...
start launcher.html
echo.
echo [*] Đang khởi chạy Streamlit Server...
"D:\Rag_thuchanh\RAG\rag_foundation\buoi_05\.venv\Scripts\streamlit.exe" run app.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Lỗi xảy ra khi chạy Streamlit server.
    pause
)
