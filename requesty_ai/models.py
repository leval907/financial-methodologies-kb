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
# Доступные модели через Requesty AI
# ============================================

AVAILABLE_MODELS = {
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
    
    "openai/gpt-4o-mini": ModelInfo(
        id="openai/gpt-4o-mini",
        provider="OpenAI",
        name="GPT-4o Mini",
        context_window=128_000,
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        description="Быстрая и дешевая модель для простых задач",
        best_for=["simple_tasks", "fast_responses", "cost_effective"]
    ),
    
    "openai/o1-mini": ModelInfo(
        id="openai/o1-mini",
        provider="OpenAI",
        name="O1 Mini",
        context_window=128_000,
        cost_per_1m_input=3.00,
        cost_per_1m_output=12.00,
        description="Reasoning модель с CoT",
        best_for=["complex_reasoning", "math", "logic"]
    ),
    
    # Anthropic models
    "anthropic/claude-3-5-sonnet-20241022": ModelInfo(
        id="anthropic/claude-3-5-sonnet-20241022",
        provider="Anthropic",
        name="Claude 3.5 Sonnet",
        context_window=200_000,
        cost_per_1m_input=3.00,
        cost_per_1m_output=15.00,
        description="Лучший reasoning среди всех моделей",
        best_for=["reasoning", "analysis", "long_context", "coding"]
    ),
    
    "anthropic/claude-3-5-haiku-20241022": ModelInfo(
        id="anthropic/claude-3-5-haiku-20241022",
        provider="Anthropic",
        name="Claude 3.5 Haiku",
        context_window=200_000,
        cost_per_1m_input=0.80,
        cost_per_1m_output=4.00,
        description="Быстрая модель Anthropic",
        best_for=["fast_responses", "simple_tasks", "cost_effective"]
    ),
    
    # Google models
    "google/gemini-1.5-pro": ModelInfo(
        id="google/gemini-1.5-pro",
        provider="Google",
        name="Gemini 1.5 Pro",
        context_window=2_000_000,  # 2M tokens!
        cost_per_1m_input=1.25,
        cost_per_1m_output=5.00,
        description="Огромный context window для длинных документов",
        best_for=["long_documents", "video", "multimodal"]
    ),
    
    "google/gemini-1.5-flash": ModelInfo(
        id="google/gemini-1.5-flash",
        provider="Google",
        name="Gemini 1.5 Flash",
        context_window=1_000_000,
        cost_per_1m_input=0.075,
        cost_per_1m_output=0.30,
        description="Очень дешевая модель с большим контекстом",
        best_for=["cost_effective", "long_documents", "fast_responses"]
    ),
}


# ============================================
# Рекомендации для нашего проекта
# ============================================

RECOMMENDED_MODELS = {
    "agent_b_outline": [
        "openai/gpt-4o-mini",  # Основная: дешево, качественно для русского
        "anthropic/claude-3-5-haiku-20241022",  # Fallback: быстро
        "google/gemini-1.5-flash",  # Backup: очень дешево
    ],
    
    "agent_b_complex": [
        "openai/gpt-4o",  # Основная: сложные методологии
        "anthropic/claude-3-5-sonnet-20241022",  # Fallback: лучший reasoning
    ],
    
    "agent_c_compiler": [
        "openai/gpt-4o-mini",  # Основная: шаблоны
        "google/gemini-1.5-flash",  # Fallback: дешево
    ],
    
    "agent_d_qa": [
        "anthropic/claude-3-5-sonnet-20241022",  # Основная: лучший для анализа
        "openai/gpt-4o",  # Fallback: тоже хорош
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
