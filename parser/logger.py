"""
Система логирования для парсера коллекционных подарков
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

from config import config

class ParserLogger:
    """Система логирования с поддержкой Rich"""
    
    def __init__(self):
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка системы логирования"""
        # Создание логгеров
        self.main_logger = logging.getLogger('parser')
        self.error_logger = logging.getLogger('parser.errors')
        self.stats_logger = logging.getLogger('parser.stats')
        
        # Настройка уровня логирования
        level = getattr(logging, config.LOG_LEVEL.upper())
        self.main_logger.setLevel(level)
        self.error_logger.setLevel(logging.ERROR)
        self.stats_logger.setLevel(logging.INFO)
        
        # Создание форматтеров
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Настройка файловых хендлеров
        self._setup_file_handlers(detailed_formatter)
        
        # Настройка консольного хендлера с Rich
        self._setup_console_handler()
    
    def _setup_file_handlers(self, formatter):
        """Настройка файловых хендлеров"""
        # Главный лог файл
        main_handler = logging.handlers.RotatingFileHandler(
            config.LOGS_DIR / 'parser.log',
            maxBytes=config.MAX_LOG_SIZE,
            backupCount=config.BACKUP_COUNT,
            encoding='utf-8'
        )
        main_handler.setFormatter(formatter)
        self.main_logger.addHandler(main_handler)
        
        # Лог ошибок
        error_handler = logging.handlers.RotatingFileHandler(
            config.LOGS_DIR / 'errors.log',
            maxBytes=config.MAX_LOG_SIZE,
            backupCount=config.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        self.error_logger.addHandler(error_handler)
        
        # Лог статистики
        stats_handler = logging.handlers.RotatingFileHandler(
            config.LOGS_DIR / 'stats.log',
            maxBytes=config.MAX_LOG_SIZE,
            backupCount=config.BACKUP_COUNT,
            encoding='utf-8'
        )
        stats_handler.setFormatter(formatter)
        self.stats_logger.addHandler(stats_handler)
    
    def _setup_console_handler(self):
        """Настройка консольного хендлера с Rich"""
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            markup=True
        )
        console_handler.setLevel(logging.INFO)
        self.main_logger.addHandler(console_handler)
    
    def create_progress_bar(self, description: str = "Processing") -> Progress:
        """Создание прогресс-бара"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[bold blue]{task.fields[speed]}/min"),
            TextColumn("ETA: [bold green]{task.fields[eta]}"),
            console=self.console
        )
        return self.progress
    
    def log_startup(self, total_collections: int, total_urls: int):
        """Логирование запуска парсера"""
        self.console.print(Panel.fit(
            f"[bold green]🚀 Parser Started[/bold green]\n"
            f"Collections: [bold]{total_collections}[/bold]\n" 
            f"Total URLs: [bold]{total_urls:,}[/bold]\n"
            f"Started at: [bold]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold]",
            title="Telegram Gifts Parser",
            border_style="green"
        ))
        
        self.main_logger.info(f"Parser started - Collections: {total_collections}, URLs: {total_urls}")
    
    def log_collection_start(self, collection_name: str, total_urls: int):
        """Логирование начала обработки коллекции"""
        self.console.print(f"[bold blue]📂 Processing collection:[/bold blue] [green]{collection_name}[/green] ({total_urls:,} URLs)")
        self.main_logger.info(f"Started processing collection: {collection_name} ({total_urls} URLs)")
    
    def log_collection_complete(self, collection_name: str, processed: int, errors: int, duration: float):
        """Логирование завершения обработки коллекции"""
        success_rate = (processed / (processed + errors)) * 100 if (processed + errors) > 0 else 0
        
        self.console.print(f"[bold green]✅ Completed:[/bold green] [blue]{collection_name}[/blue] - "
                          f"Processed: [green]{processed:,}[/green], "
                          f"Errors: [red]{errors:,}[/red], "
                          f"Success: [bold]{success_rate:.1f}%[/bold], "
                          f"Time: [yellow]{duration:.1f}s[/yellow]")
        
        self.main_logger.info(f"Completed collection: {collection_name} - "
                             f"Processed: {processed}, Errors: {errors}, Duration: {duration:.1f}s")
    
    def log_error(self, error: str, url: str = None, collection: str = None):
        """Логирование ошибки"""
        error_msg = f"Error: {error}"
        if url:
            error_msg += f" - URL: {url}"
        if collection:
            error_msg += f" - Collection: {collection}"
        
        self.error_logger.error(error_msg)
        self.main_logger.error(error_msg)
    
    def log_stats(self, stats_data: dict):
        """Логирование статистики"""
        stats_str = ", ".join([f"{k}: {v}" for k, v in stats_data.items()])
        self.stats_logger.info(f"Stats - {stats_str}")
    
    def display_final_stats(self, stats: dict):
        """Отображение итоговой статистики"""
        table = Table(title="🎯 Final Statistics")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                if key.endswith('_time') or key.endswith('_duration'):
                    value = f"{value:.2f}s"
                elif isinstance(value, int) and value > 1000:
                    value = f"{value:,}"
            table.add_row(key.replace('_', ' ').title(), str(value))
        
        self.console.print(table)
    
    def log_warning(self, message: str):
        """Логирование предупреждения"""
        self.main_logger.warning(message)
    
    def log_info(self, message: str):
        """Логирование информации"""
        self.main_logger.info(message)

# Глобальный экземпляр логгера
logger = ParserLogger()