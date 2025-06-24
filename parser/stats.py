"""
Модуль статистики и отчетности для парсера
"""

import ujson as json
import aiofiles
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict

from config import config
from logger import logger

@dataclass
class ParsingSession:
    """Данные о сессии парсинга"""
    session_id: str
    start_time: str
    end_time: Optional[str]
    duration: float
    total_collections: int
    completed_collections: int
    total_urls: int
    processed_urls: int
    successful_parses: int
    failed_parses: int
    success_rate: float
    urls_per_second: float
    config_snapshot: Dict[str, Any]

class StatsManager:
    """Менеджер статистики и отчетности"""
    
    def __init__(self):
        self.current_session: Optional[ParsingSession] = None
        self.stats_file = config.STATS_DIR / 'parsing_stats.json'
        self.sessions_file = config.STATS_DIR / 'parsing_sessions.json'
        self.summary_file = config.STATS_DIR / 'summary.json'
        
    async def start_session(self, session_id: str = None) -> str:
        """
        Начинает новую сессию парсинга
        
        Args:
            session_id: ID сессии (автоматический если не указан)
            
        Returns:
            ID созданной сессии
        """
        if session_id is None:
            session_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        self.current_session = ParsingSession(
            session_id=session_id,
            start_time=datetime.utcnow().isoformat() + 'Z',
            end_time=None,
            duration=0.0,
            total_collections=0,
            completed_collections=0,
            total_urls=0,
            processed_urls=0,
            successful_parses=0,
            failed_parses=0,
            success_rate=0.0,
            urls_per_second=0.0,
            config_snapshot=config.to_dict()
        )
        
        logger.log_info(f"Started parsing session: {session_id}")
        return session_id
    
    async def end_session(self, final_stats: Dict[str, Any]) -> bool:
        """
        Завершает текущую сессию парсинга
        
        Args:
            final_stats: Итоговая статистика парсинга
            
        Returns:
            True если сессия успешно завершена
        """
        if not self.current_session:
            logger.log_warning("No active session to end")
            return False
        
        try:
            # Обновляем данные сессии
            self.current_session.end_time = datetime.utcnow().isoformat() + 'Z'
            self.current_session.duration = final_stats.get('total_duration', 0)
            self.current_session.total_collections = final_stats.get('total_collections', 0)
            self.current_session.completed_collections = final_stats.get('completed_collections', 0)
            self.current_session.total_urls = final_stats.get('total_urls', 0)
            self.current_session.processed_urls = final_stats.get('processed_urls', 0)
            self.current_session.successful_parses = final_stats.get('successful_parses', 0)
            self.current_session.failed_parses = final_stats.get('failed_parses', 0)
            
            if self.current_session.processed_urls > 0:
                self.current_session.success_rate = (
                    self.current_session.successful_parses / self.current_session.processed_urls
                ) * 100
            
            if self.current_session.duration > 0:
                self.current_session.urls_per_second = (
                    self.current_session.processed_urls / self.current_session.duration
                )
            
            # Сохраняем сессию
            await self._save_session()
            
            logger.log_info(f"Ended parsing session: {self.current_session.session_id}")
            self.current_session = None
            return True
            
        except Exception as e:
            logger.log_error(f"Failed to end session: {e}")
            return False
    
    async def _save_session(self):
        """Сохраняет текущую сессию в файл"""
        if not self.current_session:
            return
        
        # Загружаем существующие сессии
        sessions = await self._load_sessions()
        
        # Добавляем текущую сессию
        sessions.append(asdict(self.current_session))
        
        # Сохраняем обновленный список
        async with aiofiles.open(self.sessions_file, 'w', encoding='utf-8') as f:
            json_data = json.dumps(sessions, ensure_ascii=False, indent=2)
            await f.write(json_data)
    
    async def _load_sessions(self) -> List[Dict[str, Any]]:
        """Загружает список сессий из файла"""
        if not self.sessions_file.exists():
            return []
        
        try:
            async with aiofiles.open(self.sessions_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.log_warning(f"Failed to load sessions: {e}")
            return []
    
    async def generate_collection_stats(self, data_manager) -> Dict[str, Any]:
        """
        Генерирует статистику по всем коллекциям
        
        Args:
            data_manager: Экземпляр DataManager
            
        Returns:
            Словарь со статистикой коллекций
        """
        logger.log_info("Generating collection statistics...")
        
        all_stats = await data_manager.get_all_collections_stats()
        
        # Дополнительная аналитика
        collections_stats = all_stats['collections']
        
        # Топ коллекций по размеру
        top_by_size = sorted(
            collections_stats.items(),
            key=lambda x: x[1]['total_gifts'],
            reverse=True
        )[:10]
        
        # Топ коллекций по проценту завершения
        top_by_completion = sorted(
            collections_stats.items(),
            key=lambda x: x[1]['completion_rate'],
            reverse=True
        )[:10]
        
        # Статистика по статусам
        status_analysis = {}
        for collection_name, collection_stats in collections_stats.items():
            for status, count in collection_stats['status_breakdown'].items():
                if status not in status_analysis:
                    status_analysis[status] = {'total': 0, 'collections': 0}
                status_analysis[status]['total'] += count
                status_analysis[status]['collections'] += 1
        
        enhanced_stats = {
            **all_stats,
            'analysis': {
                'top_collections_by_size': [
                    {'name': name, 'total_gifts': stats['total_gifts']}
                    for name, stats in top_by_size
                ],
                'top_collections_by_completion': [
                    {'name': name, 'completion_rate': stats['completion_rate']}
                    for name, stats in top_by_completion
                ],
                'status_analysis': status_analysis,
                'average_collection_size': all_stats['total_gifts'] / max(all_stats['total_collections'], 1),
                'average_completion_rate': sum(
                    stats['completion_rate'] for stats in collections_stats.values()
                ) / max(len(collections_stats), 1)
            }
        }
        
        # Сохраняем статистику
        stats_file = config.STATS_DIR / 'collections_stats.json'
        async with aiofiles.open(stats_file, 'w', encoding='utf-8') as f:
            json_data = json.dumps(enhanced_stats, ensure_ascii=False, indent=2)
            await f.write(json_data)
        
        logger.log_info("Collection statistics generated and saved")
        return enhanced_stats
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Генерирует отчет о производительности"""
        sessions = await self._load_sessions()
        
        if not sessions:
            return {'error': 'No sessions found'}
        
        # Анализ производительности
        total_sessions = len(sessions)
        completed_sessions = [s for s in sessions if s.get('end_time')]
        
        if not completed_sessions:
            return {'error': 'No completed sessions found'}
        
        # Средние показатели
        avg_duration = sum(s['duration'] for s in completed_sessions) / len(completed_sessions)
        avg_urls_per_second = sum(s['urls_per_second'] for s in completed_sessions) / len(completed_sessions)
        avg_success_rate = sum(s['success_rate'] for s in completed_sessions) / len(completed_sessions)
        
        # Лучшие показатели
        best_speed = max(completed_sessions, key=lambda x: x['urls_per_second'])
        best_success_rate = max(completed_sessions, key=lambda x: x['success_rate'])
        
        # Тренды (последние 10 сессий)
        recent_sessions = completed_sessions[-10:]
        if len(recent_sessions) >= 2:
            speed_trend = 'improving' if recent_sessions[-1]['urls_per_second'] > recent_sessions[0]['urls_per_second'] else 'declining'
            success_trend = 'improving' if recent_sessions[-1]['success_rate'] > recent_sessions[0]['success_rate'] else 'declining'
        else:
            speed_trend = 'insufficient_data'
            success_trend = 'insufficient_data'
        
        performance_report = {
            'summary': {
                'total_sessions': total_sessions,
                'completed_sessions': len(completed_sessions),
                'average_duration_hours': avg_duration / 3600,
                'average_urls_per_second': avg_urls_per_second,
                'average_success_rate': avg_success_rate
            },
            'best_performance': {
                'fastest_session': {
                    'session_id': best_speed['session_id'],
                    'urls_per_second': best_speed['urls_per_second'],
                    'date': best_speed['start_time']
                },
                'most_accurate_session': {
                    'session_id': best_success_rate['session_id'],
                    'success_rate': best_success_rate['success_rate'],
                    'date': best_success_rate['start_time']
                }
            },
            'trends': {
                'speed_trend': speed_trend,
                'success_trend': success_trend
            },
            'sessions_history': completed_sessions,
            'generated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Сохраняем отчет
        report_file = config.STATS_DIR / 'performance_report.json'
        async with aiofiles.open(report_file, 'w', encoding='utf-8') as f:
            json_data = json.dumps(performance_report, ensure_ascii=False, indent=2)
            await f.write(json_data)
        
        return performance_report
    
    async def generate_summary_report(self, data_manager, cache_manager) -> Dict[str, Any]:
        """
        Генерирует итоговый сводный отчет
        
        Args:
            data_manager: Экземпляр DataManager
            cache_manager: Экземпляр CacheManager
            
        Returns:
            Сводный отчет
        """
        logger.log_info("Generating summary report...")
        
        # Собираем данные из разных источников
        collection_stats = await self.generate_collection_stats(data_manager)
        performance_report = await self.generate_performance_report()
        cache_report = await cache_manager.generate_cache_report()
        
        summary = {
            'report_info': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'report_version': '1.0',
                'parser_version': '1.0.0'
            },
            'overview': {
                'total_collections': collection_stats.get('total_collections', 0),
                'total_gifts': collection_stats.get('total_gifts', 0),
                'total_processed': collection_stats.get('total_processed', 0),
                'overall_completion_rate': collection_stats.get('overall_completion_rate', 0),
                'total_sessions': len(await self._load_sessions())
            },
            'collection_summary': {
                'status_breakdown': collection_stats.get('status_summary', {}),
                'top_collections': collection_stats.get('analysis', {}).get('top_collections_by_size', [])[:5],
                'average_collection_size': collection_stats.get('analysis', {}).get('average_collection_size', 0)
            },
            'performance_summary': {
                'average_speed': performance_report.get('summary', {}).get('average_urls_per_second', 0),
                'average_success_rate': performance_report.get('summary', {}).get('average_success_rate', 0),
                'best_speed_achieved': performance_report.get('best_performance', {}).get('fastest_session', {}).get('urls_per_second', 0)
            },
            'cache_summary': cache_report,
            'recommendations': self._generate_recommendations(collection_stats, performance_report, cache_report)
        }
        
        # Сохраняем сводный отчет
        async with aiofiles.open(self.summary_file, 'w', encoding='utf-8') as f:
            json_data = json.dumps(summary, ensure_ascii=False, indent=2)
            await f.write(json_data)
        
        logger.log_info("Summary report generated and saved")
        return summary
    
    def _generate_recommendations(self, collection_stats: Dict, 
                                performance_report: Dict, 
                                cache_report: Dict) -> List[str]:
        """Генерирует рекомендации по оптимизации"""
        recommendations = []
        
        # Анализ производительности
        avg_speed = performance_report.get('summary', {}).get('average_urls_per_second', 0)
        if avg_speed < 5:
            recommendations.append("Consider increasing MAX_CONCURRENT_REQUESTS for better performance")
        
        avg_success_rate = performance_report.get('summary', {}).get('average_success_rate', 0)
        if avg_success_rate < 85:
            recommendations.append("High error rate detected. Consider adjusting retry settings or request delays")
        
        # Анализ коллекций
        completion_rate = collection_stats.get('overall_completion_rate', 0)
        if completion_rate < 90:
            recommendations.append("Some collections have low completion rates. Consider re-running failed URLs")
        
        # Анализ кэша
        cache_size = cache_report.get('total_cached_urls', 0)
        if cache_size > 1000000:  # 1M URLs
            recommendations.append("Cache is large. Consider cleanup of old entries")
        
        # Анализ ошибок
        status_breakdown = collection_stats.get('status_summary', {})
        error_rate = (status_breakdown.get('error', 0) + status_breakdown.get('deleted', 0)) / max(sum(status_breakdown.values()), 1)
        if error_rate > 0.15:  # 15% errors
            recommendations.append("High error rate detected. Review failed URLs and adjust error handling")
        
        if not recommendations:
            recommendations.append("Parser is performing well. No specific recommendations at this time")
        
        return recommendations
    
    async def export_stats_csv(self, output_file: Path = None) -> Path:
        """Экспортирует статистику в CSV формат"""
        if output_file is None:
            output_file = config.STATS_DIR / f'stats_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        sessions = await self._load_sessions()
        
        if not sessions:
            logger.log_warning("No sessions to export")
            return output_file
        
        # Создаем CSV контент
        csv_lines = []
        csv_lines.append("session_id,start_time,end_time,duration,total_collections,completed_collections,"
                        "total_urls,processed_urls,successful_parses,failed_parses,success_rate,urls_per_second")
        
        for session in sessions:
            line = (
                f"{session.get('session_id', '')},"
                f"{session.get('start_time', '')},"
                f"{session.get('end_time', '')},"
                f"{session.get('duration', 0)},"
                f"{session.get('total_collections', 0)},"
                f"{session.get('completed_collections', 0)},"
                f"{session.get('total_urls', 0)},"
                f"{session.get('processed_urls', 0)},"
                f"{session.get('successful_parses', 0)},"
                f"{session.get('failed_parses', 0)},"
                f"{session.get('success_rate', 0)},"
                f"{session.get('urls_per_second', 0)}"
            )
            csv_lines.append(line)
        
        # Сохраняем CSV файл
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write('\n'.join(csv_lines))
        
        logger.log_info(f"Stats exported to CSV: {output_file}")
        return output_file