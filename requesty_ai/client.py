"""
Requesty AI Client с полной обработкой ошибок и retry логикой

Основано на рекомендациях из inputs/agent_1_2.md (строки 640+)
"""

import os
import openai
from dotenv import load_dotenv
import time
from typing import Optional, List, Dict, Iterator
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Загружаем переменные окружения
load_dotenv()


class RequestyClient:
    """
    Клиент для работы с Requesty AI Gateway
    
    Features:
    - Автоматический retry с exponential backoff
    - Обработка всех типов ошибок (rate limits, timeouts, connection)
    - Поддержка streaming
    - Мониторинг использования
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://router.requesty.ai/v1",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Args:
            api_key: Requesty API key (если None, загружает из REQUESTY_API_KEY)
            base_url: Базовый URL Requesty API
            timeout: Таймаут запроса в секундах
            max_retries: Максимум попыток при ошибках
        """
        self.api_key = api_key or os.getenv("REQUESTY_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "❌ REQUESTY_API_KEY not found. "
                "Set it in .env file or pass to constructor."
            )
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Инициализация OpenAI клиента
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers={
                "HTTP-Referer": os.getenv("SITE_URL", "https://example.com"),
                "X-Title": os.getenv("SITE_NAME", "My AI App"),
            }
        )
        
        logger.info(f"✅ RequestyClient initialized (base_url={base_url})")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Отправка chat completion запроса с retry логикой
        
        Args:
            messages: Список сообщений [{role, content}, ...]
            model: ID модели в формате provider/model
            temperature: Temperature для генерации (0-2)
            max_tokens: Максимум токенов в ответе
            **kwargs: Дополнительные параметры для API
            
        Returns:
            Текст ответа или None при ошибке
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔄 Attempt {attempt}/{self.max_retries} (model={model})")
                
                # Запрос к API
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Проверка наличия ответа
                if not response.choices:
                    raise ValueError("❌ API returned empty response")
                
                # Извлечение контента
                content = response.choices[0].message.content
                
                if not content or content.strip() == "":
                    raise ValueError("❌ API returned empty content")
                
                # Успешный результат
                logger.info(f"✅ Success on attempt {attempt}")
                
                # Логирование использования
                if hasattr(response, 'usage'):
                    logger.info(
                        f"📊 Tokens used: "
                        f"prompt={response.usage.prompt_tokens}, "
                        f"completion={response.usage.completion_tokens}, "
                        f"total={response.usage.total_tokens}"
                    )
                
                return content
            
            # Специфичные ошибки OpenAI API
            except openai.AuthenticationError as e:
                logger.error(f"❌ Authentication Error: {e}")
                logger.error("   Check your REQUESTY_API_KEY")
                return None  # Не ретраим, ключ неверный
            
            except openai.RateLimitError as e:
                logger.warning(f"⚠️ Rate Limit Error: {e}")
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 сек
                    logger.info(f"   Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error("   Max retries reached")
                    return None
            
            except openai.APITimeoutError as e:
                logger.warning(f"⏱️ Timeout Error: {e}")
                if attempt < self.max_retries:
                    logger.info(f"   Retrying (attempt {attempt + 1})...")
                else:
                    logger.error("   Max retries reached")
                    return None
            
            except openai.APIConnectionError as e:
                logger.warning(f"🌐 Connection Error: {e}")
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"   Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error("   Max retries reached")
                    return None
            
            except openai.APIError as e:
                logger.warning(f"⚠️ API Error: {e}")
                if attempt < self.max_retries:
                    logger.info(f"   Retrying (attempt {attempt + 1})...")
                else:
                    logger.error("   Max retries reached")
                    return None
            
            # Общие ошибки
            except ValueError as e:
                logger.error(f"❌ Validation Error: {e}")
                return None  # Не ретраим валидационные ошибки
            
            except Exception as e:
                logger.error(f"❌ Unexpected Error: {type(e).__name__}: {e}")
                if attempt < self.max_retries:
                    logger.info(f"   Retrying (attempt {attempt + 1})...")
                else:
                    logger.error("   Max retries reached")
                    return None
        
        return None  # Все попытки исчерпаны
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Streaming chat completion (для real-time вывода)
        
        Args:
            messages: Список сообщений
            model: ID модели
            temperature: Temperature
            max_tokens: Максимум токенов
            **kwargs: Дополнительные параметры
            
        Yields:
            Части ответа по мере генерации
        """
        try:
            logger.info(f"🔄 Starting stream (model={model})")
            
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("✅ Stream completed")
        
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield f"\n\n❌ Error: {e}"


# ============================================
# Convenience функции
# ============================================

def chat_with_retry(
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-4o-mini",
    max_retries: int = 3,
    timeout: int = 60,
    **kwargs
) -> Optional[str]:
    """
    Удобная функция для одиночных запросов
    
    Args:
        messages: Список сообщений
        model: ID модели
        max_retries: Максимум попыток
        timeout: Таймаут
        **kwargs: Дополнительные параметры
        
    Returns:
        Ответ или None
    """
    client = RequestyClient(max_retries=max_retries, timeout=timeout)
    return client.chat(messages, model=model, **kwargs)


def chat_with_streaming(
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-4o-mini",
    **kwargs
) -> str:
    """
    Streaming с выводом в консоль
    
    Args:
        messages: Список сообщений
        model: ID модели
        **kwargs: Дополнительные параметры
        
    Returns:
        Полный ответ
    """
    client = RequestyClient()
    full_response = ""
    
    for chunk in client.chat_stream(messages, model=model, **kwargs):
        print(chunk, end="", flush=True)
        full_response += chunk
    
    print()  # Новая строка
    return full_response


if __name__ == "__main__":
    # Тест
    print("🧪 Testing Requesty AI Client\n")
    
    messages = [
        {"role": "system", "content": "Ты эксперт по финансам."},
        {"role": "user", "content": "Что такое ОСВ в бухгалтерии? Ответь кратко."}
    ]
    
    # Обычный запрос
    print("📝 Regular chat:")
    response = chat_with_retry(messages, model="openai/gpt-4o-mini")
    
    if response:
        print(f"\n✅ Response:\n{response}\n")
    else:
        print("\n❌ Failed to get response\n")
    
    # Streaming
    print("📝 Streaming chat:")
    full_response = chat_with_streaming(messages, model="openai/gpt-4o-mini")
    print(f"\n✅ Full response received ({len(full_response)} chars)\n")
