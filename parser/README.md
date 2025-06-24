# 🎁 Telegram Collectible Gifts Parser

## Обзор
Мощный асинхронный парсер для сбора данных о коллекционных подарках Telegram с поддержкой масштабной обработки, кэширования и детальной аналитики.

## ✨ Возможности

### 🚀 Высокая производительность
- **Асинхронная обработка** до 100 одновременных соединений
- **Батчевая обработка** по 500 URL за раз
- **Умный rate limiting** для избежания блокировок
- **Retry логика** с экспоненциальными задержками

### 📊 Интеллектуальное кэширование
- **Инкрементальные обновления** - пропуск уже обработанных URL
- **Автоматическое восстановление** из существующих данных
- **Очистка устаревших записей**
- **Отслеживание прогресса** по коллекциям

### 🎯 Точное извлечение данных
- **Model, Backdrop, Symbol** - все атрибуты подарков
- **Количество и редкость**
- **Информация о владельце**
- **Высококачественные изображения**
- **Статус активности** (active/deleted/error)

### 📈 Детальная аналитика
- **Real-time мониторинг** с прогресс-барами
- **Подробная статистика** по коллекциям
- **Отчеты производительности**
- **Экспорт в CSV и JSON**

## 🏗️ Архитектура

```
/parser/
├── main.py              # CLI интерфейс и управление
├── config.py            # Конфигурация системы
├── logger.py            # Система логирования с Rich
├── gift_parser.py       # Парсинг HTML страниц подарков
├── async_downloader.py  # Асинхронная загрузка
├── data_manager.py      # Управление JSON данными
├── cache_manager.py     # Кэширование и инкременты
├── collection_manager.py # Управление коллекциями
├── stats.py             # Статистика и отчетность
├── utils.py             # Утилиты обслуживания
└── run.sh              # Удобный launcher
```

## 🎯 Структура выходных данных

```
output/
├── collections/         # JSON файлы коллекций
│   ├── lightsword.json
│   ├── astralshard.json
│   └── ...
├── logs/               # Логи работы
│   ├── parser.log
│   ├── errors.log
│   └── stats.log
├── stats/              # Статистика и отчеты
│   ├── summary.json
│   ├── collections_stats.json
│   └── performance_report.json
└── cache/              # Кэш и прогресс
    ├── processed_urls.txt
    └── progress.json
```

## 📋 Формат данных подарка

```json
{
  "url": "https://t.me/nft/lightsword-1",
  "gift_id": "lightsword-1",
  "collection": "lightsword",
  "gift_number": 1,
  "title": "Light Sword #1",
  "model": "Absinthe",
  "backdrop": "Burnt Sienna", 
  "symbol": "Shooting Star",
  "rarity": "",
  "owner": null,
  "quantity": "110335/131222",
  "total_supply": "131222",
  "image_url": "https://cdn4.cdn-telegram.org/file/...",
  "status": "active",
  "parsed_at": "2025-06-24T10:25:15Z"
}
```

## 🚀 Быстрый старт

### 1. Полная настройка
```bash
cd /app/parser
./run.sh setup
```

### 2. Запуск парсинга всех коллекций
```bash
./run.sh start          # Режим resume (рекомендуется)
./run.sh start-full     # Полная обработка (игнорировать кэш)
```

### 3. Обработка одной коллекции
```bash
./run.sh collection lightsword
```

### 4. Генерация статистики
```bash
./run.sh stats
```

## 🔧 Расширенные команды

### Проверка системы
```bash
python main.py --health-check    # Проверка всех компонентов
python main.py --config-test     # Тест конфигурации
```

### Управление данными
```bash
python utils.py show-stats                      # Общая статистика
python utils.py show-stats --collection lightsword  # Статистика коллекции
python utils.py export-urls lightsword         # Экспорт URL коллекции
python utils.py export-urls lightsword --status active  # Только активные
```

### Обслуживание кэша
```bash
python utils.py clean-cache      # Очистка старых записей
python utils.py rebuild-cache    # Перестройка из данных
```

### Исправление данных
```bash
python utils.py fix-collection lightsword --backup  # Исправление дубликатов
python utils.py check-integrity                     # Проверка целостности
```

## ⚙️ Конфигурация

### Основные параметры
```python
MAX_CONCURRENT_REQUESTS = 100    # Одновременные соединения
BATCH_SIZE = 500                 # Размер батча
REQUEST_DELAY = 0.1              # Задержка между запросами
TIMEOUT = 15                     # Таймаут запроса
RETRY_COUNT = 3                  # Количество повторов
REQUESTS_PER_SECOND = 20         # Ограничение скорости
```

