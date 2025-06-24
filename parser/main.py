#!/usr/bin/env python3
"""
Главный файл парсера коллекционных подарков Telegram

Использование:
    python main.py [OPTIONS]

Опции:
    --resume        Продолжить с того места, где остановились (по умолчанию)
    --full          Полная обработка всех URL (игнорировать кэш)
    --collection    Обработать только указанную коллекцию
    --stats-only    Только генерация статистики
    --health-check  Проверка работоспособности
    --help          Показать справку
"""

import asyncio
import sys
import signal
from pathlib import Path
import click
from typing import Optional
import time

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from logger import logger
from collection_manager import CollectionManager
from stats import StatsManager
from data_manager import DataManager
from cache_manager import CacheManager

class TelegramGiftsParser:
    """Главный класс парсера коллекционных подарков Telegram"""
    
    def __init__(self):
        self.collection_manager = CollectionManager()
        self.stats_manager = StatsManager()
        self.running = True
        self.session_id = None
        
        # Обработка сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.log_info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def run_health_check(self) -> bool:
        """
        Проверка работоспособности парсера
        
        Returns:
            True если все компоненты работают корректно
        """
        logger.log_info("Running health check...")
        
        try:
            # Проверка конфигурации
            logger.log_info("✓ Configuration loaded")
            
            # Проверка доступности файлов
            if not config.FILE_LIST.exists():
                logger.log_error("✗ File list not found")
                return False
            logger.log_info("✓ File list accessible")
            
            # Проверка материалов
            test_collection = "lightsword"
            test_file = config.MATERIALS_DIR / f"{test_collection}.txt"
            if not test_file.exists():
                logger.log_error("✗ Test collection file not found")
                return False
            logger.log_info("✓ Collection files accessible")
            
            # Проверка сетевого соединения
            await self.collection_manager.initialize()
            async with self.collection_manager.downloader:
                health_ok = await self.collection_manager.downloader.health_check()
                if not health_ok:
                    logger.log_error("✗ Network health check failed")
                    return False
                logger.log_info("✓ Network connectivity OK")
            
            # Проверка парсера
            test_html = """
            <html>
                <head>
                    <meta property="og:title" content="Light Sword #1">
                    <meta property="og:image" content="https://example.com/image.jpg">
                    <meta property="og:description" content="Model: Test\nBackdrop: Test\nSymbol: Test">
                </head>
            </html>
            """
            test_url = "https://t.me/nft/lightsword-1"
            parsed_data = self.collection_manager.gift_parser.parse_gift_data(test_html, test_url)
            if not parsed_data:
                logger.log_error("✗ Gift parser test failed")
                return False
            logger.log_info("✓ Gift parser working")
            
            logger.log_info("🎉 All health checks passed!")
            return True
            
        except Exception as e:
            logger.log_error(f"✗ Health check failed: {e}")
            return False
        finally:
            await self.collection_manager.cleanup()
    
    async def run_stats_generation(self) -> bool:
        """
        Генерирует только статистику без парсинга
        
        Returns:
            True если статистика успешно сгенерирована
        """
        logger.log_info("Generating statistics...")
        
        try:
            data_manager = DataManager()
            cache_manager = CacheManager()
            await cache_manager.load_cache()
            
            # Генерируем различные отчеты
            collection_stats = await self.stats_manager.generate_collection_stats(data_manager)
            performance_report = await self.stats_manager.generate_performance_report()
            summary_report = await self.stats_manager.generate_summary_report(data_manager, cache_manager)
            
            # Экспортируем в CSV
            csv_file = await self.stats_manager.export_stats_csv()
            
            logger.log_info(f"📊 Statistics generated successfully!")
            logger.log_info(f"📈 Collection stats: {len(collection_stats.get('collections', {}))} collections")
            logger.log_info(f"⚡ Performance report: {len(performance_report.get('sessions_history', []))} sessions")
            logger.log_info(f"📋 Summary report saved")
            logger.log_info(f"📄 CSV export: {csv_file}")
            
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to generate statistics: {e}")
            return False
    
    async def run_single_collection(self, collection_name: str, resume_mode: bool = True) -> bool:
        """
        Обрабатывает одну коллекцию
        
        Args:
            collection_name: Название коллекции
            resume_mode: Режим продолжения с кэша
            
        Returns:
            True если обработка прошла успешно
        """
        logger.log_info(f"Processing single collection: {collection_name}")
        
        try:
            # Инициализация
            await self.collection_manager.initialize()
            
            # Начинаем сессию
            self.session_id = await self.stats_manager.start_session(f"single_{collection_name}")
            
            # Обрабатываем коллекцию
            collection_stats = await self.collection_manager.process_collection(collection_name, resume_mode)
            
            # Создаем итоговую статистику
            final_stats = {
                'total_collections': 1,
                'completed_collections': 1 if collection_stats['processed_urls'] > 0 else 0,
                'total_urls': collection_stats['total_urls'],
                'processed_urls': collection_stats['processed_urls'],
                'successful_parses': collection_stats['successful_parses'],
                'failed_parses': collection_stats['failed_parses'],
                'total_duration': collection_stats['duration']
            }
            
            # Завершаем сессию
            await self.stats_manager.end_session(final_stats)
            
            logger.log_info(f"✅ Collection {collection_name} processed successfully!")
            logger.display_final_stats(final_stats)
            
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to process collection {collection_name}: {e}")
            return False
        finally:
            await self.collection_manager.cleanup()
    
    async def run_full_parsing(self, resume_mode: bool = True) -> bool:
        """
        Запускает полную обработку всех коллекций
        
        Args:
            resume_mode: Режим продолжения с кэша
            
        Returns:
            True если обработка прошла успешно
        """
        logger.log_info("Starting full parsing of all collections...")
        
        try:
            # Инициализация
            await self.collection_manager.initialize()
            
            # Начинаем сессию
            self.session_id = await self.stats_manager.start_session()
            
            # Запускаем обработку всех коллекций
            final_stats = await self.collection_manager.process_all_collections(resume_mode)
            
            if not self.running:
                logger.log_info("Parsing interrupted by user")
                return False
            
            # Завершаем сессию
            await self.stats_manager.end_session(final_stats)
            
            # Генерируем итоговые отчеты
            await self.run_stats_generation()
            
            logger.log_info("🎉 Full parsing completed successfully!")
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to complete full parsing: {e}")
            return False
        finally:
            await self.collection_manager.cleanup()

