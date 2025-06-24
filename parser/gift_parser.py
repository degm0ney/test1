"""
Парсер одного подарка Telegram
"""

import re
from datetime import datetime
from typing import Dict, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import asyncio

class GiftParser:
    """Парсер для извлечения данных одного подарка"""
    
    def __init__(self):
        self.url_pattern = re.compile(r'https://t\.me/nft/([^/]+)-(\d+)')
        self.meta_selectors = {
            'title': ['meta[property="og:title"]', 'title'],
            'image': ['meta[property="og:image"]', 'meta[property="twitter:image"]'],
            'description': ['meta[property="og:description"]', 'meta[property="twitter:description"]']
        }
    
    def parse_gift_data(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Парсит HTML контент и извлекает данные подарка
        
        Args:
            html_content: HTML контент страницы
            url: URL страницы
            
        Returns:
            Словарь с данными подарка или None при ошибке
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Извлекаем базовую информацию из URL
            url_match = self.url_pattern.match(url)
            if not url_match:
                return None
            
            collection_name = url_match.group(1)
            gift_number = url_match.group(2)
            gift_id = f"{collection_name}-{gift_number}"
            
            # Извлекаем данные из мета-тегов
            title = self._extract_meta_content(soup, self.meta_selectors['title'])
            image_url = self._extract_meta_content(soup, self.meta_selectors['image'])
            description = self._extract_meta_content(soup, self.meta_selectors['description'])
            
            # Парсим данные из таблицы (новый метод)
            table_data = self._parse_gift_table(soup)
            
            # Парсим описание для получения атрибутов (резервный метод)
            attributes = self._parse_description(description) if description else {}
            
            # Объединяем данные из таблицы и мета-тегов
            attributes.update(table_data)
            
            # Извлекаем владельца
            owner = table_data.get('Owner') or self._extract_owner(soup)
            
            # Извлекаем количество и редкость
            quantity_info = self._extract_quantity_from_table(table_data) or self._extract_quantity_info(soup, html_content)
            
            # Проверяем статус подарка
            status = self._determine_status(soup, html_content)
            
            # Собираем все данные
            gift_data = {
                "url": url,
                "gift_id": gift_id,
                "collection": collection_name,
                "gift_number": int(gift_number),
                "title": title or f"{collection_name.title()} #{gift_number}",
                "model": self._clean_attribute(attributes.get('Model', '')),
                "backdrop": self._clean_attribute(attributes.get('Backdrop', '')),
                "symbol": self._clean_attribute(attributes.get('Symbol', '')),
                "rarity": attributes.get('Rarity', ''),
                "owner": owner,
                "quantity": quantity_info.get('quantity', ''),
                "total_supply": quantity_info.get('total_supply', ''),
                "other_data": self._extract_additional_data(attributes),
                "image_url": image_url or '',
                "status": status,
                "parsed_at": datetime.utcnow().isoformat() + 'Z'
            }
            
            return gift_data
            
        except Exception as e:
            return None
    
    def _extract_meta_content(self, soup: BeautifulSoup, selectors: list) -> Optional[str]:
        """Извлекает контент из мета-тегов по списку селекторов"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    return element.get('content', '').strip()
                else:
                    return element.get_text().strip()
        return None
    
    def _parse_description(self, description: str) -> Dict[str, str]:
        """Парсит описание для извлечения атрибутов подарка"""
        attributes = {}
        if not description:
            return attributes
        
        # Разбиваем описание на строки
        lines = description.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                attributes[key.strip()] = value.strip()
        
        return attributes
    
    def _parse_gift_table(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Парсит данные из таблицы подарка"""
        table_data = {}
        
        # Ищем таблицу с данными подарка
        table = soup.select_one('table.tgme_gift_table')
        if not table:
            return table_data
        
        # Извлекаем данные из строк таблицы
        rows = table.select('tr')
        for row in rows:
            th = row.select_one('th')
            td = row.select_one('td')
            
            if th and td:
                key = th.get_text().strip()
                value = td.get_text().strip()
                
                # Очищаем значение от HTML разметки
                value = self._clean_table_value(value)
                
                table_data[key] = value
        
        return table_data
    
    def _clean_table_value(self, value: str) -> str:
        """Очищает значение из таблицы от лишних символов"""
        if not value:
            return ''
        
        # Убираем проценты редкости в скобках
        import re
        value = re.sub(r'\s*\d+(?:\.\d+)?%\s*', '', value)
        value = re.sub(r'\s*<mark>.*?</mark>\s*', '', value)
        
        return value.strip()
    
    def _clean_attribute(self, value: str) -> str:
        """Очищает атрибут от лишних символов"""
        if not value:
            return ''
        
        # Убираем HTML теги если они есть
        import re
        value = re.sub(r'<[^>]+>', '', value)
        
        # Убираем проценты редкости
        value = re.sub(r'\s*\d+(?:\.\d+)?%\s*', '', value)
        
        return value.strip()
    
    def _extract_quantity_from_table(self, table_data: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Извлекает информацию о количестве из данных таблицы"""
        quantity_info = {'quantity': '', 'total_supply': ''}
        
        quantity_text = table_data.get('Quantity', '')
        if not quantity_text:
            return None
        
        # Ищем паттерн "110 335/131 222 issued"
        import re
        match = re.search(r'(\d+(?:\s\d+)*)/(\d+(?:\s\d+)*)', quantity_text)
        if match:
            current = match.group(1).replace(' ', '')
            total = match.group(2).replace(' ', '')
            quantity_info['quantity'] = f"{current}/{total}"
            quantity_info['total_supply'] = total
        
        return quantity_info
    
    def _extract_quantity_info(self, soup: BeautifulSoup, html_content: str) -> Dict[str, str]:
        """Извлекает информацию о количестве и общем предложении"""
        quantity_info = {'quantity': '', 'total_supply': ''}
        
        # Ищем паттерны вида "123/456" или "123 of 456"
        quantity_patterns = [
            r'(\d+(?:,\d+)*)\s*/\s*(\d+(?:,\d+)*)',
            r'(\d+(?:,\d+)*)\s+of\s+(\d+(?:,\d+)*)',
            r'#(\d+(?:,\d+)*)\s*/\s*(\d+(?:,\d+)*)'
        ]
        
        for pattern in quantity_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                current, total = matches[0]
                quantity_info['quantity'] = f"{current}/{total}"
                quantity_info['total_supply'] = total
                break
        
        return quantity_info
    
    def _extract_owner(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает информацию о владельце подарка"""
        # Ищем различные варианты отображения владельца
        owner_selectors = [
            '.owner',
            '.gift-owner',
            '[class*="owner"]',
            'span:contains("Owner")',
            'div:contains("Owned by")'
        ]
        
        for selector in owner_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    owner_text = element.get_text().strip()
                    # Очищаем текст от префиксов
                    owner_text = re.sub(r'^(Owner|Owned by):?\s*', '', owner_text, flags=re.IGNORECASE)
                    if owner_text and len(owner_text) < 100:  # Разумное ограничение длины
                        return owner_text
            except:
                continue
        
        return None
    
    def _determine_status(self, soup: BeautifulSoup, html_content: str) -> str:
        """Определяет статус подарка"""
        # Проверяем наличие индикаторов статуса
        if 'not found' in html_content.lower() or '404' in html_content:
            return 'deleted'
        
        if 'private' in html_content.lower() or 'unavailable' in html_content.lower():
            return 'private'
        
        # Проверяем наличие основной информации
        if soup.select_one('meta[property="og:title"]'):
            return 'active'
        
        return 'unknown'
    
    def _extract_additional_data(self, attributes: Dict[str, str]) -> str:
        """Извлекает дополнительные данные о подарке"""
        additional_info = []
        
        for key, value in attributes.items():
            if key not in ['Model', 'Backdrop', 'Symbol', 'Rarity'] and value:
                additional_info.append(f"{key}: {value}")
        
        return "; ".join(additional_info)
    
    def validate_gift_data(self, gift_data: Dict[str, Any]) -> bool:
        """Валидирует данные подарка"""
        required_fields = ['url', 'gift_id', 'collection', 'status']
        
        for field in required_fields:
            if field not in gift_data or not gift_data[field]:
                return False
        
        # Проверяем валидность URL
        try:
            parsed_url = urlparse(gift_data['url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
        except:
            return False
        
        return True
    
    async def parse_multiple_gifts(self, html_contents: list, urls: list) -> list:
        """Асинхронно парсит несколько подарков"""
        tasks = []
        for html_content, url in zip(html_contents, urls):
            task = asyncio.create_task(self._parse_single_async(html_content, url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем успешные результаты
        valid_results = []
        for result in results:
            if isinstance(result, dict) and self.validate_gift_data(result):
                valid_results.append(result)
        
        return valid_results
    
    async def _parse_single_async(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """Асинхронная версия парсинга одного подарка"""
        return await asyncio.to_thread(self.parse_gift_data, html_content, url)