import os
import requests

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


def generate_test_cases(prompt):

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json"
    }

    payload = {

        "model": 
            "openai/gpt-oss-120b:free",
            # "deepseek/deepseek-v4-flash:free",

        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 16000,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["choices"][0]
        ["message"]["content"]
    )