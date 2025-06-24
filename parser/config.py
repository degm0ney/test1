"""
Конфигурация парсера коллекционных подарков Telegram
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ParserConfig:
    """Основная конфигурация парсера"""
    
    # Пути к файлам и директориям
    MATERIALS_DIR: Path = Path("/app/materials")
    OUTPUT_DIR: Path = Path("/app/output")
    COLLECTIONS_DIR: Path = OUTPUT_DIR / "collections"
    LOGS_DIR: Path = OUTPUT_DIR / "logs"
    STATS_DIR: Path = OUTPUT_DIR / "stats"
    CACHE_DIR: Path = OUTPUT_DIR / "cache"
    
    # Файлы
    FILE_LIST: Path = MATERIALS_DIR / "file_list.txt"
    CACHE_FILE: Path = CACHE_DIR / "processed_urls.txt"
    PROGRESS_CACHE: Path = CACHE_DIR / "progress.json"
    
    # Производительность
    MAX_CONCURRENT_REQUESTS: int = 100
    BATCH_SIZE: int = 500
    REQUEST_DELAY: float = 0.1
    TIMEOUT: int = 15
    RETRY_COUNT: int = 3
    RETRY_DELAY: float = 1.0
    
    # Rate limiting
    REQUESTS_PER_SECOND: int = 20
    BURST_SIZE: int = 50
    
    # Сохранение данных
    SAVE_INTERVAL: int = 1000
    AUTO_BACKUP: bool = True
    BACKUP_INTERVAL: int = 10000
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5
    
    # User-Agent и заголовки
    USER_AGENTS: List[str] = None
    DEFAULT_HEADERS: Dict[str, str] = None
    
    # Мониторинг
    PROGRESS_UPDATE_INTERVAL: int = 100
    STATS_UPDATE_INTERVAL: int = 1000
    
    # Обработка ошибок
    SKIP_404_ERRORS: bool = True
    SKIP_TIMEOUT_ERRORS: bool = False
    MAX_CONSECUTIVE_ERRORS: int = 50
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        if self.USER_AGENTS is None:
            self.USER_AGENTS = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
            ]
        
        if self.DEFAULT_HEADERS is None:
            self.DEFAULT_HEADERS = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
        
        self._create_directories()
    
    def _create_directories(self):
        """Создание необходимых директорий"""
        for directory in [self.OUTPUT_DIR, self.COLLECTIONS_DIR, self.LOGS_DIR, 
                         self.STATS_DIR, self.CACHE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> 'ParserConfig':
        """Создание конфигурации из переменных окружения"""
        config = cls()
        
        # Переопределение из переменных окружения
        if os.getenv('MAX_CONCURRENT_REQUESTS'):
            config.MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS'))
        
        if os.getenv('BATCH_SIZE'):
            config.BATCH_SIZE = int(os.getenv('BATCH_SIZE'))
        
        if os.getenv('REQUEST_DELAY'):
            config.REQUEST_DELAY = float(os.getenv('REQUEST_DELAY'))
        
        if os.getenv('TIMEOUT'):
            config.TIMEOUT = int(os.getenv('TIMEOUT'))
        
        if os.getenv('RETRY_COUNT'):
            config.RETRY_COUNT = int(os.getenv('RETRY_COUNT'))
        
        if os.getenv('LOG_LEVEL'):
            config.LOG_LEVEL = os.getenv('LOG_LEVEL')
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование конфигурации в словарь"""
        return {
            'max_concurrent_requests': self.MAX_CONCURRENT_REQUESTS,
            'batch_size': self.BATCH_SIZE,
            'request_delay': self.REQUEST_DELAY,
            'timeout': self.TIMEOUT,
            'retry_count': self.RETRY_COUNT,
            'requests_per_second': self.REQUESTS_PER_SECOND,
            'save_interval': self.SAVE_INTERVAL,
            'log_level': self.LOG_LEVEL
        }

# Глобальный экземпляр конфигурации
config = ParserConfig.from_env()