"""
Agent H: Semantic Linker
Создает семантические связи между entities через LLM
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from requesty_ai import RequestyClient
from arangodb.client import ArangoDBClient
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticLinker:
    """
    Agent H: Создает семантические связи stages ↔ indicators/tools/rules
    
    Стратегия:
    1. Читает stage из ArangoDB
    2. Формирует prompt с описанием stage и списком candidates
    3. LLM выбирает релевантные entities
    4. Создает edges в ArangoDB с confidence scores
    """
    
    def __init__(
        self,
        requesty_api_key: Optional[str] = None,
        model: str = 'alibaba/qwen3-max',
        batch_size: int = 50,
        dry_run: bool = False
    ):
        """
        Args:
            requesty_api_key: API ключ Requesty AI (если None - из env)
            model: Модель для LLM (по умолчанию qwen3-max)
            batch_size: Сколько candidates показывать LLM за раз
            dry_run: Если True, не создает edges, только логирует
        
        Note:
            Env переменные для ArangoDB должны быть загружены ДО создания этого класса
        """

        
        # Инициализация Requesty AI
        self.requesty = RequestyClient(api_key=requesty_api_key)
        self.model = model
        self.batch_size = batch_size
        self.dry_run = dry_run
        
        logger.info(f"✅ Requesty AI инициализирован (model: {model})")
        
        # Инициализация ArangoDB (подключаемся при первом использовании)
        # Читаем параметры из env (уже загружены в __main__.py)
        import os
        arango_host = os.getenv('ARANGO_HOST', 'localhost')
        arango_port = os.getenv('ARANGO_PORT', '8529')
        arango_user = os.getenv('ARANGO_USER', 'root')
        arango_password = os.getenv('ARANGO_PASSWORD', '')
        arango_db = os.getenv('ARANGO_DB', 'fin_kb_method')
        
        logger.info(f"📊 Параметры ArangoDB:")
        logger.info(f"  host: {arango_host}:{arango_port}")
        logger.info(f"  user: {arango_user}")
        logger.info(f"  password: {'***' if arango_password else 'NOT SET'}")
        logger.info(f"  db: {arango_db}")
        
        self.arango_client = ArangoDBClient(
            host=f"http://{arango_host}:{arango_port}",
            username=arango_user,
            password=arango_password,
            db_name=arango_db
        )
        self.db = None  # Будет подключено в link_methodology()
        
        logger.info("✅ ArangoDB клиент создан")
        
        # Статистика
        self.stats = {
            'stages_processed': 0,
            'indicators_linked': 0,
            'tools_linked': 0,
            'rules_linked': 0,
            'llm_calls': 0,
            'total_tokens': 0
        }
    
    
    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Отправка запроса к LLM через Requesty AI"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.requesty.chat(
                messages=messages,
                model=self.model,
                temperature=0.3  # Низкая температура для стабильности
            )
            
            self.stats['llm_calls'] += 1
            # Токены не возвращаются в этом API, считаем приблизительно
            self.stats['total_tokens'] += len(response) // 4  # Примерная оценка
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {e}")
            return None
    
    
    def load_all_candidates(self) -> Dict[str, List[Dict]]:
        """Загружает все indicators, tools, rules из ArangoDB"""
        logger.info("📥 Загружаем candidates из ArangoDB...")
        
        candidates = {
            'indicators': [],
            'tools': [],
            'rules': []
        }
        
        # Indicators
        for ind in self.db.collection('indicators').all():
            candidates['indicators'].append({
                'id': ind['_key'],
                'name': ind.get('name', ''),
                'description': ind.get('description', '')[:200]  # Ограничиваем длину
            })
        
        # Tools
        for tool in self.db.collection('tools').all():
            candidates['tools'].append({
                'id': tool['_key'],
                'name': tool.get('name', ''),
                'description': tool.get('description', '')[:200]
            })
        
        # Rules
        for rule in self.db.collection('rules').all():
            candidates['rules'].append({
                'id': rule['_key'],
                'title': rule.get('title', ''),
                'condition': rule.get('condition', '')[:150]
            })
        
        logger.info(f"✅ Загружено: {len(candidates['indicators'])} indicators, "
                   f"{len(candidates['tools'])} tools, {len(candidates['rules'])} rules")
        
        return candidates
    
    
    def find_relevant_entities(
        self,
        stage: Dict,
        candidates: List[Dict],
        entity_type: str
    ) -> List[Tuple[str, float]]:
        """
        Находит релевантные entities для stage через LLM
        
        Returns:
            List of (entity_id, confidence_score)
        """
        # Формируем prompt
        system_prompt = f"""Ты - эксперт по финансовым методологиям.
Твоя задача: определить, какие {entity_type} релевантны для данного этапа.

Критерии релевантности:
- Индикаторы: метрики/KPI, которые нужно считать на этом этапе
- Инструменты: программы/шаблоны/фреймворки, используемые на этапе
- Правила: бизнес-правила/условия, применимые к этапу

Ответь ТОЛЬКО в формате JSON:
{{
  "relevant": ["id1", "id2", ...],
  "confidence": 0.85
}}

Если ничего не релевантно, верни: {{"relevant": [], "confidence": 0.0}}
"""

        # Формируем список candidates для промпта
        candidates_text = "\n".join([
            f"- {c['id']}: {c.get('name') or c.get('title', 'N/A')} - {c.get('description', c.get('condition', 'N/A'))[:100]}"
            for c in candidates[:self.batch_size]
        ])
        
        prompt = f"""Этап методологии:
