"""
Утилиты для парсера - скрипты для обслуживания и анализа
"""

import asyncio
import sys
from pathlib import Path
import click
import ujson as json
from datetime import datetime

# Добавляем путь к модулям парсера
sys.path.insert(0, str(Path(__file__).parent))

from data_manager import DataManager
from cache_manager import CacheManager
from config import config

@click.group()
def cli():
    """Утилиты для парсера коллекционных подарков"""
    pass

@cli.command()
@click.argument('collection_name')
@click.option('--status', default=None, help='Filter by status (active, deleted, error)')
@click.option('--output', default=None, help='Output file path')
def export_urls(collection_name, status, output):
    """Экспорт URL коллекции с фильтрацией по статусу"""
    async def run():
        data_manager = DataManager()
        urls = await data_manager.export_collection_urls(collection_name, status)
        
        if not urls:
            click.echo(f"No URLs found for collection {collection_name} with status {status}")
            return
        
        if output:
            output_file = Path(output)
        else:
            status_suffix = f"_{status}" if status else ""
            output_file = config.OUTPUT_DIR / f"{collection_name}_urls{status_suffix}.txt"
        
        with open(output_file, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        
        click.echo(f"Exported {len(urls)} URLs to {output_file}")
    
    asyncio.run(run())

@cli.command()
@click.option('--collection', default=None, help='Specific collection')
def show_stats(collection):
    """Показать статистику коллекций"""
    async def run():
        data_manager = DataManager()
        
        if collection:
            stats = await data_manager.get_collection_stats(collection)
            click.echo(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            stats = await data_manager.get_all_collections_stats()
            
            # Красивый вывод
            click.echo(f"📊 Collections Statistics")
            click.echo(f"========================")
            click.echo(f"Total Collections: {stats['total_collections']}")
            click.echo(f"Total Gifts: {stats['total_gifts']:,}")
            click.echo(f"Total Processed: {stats['total_processed']:,}")
            click.echo(f"Completion Rate: {stats['overall_completion_rate']:.2f}%")
            click.echo()
            
            click.echo("Status Breakdown:")
            for status, count in stats['status_summary'].items():
                click.echo(f"  {status}: {count:,}")
            click.echo()
            
            click.echo("Top 10 Collections by Size:")
            sorted_collections = sorted(
                stats['collections'].items(),
                key=lambda x: x[1]['total_gifts'],
                reverse=True
            )
            for name, collection_stats in sorted_collections[:10]:
                click.echo(f"  {name}: {collection_stats['total_gifts']:,} gifts "
                          f"({collection_stats['completion_rate']:.1f}% complete)")
    
    asyncio.run(run())

@cli.command()
def clean_cache():
    """Очистка старых записей кэша"""
    async def run():
        cache_manager = CacheManager()
        await cache_manager.load_cache()
        
        # Очистка записей старше 30 дней
        await cache_manager.cleanup_old_cache_entries(30)
        await cache_manager.save_cache(force=True)
        
        click.echo("✅ Cache cleaned successfully")
    
    asyncio.run(run())

@cli.command()
def rebuild_cache():
    """Перестройка кэша из существующих данных"""
    async def run():
        cache_manager = CacheManager()
        data_manager = DataManager()
        
        rebuilt_count = await cache_manager.rebuild_cache_from_collections(data_manager)
        await cache_manager.save_cache(force=True)
        
        click.echo(f"✅ Cache rebuilt: {rebuilt_count} entries restored")
    
    asyncio.run(run())

@cli.command()
@click.argument('collection_names', nargs=-1, required=True)
def merge_collections(collection_names):
    """Объединение нескольких коллекций в одну"""
    async def run():
        if len(collection_names) < 2:
            click.echo("Error: Need at least 2 collections to merge")
            return
        
        target_name = collection_names[0]
        source_names = collection_names[1:]
        
        data_manager = DataManager()
        
        # Загружаем целевую коллекцию
        target_collection = await data_manager.load_collection(target_name)
        
        merged_count = 0
        for source_name in source_names:
            source_collection = await data_manager.load_collection(source_name)
            source_gifts = source_collection.get('gifts', [])
            
            if source_gifts:
                added = await data_manager.add_gifts_to_collection(target_name, source_gifts)
                merged_count += added
                click.echo(f"Merged {added} gifts from {source_name}")
        
        await data_manager.save_collection(target_name)
        click.echo(f"✅ Successfully merged {merged_count} gifts into {target_name}")
    
    asyncio.run(run())

@cli.command()
@click.argument('collection_name')
@click.option('--backup', is_flag=True, help='Create backup before fixing')
def fix_collection(collection_name, backup):
    """Исправление и валидация данных коллекции"""
    async def run():
        data_manager = DataManager()
        collection_data = await data_manager.load_collection(collection_name)
        
        if backup:
            backup_file = config.COLLECTIONS_DIR / f"{collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                json.dump(collection_data, f, indent=2, ensure_ascii=False)
            click.echo(f"Backup created: {backup_file}")
        
        gifts = collection_data.get('gifts', [])
        original_count = len(gifts)
        
        # Удаляем дубликаты по gift_id
        seen_ids = set()
        unique_gifts = []
        duplicates_removed = 0
        
        for gift in gifts:
            gift_id = gift.get('gift_id')
            if gift_id and gift_id not in seen_ids:
                seen_ids.add(gift_id)
                unique_gifts.append(gift)
            else:
                duplicates_removed += 1
        
        # Исправляем недостающие поля
        fixed_count = 0
        for gift in unique_gifts:
            original_gift = gift.copy()
            
            # Добавляем недостающие поля
            if not gift.get('parsed_at'):
                gift['parsed_at'] = datetime.utcnow().isoformat() + 'Z'
                fixed_count += 1
            
            if not gift.get('status'):
                gift['status'] = 'active'
                fixed_count += 1
        
        # Обновляем коллекцию
        collection_data['gifts'] = unique_gifts
        collection_data['total_gifts'] = len(unique_gifts)
        collection_data['processed_gifts'] = len([g for g in unique_gifts if g.get('status') == 'active'])
        collection_data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        # Сохраняем
        data_manager.collections_cache[collection_name] = collection_data
        await data_manager.save_collection(collection_name)
        
        click.echo(f"✅ Collection {collection_name} fixed:")
        click.echo(f"  Original gifts: {original_count}")
        click.echo(f"  Duplicates removed: {duplicates_removed}")
        click.echo(f"  Fields fixed: {fixed_count}")
        click.echo(f"  Final gifts: {len(unique_gifts)}")
    
    asyncio.run(run())

@cli.command()
def check_integrity():
    """Проверка целостности всех данных"""
    async def run():
        data_manager = DataManager()
        cache_manager = CacheManager()
        await cache_manager.load_cache()
        
        # Получаем все коллекции
        collection_files = list(config.COLLECTIONS_DIR.glob("*.json"))
        
        total_issues = 0
        for collection_file in collection_files:
            if collection_file.name.endswith('.backup'):
                continue
            
            collection_name = collection_file.stem
            try:
                collection_data = await data_manager.load_collection(collection_name)
                gifts = collection_data.get('gifts', [])
                
                # Проверяем дубликаты
                gift_ids = [g.get('gift_id') for g in gifts if g.get('gift_id')]
                duplicates = len(gift_ids) - len(set(gift_ids))
                
                # Проверяем отсутствующие поля
                missing_fields = 0
                for gift in gifts:
                    required_fields = ['gift_id', 'url', 'status']
                    for field in required_fields:
                        if not gift.get(field):
                            missing_fields += 1
                            break
                
                if duplicates > 0 or missing_fields > 0:
                    click.echo(f"⚠️  {collection_name}:")
                    if duplicates > 0:
                        click.echo(f"    Duplicates: {duplicates}")
                    if missing_fields > 0:
                        click.echo(f"    Missing required fields: {missing_fields}")
                    total_issues += duplicates + missing_fields
                
            except Exception as e:
                click.echo(f"❌ Error checking {collection_name}: {e}")
                total_issues += 1
        
        if total_issues == 0:
            click.echo("✅ All collections are healthy!")
        else:
            click.echo(f"⚠️  Found {total_issues} issues across collections")
            click.echo("Run 'fix-collection <name>' to fix individual collections")
    
    asyncio.run(run())

if __name__ == '__main__':
    cli()