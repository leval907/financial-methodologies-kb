#!/usr/bin/env python3
"""
Agent C: Compiler
Компилирует outline.yaml в структурированную markdown документацию.

Вход:
- work/<book_id>/outline.yaml

Выход:
- docs/methodologies/<id>/README.md
- docs/methodologies/<id>/stages/*.md
- docs/methodologies/<id>/tools/*.md
- docs/methodologies/<id>/indicators/*.md
- data/methodologies/<id>.yaml

Модель: GigaChat Lite (primary) + Qwen3-Max (fallback)
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import json
from datetime import datetime

# GigaChat
try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
except ImportError:
    print("⚠️  Warning: gigachat not installed. Install: pip install gigachat")
    GigaChat = None

# Requesty AI
try:
    from openai import OpenAI
except ImportError:
    print("⚠️  Warning: openai not installed. Install: pip install openai")
    OpenAI = None


class MethodologyCompiler:
    """
    Компилятор методологии: outline.yaml → markdown docs.
    
    Использует:
    - GigaChat Lite (primary) - быстрая генерация по шаблонам
    - Qwen3-Max (fallback) - если GigaChat недоступен
    """
    
    def __init__(
        self,
        gigachat_credentials: Optional[str] = None,
        requesty_api_key: Optional[str] = None,
        use_gigachat: bool = True
    ):
        """
        Инициализация компилятора.
        
        Args:
            gigachat_credentials: Credentials для GigaChat API
            requesty_api_key: API key для Requesty AI (fallback)
            use_gigachat: Использовать GigaChat как primary модель
        """
        self.use_gigachat = use_gigachat and GigaChat is not None
        self.gigachat_client = None
        self.requesty_client = None
        
        # Инициализация GigaChat
        if self.use_gigachat and gigachat_credentials:
            try:
                self.gigachat_client = GigaChat(
                    credentials=gigachat_credentials,
                    scope="GIGACHAT_API_PERS",
                    verify_ssl_certs=False
                )
                print("✅ GigaChat initialized (primary)")
            except Exception as e:
                print(f"⚠️  GigaChat init failed: {e}")
                self.use_gigachat = False
        
        # Инициализация Requesty AI (fallback)
        if requesty_api_key and OpenAI:
            try:
                self.requesty_client = OpenAI(
                    api_key=requesty_api_key,
                    base_url="https://router.requesty.ai/v1"
                )
                print("✅ Requesty AI initialized (fallback)")
            except Exception as e:
                print(f"⚠️  Requesty AI init failed: {e}")
    
    def chat(self, system_prompt: str, user_prompt: str, model: str = "gigachat-lite") -> str:
        """
        Универсальный метод для LLM запросов с автоматическим fallback.
        
        Args:
            system_prompt: Системный промпт
            user_prompt: Пользовательский промпт
            model: Модель (gigachat-lite или alibaba/qwen3-max)
        
        Returns:
            Ответ модели
        """
        # Попытка 1: GigaChat Lite (primary)
        if self.use_gigachat and self.gigachat_client:
            try:
                messages = [
                    Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                    Messages(role=MessagesRole.USER, content=user_prompt)
                ]
                
                response = self.gigachat_client.chat(
                    Chat(
                        messages=messages,
                        temperature=0.3,  # Меньше креативности для шаблонов
                        max_tokens=2000
                    )
                )
                
                return response.choices[0].message.content
            except Exception as e:
                print(f"⚠️  GigaChat Lite failed: {e}")
                print("→ Switching to Qwen3-Max fallback...")
        
        # Попытка 2: Qwen3-Max через Requesty (fallback)
        if self.requesty_client:
            try:
                response = self.requesty_client.chat.completions.create(
                    model="alibaba/qwen3-max",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                return response.choices[0].message.content
            except Exception as e:
                print(f"❌ Qwen3-Max failed: {e}")
                return f"ERROR: All models failed. {e}"
        
        return "ERROR: No models available"
    
    def load_outline(self, outline_path: Path) -> Dict[str, Any]:
        """Загрузка outline.yaml."""
        with open(outline_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def generate_readme(self, outline: Dict[str, Any]) -> str:
        """
        Генерация README.md для методологии.
        
        Содержит:
        - Название и описание
        - Тип методологии
        - Структура (stages overview)
        - Ссылки на подстраницы
        """
        metadata = outline.get('metadata', {})
        classification = outline.get('classification', {})
        structure = outline.get('structure', {})
        
        system_prompt = """Ты эксперт по финансовой методологии и техническому писательству.
