"""
Agent E: Graph DB Publisher

Загружает одобренные методологии из Agent C/D в ArangoDB.

Вход:
- data/methodologies/<id>.yaml (compiled, qa_approved)
- data/qa/<id>.json (QA report от Agent D)

Выход:
- Документы в ArangoDB (methodologies, stages, tools, indicators, rules)
- Edges (methodology_has_stage, stage_uses_*, *_uses_term)
- Term stubs (glossary_terms с status="needs_definition")
- JSON отчет (data/published/<id>.json)

Особенности:
- Идемпотентная загрузка (upsert на основе _key)
- Stable IDs (_key = methodology_id, stage_001, tool_001, etc)
- Автоматическое создание term stubs
- Lineage tracking (source.agent = "Agent E")
"""
import os
import sys
import json
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Импорт из корня проекта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from arangodb.client import ArangoDBClient


def utc_now_iso() -> str:
    """Current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of text content"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def compute_compiled_hash(yaml_path: str) -> str:
    """Compute hash of entire compiled YAML file"""
    with open(yaml_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


class AgentE:
    """Agent E: Graph DB Publisher"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize Agent E
        
        Args:
            base_dir: Base directory of the project (defaults to repo root)
        """
        # Agent E находится в pipeline/agents/, base_dir - это корень репо
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent.parent.absolute()
        self.data_dir = self.base_dir / "data"
        self.methodologies_dir = self.data_dir / "methodologies"
        self.qa_dir = self.data_dir / "qa"
        self.published_dir = self.data_dir / "published"
        
        # Create published dir if not exists
        self.published_dir.mkdir(parents=True, exist_ok=True)
        
        # Load env and create ArangoDB client
        load_dotenv(self.base_dir / '.env.arango')
        self.db_client = ArangoDBClient(base_dir=str(self.base_dir))
    
    def load_methodology_yaml(self, yaml_path: Path) -> Dict[str, Any]:
        """Load and validate methodology YAML"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError(f"Empty YAML file: {yaml_path}")
        
        if 'methodology_id' not in data:
            raise ValueError(f"Missing methodology_id in {yaml_path}")
        
        return data
    
    def load_qa_report(self, methodology_id: str) -> Optional[Dict[str, Any]]:
        """Load QA report if exists"""
        qa_path = self.qa_dir / f"{methodology_id}.json"
        if not qa_path.exists():
            return None
        
        with open(qa_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def check_qa_approval(self, qa_report: Optional[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Check if methodology is QA approved
        
        Returns:
            (approved, status_message)
        """
        if not qa_report:
            return False, "No QA report found"
        
        if qa_report.get('approved') is True:
            return True, "QA approved"
        
        issues_count = qa_report.get('issues_count', 0)
        return False, f"QA failed with {issues_count} issues"
    
    def build_content_text(self, entity_type: str, data: Dict[str, Any]) -> str:
        """
        Build searchable content_text for entity
        
        Rules:
        - methodology: title + description + tags
        - stage: title + description + tools names + indicators names
        - indicator: name + description + formula
        - tool: title + description
        """
        parts = []
        
        if entity_type == "methodology":
            parts.append(data.get('title', ''))
            parts.append(data.get('description', ''))
            parts.extend(data.get('tags', []))
        
        elif entity_type == "stage":
            parts.append(data.get('title', ''))
            parts.append(data.get('description', ''))
            # Add tool names
            for tool in data.get('tools', []):
                parts.append(tool.get('title', ''))
            # Add indicator names
            for ind in data.get('indicators', []):
                parts.append(ind.get('name', ''))
        
        elif entity_type == "indicator":
            parts.append(data.get('name', ''))
            parts.append(data.get('description', ''))
            parts.append(data.get('formula', ''))
        
        elif entity_type == "tool":
            parts.append(data.get('title', ''))
            parts.append(data.get('description', ''))
        
        # Join and clean
        text = ' '.join(parts).strip()
        return ' '.join(text.split())  # Normalize whitespace
    
    def extract_entities(self, method_data: Dict[str, Any], yaml_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all entities from methodology YAML
        
        Returns:
            Dict with lists: methodologies, stages, tools, indicators, rules
        """
        methodology_id = method_data['methodology_id']
        compiled_hash = compute_compiled_hash(yaml_path)
        
        entities = {
            "methodologies": [],
            "stages": [],
            "tools": [],
            "indicators": [],
            "rules": []
        }
        
        # Source lineage
        source = {
            "repo": "financial-methodologies-kb",
            "ref": "main",  # TODO: get from git
            "path": str(yaml_path.relative_to(self.base_dir)),
            "agent": "Agent E"
        }
        
        # 1) Methodology document
        method_doc = {
            "_key": methodology_id,
            "methodology_id": methodology_id,
            "title": method_data.get('title', ''),
            "methodology_type": method_data.get('methodology_type', ''),
            "description": method_data.get('description', ''),
            "scope": method_data.get('scope', ''),
            "status": method_data.get('status', 'draft'),
            "tags": method_data.get('tags', []),
            "source": source,
            "compiled_hash": compiled_hash,
            "content_text": self.build_content_text("methodology", method_data),
            "content_hash": "",  # will be computed after content_text
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso()
        }
        method_doc['content_hash'] = compute_content_hash(method_doc['content_text'])
        entities["methodologies"].append(method_doc)
        
        # 2) Stages, tools, indicators, rules
        tool_counter = 1
        indicator_counter = 1
        rule_counter = 1
        
        for stage in method_data.get('stages', []):
            stage_id = stage.get('stage_id', f"stage_{stage.get('order', 1):03d}")
            
            # Stage document
            stage_doc = {
                "_key": stage_id,
                "stage_id": stage_id,
                "title": stage['title'],
                "description": stage.get('description', ''),
                "order": stage.get('order', 0),
                "order_display": stage.get('order_display', ''),
                "substages": stage.get('substages', []),
                "status": "active",
                "source": source,
                "content_text": self.build_content_text("stage", stage),
                "content_hash": "",
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso()
            }
            stage_doc['content_hash'] = compute_content_hash(stage_doc['content_text'])
            entities["stages"].append(stage_doc)
            
            # Tools in this stage
            for tool in stage.get('tools', []):
                tool_id = f"tool_{tool_counter:03d}"
                tool_doc = {
                    "_key": tool_id,
                    "tool_id": tool_id,
                    "title": tool['title'],
                    "description": tool.get('description', ''),
                    "type": tool.get('type', 'other'),
                    "usage_type": tool.get('usage_type', 'optional'),
                    "content_text": self.build_content_text("tool", tool),
                    "content_hash": "",
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso()
                }
                tool_doc['content_hash'] = compute_content_hash(tool_doc['content_text'])
                entities["tools"].append(tool_doc)
                tool_counter += 1
            
            # Indicators in this stage
            for indicator in stage.get('indicators', []):
                ind_id = f"ind_{indicator_counter:03d}"
                ind_doc = {
                    "_key": ind_id,
                    "indicator_id": ind_id,
                    "name": indicator['name'],
                    "description": indicator.get('description', ''),
                    "formula": indicator.get('formula', ''),
                    "unit": indicator.get('unit', ''),
                    "threshold": indicator.get('threshold', {}),
                    "calculation_complexity": indicator.get('calculation_complexity', 'simple'),
                    "data_sources": indicator.get('data_sources', []),
                    "content_text": self.build_content_text("indicator", indicator),
                    "content_hash": "",
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso()
                }
                ind_doc['content_hash'] = compute_content_hash(ind_doc['content_text'])
                entities["indicators"].append(ind_doc)
                indicator_counter += 1
            
            # Rules in this stage
            for rule in stage.get('rules', []):
                rule_id = f"rule_{rule_counter:03d}"
                rule_doc = {
                    "_key": rule_id,
                    "rule_id": rule_id,
                    "title": rule.get('title', 'Rule'),
                    "description": rule.get('description', ''),
                    "severity": rule.get('severity', 'info'),
                    "content_text": rule.get('description', ''),
                    "content_hash": "",
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso()
                }
                rule_doc['content_hash'] = compute_content_hash(rule_doc['content_text'])
                entities["rules"].append(rule_doc)
                rule_counter += 1
        
        return entities
    
    def extract_edges(self, method_data: Dict[str, Any], entities: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all edges from methodology
        
        Returns:
            Dict with edge lists: methodology_has_stage, stage_uses_tool, etc
        """
        methodology_id = method_data['methodology_id']
        
        edges = {
            "methodology_has_stage": [],
            "stage_uses_tool": [],
            "stage_uses_indicator": [],
            "stage_has_rule": [],
            "indicator_depends_on": []
        }
        
        # Source lineage
        source = {
            "repo": "financial-methodologies-kb",
            "ref": "main",
            "path": f"data/methodologies/{methodology_id}.yaml",
            "agent": "Agent E"
        }
        
        # Build index: entity_id -> _key
        stage_index = {s['stage_id']: s['_key'] for s in entities['stages']}
        tool_index = {i: entities['tools'][i]['_key'] for i in range(len(entities['tools']))}
        indicator_index = {i: entities['indicators'][i]['_key'] for i in range(len(entities['indicators']))}
        rule_index = {i: entities['rules'][i]['_key'] for i in range(len(entities['rules']))}
        
        tool_counter = 0
        indicator_counter = 0
        rule_counter = 0
        
        for stage in method_data.get('stages', []):
            stage_id = stage.get('stage_id', f"stage_{stage.get('order', 1):03d}")
            stage_key = stage_index.get(stage_id)
            
            if not stage_key:
                continue
            
            # methodology → stage
            edges["methodology_has_stage"].append({
                "_from": f"methodologies/{methodology_id}",
                "_to": f"stages/{stage_key}",
                "order": stage.get('order', 0),
                "source": source,
                "created_at": utc_now_iso()
            })
            
            # stage → tools
            for tool in stage.get('tools', []):
                tool_key = tool_index.get(tool_counter)
                if tool_key:
                    edges["stage_uses_tool"].append({
                        "_from": f"stages/{stage_key}",
                        "_to": f"tools/{tool_key}",
                        "usage_type": tool.get('usage_type', 'optional'),
                        "created_at": utc_now_iso()
                    })
                tool_counter += 1
            
            # stage → indicators
            for indicator in stage.get('indicators', []):
                ind_key = indicator_index.get(indicator_counter)
                if ind_key:
                    edges["stage_uses_indicator"].append({
                        "_from": f"stages/{stage_key}",
                        "_to": f"indicators/{ind_key}",
                        "created_at": utc_now_iso()
                    })
                indicator_counter += 1
            
            # stage → rules
            for rule in stage.get('rules', []):
                rule_key = rule_index.get(rule_counter)
                if rule_key:
                    edges["stage_has_rule"].append({
                        "_from": f"stages/{stage_key}",
                        "_to": f"rules/{rule_key}",
                        "created_at": utc_now_iso()
                    })
                rule_counter += 1
        
        return edges
    
    def publish_methodology(self, methodology_id: str, skip_qa_check: bool = False) -> Dict[str, Any]:
        """
        Publish methodology to ArangoDB
        
        Args:
            methodology_id: ID методологии (например "accounting-basics-test")
            skip_qa_check: Пропустить проверку QA approval (для тестирования)
        
        Returns:
            Dict с результатами публикации
        """
        print(f"\n📚 Publishing methodology: {methodology_id}")
        print("=" * 60)
        
        # 1) Load YAML
        yaml_path = self.methodologies_dir / f"{methodology_id}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Methodology YAML not found: {yaml_path}")
        
        method_data = self.load_methodology_yaml(yaml_path)
        print(f"✅ Loaded: {yaml_path.name}")
        
        # 2) Load and check QA
        qa_report = self.load_qa_report(methodology_id)
        if not skip_qa_check:
            approved, status_msg = self.check_qa_approval(qa_report)
            if not approved:
                raise ValueError(f"Cannot publish: {status_msg}")
            print(f"✅ QA approved")
        else:
            print(f"⚠️  Skipping QA check (forced publish)")
        
        # 3) Connect to ArangoDB
        self.db_client.connect()
        print(f"✅ Connected to ArangoDB")
        
        # 4) Extract entities
        entities = self.extract_entities(method_data, yaml_path)
        print(f"\n📦 Extracted entities:")
        print(f"  - Methodologies: {len(entities['methodologies'])}")
        print(f"  - Stages: {len(entities['stages'])}")
        print(f"  - Tools: {len(entities['tools'])}")
        print(f"  - Indicators: {len(entities['indicators'])}")
        print(f"  - Rules: {len(entities['rules'])}")
        
        # 5) Extract edges
        edges = self.extract_edges(method_data, entities)
        print(f"\n🔗 Extracted edges:")
        print(f"  - methodology_has_stage: {len(edges['methodology_has_stage'])}")
        print(f"  - stage_uses_tool: {len(edges['stage_uses_tool'])}")
        print(f"  - stage_uses_indicator: {len(edges['stage_uses_indicator'])}")
        print(f"  - stage_has_rule: {len(edges['stage_has_rule'])}")
        
        # 6) Upsert entities
        print(f"\n📝 Upserting entities to ArangoDB...")
        bundle = {"entities": entities, "qa_warnings": []}
        entity_result = self.db_client.upsert_entities(bundle)
        
        # 7) Upsert edges
        print(f"\n🔗 Upserting edges to ArangoDB...")
        bundle = {"edges": edges, "qa_warnings": []}
        edge_result = self.db_client.upsert_edges(bundle)
        
        # 8) Save publish report
        report = {
            "methodology_id": methodology_id,
            "published_at": utc_now_iso(),
            "agent": "Agent E v1.0",
            "source_yaml": str(yaml_path.relative_to(self.base_dir)),
            "compiled_hash": method_data.get('compiled_hash'),
            "qa_approved": not skip_qa_check,
            "entities": entity_result,
            "edges": edge_result,
            "qa_warnings_count": len(bundle.get('qa_warnings', []))
        }
        
        report_path = self.published_dir / f"{methodology_id}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Published successfully!")
        print(f"📄 Report saved: {report_path}")
        
        self.db_client.disconnect()
        
        return report


def main():
    """CLI для Agent E"""
    parser = argparse.ArgumentParser(description="Agent E: Graph DB Publisher")
    parser.add_argument("methodology_id", help="ID методологии для публикации")
    parser.add_argument("--skip-qa", action="store_true", help="Пропустить проверку QA approval")
    parser.add_argument("--base-dir", help="Base directory (defaults to parent of this file)")
    
    args = parser.parse_args()
    
    try:
        agent = AgentE(base_dir=args.base_dir)
        report = agent.publish_methodology(args.methodology_id, skip_qa_check=args.skip_qa)
        
        print(f"\n📊 Summary:")
        print(f"  Methodology: {report['methodology_id']}")
        print(f"  Entities upserted: {sum(r['upserted'] for r in report['entities']['entities'].values())}")
        print(f"  Edges upserted: {sum(r['upserted'] for r in report['edges']['edges'].values())}")
        print(f"  QA warnings: {report['qa_warnings_count']}")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
