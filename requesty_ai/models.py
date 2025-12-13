"""
Доступные модели в Requesty AI

Информация о провайдерах, моделях и их характеристиках
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ModelInfo:
    """Информация о модели"""
    id: str
    provider: str
    name: str
    context_window: int
    cost_per_1m_input: float  # USD
    cost_per_1m_output: float  # USD
    description: str
    best_for: List[str]


# ============================================
# Доступные модели через Requesty AI (РЕАЛЬНЫЕ из dashboard)
# ============================================

AVAILABLE_MODELS = {
    # Alibaba Qwen3-Max - ПРАВИЛЬНО определяет методологию! Отличный русский
    "alibaba/qwen3-max": ModelInfo(
        id="alibaba/qwen3-max",
        provider="Alibaba",
        name="Qwen3-Max",
        context_window=32_000,
        cost_per_1m_input=0.0,  # уточняется
        cost_per_1m_output=0.0,
        description="Мощная модель от Alibaba, правильно определяет diagnostic",
        best_for=["russian", "methodology_classification", "structured_extraction"]
    ),
    
    # DeepSeek - ОЧЕНЬ ДЕШЕВО! Отличное соотношение цена/качество
    "deepseek/deepseek-chat": ModelInfo(
        id="deepseek/deepseek-chat",
        provider="DeepSeek",
        name="DeepSeek Chat",
        context_window=64_000,
        cost_per_1m_input=0.14,  # $0.14 per 1M tokens!
        cost_per_1m_output=0.28,
        description="Очень дешевая и качественная китайская модель",
        best_for=["cost_effective", "reasoning", "coding", "multilingual"]
    ),
    
    # Smart/Task - умная маршрутизация
    "smart/task": ModelInfo(
        id="smart/task",
        provider="Smart",
        name="Smart Task Router",
        context_window=128_000,
        cost_per_1m_input=0.10,  # Очень дешево благодаря routing
        cost_per_1m_output=0.30,
        description="Автоматический выбор оптимальной модели для задачи",
        best_for=["auto_routing", "cost_effective", "versatile"]
    ),
    
    # OpenAI models
    "openai/gpt-4o": ModelInfo(
        id="openai/gpt-4o",
        provider="OpenAI",
        name="GPT-4o",
        context_window=128_000,
        cost_per_1m_input=2.50,
        cost_per_1m_output=10.00,
        description="Самая мощная модель OpenAI",
        best_for=["reasoning", "complex_tasks", "coding", "multilingual"]
    ),
    
    "openai/gpt-5-mini": ModelInfo(
        id="openai/gpt-5-mini",
        provider="OpenAI",
        name="GPT-5 Mini",
        context_window=128_000,
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        description="Быстрая и дешевая модель OpenAI",
        best_for=["simple_tasks", "fast_responses", "cost_effective"]
    ),
    
    # Google Gemini models
    "google/gemini-2.5-flash": ModelInfo(
        id="google/gemini-2.5-flash",
        provider="Google",
        name="Gemini 2.5 Flash",
        context_window=1_000_000,
        cost_per_1m_input=0.075,
        cost_per_1m_output=0.30,
        description="Очень дешевая модель с огромным контекстом",
        best_for=["cost_effective", "long_documents", "fast_responses"]
    ),
    
    "google/gemini-2.5-pro": ModelInfo(
        id="google/gemini-2.5-pro",
        provider="Google",
        name="Gemini 2.5 Pro",
        context_window=2_000_000,
        cost_per_1m_input=1.25,
        cost_per_1m_output=5.00,
        description="Огромный context window для длинных документов",
        best_for=["long_documents", "video", "multimodal"]
    ),
    
    # Coding специализированные (ВАЖНО: у нас работает coding/, но НЕ google/)
    "coding/gemini-2.5-pro": ModelInfo(
        id="coding/gemini-2.5-pro",
        provider="Coding",
        name="Gemini 2.5 Pro (Coding)",
        context_window=2_000_000,  # 2M tokens!
        cost_per_1m_input=1.25,
        cost_per_1m_output=5.00,
        description="Gemini с 2M context, оптимизированный для кода и длинных документов",
        best_for=["coding", "long_documents", "debugging", "code_generation"]
    ),
    
    # XAI Grok
    "xai/grok-code-fast-1": ModelInfo(
        id="xai/grok-code-fast-1",
        provider="XAI",
        name="Grok Code Fast 1",
        context_window=128_000,
        cost_per_1m_input=0.50,
        cost_per_1m_output=1.50,
        description="Быстрая модель для кода от XAI",
        best_for=["coding", "fast_responses", "technical_writing"]
    ),
}


# ============================================
# Рекомендации для нашего проекта (ФИНАЛЬНАЯ СТРАТЕГИЯ: GigaChat + Qwen3-Max)
# ============================================

RECOMMENDED_MODELS = {
    "agent_b_outline": [
        "gigachat",  # 🥇 PRIMARY: бесплатно, быстро (1.06s), правильно определяет diagnostic
        "alibaba/qwen3-max",  # 🥈 FALLBACK: правильно определяет diagnostic, русские ключи
        "deepseek/deepseek-chat",  # 🥉 Альтернатива: дешево, но медленнее (4.31s)
    ],
    
    "agent_b_complex": [
        "gigachat",  # 🥇 PRIMARY: отлично для русских методологий
        "alibaba/qwen3-max",  # 🥈 FALLBACK: мощная универсальная модель
        "openai/gpt-4o",  # 🥉 Только если критично и GigaChat/Qwen не справились
    ],
    
    "agent_c_compiler": [
        "gigachat-lite",  # 🥇 PRIMARY: бесплатно, быстро для шаблонов
        "alibaba/qwen3-max",  # 🥈 FALLBACK: универсальная замена
        "deepseek/deepseek-chat",  # 🥉 Альтернатива: дешево
    ],
    
    "agent_d_qa": [
        "gigachat-pro",  # 🥇 PRIMARY: бесплатно, хороший reasoning
        "alibaba/qwen3-max",  # 🥈 FALLBACK: надежная замена
        "claude-3.5-sonnet",  # 🥉 PREMIUM: только для критичных книг (ПБУ, МСФО)
    ],
    
    "long_documents": [
        "coding/gemini-2.5-pro",  # 🏆 2M tokens context! (работает)
        "google/gemini-2.5-flash",  # 1M tokens context, очень дешево
    ],
    
    "full_books": [
        "coding/gemini-2.5-pro",  # Можно загрузить целую книгу целиком!
    ],
}


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Получить информацию о модели"""
    return AVAILABLE_MODELS.get(model_id)


