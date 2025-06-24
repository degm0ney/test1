# 🎁 Telegram Gifts Parser для Windows 10

## 🚀 Быстрый старт на Windows

### Вариант 1: Через командную строку Windows (cmd)

1. **Открыть cmd как администратор**
2. **Перейти в папку парсера:**
   ```cmd
   cd C:\путь\к\вашей\папке\parser
   ```

3. **Полная настройка (выполнить один раз):**
   ```cmd
   run.bat setup
   ```

4. **Демо-режим (для тестирования):**
   ```cmd
   run.bat demo
   ```

5. **Запуск полного парсинга:**
   ```cmd
   run.bat start
   ```

### Вариант 2: Через Python Launcher (для PyCharm)

1. **Настройка:**
   ```cmd
   python launcher.py setup
   ```

2. **Демо-режим:**
   ```cmd
   python launcher.py demo
   ```

3. **Полный парсинг:**
   ```cmd
   python launcher.py start
   ```

4. **Обработка одной коллекции:**
   ```cmd
   python launcher.py collection lightsword
   ```

### Вариант 3: Настройка в PyCharm

1. **Создать новую конфигурацию запуска:**
   - **Script path:** `C:\путь\к\вашей\папке\parser\launcher.py`
   - **Parameters:** `demo` (для демо) или `start` (для полного парсинга)
   - **Working directory:** `C:\путь\к\вашей\папке\parser`

2. **Запустить через PyCharm** (F5 или зеленая кнопка)

## 📊 Автоматическое сохранение результатов

**Ключевая особенность:** Файлы результатов обновляются **каждую минуту** автоматически!

### Где смотреть результаты:
- **Основные данные:** `output/collections/[название_коллекции].json`
- **Логи работы:** `output/logs/parser.log`
- **Статистика:** `output/stats/`
- **Демо-результаты:** `output/demo_results.json`

### Как отслеживать прогресс:
1. **В реальном времени:** Смотрите логи в консоли
2. **Файлы JSON:** Обновляются каждые 60 секунд автоматически
3. **Промежуточные сохранения:** Каждые 30 секунд при активной обработке

## ⚙️ Команды управления

### Команды для run.bat:
```cmd
run.bat help           # Показать справку
run.bat setup          # Полная настройка
run.bat install        # Только установка зависимостей
run.bat check          # Проверка окружения
run.bat health-check   # Проверка работоспособности
run.bat demo           # Демо-парсинг (20 URL)
run.bat start          # Полный парсинг (продолжить с кэша)
run.bat start-full     # Полный парсинг (игнорировать кэш)
run.bat collection lightsword    # Обработать только коллекцию lightsword
run.bat stats          # Генерировать статистику
```

### Команды для launcher.py:
```cmd
python launcher.py setup
python launcher.py demo
python launcher.py start
python launcher.py start --full
python launcher.py collection lightsword
python launcher.py stats
python launcher.py health-check
```

## 🔧 Настройка производительности

### Переменные окружения (опционально):
```cmd
set MAX_CONCURRENT_REQUESTS=150
set BATCH_SIZE=1000
set REQUEST_DELAY=0.05
python launcher.py start
```

### Для медленных соединений:
```cmd
set MAX_CONCURRENT_REQUESTS=50
set REQUEST_DELAY=0.5
python launcher.py start
```

## 📁 Структура выходных файлов

```
output/
├── collections/          # JSON файлы коллекций (обновляются каждую минуту)
│   ├── lightsword.json
│   ├── astralshard.json
│   └── ...
├── logs/                # Логи работы
│   ├── parser.log
│   └── errors.log
├── stats/               # Статистика и отчеты
│   └── summary.json
└── cache/               # Кэш и прогресс
    ├── processed_urls.txt
    └── progress.json
```

## 🎯 Примеры использования

### 1. Первый запуск (тестирование):
```cmd
# Настройка
run.bat setup

# Демо-режим для проверки
run.bat demo

# Проверить результаты в output/demo_results.json
```

### 2. Обработка конкретной коллекции:
```cmd
run.bat collection lightsword
```

### 3. Полный парсинг всех коллекций:
```cmd
run.bat start
```

### 4. Генерация отчетов:
```cmd
run.bat stats
```

## 🛠️ Устранение проблем

### Если парсер не запускается:
1. **Проверить Python:** `python --version` (нужен 3.9+)
2. **Установить зависимости:** `run.bat install`
3. **Проверить окружение:** `run.bat check`
4. **Запустить диагностику:** `run.bat health-check`

### Если медленно работает:
```cmd
# Увеличить параллелизм
set MAX_CONCURRENT_REQUESTS=200
set REQUESTS_PER_SECOND=50
run.bat start
```

### Если много ошибок:
```cmd
# Снизить нагрузку
set MAX_CONCURRENT_REQUESTS=30
set REQUEST_DELAY=1.0
run.bat start
```

## 📈 Мониторинг работы

### В реальном времени:
- Прогресс отображается в консоли
- Скорость обработки: ~200-500 URL/минуту
- ETA (оставшееся время) показывается автоматически

### Файлы результатов:
- **Обновляются каждую минуту** автоматически
- Можно открывать в любом редакторе JSON
- Содержат полную информацию о подарках

### Логи:
- `output/logs/parser.log` - основные логи
- `output/logs/errors.log` - только ошибки

## 🎉 Готово!

Парсер настроен для работы на Windows 10 через cmd или PyCharm. 
Файлы результатов будут автоматически обновляться каждую минуту, 
так что вы всегда сможете видеть текущий прогресс работы!

**Для быстрого старта:** 
1. `run.bat setup`
2. `run.bat demo` 
3. `run.bat start`