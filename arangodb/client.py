"""
ArangoDB Client for Financial Methodologies KB
"""
import os
from typing import Optional, Dict, Any, List
from arango import ArangoClient as ArClient
from arango.database import StandardDatabase
from arango.exceptions import DatabaseCreateError, CollectionCreateError


class ArangoDBClient:
    """
    Клиент для работы с ArangoDB.
    
    Управляет подключением к базе данных и создает необходимые коллекции.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        db_name: Optional[str] = None
    ):
        """
        Инициализация клиента.
        
        Args:
            host: URL сервера ArangoDB (по умолчанию из env ARANGO_HOST:ARANGO_PORT)
            username: Имя пользователя (по умолчанию из env ARANGO_USER)
            password: Пароль (по умолчанию из env ARANGO_PASSWORD)
            db_name: Имя базы данных (по умолчанию из env ARANGO_DB)
        """
        arango_host = os.getenv("ARANGO_HOST", "localhost")
        arango_port = os.getenv("ARANGO_PORT", "8529")
        
        self.host = host or f"http://{arango_host}:{arango_port}"
        self.username = username or os.getenv("ARANGO_USER", "root")
        self.password = password or os.getenv("ARANGO_PASSWORD", "")
        self.db_name = db_name or os.getenv("ARANGO_DB", "fin_kb_method")
        
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
