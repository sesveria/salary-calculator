@echo off
REM 升级脚本：保留 salary.db，替换其他文件
echo ========================================
echo  工资计算应用 - 升级脚本
echo ========================================
echo.
echo 本脚本将保留 salary.db（你的数据）
echo 并替换所有代码文件为新版本
echo.
set /p confirm="继续升级？(Y/N): "
if /i not "%confirm%"=="Y" goto :cancel

if not exist salary.db (
    echo [警告] 未找到 salary.db，将全新安装
)

xcopy /E /Y core\* core\ 2>nul
xcopy /E /Y data\* data\ 2>nul
xcopy /E /Y gui\* gui\ 2>nul
xcopy /E /Y tests\* tests\ 2>nul
copy /Y main.py main.py 2>nul
copy /Y holiday.py holiday.py 2>nul
copy /Y update_holidays.py update_holidays.py 2>nul
copy /Y requirements.txt requirements.txt 2>nul

echo.
echo ✅ 升级完成！
echo 运行 python main.py 启动程序
pause
goto :eof

:cancel
echo 已取消
pause
