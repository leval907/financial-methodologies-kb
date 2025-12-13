#!/usr/bin/env python3
"""
Workflow Pipeline для работы с книгами из S3
Извлекает содержимое книг и создает методики по шаблону
"""

import os
import sys
from pathlib import Path
import boto3
from botocore.config import Config

# S3 Configuration
ENDPOINT_URL = 'https://s3.ru1.storage.beget.cloud'
BUCKET_NAME = 'db6a1f644d97-la-ducem1'
S3_PREFIX = 'Financial Methodologies_kb/books/'

class MethodologyPipeline:
    """Pipeline для создания методик из книг в S3"""
    
    def __init__(self):
        """Инициализация клиента S3"""
        self.s3 = boto3.client(
            's3',
            endpoint_url=ENDPOINT_URL,
            region_name='ru1',
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = BUCKET_NAME
        self.s3_prefix = S3_PREFIX
        self.local_cache = Path('cache/books')
        self.local_cache.mkdir(parents=True, exist_ok=True)
        
        print(f"🔗 Pipeline initialized")
        print(f"📦 Bucket: {self.bucket_name}")
        print(f"📂 S3 Prefix: {self.s3_prefix}")
        print(f"💾 Local cache: {self.local_cache}")
    
    def list_books(self) -> list:
        """
        Получить список всех книг в S3
        
        Returns:
            list: Список ключей объектов
        """
        try:
            print(f"\n📚 Fetching book list from S3...")
            
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.s3_prefix
            )
            
            if 'Contents' not in response:
                print(f"📭 No books found in {self.s3_prefix}")
                return []
            
            books = []
            for obj in response['Contents']:
                key = obj['Key']
                # Пропускаем папки
                if key.endswith('/'):
                    continue
                
                size_mb = obj['Size'] / (1024 * 1024)
                books.append({
                    'key': key,
                    'name': Path(key).name,
                    'size_mb': size_mb,
                    'modified': obj['LastModified']
                })
                print(f"   📄 {Path(key).name} ({size_mb:.2f} MB)")
            
            print(f"\n✅ Found {len(books)} books")
            return books
            
        except Exception as e:
            print(f"❌ Error listing books: {e}")
            return []
    
    def download_book(self, s3_key: str, local_path: str = None) -> Path:
        """
        Скачать книгу из S3 в локальный кеш
        
        Args:
            s3_key: Ключ объекта в S3
            local_path: Путь для сохранения (если None, использует cache/)
        
        Returns:
            Path: Путь к скачанному файлу
        """
        if local_path is None:
            filename = Path(s3_key).name
            local_path = self.local_cache / filename
        else:
            local_path = Path(local_path)
        
        # Проверяем, есть ли уже файл
        if local_path.exists():
            print(f"✓ File already cached: {local_path.name}")
            return local_path
        
        try:
            print(f"⬇️  Downloading {Path(s3_key).name}...")
            
            # Создаем родительские директории
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            self.s3.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            
            size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded: {local_path.name} ({size_mb:.2f} MB)")
            return local_path
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    def extract_book_info(self, book_path: Path) -> dict:
        """
        Извлечь базовую информацию о книге
        
        Args:
            book_path: Путь к файлу книги
        
        Returns:
            dict: Информация о книге
        """
        info = {
            'filename': book_path.name,
            'extension': book_path.suffix.lower(),
            'size_mb': book_path.stat().st_size / (1024 * 1024),
            'methodology_type': self._detect_methodology_type(book_path.name)
        }
        
        print(f"\n📖 Book info:")
        print(f"   Name: {info['filename']}")
        print(f"   Type: {info['methodology_type']}")
        print(f"   Format: {info['extension']}")
        print(f"   Size: {info['size_mb']:.2f} MB")
        
        return info
    
    def _detect_methodology_type(self, filename: str) -> str:
        """Определить тип методики по имени файла"""
        filename_lower = filename.lower()
        
        if 'simple' in filename_lower or 'numbers' in filename_lower:
            return 'Simple Numbers'
        elif 'тос' in filename_lower or 'corbett' in filename_lower or 'корбет' in filename_lower:
            return 'Theory of Constraints (TOC)'
        elif 'power' in filename_lower or 'сила' in filename_lower or 'одного' in filename_lower:
            return 'Power of One'
        elif 'стоимость' in filename_lower or 'valuation' in filename_lower or 'коуленд' in filename_lower:
            return 'Company Valuation'
        elif 'метрик' in filename_lower or 'metrics' in filename_lower:
            return 'Business Metrics'
        elif 'бухгалтерия' in filename_lower:
            return 'Accounting Fundamentals'
        else:
            return 'Unknown'
    
    def create_methodology_stub(self, book_info: dict) -> Path:
        """
        Создать заготовку методики по шаблону
        
        Args:
            book_info: Информация о книге
        
        Returns:
            Path: Путь к созданной методике
        """
        methodology_type = book_info['methodology_type']
        
        # Определяем ID методики
        methodology_id = methodology_type.lower().replace(' ', '-').replace('(', '').replace(')', '')
        
        # Создаем директорию для методики
        methodology_dir = Path('docs/methodologies') / methodology_id
        methodology_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь к файлу
        methodology_file = methodology_dir / 'README.md'
        
        if methodology_file.exists():
            print(f"✓ Methodology already exists: {methodology_file}")
            return methodology_file
        
        # Читаем шаблон
        template_path = Path('templates/README.md')
        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return None
        
        # Создаем методику из шаблона
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Заменяем плейсхолдеры
        content = template.replace('[Название методики]', methodology_type)
        content = content.replace('[methodology-id]', methodology_id)
        
        # Добавляем информацию об источнике
        source_section = f"""
## Источник

**Книга**: {book_info['filename']}
**Размер**: {book_info['size_mb']:.2f} MB
**Формат**: {book_info['extension']}

**Статус**: Методика в процессе формализации из книги.
"""
        
        # Вставляем информацию об источнике перед разделом "Описание"
        content = content.replace('## Описание', source_section + '\n## Описание')
        
        # Сохраняем файл
        with open(methodology_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Created methodology stub: {methodology_file}")
        return methodology_file
    
    def process_book(self, book: dict) -> dict:
        """
        Полный цикл обработки книги
        
        Args:
            book: Информация о книге из list_books()
        
        Returns:
            dict: Результат обработки
        """
        print(f"\n{'='*60}")
        print(f"📖 Processing: {book['name']}")
        print(f"{'='*60}")
        
        result = {
            'book': book['name'],
            'success': False,
            'steps': []
        }
        
        # Шаг 1: Скачать книгу
        local_path = self.download_book(book['key'])
        if not local_path:
            result['error'] = 'Download failed'
            return result
        result['steps'].append('downloaded')
        
        # Шаг 2: Извлечь информацию
        book_info = self.extract_book_info(local_path)
        result['steps'].append('info_extracted')
        result['methodology_type'] = book_info['methodology_type']
        
        # Шаг 3: Создать заготовку методики
        methodology_file = self.create_methodology_stub(book_info)
        if methodology_file:
            result['steps'].append('methodology_created')
            result['methodology_file'] = str(methodology_file)
            result['success'] = True
        
        return result
    
    def process_all_books(self) -> list:
        """
        Обработать все книги в S3
        
        Returns:
            list: Результаты обработки всех книг
        """
        books = self.list_books()
        
        if not books:
            print("❌ No books to process")
            return []
        
        results = []
        
        print(f"\n🚀 Starting pipeline for {len(books)} books...\n")
        
        for book in books:
            result = self.process_book(book)
            results.append(result)
        
        # Итоговая статистика
        print(f"\n{'='*60}")
        print(f"📊 Pipeline Summary")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if r['success'])
        print(f"✅ Successful: {successful}/{len(results)}")
        
        print(f"\n📋 Created methodologies:")
        for result in results:
            if result['success']:
                print(f"   ✓ {result['methodology_type']}: {result['methodology_file']}")
        
        return results


def main():
    """CLI интерфейс"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 workflow_pipeline.py list")
        print("  python3 workflow_pipeline.py process-all")
        print("  python3 workflow_pipeline.py process <book_name>")
        sys.exit(1)
    
    command = sys.argv[1]
    pipeline = MethodologyPipeline()
    
    if command == 'list':
        pipeline.list_books()
    
    elif command == 'process-all':
        pipeline.process_all_books()
    
    elif command == 'process' and len(sys.argv) > 2:
        book_name = sys.argv[2]
        books = pipeline.list_books()
        book = next((b for b in books if book_name in b['name']), None)
        
        if book:
            pipeline.process_book(book)
        else:
            print(f"❌ Book not found: {book_name}")
            print(f"Available books:")
            for b in books:
                print(f"   - {b['name']}")
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