# CLI интерфейс с Click
@click.command()
@click.option('--resume/--full', default=True, 
              help='Resume from cache (default) or full reprocessing')
@click.option('--collection', type=str, default=None,
              help='Process only specific collection')
@click.option('--stats-only', is_flag=True, default=False,
              help='Generate statistics only (no parsing)')
@click.option('--health-check', is_flag=True, default=False,
              help='Run health check only')
@click.option('--config-test', is_flag=True, default=False,
              help='Test configuration and exit')
def main(resume, collection, stats_only, health_check, config_test):
    """
    Telegram Collectible Gifts Parser
    
    Парсер коллекционных подарков Telegram с поддержкой асинхронной обработки,
    кэширования и детальной статистики.
    """
    
    # Баннер
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           🎁 TELEGRAM COLLECTIBLE GIFTS PARSER 🎁            ║
    ║                                                               ║
    ║                          v1.0                                ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Тест конфигурации
    if config_test:
        logger.log_info("Configuration test:")
        logger.log_info(f"Materials dir: {config.MATERIALS_DIR}")
        logger.log_info(f"Output dir: {config.OUTPUT_DIR}")
        logger.log_info(f"Max concurrent: {config.MAX_CONCURRENT_REQUESTS}")
        logger.log_info(f"Batch size: {config.BATCH_SIZE}")
        logger.log_info("✅ Configuration OK")
        return
    
    # Создаем парсер
    parser = TelegramGiftsParser()
    
    # Выбор режима работы
    async def run_async():
        try:
            if health_check:
                success = await parser.run_health_check()
                sys.exit(0 if success else 1)
                
            elif stats_only:
                success = await parser.run_stats_generation()
                sys.exit(0 if success else 1)
                
            elif collection:
                success = await parser.run_single_collection(collection, resume)
                sys.exit(0 if success else 1)
                
            else:
                success = await parser.run_full_parsing(resume)
                sys.exit(0 if success else 1)
                
        except KeyboardInterrupt:
            logger.log_info("Interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.log_error(f"Unexpected error: {e}")
            sys.exit(1)
    
    # Запуск асинхронного кода
    asyncio.run(run_async())

if __name__ == "__main__":
    main()