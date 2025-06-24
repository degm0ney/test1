"""
Менеджер кэша для отслеживания обработанных URL и инкрементальных обновлений
"""

import ujson as json
import aiofiles
import asyncio
from typing import Set, Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

from config import config
from logger import logger

class CacheManager:
    """Менеджер кэша для оптимизации повторных запусков парсера"""
    
    def __init__(self):
        self.processed_urls: Set[str] = set()
        self.url_status_cache: Dict[str, Dict[str, Any]] = {}
        self.collection_progress: Dict[str, Dict[str, Any]] = {}
        self.cache_dirty = False
        self.last_save_time = datetime.utcnow()
        
    async def load_cache(self) -> bool:
        """
        Загружает кэш из файлов
        
        Returns:
            True если кэш успешно загружен
        """
        try:
            # Загрузка списка обработанных URL
            await self._load_processed_urls()
            
            # Загрузка кэша статусов URL
            await self._load_url_status_cache()
            
            # Загрузка прогресса коллекций
            await self._load_collection_progress()
            
            logger.log_info(f"Cache loaded: {len(self.processed_urls)} processed URLs, "
                           f"{len(self.url_status_cache)} cached statuses")
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to load cache: {e}")
            return False
    
    async def _load_processed_urls(self):
        """Загружает список обработанных URL"""
        if config.CACHE_FILE.exists():
            async with aiofiles.open(config.CACHE_FILE, 'r', encoding='utf-8') as f:
                async for line in f:
                    url = line.strip()
                    if url:
                        self.processed_urls.add(url)
    
    async def _load_url_status_cache(self):
        """Загружает кэш статусов URL"""
        cache_file = config.CACHE_DIR / 'url_status_cache.json'
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.url_status_cache = json.loads(content)
            except Exception as e:
                logger.log_warning(f"Failed to load URL status cache: {e}")
                self.url_status_cache = {}
    
    async def _load_collection_progress(self):
        """Загружает прогресс обработки коллекций"""
        if config.PROGRESS_CACHE.exists():
            try:
                async with aiofiles.open(config.PROGRESS_CACHE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.collection_progress = json.loads(content)
            except Exception as e:
                logger.log_warning(f"Failed to load collection progress: {e}")
                self.collection_progress = {}
    
    async def save_cache(self, force: bool = False) -> bool:
        """
        Сохраняет кэш в файлы
        
        Args:
            force: Принудительное сохранение
            
        Returns:
            True если кэш успешно сохранен
        """
        if not self.cache_dirty and not force:
            return True
        
        try:
            # Сохранение списка обработанных URL
            await self._save_processed_urls()
            
            # Сохранение кэша статусов URL
            await self._save_url_status_cache()
            
            # Сохранение прогресса коллекций
            await self._save_collection_progress()
            
            self.cache_dirty = False
            self.last_save_time = datetime.utcnow()
            
            logger.log_info("Cache saved successfully")
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to save cache: {e}")
            return False
    
    async def _save_processed_urls(self):
        """Сохраняет список обработанных URL"""
        async with aiofiles.open(config.CACHE_FILE, 'w', encoding='utf-8') as f:
            for url in sorted(self.processed_urls):
                await f.write(f"{url}\n")
    
    async def _save_url_status_cache(self):
        """Сохраняет кэш статусов URL"""
        cache_file = config.CACHE_DIR / 'url_status_cache.json'
        async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
            json_data = json.dumps(self.url_status_cache, ensure_ascii=False, indent=2)
            await f.write(json_data)
    
    async def _save_collection_progress(self):
        """Сохраняет прогресс обработки коллекций"""
        async with aiofiles.open(config.PROGRESS_CACHE, 'w', encoding='utf-8') as f:
            json_data = json.dumps(self.collection_progress, ensure_ascii=False, indent=2)
            await f.write(json_data)
    
    def is_url_processed(self, url: str) -> bool:
        """Проверяет, был ли URL уже обработан"""
        return url in self.processed_urls
    
    def mark_url_processed(self, url: str, status: str = 'processed', 
                          metadata: Optional[Dict[str, Any]] = None):
        """
        Отмечает URL как обработанный
        
        Args:
            url: URL для отметки
            status: Статус обработки
            metadata: Дополнительные метаданные
        """
        self.processed_urls.add(url)
        
        # Сохраняем дополнительную информацию о URL
        self.url_status_cache[url] = {
            'status': status,
            'processed_at': datetime.utcnow().isoformat() + 'Z',
            'metadata': metadata or {}
        }
        
        self.cache_dirty = True
    
    def get_url_status(self, url: str) -> Optional[Dict[str, Any]]:
        """Возвращает статус URL из кэша"""
        return self.url_status_cache.get(url)
    
    def filter_unprocessed_urls(self, urls: List[str]) -> List[str]:
        """
        Фильтрует список URL, оставляя только необработанные
        
        Args:
            urls: Список URL для фильтрации
            
        Returns:
            Список необработанных URL
        """
        return [url for url in urls if not self.is_url_processed(url)]
    
    async def update_collection_progress(self, collection_name: str, 
                                       total_urls: int, processed_urls: int,
                                       success_count: int, error_count: int):
        """
        Обновляет прогресс обработки коллекции
        
        Args:
            collection_name: Название коллекции
            total_urls: Общее количество URL
            processed_urls: Количество обработанных URL
            success_count: Количество успешных обработок
            error_count: Количество ошибок
        """
        self.collection_progress[collection_name] = {
            'total_urls': total_urls,
            'processed_urls': processed_urls,
            'success_count': success_count,
            'error_count': error_count,
            'completion_rate': (processed_urls / total_urls) * 100 if total_urls > 0 else 0,
            'success_rate': (success_count / processed_urls) * 100 if processed_urls > 0 else 0,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.cache_dirty = True
    
    def get_collection_progress(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Возвращает прогресс обработки коллекции"""
        return self.collection_progress.get(collection_name)
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Возвращает общий прогресс обработки всех коллекций"""
        if not self.collection_progress:
            return {
                'total_collections': 0,
                'completed_collections': 0,
                'total_urls': 0,
                'processed_urls': 0,
                'overall_completion_rate': 0.0
            }
        
        total_urls = sum(p['total_urls'] for p in self.collection_progress.values())
        processed_urls = sum(p['processed_urls'] for p in self.collection_progress.values())
        completed_collections = sum(1 for p in self.collection_progress.values() 
                                  if p['completion_rate'] >= 100.0)
        
        return {
            'total_collections': len(self.collection_progress),
            'completed_collections': completed_collections,
            'total_urls': total_urls,
            'processed_urls': processed_urls,
            'overall_completion_rate': (processed_urls / total_urls) * 100 if total_urls > 0 else 0.0
        }
    
    async def cleanup_old_cache_entries(self, max_age_days: int = 30):
        """
        Очищает старые записи кэша
        
        Args:
            max_age_days: Максимальный возраст записей в днях
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cutoff_str = cutoff_date.isoformat() + 'Z'
        
        cleaned_count = 0
        urls_to_remove = []
        
        for url, cache_data in self.url_status_cache.items():
            processed_at = cache_data.get('processed_at', '')
            if processed_at < cutoff_str:
                urls_to_remove.append(url)
        
        for url in urls_to_remove:
            del self.url_status_cache[url]
            self.processed_urls.discard(url)
            cleaned_count += 1
        
        if cleaned_count > 0:
            self.cache_dirty = True
            logger.log_info(f"Cleaned {cleaned_count} old cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        return {
            'processed_urls_count': len(self.processed_urls),
            'cached_statuses_count': len(self.url_status_cache),
            'collections_tracked': len(self.collection_progress),
            'cache_dirty': self.cache_dirty,
            'last_save_time': self.last_save_time.isoformat() + 'Z'
        }
    
    async def rebuild_cache_from_collections(self, data_manager) -> int:
        """
        Перестраивает кэш на основе существующих данных коллекций
        
        Args:
            data_manager: Экземпляр DataManager
            
        Returns:
            Количество восстановленных записей
        """
        logger.log_info("Rebuilding cache from existing collections...")
        
        # Очищаем текущий кэш
        self.processed_urls.clear()
        self.url_status_cache.clear()
        
        rebuilt_count = 0
        collection_files = list(config.COLLECTIONS_DIR.glob("*.json"))
        
        for collection_file in collection_files:
            if collection_file.name.endswith('.backup'):
                continue
            
            collection_name = collection_file.stem
            try:
                collection_data = await data_manager.load_collection(collection_name)
                
                for gift in collection_data.get('gifts', []):
                    url = gift.get('url')
                    status = gift.get('status', 'unknown')
                    parsed_at = gift.get('parsed_at')
                    
                    if url:
                        self.mark_url_processed(url, status, {
                            'gift_id': gift.get('gift_id'),
                            'collection': collection_name,
                            'parsed_at': parsed_at
                        })
                        rebuilt_count += 1
                
            except Exception as e:
                logger.log_error(f"Failed to rebuild cache for {collection_name}: {e}")
        
        logger.log_info(f"Cache rebuilt: {rebuilt_count} entries restored")
        return rebuilt_count
    
    async def generate_cache_report(self) -> Dict[str, Any]:
        """Генерирует подробный отчет о состоянии кэша"""
        status_breakdown = {}
        collection_breakdown = {}
        
        for url, cache_data in self.url_status_cache.items():
            status = cache_data.get('status', 'unknown')
            collection = cache_data.get('metadata', {}).get('collection', 'unknown')
            
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
            collection_breakdown[collection] = collection_breakdown.get(collection, 0) + 1
        
        return {
            'total_cached_urls': len(self.url_status_cache),
            'total_processed_urls': len(self.processed_urls),
            'status_breakdown': status_breakdown,
            'collection_breakdown': collection_breakdown,
            'cache_stats': self.get_cache_stats(),
            'overall_progress': self.get_overall_progress(),
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }