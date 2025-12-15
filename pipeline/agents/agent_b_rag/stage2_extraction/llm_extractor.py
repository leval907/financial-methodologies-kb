"""
LLM-based extraction from retrieved chunks
"""
import httpx
from typing import List, Dict
import json
from pathlib import Path

class LLMExtractor:
    """
    Extract structured methodology data using LLM
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = 'alibaba/qwen3-max',
        temperature: float = 0.3
    ):
        """
        Args:
            api_key: Requesty AI API key
            model: LLM model name
            temperature: Sampling temperature
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = 'https://router.requesty.ai/v1/chat/completions'
    
    def extract_from_chunks(
        self,
        chunks: List[Dict],
        category: str,
        prompt_template: str
    ) -> List[Dict]:
        """
        Extract structured data from chunks using LLM
        
        Args:
            chunks: Retrieved chunks from RAG search
            category: Category type ('stages', 'tools', 'indicators', 'rules')
            prompt_template: Prompt template for extraction
        
        Returns:
            List of extracted entities
        """
        # Combine chunks into context
        context = self._prepare_context(chunks)
        
        # Format prompt
        prompt = prompt_template.replace('{context}', context)
        prompt = prompt.replace('{category}', category)
        
        # Call LLM
        try:
            response = httpx.post(
                self.base_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'Вы эксперт по извлечению структурированной информации из текстов по управленческим методологиям.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': self.temperature,
                    'max_tokens': 4000
                },
                timeout=120.0
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON response
            entities = self._parse_response(content)
            
            # Add source metadata
            for entity in entities:
                entity['source_chunks'] = [c['id'] for c in chunks]
                entity['category'] = category
            
            return entities
            
        except Exception as e:
            print(f'Error extracting {category}: {e}')
            return []
    
    def _prepare_context(self, chunks: List[Dict], max_tokens: int = 8000) -> str:
        """
        Prepare context from chunks with token limit
        
        Args:
            chunks: List of chunks
            max_tokens: Maximum context length in tokens (approximate)
        
        Returns:
            Formatted context string
        """
        context_parts = []
        total_words = 0
        
        for chunk in chunks:
            text = chunk['text']
            page = chunk['page']
            score = chunk.get('score', 0.0)
            
            chunk_text = f"[Страница {page}, релевантность: {score:.2f}]\n{text}\n"
            chunk_words = len(chunk_text.split())
            
            if total_words + chunk_words > max_tokens:
                break
            
            context_parts.append(chunk_text)
            total_words += chunk_words
        
        return '\n---\n'.join(context_parts)
    
    def _parse_response(self, content: str) -> List[Dict]:
        """
        Parse LLM response into structured format
        
        Args:
            content: LLM response text
        
        Returns:
            List of extracted entities
        """
        try:
            # Try to extract JSON from markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Try common keys
                for key in ['items', 'entities', 'results', 'data']:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # If dict has structure, wrap in list
                if any(k in data for k in ['name', 'title', 'id']):
                    return [data]
            
            return []
            
        except json.JSONDecodeError as e:
            print(f'JSON parsing error: {e}')
            print(f'Content: {content[:500]}...')
            return []
