"""
Менеджер данных для сохранения и загрузки JSON файлов коллекций
"""

import ujson as json
import aiofiles
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import shutil

from config import config
from logger import logger

class DataManager:
    """Менеджер для работы с JSON данными коллекций"""
    
    def __init__(self):
        self.collections_cache: Dict[str, Dict] = {}
        self.pending_writes: Dict[str, List[Dict]] = {}
        self.write_lock = asyncio.Lock()
        
    async def load_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        Загружает данные коллекции из JSON файла
        
        Args:
            collection_name: Название коллекции
            
        Returns:
            Словарь с данными коллекции
        """
        collection_file = config.COLLECTIONS_DIR / f"{collection_name}.json"
        
        if collection_name in self.collections_cache:
            return self.collections_cache[collection_name]
        
        if collection_file.exists():
            try:
                async with aiofiles.open(collection_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    collection_data = json.loads(content)
                    self.collections_cache[collection_name] = collection_data
                    logger.log_info(f"Loaded collection {collection_name}: {len(collection_data.get('gifts', []))} gifts")
                    return collection_data
            except Exception as e:
                logger.log_error(f"Failed to load collection {collection_name}: {e}")
        
        # Создаем новую коллекцию если файл не существует
        new_collection = self._create_empty_collection(collection_name)
        self.collections_cache[collection_name] = new_collection
        return new_collection
    
    def _create_empty_collection(self, collection_name: str) -> Dict[str, Any]:
        """Создает пустую структуру коллекции"""
        return {
            "collection_name": collection_name,
            "total_gifts": 0,
            "processed_gifts": 0,
            "last_updated": datetime.utcnow().isoformat() + 'Z',
            "created_at": datetime.utcnow().isoformat() + 'Z',
            "gifts": []
        }
    
    async def save_collection(self, collection_name: str, force_write: bool = False) -> bool:
        """
        Сохраняет коллекцию в JSON файл
        
        Args:
            collection_name: Название коллекции
            force_write: Принудительная запись независимо от буфера
            
        Returns:
            True если сохранение прошло успешно
        """
        async with self.write_lock:
            try:
                if collection_name not in self.collections_cache:
                    logger.log_warning(f"Collection {collection_name} not found in cache")
                    return False
                
                collection_data = self.collections_cache[collection_name]
                collection_data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
                collection_data['processed_gifts'] = len(collection_data['gifts'])
                
                collection_file = config.COLLECTIONS_DIR / f"{collection_name}.json"
                
                # Создаем резервную копию если файл существует
                if collection_file.exists() and config.AUTO_BACKUP:
                    backup_file = config.COLLECTIONS_DIR / f"{collection_name}.json.backup"
                    shutil.copy2(collection_file, backup_file)
                
                # Сохраняем данные в временный файл, затем переименовываем
                temp_file = collection_file.with_suffix('.tmp')
                
                async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                    json_data = json.dumps(collection_data, ensure_ascii=False, indent=2)
                    await f.write(json_data)
                
                # Атомарное переименование
                temp_file.rename(collection_file)
                
                logger.log_info(f"Saved collection {collection_name}: {len(collection_data['gifts'])} gifts")
                return True
                
            except Exception as e:
                logger.log_error(f"Failed to save collection {collection_name}: {e}")
                return False
    
    async def add_gifts_to_collection(self, collection_name: str, gifts: List[Dict[str, Any]]) -> int:
        """
        Добавляет подарки в коллекцию
        
        Args:
            collection_name: Название коллекции
            gifts: Список подарков для добавления
            
        Returns:
            Количество успешно добавленных подарков
        """
        if not gifts:
            return 0
        
        collection_data = await self.load_collection(collection_name)
        
        # Создаем индекс существующих подарков для быстрого поиска
        existing_gift_ids = {gift.get('gift_id') for gift in collection_data['gifts']}
        
        added_count = 0
        updated_count = 0
        
        for gift in gifts:
            gift_id = gift.get('gift_id')
            if not gift_id:
                continue
            
            if gift_id in existing_gift_ids:
                # Обновляем существующий подарок
                for i, existing_gift in enumerate(collection_data['gifts']):
                    if existing_gift.get('gift_id') == gift_id:
                        # Сохраняем историю изменений
                        if existing_gift != gift:
                            gift['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                            gift['previous_status'] = existing_gift.get('status')
                            collection_data['gifts'][i] = gift
                            updated_count += 1
                        break
            else:
                # Добавляем новый подарок
                collection_data['gifts'].append(gift)
                existing_gift_ids.add(gift_id)
                added_count += 1
        
        # Обновляем метаданные коллекции
        collection_data['total_gifts'] = len(collection_data['gifts'])
        collection_data['processed_gifts'] = len([g for g in collection_data['gifts'] if g.get('status') == 'active'])
        
        self.collections_cache[collection_name] = collection_data
        
        if added_count > 0 or updated_count > 0:
            logger.log_info(f"Collection {collection_name}: added {added_count}, updated {updated_count} gifts")
        
        return added_count + updated_count
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Возвращает статистику коллекции"""
        collection_data = await self.load_collection(collection_name)
        
        gifts = collection_data.get('gifts', [])
        total_gifts = len(gifts)
        
        if total_gifts == 0:
            return {
                'collection_name': collection_name,
                'total_gifts': 0,
                'processed_gifts': 0,
                'status_breakdown': {},
                'completion_rate': 0.0
            }
        
        # Подсчитываем статусы
        status_counts = {}
        for gift in gifts:
            status = gift.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        active_gifts = status_counts.get('active', 0)
        completion_rate = (active_gifts / total_gifts) * 100 if total_gifts > 0 else 0
        
        return {
            'collection_name': collection_name,
            'total_gifts': total_gifts,
            'processed_gifts': active_gifts,
            'status_breakdown': status_counts,
            'completion_rate': completion_rate,
            'last_updated': collection_data.get('last_updated'),
            'created_at': collection_data.get('created_at')
        }
    
    async def get_all_collections_stats(self) -> Dict[str, Any]:
        """Возвращает общую статистику всех коллекций"""
        total_stats = {
            'total_collections': 0,
            'total_gifts': 0,
            'total_processed': 0,
            'collections': {},
            'status_summary': {},
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Получаем список всех JSON файлов коллекций
        collection_files = list(config.COLLECTIONS_DIR.glob("*.json"))
        
        for collection_file in collection_files:
            if collection_file.name.endswith('.backup'):
                continue
                
            collection_name = collection_file.stem
            try:
                collection_stats = await self.get_collection_stats(collection_name)
                
                total_stats['collections'][collection_name] = collection_stats
                total_stats['total_gifts'] += collection_stats['total_gifts']
                total_stats['total_processed'] += collection_stats['processed_gifts']
                
                # Суммируем статусы
                for status, count in collection_stats['status_breakdown'].items():
                    total_stats['status_summary'][status] = total_stats['status_summary'].get(status, 0) + count
                
            except Exception as e:
                logger.log_error(f"Failed to get stats for {collection_name}: {e}")
        
        total_stats['total_collections'] = len(total_stats['collections'])
        
        if total_stats['total_gifts'] > 0:
            total_stats['overall_completion_rate'] = (total_stats['total_processed'] / total_stats['total_gifts']) * 100
        else:
            total_stats['overall_completion_rate'] = 0.0
        
        return total_stats
    
    async def save_all_collections(self) -> Dict[str, bool]:
        """Сохраняет все коллекции из кэша"""
        results = {}
        
        for collection_name in self.collections_cache.keys():
            results[collection_name] = await self.save_collection(collection_name, force_write=True)
        
        return results
    
    async def export_collection_urls(self, collection_name: str, status_filter: str = None) -> List[str]:
        """
        Экспортирует URL'ы коллекции с опциональной фильтрацией по статусу
        
        Args:
            collection_name: Название коллекции
            status_filter: Фильтр по статусу ('active', 'deleted', etc.)
            
        Returns:
            Список URL'ов
        """
        collection_data = await self.load_collection(collection_name)
        urls = []
        
        for gift in collection_data.get('gifts', []):
            if status_filter is None or gift.get('status') == status_filter:
                url = gift.get('url')
                if url:
                    urls.append(url)
        
        return urls
    
    async def cleanup_old_backups(self, keep_count: int = 5):
        """Очистка старых backup файлов"""
        backup_files = list(config.COLLECTIONS_DIR.glob("*.backup"))
        
        if len(backup_files) > keep_count:
            # Сортируем по времени модификации
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            
            # Удаляем старые файлы
            for backup_file in backup_files[:-keep_count]:
                try:
                    backup_file.unlink()
                    logger.log_info(f"Removed old backup: {backup_file.name}")
                except Exception as e:
                    logger.log_error(f"Failed to remove backup {backup_file.name}: {e}")