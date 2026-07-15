@echo off
REM Windows 打包脚本
REM 用法: build.bat

echo === 工资计算器 Windows 打包 ===
echo.

REM 安装依赖
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 依赖安装失败
    exit /b 1
)

REM 打包为 exe
flet pack main.py --name 工资计算器 --icon assets/icon.ico --product-name "工资计算器" --product-version "1.0.0"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ 打包成功!
    echo 输出: dist/工资计算器.exe
) else (
    echo.
    echo [ERROR] 打包失败
    exit /b 1
)
