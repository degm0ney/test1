#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсера на небольшой выборке
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям парсера
sys.path.insert(0, str(Path(__file__).parent))

from async_downloader import AsyncDownloader
from gift_parser import GiftParser
from logger import logger

async def test_parsing():
    """Тестирует парсинг на нескольких URL"""
    logger.log_info("🧪 Starting parsing test...")
    
    # Тестовые URL
    test_urls = [
        "https://t.me/nft/lightsword-1",
        "https://t.me/nft/lightsword-2",
        "https://t.me/nft/lightsword-3",
        "https://t.me/nft/astralshard-1",
        "https://t.me/nft/restlessjar-1"
    ]
    
    parser = GiftParser()
    
    async with AsyncDownloader() as downloader:
        # Загружаем страницы
        logger.log_info(f"📥 Downloading {len(test_urls)} test URLs...")
        results = await downloader.download_batch(test_urls)
        
        # Парсим результаты
        parsed_gifts = []
        for url, html_content, error in results:
            if html_content:
                gift_data = parser.parse_gift_data(html_content, url)
                if gift_data and parser.validate_gift_data(gift_data):
                    parsed_gifts.append(gift_data)
                    logger.log_info(f"✅ Parsed: {gift_data['gift_id']} - {gift_data['title']}")
                    logger.log_info(f"   Model: {gift_data['model']}, Backdrop: {gift_data['backdrop']}")
                else:
                    logger.log_info(f"❌ Failed to parse: {url}")
            else:
                logger.log_info(f"❌ Failed to download: {url} - {error}")
        
        # Статистика загрузчика
        stats = downloader.get_stats()
        logger.log_info(f"📊 Download stats: {stats}")
        
        # Итоги
        logger.log_info(f"🎯 Test Results:")
        logger.log_info(f"   Total URLs: {len(test_urls)}")
        logger.log_info(f"   Successfully parsed: {len(parsed_gifts)}")
        logger.log_info(f"   Success rate: {(len(parsed_gifts)/len(test_urls)*100):.1f}%")
        
        if parsed_gifts:
            logger.log_info(f"📝 Sample parsed gift:")
            sample = parsed_gifts[0]
            for key, value in sample.items():
                if key not in ['other_data', 'parsed_at']:
                    logger.log_info(f"   {key}: {value}")
        
        return len(parsed_gifts) > 0

if __name__ == "__main__":
    try:
        success = asyncio.run(test_parsing())
        if success:
            print("\n🎉 Parsing test completed successfully!")
            print("The parser is ready for full operation.")
        else:
            print("\n❌ Parsing test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)