#!/bin/bash

# Установщик и лончер для парсера Telegram подарков

set -e

echo "🎁 Telegram Collectible Gifts Parser Setup 🎁"
echo "============================================="

# Функция для установки зависимостей
install_dependencies() {
    echo "📦 Installing Python dependencies..."
    cd /app/parser
    pip install -r requirements.txt
    echo "✅ Dependencies installed successfully!"
}

# Функция для проверки окружения
check_environment() {
    echo "🔍 Checking environment..."
    
    # Проверка Python версии
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "Python version: $python_version"
    
    # Проверка файлов материалов
    if [ ! -f "/app/materials/file_list.txt" ]; then
        echo "❌ Error: file_list.txt not found in materials directory"
        exit 1
    fi
    
    # Проверка нескольких коллекций
    if [ ! -f "/app/materials/lightsword.txt" ]; then
        echo "❌ Error: Collection files not found in materials directory"
        exit 1
    fi
    
    echo "✅ Environment check passed!"
}

# Функция для создания директорий
create_directories() {
    echo "📁 Creating output directories..."
    mkdir -p /app/output/{collections,logs,stats,cache}
    echo "✅ Directories created!"
}

# Функция для запуска health check
run_health_check() {
    echo "🏥 Running health check..."
    cd /app/parser
    python main.py --health-check
}

# Функция для быстрого старта
quick_start() {
    echo "🚀 Starting parser with default settings..."
    cd /app/parser
    python main.py --resume
}

# Функция для генерации статистики
generate_stats() {
    echo "📊 Generating statistics..."
    cd /app/parser
    python main.py --stats-only
}

# Функция для обработки одной коллекции
process_single_collection() {
    local collection_name=$1
    echo "🎯 Processing single collection: $collection_name"
    cd /app/parser
    python main.py --collection "$collection_name" --resume
}

# Функция для показа помощи
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  install           Install dependencies"
    echo "  check             Check environment"
    echo "  health-check      Run health check"
    echo "  start             Start full parsing (resume mode)"
    echo "  start-full        Start full parsing (ignore cache)"
    echo "  stats             Generate statistics only"
    echo "  collection <name> Process single collection"
    echo "  setup             Run full setup (install + check + health-check)"
    echo "  help              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 setup                    # Complete setup"
    echo "  $0 start                    # Start parsing"
    echo "  $0 collection lightsword    # Process only lightsword collection"
    echo "  $0 stats                    # Generate reports"
}

# Основная логика
case "${1:-help}" in
    "install")
        install_dependencies
        ;;
    "check")
        check_environment
        ;;
    "health-check")
        run_health_check
        ;;
    "start")
        cd /app/parser
        python main.py --resume
        ;;
    "start-full")
        cd /app/parser
        python main.py --full
        ;;
    "stats")
        generate_stats
        ;;
    "collection")
        if [ -z "$2" ]; then
            echo "❌ Error: Collection name required"
            echo "Usage: $0 collection <collection_name>"
            exit 1
        fi
        process_single_collection "$2"
        ;;
    "setup")
        create_directories
        install_dependencies
        check_environment
        run_health_check
        echo ""
        echo "🎉 Setup completed successfully!"
        echo "To start parsing, run: $0 start"
        ;;
    "help"|*)
        show_help
        ;;
esac