"""
ArangoDB Client for Financial Methodologies KB

Production-ready client with:
- apply_schema(): idempotent schema setup
- upsert_entities(): bulk upsert with merge
- upsert_edges(): bulk edges with glossary stub creation
- QA warnings for missing terms
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from arango import ArangoClient as ArClient
from arango.database import StandardDatabase
from arango.exceptions import DatabaseCreateError, CollectionCreateError


def utc_now_iso() -> str:
    """Current UTC time in ISO format"""
    return datetime.now(timezone.utc).isoformat()


class ArangoDBClient:
    """
    Клиент для работы с ArangoDB.
    
    Управляет подключением к базе данных и создает необходимые коллекции.
    Методы:
    - apply_schema(): создает коллекции, граф, view (idempotent)
    - upsert_entities(bundle): массовая загрузка документов
    - upsert_edges(bundle): массовая загрузка связей + создание term stubs
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        db_name: Optional[str] = None,
        base_dir: Optional[str] = None
    ):
        """
        Инициализация клиента.
        
        Args:
            host: URL сервера ArangoDB (по умолчанию из env ARANGO_HOST:ARANGO_PORT)
            username: Имя пользователя (по умолчанию из env ARANGO_USER)
            password: Пароль (по умолчанию из env ARANGO_PASSWORD)
            db_name: Имя базы данных (по умолчанию из env ARANGO_DB)
            base_dir: Базовая директория для поиска schema/ и views/
        """
        arango_host = os.getenv("ARANGO_HOST", "localhost")
        arango_port = os.getenv("ARANGO_PORT", "8529")
        
        self.host = host or f"http://{arango_host}:{arango_port}"
        self.username = username or os.getenv("ARANGO_USER", "root")
        self.password = password or os.getenv("ARANGO_PASSWORD", "")
        self.db_name = db_name or os.getenv("ARANGO_DB", "fin_kb_method")
        
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.schema_dir = os.path.join(self.base_dir, "arangodb", "schema")
        self.views_dir = os.path.join(self.base_dir, "arangodb", "views")
        
        self.client: Optional[ArClient] = None
        self.db: Optional[StandardDatabase] = None
    
    def connect(self) -> StandardDatabase:
        """
        Подключение к ArangoDB.
        
        Returns:
            Database instance
        """
        print(f"🔌 Connecting to ArangoDB at {self.host}...")
        
        # Создаем клиент
        self.client = ArClient(hosts=self.host)
        
        # Подключаемся к системной базе
        sys_db = self.client.db('_system', username=self.username, password=self.password)
        
        # Создаем базу данных, если не существует
        if not sys_db.has_database(self.db_name):
            print(f"📦 Creating database '{self.db_name}'...")
            try:
                sys_db.create_database(self.db_name)
                print(f"✅ Database '{self.db_name}' created")
            except DatabaseCreateError as e:
                print(f"⚠️  Database creation error: {e}")
        
        # Подключаемся к нашей базе
        self.db = self.client.db(self.db_name, username=self.username, password=self.password)
        print(f"✅ Connected to database '{self.db_name}'")
        
        return self.db
    
    def setup_collections(self):
        """
        Создание коллекций и индексов.
        """
        if not self.db:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        print("📋 Setting up collections...")
        
        # Document collections
        doc_collections = [
            "methodologies",
            "stages",
            "tools",
            "indicators",
            "rules",
            "glossary_terms",  # NEW: глоссарий терминов
            "embeddings",      # NEW: vector embeddings (отдельно от сущностей)
            "chunks"           # NEW: чанки для RAG (опционально)
        ]
        
        for coll_name in doc_collections:
            if not self.db.has_collection(coll_name):
                try:
                    self.db.create_collection(coll_name)
                    print(f"  ✅ Created collection: {coll_name}")
                except CollectionCreateError as e:
                    print(f"  ⚠️  Error creating {coll_name}: {e}")
            else:
                print(f"  ⏭️  Collection already exists: {coll_name}")
        
        # Edge collections (семантические названия)
        edge_collections = [
            "methodology_has_stage",     # methodology → stage
            "stage_uses_tool",           # stage → tool
            "stage_uses_indicator",      # stage → indicator
            "stage_has_rule",            # stage → rule
            "indicator_depends_on",      # indicator → indicator (зависимости)
            "methodology_uses_term",     # methodology → glossary_term (relation_type: defines/uses/mentions)
            "stage_uses_term",           # stage → glossary_term
            "indicator_uses_term",       # indicator → glossary_term
            "tool_uses_term",            # tool → glossary_term
            "term_relates_to",           # glossary_term → glossary_term (relation_type: synonym/related/antonym)
            "chunk_of"                   # chunk → document (RAG chunks)
        ]
        
        for coll_name in edge_collections:
            if not self.db.has_collection(coll_name):
                try:
                    self.db.create_collection(coll_name, edge=True)
                    print(f"  ✅ Created edge collection: {coll_name}")
                except CollectionCreateError as e:
                    print(f"  ⚠️  Error creating {coll_name}: {e}")
            else:
                print(f"  ⏭️  Edge collection already exists: {coll_name}")
        
        # Создаем индексы
        self._create_indexes()
        
        print("✅ Collections setup complete")
    
    def _create_indexes(self):
        """
        Создание индексов для быстрого поиска.
        """
        print("🔍 Creating indexes...")
        
        try:
            # Индексы для methodologies
            methodologies = self.db.collection("methodologies")
            methodologies.add_index({
                'type': 'hash',
                'fields': ['methodology_id'],
                'unique': True
            })
            print("  ✅ Index: methodologies.methodology_id")
            
            methodologies.add_index({
                'type': 'fulltext',
                'fields': ['title']
            })
            print("  ✅ Fulltext index: methodologies.title")
            
            # Индексы для stages
            stages = self.db.collection("stages")
            stages.add_index({
                'type': 'hash',
                'fields': ['stage_id'],
                'unique': True
            })
            print("  ✅ Index: stages.stage_id")
            
            # Индексы для indicators
            indicators = self.db.collection("indicators")
            indicators.add_index({
                'type': 'hash',
                'fields': ['indicator_id'],
                'unique': True
            })
            print("  ✅ Index: indicators.indicator_id")
            
            indicators.add_index({
                'type': 'fulltext',
                'fields': ['name']
            })
            print("  ✅ Fulltext index: indicators.name")
            
            # Индексы для glossary_terms
            terms = self.db.collection("glossary_terms")
            terms.add_index({
                'type': 'hash',
                'fields': ['term_id'],
                'unique': True
            })
            print("  ✅ Index: glossary_terms.term_id")
            
            terms.add_index({
                'type': 'fulltext',
                'fields': ['name']
            })
            print("  ✅ Fulltext index: glossary_terms.name")
            
            terms.add_index({
                'type': 'hash',
                'fields': ['status']
            })
            print("  ✅ Index: glossary_terms.status")
            
            print("✅ Indexes created")
        except Exception as e:
            # Индексы могут уже существовать
            print(f"  ⚠️  Index creation: {e}")
            print("  ⏭️  Continuing (indexes may already exist)")
    
    def create_graph(self):
        """
        Создание именованного графа для методологий.
        """
        if not self.db:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        graph_name = "methodology_graph"
        
        if self.db.has_graph(graph_name):
            print(f"⏭️  Graph '{graph_name}' already exists")
            return self.db.graph(graph_name)
        
        print(f"🕸️  Creating graph '{graph_name}'...")
        
        # Определяем структуру графа
        edge_definitions = [
            {
                'edge_collection': 'methodology_has_stage',
                'from_vertex_collections': ['methodologies'],
                'to_vertex_collections': ['stages']
            },
            {
                'edge_collection': 'stage_uses_tool',
                'from_vertex_collections': ['stages'],
                'to_vertex_collections': ['tools']
            },
            {
                'edge_collection': 'stage_uses_indicator',
                'from_vertex_collections': ['stages'],
                'to_vertex_collections': ['indicators']
            },
            {
                'edge_collection': 'stage_has_rule',
                'from_vertex_collections': ['stages'],
                'to_vertex_collections': ['rules']
            },
            {
                'edge_collection': 'indicator_depends_on',
                'from_vertex_collections': ['indicators'],
                'to_vertex_collections': ['indicators']
            },
            {
                'edge_collection': 'methodology_uses_term',
                'from_vertex_collections': ['methodologies'],
                'to_vertex_collections': ['glossary_terms']
            },
            {
                'edge_collection': 'stage_uses_term',
                'from_vertex_collections': ['stages'],
                'to_vertex_collections': ['glossary_terms']
            },
            {
                'edge_collection': 'indicator_uses_term',
                'from_vertex_collections': ['indicators'],
                'to_vertex_collections': ['glossary_terms']
            },
            {
                'edge_collection': 'tool_uses_term',
                'from_vertex_collections': ['tools'],
                'to_vertex_collections': ['glossary_terms']
            },
            {
                'edge_collection': 'term_relates_to',
                'from_vertex_collections': ['glossary_terms'],
                'to_vertex_collections': ['glossary_terms']
            },
            {
                'edge_collection': 'chunk_of',
                'from_vertex_collections': ['chunks'],
                'to_vertex_collections': ['methodologies', 'stages', 'tools', 'indicators', 'rules', 'glossary_terms']
            }
        ]
        
        graph = self.db.create_graph(graph_name, edge_definitions=edge_definitions)
        print(f"✅ Graph '{graph_name}' created")
        
        return graph
    
    def create_search_view(self):
        """
        Создание ArangoSearch view для полнотекстового поиска.
        """
        if not self.db:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        view_name = "kb_search_view"
        
        # Проверяем существование view
        try:
            existing_view = self.db.view(view_name)
            if existing_view:
                print(f"⏭️  View '{view_name}' already exists")
                return existing_view
        except:
            pass  # View не существует, создаем
        
        print(f"🔍 Creating ArangoSearch view '{view_name}'...")
        
        # Загружаем конфигурацию view из файла
        import json
        import os
        
        view_config_path = os.path.join(
            os.path.dirname(__file__),
            'views',
            'kb_search_view.json'
        )
        
        try:
            with open(view_config_path, 'r', encoding='utf-8') as f:
                view_config = json.load(f)
            
            view = self.db.create_view(
                name=view_name,
                view_type='arangosearch',
                properties=view_config
            )
            print(f"✅ ArangoSearch view '{view_name}' created")
            return view
            
        except FileNotFoundError:
            print(f"⚠️  View config not found: {view_config_path}")
            print("  Skipping view creation")
            return None
        except Exception as e:
            print(f"⚠️  Error creating view: {e}")
            return None
    
    def apply_schema(self) -> Dict[str, Any]:
        """
        Идемпотентное применение схемы из файлов.
        
        Читает:
        - arangodb/schema/*.json (создает document collections)
        - arangodb/schema/edges_spec.json (создает edge collections + граф)
        - arangodb/views/kb_search_view.json (создает/обновляет view)
        
        Returns:
            Dict с результатами создания
        """
        if not self.db:
            raise RuntimeError("Not connected. Call connect() first.")
        
        print("📋 Applying schema from files...")
        
        results = {
            "created_doc_collections": [],
            "created_edge_collections": [],
            "added_edge_definitions": [],
            "created_view": False,
            "updated_view": False
        }
        
        # 1) Document collections из файлов схем
        for fname in os.listdir(self.schema_dir):
            if not fname.endswith(".json") or fname == "edges_spec.json":
                continue
            
            col_name = fname.replace(".json", "")
            if not self.db.has_collection(col_name):
                self.db.create_collection(col_name)
                results["created_doc_collections"].append(col_name)
                print(f"  ✅ Created collection: {col_name}")
        
        # 2) Edge collections из edges_spec.json
        edges_spec_path = os.path.join(self.schema_dir, "edges_spec.json")
        if os.path.exists(edges_spec_path):
            with open(edges_spec_path, "r", encoding="utf-8") as f:
                edges_spec = json.load(f)
            
            # Достаем все edge определения из definitions
            for edge_name in edges_spec.get("definitions", {}).keys():
                if not self.db.has_collection(edge_name):
                    self.db.create_collection(edge_name, edge=True)
                    results["created_edge_collections"].append(edge_name)
                    print(f"  ✅ Created edge collection: {edge_name}")
        
        # 3) Создаем граф с edge definitions
        graph_name = "methodology_graph"
        if not self.db.has_graph(graph_name):
            self.db.create_graph(graph_name)
            print(f"  ✅ Created graph: {graph_name}")
        
        graph = self.db.graph(graph_name)
        existing_defs = {d["edge_collection"] for d in graph.edge_definitions()}
        
        # Добавляем edge definitions из схемы
        edge_defs_map = {
            "methodology_has_stage": (["methodologies"], ["stages"]),
            "stage_uses_tool": (["stages"], ["tools"]),
            "stage_uses_indicator": (["stages"], ["indicators"]),
            "stage_has_rule": (["stages"], ["rules"]),
            "indicator_depends_on": (["indicators"], ["indicators"]),
            "methodology_uses_term": (["methodologies"], ["glossary_terms"]),
            "stage_uses_term": (["stages"], ["glossary_terms"]),
            "indicator_uses_term": (["indicators"], ["glossary_terms"]),
            "tool_uses_term": (["tools"], ["glossary_terms"]),
            "term_relates_to": (["glossary_terms"], ["glossary_terms"]),
            "chunk_of": (["chunks"], ["methodologies", "stages", "tools", "indicators", "rules", "glossary_terms"])
        }
        
        for edge_name, (from_cols, to_cols) in edge_defs_map.items():
            if edge_name not in existing_defs:
                try:
                    graph.create_edge_definition(
                        edge_collection=edge_name,
                        from_vertex_collections=from_cols,
                        to_vertex_collections=to_cols
                    )
                    results["added_edge_definitions"].append(edge_name)
                    print(f"  ✅ Added edge definition: {edge_name}")
                except Exception as e:
                    print(f"  ⚠️  Error adding edge definition {edge_name}: {e}")
        
        # 4) Создаем/обновляем ArangoSearch view
        view_path = os.path.join(self.views_dir, "kb_search_view.json")
        if os.path.exists(view_path):
            with open(view_path, "r", encoding="utf-8") as f:
                view_spec = json.load(f)
            
            view_name = view_spec.get("name", "kb_search_view")
            
            # Проверяем существование view через has_view (если доступно) или try/except
            try:
                # Пытаемся получить view
                view_info = self.db.view(view_name)
                # View exists - skip update (view.replace не работает так как ожидается)
                results["updated_view"] = False
                print(f"  ⏭️  View '{view_name}' already exists (skipping update)")
            except:
                # View doesn't exist - create it
                try:
                    self.db.create_arangosearch_view(
                        name=view_name,
                        properties=view_spec.get("properties", {})
                    )
                    results["created_view"] = True
                    print(f"  ✅ Created view: {view_name}")
                except Exception as e:
                    print(f"  ⚠️  Error creating view {view_name}: {e}")
        
        print("✅ Schema applied")
        return results
    
    def upsert_entities(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Массовая загрузка сущностей с merge update.
        
        Args:
            bundle: {
                "entities": {
                    "methodologies": [{"_key": "...", ...}],
                    "stages": [...],
                    ...
                },
                "qa_warnings": []  # опционально, будет дополнен
            }
        
        Returns:
            Dict с результатами загрузки
        """
        if not self.db:
            raise RuntimeError("Not connected. Call connect() first.")
        
        entities = bundle.get("entities", {})
        qa_warnings = bundle.setdefault("qa_warnings", [])
        
        results = {}
        
        for col_name, docs in entities.items():
            if not docs:
                continue
            
            if not isinstance(docs, list):
                raise ValueError(f"entities['{col_name}'] must be a list")
            
            # Создаем коллекцию если не существует
            if not self.db.has_collection(col_name):
                self.db.create_collection(col_name)
            
            col = self.db.collection(col_name)
            
            stats = {
                "upserted": 0,
                "inserted": 0,
                "updated": 0,
                "errors": 0
            }
            
            for doc in docs:
                try:
                    if "_key" not in doc:
                        raise ValueError(f"Missing _key in {col_name} doc")
                    
                    # Добавляем стандартные поля
                    doc.setdefault("updated_at", utc_now_iso())
                    doc.setdefault("created_at", utc_now_iso())
                    doc.setdefault("entity_type", self._infer_entity_type(col_name))
                    
                    key = doc["_key"]
                    if col.has(key):
                        # Update существующего документа (merge)
                        existing = col.get(key)
                        if existing and "created_at" in existing:
                            doc["created_at"] = existing["created_at"]
                        col.update(doc, merge=True, keep_none=False)
                        stats["updated"] += 1
                    else:
                        # Insert нового документа
                        col.insert(doc)
                        stats["inserted"] += 1
                    
                    stats["upserted"] += 1
                    
                except Exception as ex:
                    stats["errors"] += 1
                    qa_warnings.append({
                        "type": "entity_upsert_failed",
                        "collection": col_name,
                        "doc_key": doc.get("_key"),
                        "message": str(ex),
                        "at": utc_now_iso()
                    })
            
            results[col_name] = stats
            print(f"  📝 {col_name}: {stats['inserted']} inserted, {stats['updated']} updated, {stats['errors']} errors")
        
        return {
            "entities": results,
            "qa_warnings_count": len(qa_warnings)
        }
    
    def upsert_edges(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Массовая загрузка edges с автоматическим созданием term stubs.
        
        Если edge указывает на glossary_terms/<term_key>, а термин не существует,
        создается stub с status="needs_definition" + QA warning.
        
        Args:
            bundle: {
                "edges": {
                    "methodology_has_stage": [{"_from": "...", "_to": "...", ...}],
                    "methodology_uses_term": [{"_from": "...", "_to": "glossary_terms/...", "relation_type": "mentions"}],
                    ...
                },
                "qa_warnings": []
            }
        
        Returns:
            Dict с результатами загрузки
        """
        if not self.db:
            raise RuntimeError("Not connected. Call connect() first.")
        
        edges_map = bundle.get("edges", {})
        qa_warnings = bundle.setdefault("qa_warnings", [])
        
        # Проверяем наличие glossary_terms коллекции
        if not self.db.has_collection("glossary_terms"):
            self.db.create_collection("glossary_terms")
        
        glossary = self.db.collection("glossary_terms")
        
        results = {}
        
        for edge_col_name, edge_docs in edges_map.items():
            if not edge_docs:
                continue
            
            if not isinstance(edge_docs, list):
                raise ValueError(f"edges['{edge_col_name}'] must be a list")
            
            # Создаем edge коллекцию если не существует
            if not self.db.has_collection(edge_col_name):
                self.db.create_collection(edge_col_name, edge=True)
            
            ecol = self.db.collection(edge_col_name)
            
            stats = {
                "upserted": 0,
                "inserted": 0,
                "updated": 0,
                "errors": 0,
                "created_glossary_stubs": 0
            }
            
            for edge in edge_docs:
                try:
                    if "_from" not in edge or "_to" not in edge:
                        raise ValueError(f"Edge missing _from/_to in {edge_col_name}")
                    
                    edge.setdefault("created_at", utc_now_iso())
                    
                    # ---- Glossary stub rule ----
                    # Если edge ведет в glossary_terms/<key>, проверяем существование термина
                    to_id = edge["_to"]
                    if to_id.startswith("glossary_terms/"):
                        term_key = to_id.split("/", 1)[1]
                        if not glossary.has(term_key):
                            # Создаем stub термина
                            stub = {
                                "_key": term_key,
                                "term_id": term_key,
                                "name": edge.get("term_name") or term_key,
                                "definition": "",
                                "aliases": [],
                                "tags": [],
                                "status": "needs_definition",
                                "entity_type": "term",
                                "created_at": utc_now_iso(),
                                "updated_at": utc_now_iso()
                            }
                            glossary.insert(stub)
                            stats["created_glossary_stubs"] += 1
                            qa_warnings.append({
                                "type": "glossary_term_stub_created",
                                "term_key": term_key,
                                "edge_collection": edge_col_name,
                                "from": edge["_from"],
                                "relation_type": edge.get("relation_type"),
                                "message": f"Glossary term '{term_key}' missing; created stub with status='needs_definition'",
                                "at": utc_now_iso()
                            })
                    
                    # Генерируем deterministic _key для идемпотентности
                    # Формат: hash от from_id|to_id|relation_type
                    rel_type = edge.get("relation_type", edge.get("relation", "related"))
                    edge_signature = f"{edge['_from']}|{edge['_to']}|{rel_type}"
                    edge_key = hashlib.md5(edge_signature.encode()).hexdigest()[:32]
                    edge.setdefault("_key", edge_key)
                    
                    key = edge["_key"]
                    if ecol.has(key):
                        # Update существующего edge
                        ecol.update(edge, merge=True, keep_none=False)
                        stats["updated"] += 1
                    else:
                        # Insert нового edge
                        ecol.insert(edge)
                        stats["inserted"] += 1
                    
                    stats["upserted"] += 1
                    
                except Exception as ex:
                    stats["errors"] += 1
                    qa_warnings.append({
                        "type": "edge_upsert_failed",
                        "collection": edge_col_name,
                        "edge_key": edge.get("_key"),
                        "from": edge.get("_from"),
                        "to": edge.get("_to"),
                        "message": str(ex),
                        "at": utc_now_iso()
                    })
            
            results[edge_col_name] = stats
            if stats["created_glossary_stubs"] > 0:
                print(f"  🔗 {edge_col_name}: {stats['inserted']} inserted, {stats['updated']} updated, {stats['created_glossary_stubs']} term stubs created")
            else:
                print(f"  🔗 {edge_col_name}: {stats['inserted']} inserted, {stats['updated']} updated")
        
        return {
            "edges": results,
            "qa_warnings_count": len(qa_warnings)
        }
    
    def _infer_entity_type(self, collection_name: str) -> str:
        """Определяет entity_type по имени коллекции"""
        mapping = {
            "methodologies": "methodology",
            "stages": "stage",
            "tools": "tool",
            "indicators": "indicator",
            "rules": "rule",
            "glossary_terms": "term",
            "chunks": "chunk",
            "embeddings": "embedding"
        }
        return mapping.get(collection_name, "entity")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверка состояния подключения.
        
        Returns:
            Словарь со статусом и метриками
        """
        if not self.db:
            return {
                "status": "disconnected",
                "error": "Not connected to database"
            }
        
        try:
            # Проверяем доступность
            version = self.db.version()
            
            # Считаем документы в коллекциях
            collections = {}
            for coll_name in ["methodologies", "stages", "tools", "indicators", "rules", "glossary_terms", "embeddings", "chunks"]:
                if self.db.has_collection(coll_name):
                    coll = self.db.collection(coll_name)
                    collections[coll_name] = coll.count()
            
            return {
                "status": "connected",
                "database": self.db_name,
                "version": version,
                "collections": collections
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def disconnect(self):
        """
        Закрытие подключения.
        """
        if self.client:
            self.client.close()
            print("🔌 Disconnected from ArangoDB")


def main():
    """
    Пример использования: инициализация базы данных.
    """
    import sys
    from dotenv import load_dotenv
    
    # Загружаем переменные окружения
    load_dotenv('.env.arango')
    
    # Создаем клиент (все параметры из .env.arango)
    client = ArangoDBClient()
    
    try:
        # Подключаемся
        client.connect()
        
        # Создаем коллекции
        client.setup_collections()
        
        # Создаем граф
        client.create_graph()
        
        # Создаем ArangoSearch view
        client.create_search_view()
        
        # Проверяем здоровье
        health = client.health_check()
        print("\n📊 Health check:")
        print(f"  Status: {health['status']}")
        if health['status'] == 'connected':
            print(f"  Database: {health['database']}")
            print(f"  Version: {health['version']}")
            print(f"  Collections:")
            for coll_name, count in health['collections'].items():
                print(f"    {coll_name}: {count} documents")
        
        print("\n✅ ArangoDB setup complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