def list_models(provider: Optional[str] = None) -> List[ModelInfo]:
    """
    Список всех моделей (опционально фильтр по провайдеру)
    
    Args:
        provider: Фильтр по провайдеру (OpenAI, Anthropic, Google)
        
    Returns:
        Список моделей
    """
    models = list(AVAILABLE_MODELS.values())
    
    if provider:
        models = [m for m in models if m.provider.lower() == provider.lower()]
    
    return models


def estimate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int
) -> Optional[float]:
    """
    Оценить стоимость запроса
    
    Args:
        model_id: ID модели
        input_tokens: Количество input токенов
        output_tokens: Количество output токенов
        
    Returns:
        Стоимость в USD
    """
    model = get_model_info(model_id)
    
    if not model:
        return None
    
    cost_input = (input_tokens / 1_000_000) * model.cost_per_1m_input
    cost_output = (output_tokens / 1_000_000) * model.cost_per_1m_output
    
    return cost_input + cost_output


if __name__ == "__main__":
    # Тест
    print("📊 Available Models:\n")
    
    for model_id, model in AVAILABLE_MODELS.items():
        print(f"🤖 {model.name} ({model.provider})")
        print(f"   ID: {model.id}")
        print(f"   Context: {model.context_window:,} tokens")
        print(f"   Cost: ${model.cost_per_1m_input:.2f}/${model.cost_per_1m_output:.2f} per 1M tokens")
        print(f"   Best for: {', '.join(model.best_for)}")
        print()
    
    # Пример оценки стоимости
    print("💰 Cost Estimation Example:")
    cost = estimate_cost("openai/gpt-4o-mini", input_tokens=10_000, output_tokens=5_000)
    print(f"   10K input + 5K output tokens = ${cost:.4f}")
    
    print("\n🎯 Recommended Models for Agent B:")
    for model_id in RECOMMENDED_MODELS["agent_b_outline"]:
        model = get_model_info(model_id)
        print(f"   - {model.name} ({model.provider})")