Твоя задача - создавать четкие, структурированные README для финансовых методологий.

Требования:
- Используй markdown форматирование
- Будь кратким и конкретным
- Фокусируйся на практической пользе
- Используй профессиональную терминологию
"""
        
        user_prompt = f"""Создай README.md для методологии.

**Данные:**

Метаданные:
{yaml.dump(metadata, allow_unicode=True)}

Классификация:
{yaml.dump(classification, allow_unicode=True)}

Этапы:
{yaml.dump(structure.get('stages', []), allow_unicode=True)}

**Требования к README:**

# Название методологии

## 📋 Описание

[Краткое описание методологии, её цель и область применения]

## 🎯 Тип методологии

[Тип: {classification.get('methodology_type', 'unknown')}]
[Объяснить что это значит]

## 📊 Структура

### Этапы методологии

[Список этапов с кратким описанием каждого]

1. **[Название этапа]** - [Краткое описание]
2. ...

## 📚 Связанные разделы

- [Stages](./stages/) - Подробное описание этапов
- [Tools](./tools/) - Инструменты и шаблоны
- [Indicators](./indicators/) - Показатели и формулы

## 🔗 Связанные методологии

[Если есть related_methodologies]

---

Сгенерируй только содержимое README в markdown формате. Без комментариев."""
        
        return self.chat(system_prompt, user_prompt)
    
    def generate_stage_doc(self, stage: Dict[str, Any], stage_num: int) -> str:
        """
        Генерация документации для одного этапа.
        
        Содержит:
        - Название и описание этапа
        - Порядок выполнения
        - Подэтапы (если есть)
        - Инструменты (если есть)
        - Индикаторы (если есть)
        - Примеры
        """
        system_prompt = """Ты эксперт по финансовым методологиям и процессам.
Твоя задача - создавать подробную документацию для каждого этапа методологии.

Требования:
- Четкая структура
- Пошаговые инструкции
- Практические примеры
- Связь с другими этапами
"""
        
        user_prompt = f"""Создай детальную документацию для этапа методологии.

**Данные этапа:**
{yaml.dump(stage, allow_unicode=True)}

**Требования к документу:**

# {stage.get('title', f'Этап {stage_num}')}

## 📝 Описание

{stage.get('description', '')}

## 🔢 Порядок выполнения

Этап {stage.get('order', stage_num)} в методологии

## 📋 Подэтапы

[Если есть substages - список подэтапов]

## 🛠 Используемые инструменты

[Если есть связанные tools]

## 📊 Измеряемые показатели

[Если есть связанные indicators]

## 💡 Практические рекомендации

[Советы по выполнению этапа]

## ⚠️ Частые ошибки

[Типичные проблемы и как их избежать]

## 🔗 Связанные разделы

- [← Предыдущий этап]
- [→ Следующий этап]

---

Сгенерируй только содержимое документа в markdown формате. Будь конкретным и практичным."""
        
        return self.chat(system_prompt, user_prompt)
    
    def generate_tool_doc(self, tool: Dict[str, Any]) -> str:
        """
        Генерация документации для инструмента.
        
        Содержит:
        - Название и описание
        - Тип инструмента
        - Как использовать
        - Шаблон (если есть)
        - Примеры
        """
        system_prompt = """Ты эксперт по финансовым инструментам и шаблонам.
Твоя задача - создавать четкие инструкции по использованию инструментов.

Требования:
- Пошаговые инструкции
- Примеры использования
- Ссылки на шаблоны
"""
        
        user_prompt = f"""Создай документацию для инструмента/шаблона.

**Данные инструмента:**
{yaml.dump(tool, allow_unicode=True)}

**Требования к документу:**

# {tool.get('title', 'Инструмент')}

## 📝 Описание

{tool.get('description', '')}

## 🏷 Тип инструмента

[{tool.get('type', 'unknown')}]

## 📋 Как использовать

[Пошаговая инструкция]

## 📄 Шаблон

[Если template_available - описать структуру шаблона]

## 💡 Примеры использования

[Конкретные примеры]

## 🔗 Связанные этапы

[Где используется этот инструмент]

---

Сгенерируй только содержимое документа в markdown формате."""
        
        return self.chat(system_prompt, user_prompt)
    
    def generate_indicator_doc(self, indicator: Dict[str, Any]) -> str:
        """
        Генерация документации для показателя.
        
        Содержит:
        - Название и описание
        - Формула расчета
        - Нормативные значения
        - Интерпретация
        - Примеры расчета
        """
        system_prompt = """Ты эксперт по финансовому анализу и показателям.
Твоя задача - создавать четкую документацию для финансовых показателей.

Требования:
- Четкие формулы
- Примеры расчета
- Интерпретация значений
- Связь с glossary
"""
        
        user_prompt = f"""Создай документацию для финансового показателя.

**Данные показателя:**
{yaml.dump(indicator, allow_unicode=True)}

**Требования к документу:**

# {indicator.get('title', 'Показатель')}

## 📝 Описание

{indicator.get('description', '')}

## 🧮 Формула расчета

[Если есть formula - показать формулу в LaTeX или markdown]

## 📊 Нормативные значения

[Если есть criteria - показать диапазоны]

## 💡 Интерпретация

Что означает:
- Высокое значение
- Низкое значение
- Нормальное значение

## 🔗 Связь с глоссарием

[Если есть glossary_refs]

## 📈 Примеры расчета

[Конкретные примеры]

## 🔗 Связанные показатели

[Другие связанные индикаторы]

---

