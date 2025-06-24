#!/usr/bin/env python3
"""
Демонстрационный скрипт парсера с ограниченным количеством URL
"""

import asyncio
import sys
from pathlib import Path
import ujson as json

# Добавляем путь к модулям парсера
sys.path.insert(0, str(Path(__file__).parent))

from collection_manager import CollectionManager
from config import config
from logger import logger

async def demo_parsing():
    """Демонстрация парсинга на ограниченном наборе URL"""
    
    logger.log_info("🎭 Starting demonstration parsing...")
    
    # Создаем временный файл с ограниченным количеством URL
    demo_collection = "lightsword_demo"
    demo_file = config.MATERIALS_DIR / f"{demo_collection}.txt"
    
    # Берем первые 20 URL из lightsword
    original_file = config.MATERIALS_DIR / "lightsword.txt"
    demo_urls = []
    
    with open(original_file, 'r') as f:
        for i, line in enumerate(f):
            if i >= 20:  # Ограничиваем 20 URL для демо
                break
            demo_urls.append(line.strip())
    
    # Создаем демо файл
    with open(demo_file, 'w') as f:
        for url in demo_urls:
            f.write(f"{url}\n")
    
    logger.log_info(f"📝 Created demo collection with {len(demo_urls)} URLs")
    
    # Инициализируем менеджер коллекций
    manager = CollectionManager()
    await manager.initialize()
    
    try:
        # Обрабатываем демо коллекцию
        stats = await manager.process_collection(demo_collection, resume_mode=False)
        
        # Показываем результаты
        logger.log_info("🎉 Demo parsing completed!")
        logger.log_info(f"📊 Results:")
        logger.log_info(f"   Total URLs: {stats['total_urls']}")
        logger.log_info(f"   Processed: {stats['processed_urls']}")
        logger.log_info(f"   Successful: {stats['successful_parses']}")
        logger.log_info(f"   Failed: {stats['failed_parses']}")
        logger.log_info(f"   Success rate: {stats['success_rate']:.1f}%")
        logger.log_info(f"   Speed: {stats['urls_per_second']:.1f} URLs/sec")
        
        # Показываем примеры данных
        collection_data = await manager.data_manager.load_collection(demo_collection)
        gifts = collection_data.get('gifts', [])
        
        if gifts:
            logger.log_info("📋 Sample parsed gifts:")
            for gift in gifts[:3]:  # Показываем первые 3 подарка
                logger.log_info(f"   🎁 {gift['gift_id']}: {gift['title']}")
                logger.log_info(f"      Model: {gift['model']}, Backdrop: {gift['backdrop']}")
                logger.log_info(f"      Symbol: {gift['symbol']}, Quantity: {gift['quantity']}")
        
        # Сохраняем демо данные
        demo_output = config.OUTPUT_DIR / "demo_results.json"
        with open(demo_output, 'w', encoding='utf-8') as f:
            demo_data = {
                'demo_info': {
                    'collection': demo_collection,
                    'urls_tested': len(demo_urls),
                    'timestamp': stats.get('timestamp', ''),
                    'stats': stats
                },
                'sample_gifts': gifts[:5]  # Первые 5 подарков как примеры
            }
            f.write(json.dumps(demo_data, ensure_ascii=False, indent=2))
        
        logger.log_info(f"💾 Demo results saved to: {demo_output}")
        
        return True
        
    except Exception as e:
        logger.log_error(f"Demo failed: {e}")
        return False
        
    finally:
        await manager.cleanup()
        # Удаляем временный файл
        if demo_file.exists():
            demo_file.unlink()

if __name__ == "__main__":
    try:
        success = asyncio.run(demo_parsing())
        if success:
            print("\n🎉 Demonstration completed successfully!")
            print("📊 Check /app/output/demo_results.json for detailed results")
            print("🚀 Parser is ready for full-scale operation!")
        else:
            print("\n❌ Demonstration failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        sys.exit(1)