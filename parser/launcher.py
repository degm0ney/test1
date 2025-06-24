#!/usr/bin/env python3
"""
Windows-совместимый launcher для парсера подарков Telegram
Универсальный способ запуска из PyCharm или командной строки
"""

import sys
import subprocess
import os
from pathlib import Path
import argparse

def run_command(cmd_args):
    """Запуск команды через subprocess"""
    try:
        result = subprocess.run(cmd_args, capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Ошибка при выполнении команды: {e}")
        return False

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка Python зависимостей...")
    
    # Обновляем pip
    if not run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"]):
        print("❌ Ошибка при обновлении pip")
        return False
    
    # Устанавливаем зависимости
    req_file = Path(__file__).parent / "requirements.txt"
    if not run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)]):
        print("❌ Ошибка при установке зависимостей")
        return False
    
    print("✅ Зависимости установлены успешно!")
    return True

def check_environment():
    """Проверка окружения"""
    print("🔍 Проверка окружения...")
    
    # Проверка Python
    print(f"Python версия: {sys.version}")
    
    # Проверка файлов
    materials_dir = Path(__file__).parent.parent / "materials"
    file_list = materials_dir / "file_list.txt"
    
    if not file_list.exists():
        print("❌ Ошибка: file_list.txt не найден в materials директории")
        return False
    
    # Проверка коллекций
    lightsword_file = materials_dir / "lightsword.txt"
    if not lightsword_file.exists():
        print("❌ Ошибка: Файлы коллекций не найдены в materials директории")
        return False
    
    print("✅ Проверка окружения прошла успешно!")
    return True

def create_directories():
    """Создание необходимых директорий"""
    print("📁 Создание выходных директорий...")
    
    output_dir = Path(__file__).parent.parent / "output"
    dirs_to_create = [
        output_dir,
        output_dir / "collections",
        output_dir / "logs", 
        output_dir / "stats",
        output_dir / "cache"
    ]
    
    for directory in dirs_to_create:
        directory.mkdir(parents=True, exist_ok=True)
    
    print("✅ Директории созданы!")
    return True

def run_health_check():
    """Запуск health check"""
    print("🏥 Запуск health check...")
    return run_command([sys.executable, "main.py", "--health-check"])

def run_parsing(mode="resume", collection=None):
    """Запуск парсинга"""
    if collection:
        print(f"🎯 Обработка коллекции: {collection}")
        args = [sys.executable, "main.py", "--collection", collection, "--resume"]
    else:
        mode_text = "resume" if mode == "resume" else "полный (игнорировать кэш)"
        print(f"🚀 Запуск парсинга в режиме: {mode_text}")
        flag = "--resume" if mode == "resume" else "--full"
        args = [sys.executable, "main.py", flag]
    
    return run_command(args)

def run_demo():
    """Запуск демо-парсинга"""
    print("🎭 Запуск демо-парсинга...")
    return run_command([sys.executable, "demo.py"])

def run_stats():
    """Генерация статистики"""
    print("📊 Генерация статистики...")
    return run_command([sys.executable, "main.py", "--stats-only"])

def main():
    """Главная функция launcher'а"""
    
    # Изменяем рабочую директорию на директорию скрипта
    os.chdir(Path(__file__).parent)
    
    parser = argparse.ArgumentParser(
        description="Windows-совместимый launcher для парсера подарков Telegram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python launcher.py setup                    # Полная настройка
  python launcher.py demo                     # Демо-режим для тестирования  
  python launcher.py start                    # Запуск парсинга
  python launcher.py start --full             # Полный парсинг (игнорировать кэш)
  python launcher.py collection lightsword    # Обработать только lightsword
  python launcher.py stats                    # Генерировать отчеты
  python launcher.py install                  # Только установка зависимостей
        """
    )
    
    parser.add_argument('command', choices=[
        'setup', 'install', 'check', 'health-check', 
        'start', 'demo', 'stats', 'collection'
    ], help='Команда для выполнения')
    
    parser.add_argument('--full', action='store_true', 
                       help='Полный парсинг (игнорировать кэш)')
    
    parser.add_argument('collection_name', nargs='?', 
                       help='Имя коллекции для обработки')
    
    # Банер
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           🎁 TELEGRAM COLLECTIBLE GIFTS PARSER 🎁            ║
    ║                                                               ║
    ║                    Windows Launcher v1.0                     ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    args = parser.parse_args()
    success = True
    
    try:
        if args.command == 'setup':
            success = (create_directories() and 
                      install_dependencies() and 
                      check_environment() and 
                      run_health_check())
            if success:
                print("\n🎉 Настройка завершена успешно!")
                print("Для запуска парсинга выполните: python launcher.py start")
                print("Для демо-режима выполните: python launcher.py demo")
        
        elif args.command == 'install':
            success = install_dependencies()
        
        elif args.command == 'check':
            success = check_environment()
        
        elif args.command == 'health-check':
            success = run_health_check()
        
        elif args.command == 'start':
            mode = "full" if args.full else "resume"
            success = run_parsing(mode)
        
        elif args.command == 'demo':
            success = run_demo()
        
        elif args.command == 'stats':
            success = run_stats()
        
        elif args.command == 'collection':
            if not args.collection_name:
                print("❌ Ошибка: Требуется имя коллекции")
                print("Использование: python launcher.py collection <имя_коллекции>")
                success = False
            else:
                success = run_parsing("resume", args.collection_name)
    
    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем")
        success = False
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        success = False
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()