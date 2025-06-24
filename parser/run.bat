@echo off
chcp 65001 >nul
echo 🎁 Telegram Collectible Gifts Parser для Windows 🎁
echo =====================================================

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="setup" goto setup
if "%1"=="install" goto install
if "%1"=="check" goto check
if "%1"=="health-check" goto health_check
if "%1"=="start" goto start
if "%1"=="start-full" goto start_full
if "%1"=="demo" goto demo
if "%1"=="stats" goto stats
if "%1"=="collection" goto collection

:help
echo Использование: %0 [КОМАНДА]
echo.
echo Команды:
echo   install           Установить зависимости
echo   check             Проверить окружение
echo   health-check      Запустить health check
echo   start             Запустить полный парсинг (режим resume)
echo   start-full        Запустить полный парсинг (игнорировать кэш)
echo   demo              Демо-парсинг на небольшой выборке
echo   stats             Генерировать только статистику
echo   collection ^<name^> Обработать одну коллекцию
echo   setup             Полная настройка (install + check + health-check)
echo   help              Показать эту справку
echo.
echo Примеры:
echo   %0 setup                    # Полная настройка
echo   %0 demo                     # Демо-режим для тестирования
echo   %0 start                    # Запуск парсинга
echo   %0 collection lightsword    # Обработать только lightsword коллекцию
echo   %0 stats                    # Генерировать отчеты
goto end

:install
echo 📦 Установка Python зависимостей...
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Ошибка при установке зависимостей
    exit /b 1
)
echo ✅ Зависимости установлены успешно!
goto end

:check
echo 🔍 Проверка окружения...
cd /d "%~dp0"
python --version
if %errorlevel% neq 0 (
    echo ❌ Python не найден
    exit /b 1
)

if not exist "..\materials\file_list.txt" (
    echo ❌ Ошибка: file_list.txt не найден в materials директории
    exit /b 1
)

if not exist "..\materials\lightsword.txt" (
    echo ❌ Ошибка: Файлы коллекций не найдены в materials директории
    exit /b 1
)

echo ✅ Проверка окружения прошла успешно!
goto end

:health_check
echo 🏥 Запуск health check...
cd /d "%~dp0"
python main.py --health-check
goto end

:start
echo 🚀 Запуск парсера с настройками по умолчанию...
cd /d "%~dp0"
python main.py --resume
goto end

:start_full
echo 🚀 Запуск полного парсинга (игнорировать кэш)...
cd /d "%~dp0"
python main.py --full
goto end

:demo
echo 🎭 Запуск демо-парсинга...
cd /d "%~dp0"
python demo.py
goto end

:stats
echo 📊 Генерация статистики...
cd /d "%~dp0"
python main.py --stats-only
goto end

:collection
if "%2"=="" (
    echo ❌ Ошибка: Требуется имя коллекции
    echo Использование: %0 collection ^<имя_коллекции^>
    exit /b 1
)
echo 🎯 Обработка коллекции: %2
cd /d "%~dp0"
python main.py --collection "%2" --resume
goto end

:setup
echo 📁 Создание выходных директорий...
cd /d "%~dp0"
if not exist "..\output" mkdir "..\output"
if not exist "..\output\collections" mkdir "..\output\collections"
if not exist "..\output\logs" mkdir "..\output\logs"
if not exist "..\output\stats" mkdir "..\output\stats"
if not exist "..\output\cache" mkdir "..\output\cache"
echo ✅ Директории созданы!

call :install
if %errorlevel% neq 0 goto end

call :check
if %errorlevel% neq 0 goto end

call :health_check
if %errorlevel% neq 0 goto end

echo.
echo 🎉 Настройка завершена успешно!
echo Для запуска парсинга выполните: %0 start
echo Для демо-режима выполните: %0 demo
goto end

:end