Сгенерируй только содержимое документа в markdown формате."""
        
        return self.chat(system_prompt, user_prompt)
    
    def compile_methodology(
        self,
        outline_path: Path,
        output_dir: Path,
        methodology_id: str
    ) -> Dict[str, Any]:
        """
        Компиляция полной методологии.
        
        Args:
            outline_path: Путь к outline.yaml
            output_dir: Директория для выходных файлов (docs/)
            methodology_id: ID методологии (например, pbu-1-2008)
        
        Returns:
            Статистика генерации
        """
        print(f"\n📚 Компиляция методологии: {methodology_id}")
        print(f"→ Outline: {outline_path}")
        print(f"→ Output: {output_dir}")
        
        # Загрузка outline
        outline = self.load_outline(outline_path)
        structure = outline.get('structure', {})
        
        # Создание структуры директорий
        methodology_dir = output_dir / methodology_id
        stages_dir = methodology_dir / "stages"
        tools_dir = methodology_dir / "tools"
        indicators_dir = methodology_dir / "indicators"
        
        for dir_path in [methodology_dir, stages_dir, tools_dir, indicators_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'generated_files': 0,
            'total_stages': len(structure.get('stages', [])),
            'total_tools': len(structure.get('tools', [])),
            'total_indicators': len(structure.get('indicators', [])),
            'errors': []
        }
        
        # 1. Генерация README.md
        print("\n📝 Генерация README.md...")
        try:
            readme_content = self.generate_readme(outline)
            readme_path = methodology_dir / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print(f"✅ README.md создан")
            stats['generated_files'] += 1
        except Exception as e:
            print(f"❌ Ошибка генерации README: {e}")
            stats['errors'].append(f"README: {e}")
        
        # 2. Генерация документации для этапов
        print(f"\n📋 Генерация документации для {stats['total_stages']} этапов...")
        for i, stage in enumerate(structure.get('stages', []), 1):
            try:
                stage_content = self.generate_stage_doc(stage, i)
                stage_filename = f"stage_{i:02d}_{self._slugify(stage.get('title', ''))}.md"
                stage_path = stages_dir / stage_filename
                
                with open(stage_path, 'w', encoding='utf-8') as f:
                    f.write(stage_content)
                
                print(f"✅ {i}/{stats['total_stages']}: {stage.get('title', '')}")
                stats['generated_files'] += 1
            except Exception as e:
                print(f"❌ Ошибка этапа {i}: {e}")
                stats['errors'].append(f"Stage {i}: {e}")
        
        # 3. Генерация документации для инструментов
        if stats['total_tools'] > 0:
            print(f"\n🛠 Генерация документации для {stats['total_tools']} инструментов...")
            for i, tool in enumerate(structure.get('tools', []), 1):
                try:
                    tool_content = self.generate_tool_doc(tool)
                    tool_filename = f"tool_{i:02d}_{self._slugify(tool.get('title', ''))}.md"
                    tool_path = tools_dir / tool_filename
                    
                    with open(tool_path, 'w', encoding='utf-8') as f:
                        f.write(tool_content)
                    
                    print(f"✅ {i}/{stats['total_tools']}: {tool.get('title', '')}")
                    stats['generated_files'] += 1
                except Exception as e:
                    print(f"❌ Ошибка инструмента {i}: {e}")
                    stats['errors'].append(f"Tool {i}: {e}")
        
        # 4. Генерация документации для показателей
        if stats['total_indicators'] > 0:
            print(f"\n📊 Генерация документации для {stats['total_indicators']} показателей...")
            for i, indicator in enumerate(structure.get('indicators', []), 1):
                try:
                    indicator_content = self.generate_indicator_doc(indicator)
                    indicator_filename = f"indicator_{i:02d}_{self._slugify(indicator.get('title', ''))}.md"
                    indicator_path = indicators_dir / indicator_filename
                    
                    with open(indicator_path, 'w', encoding='utf-8') as f:
                        f.write(indicator_content)
                    
                    print(f"✅ {i}/{stats['total_indicators']}: {indicator.get('title', '')}")
                    stats['generated_files'] += 1
                except Exception as e:
                    print(f"❌ Ошибка показателя {i}: {e}")
                    stats['errors'].append(f"Indicator {i}: {e}")
        
        # 5. Сохранение полного outline в data/
        data_dir = output_dir.parent / "data" / "methodologies"
        data_dir.mkdir(parents=True, exist_ok=True)
        data_path = data_dir / f"{methodology_id}.yaml"
        
        with open(data_path, 'w', encoding='utf-8') as f:
            yaml.dump(outline, f, allow_unicode=True, sort_keys=False)
        
        print(f"\n💾 YAML данные: {data_path}")
        stats['generated_files'] += 1
        
        # Итоги
        print("\n" + "="*60)
        print("✅ КОМПИЛЯЦИЯ ЗАВЕРШЕНА")
        print(f"📁 Создано файлов: {stats['generated_files']}")
        print(f"📋 Этапов: {stats['total_stages']}")
        print(f"🛠 Инструментов: {stats['total_tools']}")
        print(f"📊 Показателей: {stats['total_indicators']}")
        
        if stats['errors']:
            print(f"\n⚠️  Ошибок: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        
        print("="*60)
        
        return stats
    
    def _slugify(self, text: str) -> str:
        """Преобразование текста в slug для имени файла."""
        import re
        # Транслитерация русских букв
        translit = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        text = text.lower()
        result = []
        for char in text:
            if char in translit:
                result.append(translit[char])
            elif char.isalnum() or char == '-':
                result.append(char)
            elif char == ' ':
                result.append('_')
        
        slug = ''.join(result)
        slug = re.sub(r'_+', '_', slug)  # Убрать двойные подчеркивания
        slug = slug.strip('_')
        
        return slug[:50]  # Ограничить длину


def main():
    """Точка входа для тестирования Agent C."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent C: Methodology Compiler")
    parser.add_argument("outline_path", type=str, help="Path to outline.yaml")
    parser.add_argument("--output-dir", type=str, default="docs/methodologies", 
                       help="Output directory for docs")
    parser.add_argument("--methodology-id", type=str, required=True,
                       help="Methodology ID (e.g., accounting-basics)")
    parser.add_argument("--gigachat-key", type=str, 
                       help="GigaChat credentials (or set GIGACHAT_CREDENTIALS env)")
    parser.add_argument("--requesty-key", type=str,
                       help="Requesty AI key (or set REQUESTY_API_KEY env)")
    
    args = parser.parse_args()
    
    # Получение credentials
    gigachat_key = args.gigachat_key or os.getenv('GIGACHAT_CREDENTIALS')
    requesty_key = args.requesty_key or os.getenv('REQUESTY_API_KEY')
    
    if not gigachat_key and not requesty_key:
        print("❌ Error: Нужен хотя бы один ключ (GigaChat или Requesty)")
        print("   Set GIGACHAT_CREDENTIALS or REQUESTY_API_KEY env variable")
        sys.exit(1)
    
    # Создание компилятора
    compiler = MethodologyCompiler(
        gigachat_credentials=gigachat_key,
        requesty_api_key=requesty_key,
        use_gigachat=True
    )
    
    # Компиляция методологии
    outline_path = Path(args.outline_path)
    output_dir = Path(args.output_dir)
    
    stats = compiler.compile_methodology(
        outline_path=outline_path,
        output_dir=output_dir,
        methodology_id=args.methodology_id
    )
    
    # Проверка на ошибки
    if stats['errors']:
        sys.exit(1)


if __name__ == "__main__":
    main()
