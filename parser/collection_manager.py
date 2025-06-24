"""
Менеджер коллекций для управления обработкой файлов коллекций
"""

import asyncio
import aiofiles
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time
from datetime import datetime

from config import config
from logger import logger
from async_downloader import AsyncDownloader
from gift_parser import GiftParser
from data_manager import DataManager
from cache_manager import CacheManager

class CollectionManager:
    """Менеджер для управления обработкой коллекций подарков"""
    
    def __init__(self):
        self.downloader = AsyncDownloader()
        self.gift_parser = GiftParser()
        self.data_manager = DataManager()
        self.cache_manager = CacheManager()
        
        # Статистика обработки
        self.processing_stats = {
            'total_collections': 0,
            'completed_collections': 0,
            'total_urls': 0,
            'processed_urls': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'skipped_urls': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def initialize(self) -> bool:
        """
        Инициализация менеджера коллекций
        
        Returns:
            True если инициализация прошла успешно
        """
        try:
            # Загрузка кэша
            await self.cache_manager.load_cache()
            
            # Запуск автоматического сохранения
            await self.data_manager.start_auto_save()
            
            # Проверка работоспособности загрузчика
            async with self.downloader:
                health_check = await self.downloader.health_check()
                if not health_check:
                    logger.log_warning("Downloader health check failed, but continuing...")
            
            logger.log_info("Collection manager initialized successfully")
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to initialize collection manager: {e}")
            return False
    
    async def load_collection_urls(self, collection_name: str) -> List[str]:
        """
        Загружает URL'ы коллекции из файла
        
        Args:
            collection_name: Название коллекции
            
        Returns:
            Список URL'ов коллекции
        """
        collection_file = config.MATERIALS_DIR / f"{collection_name}.txt"
        
        if not collection_file.exists():
            logger.log_error(f"Collection file not found: {collection_file}")
            return []
        
        urls = []
        try:
            async with aiofiles.open(collection_file, 'r', encoding='utf-8') as f:
                async for line in f:
                    url = line.strip()
                    if url and url.startswith('https://t.me/nft/'):
                        urls.append(url)
            
            logger.log_info(f"Loaded {len(urls)} URLs for collection {collection_name}")
            return urls
            
        except Exception as e:
            logger.log_error(f"Failed to load URLs for collection {collection_name}: {e}")
            return []
    
    async def process_collection(self, collection_name: str, 
                               resume_mode: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает одну коллекцию
        
        Args:
            collection_name: Название коллекции
            resume_mode: Если True, пропускает уже обработанные URL
            
        Returns:
            Статистика обработки коллекции
        """
        start_time = time.time()
        
        logger.log_collection_start(collection_name, 0)  # Обновим после загрузки URL
        
        # Загружаем URL'ы коллекции
        all_urls = await self.load_collection_urls(collection_name)
        if not all_urls:
            return self._create_collection_stats(collection_name, 0, 0, 0, 0)
        
        # Фильтруем уже обработанные URL если включен режим resume
        if resume_mode:
            urls_to_process = self.cache_manager.filter_unprocessed_urls(all_urls)
            skipped_count = len(all_urls) - len(urls_to_process)
            logger.log_info(f"Resume mode: processing {len(urls_to_process)} URLs, "
                           f"skipping {skipped_count} already processed")
        else:
            urls_to_process = all_urls
            skipped_count = 0
        
        # Обновляем логирование с правильным количеством URL
        logger.log_collection_start(collection_name, len(urls_to_process))
        
        if not urls_to_process:
            logger.log_info(f"Collection {collection_name} already fully processed")
            return self._create_collection_stats(collection_name, len(all_urls), 0, 0, skipped_count)
        
        # Обрабатываем URL'ы батчами
        processed_count = 0
        success_count = 0
        error_count = 0
        
        async with self.downloader:
            # Создаем progress callback
            def create_progress_callback():
                last_update = {'time': time.time(), 'count': 0}
                
                async def progress_callback(current: int, total: int):
                    nonlocal last_update
                    now = time.time()
                    if now - last_update['time'] >= 5.0:  # Обновляем каждые 5 секунд
                        speed = (current - last_update['count']) / (now - last_update['time'])
                        logger.log_info(f"Collection {collection_name}: {current}/{total} "
                                       f"({(current/total)*100:.1f}%) - {speed:.1f} URLs/sec")
                        last_update['time'] = now
                        last_update['count'] = current
                
                return progress_callback
            
            # Обрабатываем URL'ы с помощью downloader
            results = await self.downloader.download_with_batching(
                urls_to_process, 
                config.BATCH_SIZE,
                create_progress_callback()
            )
            
            # Парсим результаты
            for url, html_content, error in results:
                processed_count += 1
                
                if html_content is not None:
                    # Парсим данные подарка
                    gift_data = self.gift_parser.parse_gift_data(html_content, url)
                    
                    if gift_data and self.gift_parser.validate_gift_data(gift_data):
                        # Добавляем подарок в коллекцию
                        await self.data_manager.add_gifts_to_collection(collection_name, [gift_data])
                        success_count += 1
                        
                        # Отмечаем URL как обработанный
                        self.cache_manager.mark_url_processed(
                            url, 'active', 
                            {'gift_id': gift_data.get('gift_id'), 'collection': collection_name}
                        )
                    else:
                        error_count += 1
                        self.cache_manager.mark_url_processed(url, 'parse_failed')
                else:
                    error_count += 1
                    status = 'deleted' if error == "404 Not Found" else 'error'
                    self.cache_manager.mark_url_processed(url, status, {'error': error})
                
                # Периодическое сохранение
                if processed_count % config.SAVE_INTERVAL == 0:
                    await self._periodic_save(collection_name, processed_count, success_count, error_count)
        
        # Финальное сохранение
        await self.data_manager.save_collection(collection_name)
        await self.cache_manager.save_cache()
        
        # Обновляем прогресс коллекции
        await self.cache_manager.update_collection_progress(
            collection_name, len(all_urls), processed_count, success_count, error_count
        )
        
        duration = time.time() - start_time
        logger.log_collection_complete(collection_name, success_count, error_count, duration)
        
        return self._create_collection_stats(
            collection_name, len(all_urls), processed_count, success_count, error_count, duration
        )
    
    async def _periodic_save(self, collection_name: str, processed: int, success: int, errors: int):
        """Периодическое сохранение данных и кэша"""
        logger.log_info(f"Periodic save - {collection_name}: processed {processed}, "
                       f"success {success}, errors {errors}")
        
        await self.data_manager.save_collection(collection_name)
        await self.cache_manager.save_cache()
    
    def _create_collection_stats(self, collection_name: str, total_urls: int, 
                               processed: int, success: int, errors: int, 
                               duration: float = 0) -> Dict[str, Any]:
        """Создает статистику обработки коллекции"""
        return {
            'collection_name': collection_name,
            'total_urls': total_urls,
            'processed_urls': processed,
            'successful_parses': success,
            'failed_parses': errors,
            'success_rate': (success / processed) * 100 if processed > 0 else 0,
            'duration': duration,
            'urls_per_second': processed / duration if duration > 0 else 0
        }
    
    async def process_all_collections(self, resume_mode: bool = True) -> Dict[str, Any]:
        """
        Обрабатывает все коллекции из file_list.txt
        
        Args:
            resume_mode: Если True, пропускает уже обработанные URL
            
        Returns:
            Общая статистика обработки
        """
        self.processing_stats['start_time'] = time.time()
        
        # Загружаем список коллекций
        collections = await self._load_collections_list()
        if not collections:
            logger.log_error("No collections found to process")
            return self.processing_stats
        
        self.processing_stats['total_collections'] = len(collections)
        
        # Подсчитываем общее количество URL
        total_urls = 0
        for collection_name in collections:
            urls = await self.load_collection_urls(collection_name)
            total_urls += len(urls)
        
        self.processing_stats['total_urls'] = total_urls
        logger.log_startup(len(collections), total_urls)
        
        # Обрабатываем каждую коллекцию
        collection_results = {}
        
        for i, collection_name in enumerate(collections, 1):
            logger.log_info(f"Processing collection {i}/{len(collections)}: {collection_name}")
            
            try:
                collection_stats = await self.process_collection(collection_name, resume_mode)
                collection_results[collection_name] = collection_stats
                
                # Обновляем общую статистику
                self.processing_stats['completed_collections'] += 1
                self.processing_stats['processed_urls'] += collection_stats['processed_urls']
                self.processing_stats['successful_parses'] += collection_stats['successful_parses']
                self.processing_stats['failed_parses'] += collection_stats['failed_parses']
                
            except Exception as e:
                logger.log_error(f"Failed to process collection {collection_name}: {e}")
                collection_results[collection_name] = {
                    'error': str(e),
                    'processed_urls': 0,
                    'successful_parses': 0,
                    'failed_parses': 0
                }
        
        self.processing_stats['end_time'] = time.time()
        self.processing_stats['total_duration'] = (
            self.processing_stats['end_time'] - self.processing_stats['start_time']
        )
        
        # Финальное сохранение всех данных
        await self.data_manager.save_all_collections()
        await self.cache_manager.save_cache(force=True)
        
        # Генерируем итоговую статистику
        final_stats = {
            **self.processing_stats,
            'collection_results': collection_results,
            'downloader_stats': self.downloader.get_stats(),
            'cache_stats': self.cache_manager.get_cache_stats()
        }
        
        logger.display_final_stats(final_stats)
        
        return final_stats
    
    async def _load_collections_list(self) -> List[str]:
        """Загружает список коллекций из file_list.txt"""
        if not config.FILE_LIST.exists():
            logger.log_error(f"File list not found: {config.FILE_LIST}")
            return []
        
        collections = []
        try:
            async with aiofiles.open(config.FILE_LIST, 'r', encoding='utf-8') as f:
                async for line in f:
                    collection_name = line.strip()
                    if collection_name and not collection_name.startswith('#'):
                        # Убираем расширение .txt если оно есть
                        if collection_name.endswith('.txt'):
                            collection_name = collection_name[:-4]
                        collections.append(collection_name)
            
            logger.log_info(f"Loaded {len(collections)} collections from file list")
            return collections
            
        except Exception as e:
            logger.log_error(f"Failed to load collections list: {e}")
            return []
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус обработки"""
        overall_progress = self.cache_manager.get_overall_progress()
        downloader_stats = self.downloader.get_stats()
        
        return {
            'processing_stats': self.processing_stats,
            'overall_progress': overall_progress,
            'downloader_stats': downloader_stats,
            'cache_stats': self.cache_manager.get_cache_stats()
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        # Останавливаем автосохранение
        await self.data_manager.stop_auto_save()
        
        # Финальное сохранение всех коллекций
        save_results = await self.data_manager.save_all_collections()
        saved_count = sum(1 for success in save_results.values() if success)
        logger.log_info(f"💾 Финальное сохранение: {saved_count} коллекций")
        
        if hasattr(self.downloader, 'close_session'):
            await self.downloader.close_session()
        
        await self.cache_manager.save_cache(force=True)
        logger.log_info("🧹 Очистка менеджера коллекций завершена")