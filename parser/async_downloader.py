"""
Асинхронный загрузчик страниц с rate limiting и обработкой ошибок
"""

import asyncio
import aiohttp
import random
from typing import List, Dict, Tuple, Optional, Set
from aiohttp import ClientSession, ClientTimeout, ClientError
from asyncio import Semaphore
from asyncio_throttle import Throttler
from tenacity import retry, stop_after_attempt, wait_exponential
from fake_useragent import UserAgent
import time

from config import config
from logger import logger

class AsyncDownloader:
    """Асинхронный загрузчик с rate limiting и retry логикой"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.semaphore = Semaphore(config.MAX_CONCURRENT_REQUESTS)
        self.throttler = Throttler(rate_limit=config.REQUESTS_PER_SECOND, period=1.0)
        self.ua = UserAgent()
        
        # Статистика
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retries': 0,
            'timeouts': 0,
            '404_errors': 0,
            'other_errors': 0
        }
        
        # Кэш для неудачных URL (чтобы не повторять запросы)
        self.failed_urls: Set[str] = set()
        
    async def __aenter__(self):
        """Асинхронный менеджер контекста - вход"""
        await self.create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный менеджер контекста - выход"""
        await self.close_session()
    
    async def create_session(self):
        """Создание HTTP сессии"""
        timeout = ClientTimeout(total=config.TIMEOUT)
        connector = aiohttp.TCPConnector(
            limit=config.MAX_CONCURRENT_REQUESTS,
            limit_per_host=50,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            headers=config.DEFAULT_HEADERS
        )
        
        logger.log_info(f"Created HTTP session with {config.MAX_CONCURRENT_REQUESTS} max connections")
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            logger.log_info("HTTP session closed")
    
    async def download_batch(self, urls: List[str], progress_callback=None) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """
        Загружает batch URL'ов асинхронно
        
        Args:
            urls: Список URL для загрузки
            progress_callback: Callback для обновления прогресса
            
        Returns:
            List[Tuple[url, html_content, error_message]]
        """
        if not self.session:
            await self.create_session()
        
        tasks = []
        for url in urls:
            if url not in self.failed_urls:  # Пропускаем уже неудачные URL
                task = asyncio.create_task(self._download_single(url))
                tasks.append((url, task))
        
        results = []
        completed = 0
        
        for url, task in tasks:
            try:
                result = await task
                results.append(result)
                completed += 1
                
                if progress_callback and completed % 10 == 0:
                    await progress_callback(completed, len(tasks))
                    
            except Exception as e:
                logger.log_error(f"Task failed for {url}: {e}")
                results.append((url, None, str(e)))
        
        return results
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _download_single(self, url: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Загружает одну страницу с retry логикой
        
        Returns:
            Tuple[url, html_content, error_message]
        """
        async with self.semaphore:
            async with self.throttler:
                try:
                    self.stats['total_requests'] += 1
                    
                    # Добавляем случайную задержку для имитации человеческого поведения
                    await asyncio.sleep(random.uniform(0.1, config.REQUEST_DELAY))
                    
                    # Ротация User-Agent
                    headers = {
                        **config.DEFAULT_HEADERS,
                        'User-Agent': random.choice(config.USER_AGENTS)
                    }
                    
                    async with self.session.get(url, headers=headers) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            self.stats['successful_requests'] += 1
                            return (url, html_content, None)
                        
                        elif response.status == 404:
                            self.stats['404_errors'] += 1
                            self.failed_urls.add(url)
                            if config.SKIP_404_ERRORS:
                                return (url, None, "404 Not Found")
                            else:
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=404
                                )
                        
                        else:
                            self.stats['other_errors'] += 1
                            error_msg = f"HTTP {response.status}"
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=error_msg
                            )
                
                except asyncio.TimeoutError:
                    self.stats['timeouts'] += 1
                    self.stats['failed_requests'] += 1
                    error_msg = "Request timeout"
                    logger.log_error(error_msg, url)
                    
                    if config.SKIP_TIMEOUT_ERRORS:
                        return (url, None, error_msg)
                    else:
                        raise
                
                except ClientError as e:
                    self.stats['failed_requests'] += 1
                    error_msg = f"Client error: {str(e)}"
                    logger.log_error(error_msg, url)
                    return (url, None, error_msg)
                
                except Exception as e:
                    self.stats['failed_requests'] += 1
                    error_msg = f"Unexpected error: {str(e)}"
                    logger.log_error(error_msg, url)
                    raise
    
    async def download_with_batching(self, urls: List[str], batch_size: int = None, 
                                   progress_callback=None) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """
        Загружает URL'ы батчами для оптимизации памяти
        
        Args:
            urls: Список URL для загрузки
            batch_size: Размер батча (по умолчанию из конфига)
            progress_callback: Callback для обновления прогресса
            
        Returns:
            List[Tuple[url, html_content, error_message]]
        """
        if batch_size is None:
            batch_size = config.BATCH_SIZE
        
        all_results = []
        total_processed = 0
        
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            
            logger.log_info(f"Processing batch {i//batch_size + 1}/{(len(urls)-1)//batch_size + 1} "
                           f"({len(batch_urls)} URLs)")
            
            batch_results = await self.download_batch(batch_urls)
            all_results.extend(batch_results)
            
            total_processed += len(batch_urls)
            
            if progress_callback:
                await progress_callback(total_processed, len(urls))
            
            # Небольшая пауза между батчами
            if i + batch_size < len(urls):
                await asyncio.sleep(0.5)
        
        return all_results
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику загрузок"""
        stats = self.stats.copy()
        if stats['total_requests'] > 0:
            stats['success_rate'] = round((stats['successful_requests'] / stats['total_requests']) * 100, 2)
        else:
            stats['success_rate'] = 0
        
        return stats
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {key: 0 for key in self.stats.keys()}
        self.failed_urls.clear()
    
    async def health_check(self, test_url: str = "https://t.me/nft/lightsword-1") -> bool:
        """
        Проверка работоспособности загрузчика
        
        Args:
            test_url: URL для тестирования
            
        Returns:
            True если загрузчик работает корректно
        """
        try:
            # Создаем временную сессию для health check
            session_created = False
            if not self.session:
                await self.create_session()
                session_created = True
            
            start_time = time.time()
            result = await self._download_single(test_url)
            duration = time.time() - start_time
            
            success = result[1] is not None or result[2] == "404 Not Found"
            
            logger.log_info(f"Health check completed in {duration:.2f}s - "
                           f"Status: {'PASS' if success else 'FAIL'}")
            
            return success
            
        except Exception as e:
            logger.log_error(f"Health check failed: {e}")
            return False
    
    async def estimate_completion_time(self, total_urls: int) -> Dict[str, float]:
        """
        Оценка времени завершения на основе текущей производительности
        
        Args:
            total_urls: Общее количество URL
            
        Returns:
            Словарь с оценками времени
        """
        if self.stats['successful_requests'] == 0:
            # Используем консервативные оценки
            requests_per_second = config.REQUESTS_PER_SECOND * 0.7  # 70% от теоретического максимума
        else:
            # Рассчитываем на основе реальной производительности
            total_time = time.time()  # Это нужно будет отслеживать отдельно
            requests_per_second = self.stats['successful_requests'] / max(total_time, 1)
        
        estimated_seconds = total_urls / max(requests_per_second, 1)
        estimated_minutes = estimated_seconds / 60
        estimated_hours = estimated_minutes / 60
        
        return {
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_minutes,
            'estimated_hours': estimated_hours,
            'requests_per_second': requests_per_second
        }