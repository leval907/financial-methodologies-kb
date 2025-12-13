"""
Проверка доступных моделей в Requesty AI
"""

import os
from dotenv import load_dotenv
import openai

load_dotenv()

api_key = os.getenv("REQUESTY_API_KEY")

if not api_key:
    print("❌ REQUESTY_API_KEY not found in .env")
    exit(1)

client = openai.OpenAI(
    api_key=api_key,
    base_url="https://router.requesty.ai/v1"
)

print("🔍 Testing Requesty AI connection...\n")

# Попробуем доступные модели из вашего Requesty dashboard
test_models = [
    # DeepSeek (очень дешево!)
    "deepseek/deepseek-chat",
    
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-5-mini",  # или gpt-4o-mini?
    
    # Google Gemini
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    
    # Coding специализированные
    "coding/gemini-2.5-pro",
    
    # XAI
    "xai/grok-code-fast-1",
    
    # Smart task
    "smart/task",
]

messages = [{"role": "user", "content": "Hi"}]

for model in test_models:
    try:
        print(f"Testing {model}...", end=" ")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=5
        )
        print(f"✅ Works! Response: {response.choices[0].message.content[:50]}")
    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}")

print("\n💡 Tip: Check your Requesty AI dashboard to enable providers:")
print("   https://requesty.ai/dashboard")