ID: {stage['_key']}
Название: {stage['title']}
Описание: {stage.get('description', 'N/A')}

Доступные {entity_type}:
{candidates_text}

Какие из этих {entity_type} релевантны для данного этапа?
"""

        # Запрос к LLM
        response = self.chat(prompt, system_prompt)
        
        if not response:
            return []
        
        # Парсим JSON ответ
        try:
            # Ищем JSON в ответе (может быть обернут в ```json```)
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            
            data = json.loads(json_str)
            
            relevant_ids = data.get('relevant', [])
            confidence = data.get('confidence', 0.8)
            
            return [(eid, confidence) for eid in relevant_ids]
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Не удалось распарсить JSON: {response[:200]}... Ошибка: {e}")
            return []
    
    
    def create_edge(
        self,
        from_id: str,
        to_id: str,
        edge_collection: str,
        confidence: float = 0.8
    ):
        """Создает edge в ArangoDB"""
        if self.dry_run:
            logger.info(f"  [DRY RUN] {from_id} -> {to_id} ({edge_collection}, conf={confidence:.2f})")
            return
        
        try:
            # Определяем целевую коллекцию на основе edge collection
            if edge_collection == 'stage_uses_indicator':
                to_collection = 'indicators'
            elif edge_collection == 'stage_uses_tool':
                to_collection = 'tools'
            elif edge_collection == 'stage_has_rule':
                to_collection = 'rules'
            else:
                logger.error(f"❌ Неизвестный edge collection: {edge_collection}")
                return
            
            edge_doc = {
                '_from': f'stages/{from_id}',
                '_to': f'{to_collection}/{to_id}',
                'confidence': confidence,
                'created_by': 'agent_h',
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.db.collection(edge_collection).insert(edge_doc)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания edge {from_id}->{to_id}: {e}")
    
    
    def link_stage(self, stage: Dict, all_candidates: Dict[str, List[Dict]]):
        """Создает все связи для одного stage"""
        stage_id = stage['_key']
        logger.info(f"\n{'='*60}")
        logger.info(f"📍 Stage: {stage_id} - {stage['title']}")
        
        # Indicators
        logger.info("  🔍 Ищем indicators...")
        indicators = self.find_relevant_entities(stage, all_candidates['indicators'], 'indicators')
        for ind_id, conf in indicators:
            self.create_edge(stage_id, ind_id, 'stage_uses_indicator', conf)
            self.stats['indicators_linked'] += 1
        logger.info(f"  ✅ Найдено indicators: {len(indicators)}")
        
        # Tools
        logger.info("  🔍 Ищем tools...")
        tools = self.find_relevant_entities(stage, all_candidates['tools'], 'tools')
        for tool_id, conf in tools:
            self.create_edge(stage_id, tool_id, 'stage_uses_tool', conf)
            self.stats['tools_linked'] += 1
        logger.info(f"  ✅ Найдено tools: {len(tools)}")
        
        # Rules
        logger.info("  🔍 Ищем rules...")
        rules = self.find_relevant_entities(stage, all_candidates['rules'], 'rules')
        for rule_id, conf in rules:
            self.create_edge(stage_id, rule_id, 'stage_has_rule', conf)
            self.stats['rules_linked'] += 1
        logger.info(f"  ✅ Найдено rules: {len(rules)}")
        
        self.stats['stages_processed'] += 1
    
    
    def link_methodology(
        self,
        methodology_id: str = 'toc',
        limit: Optional[int] = None
    ):
        """
        Создает связи для всех stages методологии
        
        Args:
            methodology_id: ID методологии в ArangoDB
            limit: Ограничить количество stages (для тестирования)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Agent H: Semantic Linker")
        logger.info(f"📚 Методология: {methodology_id}")
        logger.info(f"🤖 Модель: {self.model}")
        logger.info(f"{'='*60}\n")
        
        # Подключаемся к ArangoDB
        if self.db is None:
            self.db = self.arango_client.connect()
            logger.info("✅ ArangoDB подключен\n")

        
        # Загружаем все candidates один раз
        all_candidates = self.load_all_candidates()
        
        # Получаем stages методологии
        query = f"""
        FOR s, e IN 1..1 OUTBOUND "methodologies/{methodology_id}" GRAPH "methodology_graph"
          FILTER IS_SAME_COLLECTION("stages", s)
          SORT s.order ASC
          {f'LIMIT {limit}' if limit else ''}
          RETURN s
        """
        
        cursor = self.db.aql.execute(query)
        stages = list(cursor)
        
        logger.info(f"📊 Найдено stages: {len(stages)}")
        
        if self.dry_run:
            logger.info("⚠️ DRY RUN MODE - edges не будут созданы")
        
        # Обрабатываем каждый stage
        for i, stage in enumerate(stages, 1):
            logger.info(f"\n[{i}/{len(stages)}]")
            self.link_stage(stage, all_candidates)
        
        # Финальная статистика
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ ЗАВЕРШЕНО")
        logger.info(f"{'='*60}")
        logger.info(f"Stages обработано: {self.stats['stages_processed']}")
        logger.info(f"Indicators связано: {self.stats['indicators_linked']}")
        logger.info(f"Tools связано: {self.stats['tools_linked']}")
        logger.info(f"Rules связано: {self.stats['rules_linked']}")
        logger.info(f"LLM вызовов: {self.stats['llm_calls']}")
        logger.info(f"Токенов использовано: {self.stats['total_tokens']}")
        logger.info(f"{'='*60}\n")
        
        return self.stats
