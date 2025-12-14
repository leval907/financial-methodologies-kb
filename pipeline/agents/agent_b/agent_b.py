"""
Agent B: Outline Builder
Извлекает stages, tools, indicators, rules из books с использованием GigaChat + Qwen3-Max
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# GigaChat SDK
try:
    from gigachat import GigaChat
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    print("⚠️ GigaChat SDK не установлен. Используйте: pip install gigachat")

# Requesty AI для fallback
from requesty_ai import RequestyClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutlineBuilder:
    """
    Agent B: Строит outline.yaml из blocks.jsonl
    
    Стратегия моделей:
    🥇 PRIMARY: GigaChat (бесплатно, быстро 1.06s, правильно определяет diagnostic)
    🥈 FALLBACK: Qwen3-Max через Requesty AI (правильно, русские ключи)
    """
    
    def __init__(
        self,
        gigachat_credentials: Optional[str] = None,
        requesty_api_key: Optional[str] = None,
        use_gigachat: bool = True
    ):
        """
        Args:
            gigachat_credentials: API ключ GigaChat (если None - из .env)
            requesty_api_key: API ключ Requesty AI (если None - из .env)
            use_gigachat: Использовать GigaChat как primary (True) или только Qwen3-Max (False)
        """
        self.use_gigachat = use_gigachat and GIGACHAT_AVAILABLE
        
        # Инициализация GigaChat
        if self.use_gigachat:
            try:
                self.gigachat = GigaChat(
                    credentials=gigachat_credentials,
                    scope="GIGACHAT_API_PERS",
                    verify_ssl_certs=False
                )
                logger.info("✅ GigaChat инициализирован (PRIMARY)")
            except Exception as e:
                logger.warning(f"⚠️ GigaChat недоступен: {e}")
                self.gigachat = None
                self.use_gigachat = False
        else:
            self.gigachat = None
        
        # Инициализация Requesty AI (fallback)
        self.requesty = RequestyClient(api_key=requesty_api_key)
        logger.info("✅ Requesty AI инициализирован (FALLBACK)")
    
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> str:
        """
        Универсальный метод для запроса к LLM с автоматическим fallback
        
        Args:
            prompt: Пользовательский промт
            system_prompt: Системный промт (опционально)
            temperature: Температура генерации (0-1)
        
        Returns:
            Текстовый ответ модели
        """
        # Попытка 1: GigaChat (PRIMARY)
        if self.use_gigachat and self.gigachat:
            try:
                logger.info("🇷🇺 Запрос к GigaChat...")
                
                # GigaChat принимает один текстовый промт
                full_prompt = prompt
                if system_prompt:
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                
                response = self.gigachat.chat(full_prompt)
                result = response.choices[0].message.content
                
                logger.info(f"✅ GigaChat ответил ({len(result)} символов)")
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ GigaChat error: {e}")
                logger.info("↪️ Переключаюсь на Qwen3-Max...")
        
        # Попытка 2: Qwen3-Max через Requesty AI (FALLBACK)
        try:
            logger.info("🇨🇳 Запрос к Qwen3-Max...")
            
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            response = self.requesty.chat(
                messages=messages,
                model='alibaba/qwen3-max',
                temperature=temperature
            )
            
            logger.info(f"✅ Qwen3-Max ответил ({len(response)} символов)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Все модели недоступны: {e}")
            raise RuntimeError("Не удалось получить ответ ни от одной модели")
    
    
    def extract_chapters_from_blocks(self, blocks_jsonl_path: Path) -> List[Dict[str, Any]]:
        """
        Извлекает главы из blocks.jsonl
        
        Если есть heading (level ≤ 2) - группирует по ним
        Если нет heading - разбивает по CHUNK_SIZE блоков
        
        Args:
            blocks_jsonl_path: Путь к blocks.jsonl
        
        Returns:
            List[Dict] с главами: [{title, blocks, pages}, ...]
        """
        CHUNK_SIZE = 50  # Блоков на "главу" если нет headings
        
        chapters = []
        current_chapter = None
        blocks_buffer = []
        has_headings = False
        
        with open(blocks_jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                block = json.loads(line)
                
                # Определяем начало новой главы (heading level ≤ 2)
                if block['type'] == 'heading' and block.get('meta', {}).get('level', 3) <= 2:
                    has_headings = True
                    
                    # Сохраняем предыдущую главу
                    if current_chapter:
                        chapters.append(current_chapter)
                    
                    # Начинаем новую главу
                    current_chapter = {
                        'title': block['text'],
                        'blocks': [block],
                        'pages': [block.get('source', {}).get('page', 1)]
                    }
                
                # Добавляем блок к текущей главе
                elif current_chapter:
                    current_chapter['blocks'].append(block)
                    page = block.get('source', {}).get('page')
                    if page and page not in current_chapter['pages']:
                        current_chapter['pages'].append(page)
                
                # Если нет headings - собираем в буфер
                else:
                    blocks_buffer.append(block)
        
        # Добавляем последнюю главу (если были headings)
        if current_chapter:
            chapters.append(current_chapter)
        
        # Если headings не найдены - делим по CHUNK_SIZE
        if not has_headings and blocks_buffer:
            logger.warning(f"⚠️ Заголовки не найдены, делю на chunks по {CHUNK_SIZE} блоков")
            
            for i in range(0, len(blocks_buffer), CHUNK_SIZE):
                chunk = blocks_buffer[i:i+CHUNK_SIZE]
                pages = list(set([b.get('source', {}).get('page', 1) for b in chunk]))
                
                chapters.append({
                    'title': f"Chunk {i//CHUNK_SIZE + 1} (блоки {i+1}-{i+len(chunk)})",
                    'blocks': chunk,
                    'pages': sorted(pages)
                })
        
        logger.info(f"📚 Извлечено глав/chunks: {len(chapters)}")
        return chapters
    
    
    def analyze_chapter(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует одну главу и извлекает stages, tools, indicators, rules
        
        Args:
            chapter: Словарь с данными главы {title, blocks, pages}
        
        Returns:
            Dict с извлеченными данными
        """
        # Собираем текст главы
        chapter_text = '\n\n'.join([
            block['text'] 
            for block in chapter['blocks'] 
            if block['type'] in ['heading', 'paragraph', 'list']
        ])
        
        # Ограничиваем длину (чтобы не превысить context window)
        max_chars = 4000
        if len(chapter_text) > max_chars:
            chapter_text = chapter_text[:max_chars] + "\n\n[...текст обрезан...]"
        
        # System prompt
        system_prompt = """Ты эксперт-методолог по финансовому анализу и бухгалтерии.
Анализируй текст структурированно и извлекай ключевые элементы методологии."""
        
        # User prompt с примером
        user_prompt = f"""Проанализируй главу книги и извлеки:

1. **Stages (этапы методологии)**: шаги, которые нужно выполнить
   Формат: [{{"title": "название", "description": "описание", "order": 1}}]

2. **Tools (инструменты)**: таблицы, шаблоны, чек-листы
   Формат: [{{"title": "название", "type": "table|template|checklist", "description": "описание"}}]

3. **Indicators (показатели)**: метрики, формулы
   Формат: [{{"name": "название", "formula": "формула если есть", "description": "описание"}}]

4. **Rules (правила)**: условия и действия
   Формат: [{{"condition": "когда", "action": "что делать", "severity": "high|medium|low"}}]

5. **Methodology type**: определи тип методологии
   Варианты: diagnostic | planning | analysis | standard

Ответь в формате JSON:
{{
  "methodology_type": "diagnostic|planning|analysis|standard",
  "stages": [...],
  "tools": [...],
  "indicators": [...],
  "rules": [...]
}}

**Глава:** {chapter['title']}

**Текст:**
{chapter_text}
"""
        
        # Запрос к LLM
        response = self.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Парсим JSON из ответа
        try:
            # Извлекаем JSON из markdown блока ```json ... ```
            if '```json' in response:
                json_start = response.index('```json') + 7
                json_end = response.index('```', json_start)
                json_str = response[json_start:json_end].strip()
            elif '```' in response:
                json_start = response.index('```') + 3
                json_end = response.index('```', json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            result['source_chapter'] = chapter['title']
            result['pages'] = chapter['pages']
            
            logger.info(f"✅ Глава '{chapter['title']}' проанализирована")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Не удалось распарсить JSON: {e}")
            logger.error(f"Ответ модели: {response[:200]}...")
            return {
                'methodology_type': 'unknown',
                'stages': [],
                'tools': [],
                'indicators': [],
                'rules': [],
                'source_chapter': chapter['title'],
                'pages': chapter['pages'],
                'error': str(e)
            }
    
    
    def build_outline(self, blocks_jsonl_path: Path) -> Dict[str, Any]:
        """
        Основной метод: строит outline.yaml из blocks.jsonl
        
        Args:
            blocks_jsonl_path: Путь к blocks.jsonl файлу
        
        Returns:
            Dict с полным outline (готов для сериализации в YAML)
        """
        logger.info(f"🚀 Начинаю обработку: {blocks_jsonl_path}")
        
        # 1. Извлекаем главы
        chapters = self.extract_chapters_from_blocks(blocks_jsonl_path)
        
        # 2. Map: Анализируем каждую главу
        chapter_analyses = []
        for i, chapter in enumerate(chapters, 1):
            logger.info(f"📖 Обрабатываю главу {i}/{len(chapters)}: {chapter['title'][:50]}...")
            analysis = self.analyze_chapter(chapter)
            chapter_analyses.append(analysis)
        
        # 3. Reduce: Собираем в единый outline
        outline = self._reduce_analyses(chapter_analyses)
        
        # 4. Нормализация и валидация (Quality Gate compliance)
        outline = self._normalize_and_validate(outline)
        
        logger.info("✅ Outline построен успешно!")
        return outline
    
    
    def _reduce_analyses(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Объединяет анализы глав в единый outline (reduce фаза)
        
        Args:
            analyses: Список анализов глав
        
        Returns:
            Объединенный outline
        """
        # Определяем общий тип методологии (берем самый частый)
        methodology_types = [a.get('methodology_type', 'unknown') for a in analyses]
        methodology_type = max(set(methodology_types), key=methodology_types.count)
        
        # Собираем все элементы
        all_stages = []
        all_tools = []
        all_indicators = []
        all_rules = []
        
        for analysis in analyses:
            all_stages.extend(analysis.get('stages', []))
            all_tools.extend(analysis.get('tools', []))
            all_indicators.extend(analysis.get('indicators', []))
            all_rules.extend(analysis.get('rules', []))
        
        # Удаляем дубликаты (по title/name)
        unique_stages = self._deduplicate_by_key(all_stages, 'title')
        unique_tools = self._deduplicate_by_key(all_tools, 'title')
        unique_indicators = self._deduplicate_by_key(all_indicators, 'name')
        unique_rules = self._deduplicate_by_key(all_rules, 'condition')
        
        outline = {
            'metadata': {
                'agent': 'Agent B v1.0 (GigaChat + Qwen3-Max)',
                'model_used': 'gigachat' if self.use_gigachat else 'qwen3-max',
                'chapters_processed': len(analyses)
            },
            'classification': {
                'methodology_type': methodology_type
            },
            'structure': {
                'stages': unique_stages,
                'tools': unique_tools,
                'indicators': unique_indicators,
                'rules': unique_rules
            }
        }
        
        logger.info(f"📊 Итого: {len(unique_stages)} stages, {len(unique_tools)} tools, "
                   f"{len(unique_indicators)} indicators, {len(unique_rules)} rules")
        
        return outline
    
    
    def _deduplicate_by_key(self, items: List[Dict], key: str) -> List[Dict]:
        """Удаляет дубликаты по ключу с нормализацией"""
        import re
        seen = set()
        unique = []
        for item in items:
            value = (item.get(key, '') or '').strip().lower()
            value = re.sub(r'\s+', ' ', value)  # normalize whitespace
            
            if value and value not in seen:
                seen.add(value)
                unique.append(item)
        return unique
    
    
    def _normalize_and_validate(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Постпроцессинг outline: нормализация + валидация под B_QUALITY_GATE
        
        Исправления:
        - Фильтрация stages с placeholder titles или пустыми descriptions
        - Перенумерация stage.order (1..N)
        - Фильтрация + дедупликация indicators с пустыми descriptions
        - Нормализация formula ('' → None)
        - Маппинг severity (high/medium → critical/warning/info/low)
        """
        import re
        structure = outline.get('structure', {})
        
        # 1. Фильтрация stages (удаляем placeholder'ы и пустые descriptions)
        stages = structure.get('stages', [])
        valid_stages = []
        for stage in stages:
            title = (stage.get('title') or '').strip()
            desc = (stage.get('description') or '').strip()
            
            # Пропускаем placeholder'ы
            if title in ['Шаг 1', 'Шаг 2', 'Шаг 3', 'Шаг 4', 'Этап 1', 'Этап 2']:
                logger.warning(f"⚠️ Пропущен placeholder stage: {title}")
                continue
            
            # Пропускаем пустые descriptions
            if len(desc) < 15:
                logger.warning(f"⚠️ Пропущен stage с коротким description: {title}")
                continue
            
            valid_stages.append(stage)
        
        # 2. Перенумерация stages (1..N)
        for i, stage in enumerate(valid_stages, 1):
            stage['order'] = i
        
        # 3. Фильтрация indicators (удаляем пустые descriptions) + дедупликация
        indicators = structure.get('indicators', [])
        valid_indicators = []
        seen_names = set()
        
        for ind in indicators:
            desc = (ind.get('description') or '').strip()
            
            if len(desc) < 10:
                logger.warning(f"⚠️ Пропущен indicator с пустым description: {ind.get('name')}")
                continue
            
            # Дедупликация по normalized name
            name = (ind.get('name') or '').strip().lower()
            name = re.sub(r'\s+', ' ', name)
            
            if name in seen_names:
                logger.warning(f"⚠️ Пропущен дубликат indicator: {ind.get('name')}")
                continue
            
            seen_names.add(name)
            
            # Нормализация formula: '' → None
            if ind.get('formula') == '':
                ind['formula'] = None
            
            valid_indicators.append(ind)
        
        # 4. Нормализация severity в rules
        SEVERITY_MAP = {
            'high': 'critical',
            'medium': 'warning',
            'low': 'info'
        }
        
        rules = structure.get('rules', [])
        for rule in rules:
            sev = rule.get('severity', 'info')
            rule['severity'] = SEVERITY_MAP.get(sev, sev)
        
        # 5. Обновляем структуру
        outline['structure'] = {
            'stages': valid_stages,
            'tools': structure.get('tools', []),
            'indicators': valid_indicators,
            'rules': rules
        }
        
        logger.info(f"✅ Нормализация: {len(valid_stages)} stages, {len(valid_indicators)} indicators")
        
        return outline