### Переменные окружения
```bash
export MAX_CONCURRENT_REQUESTS=150
export BATCH_SIZE=1000
export REQUEST_DELAY=0.05
export LOG_LEVEL=DEBUG
```

## 📊 Производительность

### Ожидаемые показатели
- **Скорость**: 200-500 URL/минуту
- **Точность**: >95% успешных парсингов
- **Надежность**: Автоматическое восстановление после ошибок
- **Память**: ~100MB для обработки больших коллекций

### Оптимизация
```bash
# Для быстрых серверов
export MAX_CONCURRENT_REQUESTS=200
export REQUESTS_PER_SECOND=50

# Для медленных соединений
export MAX_CONCURRENT_REQUESTS=50
export REQUEST_DELAY=0.5
```

## 🔍 Мониторинг

### Real-time прогресс
```
🚀 Parser Started: Processing 77 collections
📊 Progress: [████████████████████████████] 1,250,000/8,000,000 (15.6%)
🔄 Current: lightsword collection (batch 25/158)
⚡ Speed: 327 gifts/min | ETA: 25h 14m
✅ Success: 1,247,890 | ❌ Errors: 2,110

Collections Status:
  ✅ astralshard      (12,450/12,450) - Complete
  🔄 lightsword      (8,234/15,420)   - In Progress  
  ⏳ restlessjar     (0/22,180)       - Pending
```

### Логи
```bash
tail -f /app/output/logs/parser.log     # Основные логи
tail -f /app/output/logs/errors.log     # Только ошибки
tail -f /app/output/logs/stats.log      # Статистика
```

## 🛠️ Устранение неполадок

### Частые проблемы

**1. Медленная скорость**
```bash
# Увеличить параллелизм
export MAX_CONCURRENT_REQUESTS=150
export REQUESTS_PER_SECOND=30
```

**2. Много ошибок**
```bash
# Снизить нагрузку
export MAX_CONCURRENT_REQUESTS=50
export REQUEST_DELAY=0.5
```

**3. Проблемы с памятью**
```bash
# Уменьшить размер батча
export BATCH_SIZE=250
```

**4. Восстановление после сбоя**
```bash
python utils.py rebuild-cache    # Восстановить кэш
./run.sh start                   # Продолжить с места остановки
```

### Диагностика
```bash
python main.py --health-check           # Полная диагностика
python utils.py check-integrity         # Проверка данных
python test_parser.py                   # Тест парсинга
```

## 📈 Статистика и отчеты

### Генерация отчетов
```bash
./run.sh stats                          # Все отчеты
python utils.py show-stats              # Текущее состояние
```

### Экспорт данных
```bash
# CSV отчет по сессиям
python -c "
from stats import StatsManager
import asyncio
sm = StatsManager()
asyncio.run(sm.export_stats_csv())
"

# Экспорт URL коллекции
python utils.py export-urls lightsword --output lightsword_urls.txt
```

## 🎯 Примеры использования

### Обработка конкретных коллекций
```bash
# Топ-10 коллекций
for collection in lightsword astralshard restlessjar; do
    ./run.sh collection $collection
done
```

### Регулярные обновления
```bash
#!/bin/bash
# update_gifts.sh - ежедневное обновление
cd /app/parser
./run.sh start                    # Обновить данные
./run.sh stats                    # Обновить статистику
python utils.py clean-cache       # Очистить старый кэш
```

### Анализ данных
```bash
# Найти все подарки с редкими атрибутами
python -c "
import json
from pathlib import Path

for file in Path('/app/output/collections').glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        rare_gifts = [g for g in data['gifts'] 
                     if 'rare' in g.get('model', '').lower()]
        if rare_gifts:
            print(f'{file.stem}: {len(rare_gifts)} rare gifts')
"
```

## 🔐 Безопасность

- **Rate limiting** для соблюдения ограничений API
- **User-Agent ротация** для избежания блокировок
- **Retry логика** с экспоненциальными задержками
- **Graceful shutdown** при получении сигналов

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `/app/output/logs/`
2. **Запустите диагностику**: `python main.py --health-check`
3. **Проверьте конфигурацию**: `python main.py --config-test`
4. **Очистите кэш**: `python utils.py clean-cache`

---

## 🏆 Заключение

Этот парсер представляет собой production-ready решение для масштабного сбора данных о коллекционных подарках Telegram. Благодаря асинхронной архитектуре, интеллектуальному кэшированию и комплексной системе мониторинга, он способен эффективно обрабатывать миллионы URL с высокой точностью и надежностью.

**Готов к обработке 8+ миллионов подарков! 🚀**