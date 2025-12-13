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

# Попробуем разные модели
test_models = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-3-5-haiku-20241022",
    "google/gemini-1.5-flash",
    "gpt-4o-mini",  # без префикса
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
