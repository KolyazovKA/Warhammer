import requests
from ..config import DEEPSEEK_KEY

def ask_deepseek(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты отвечаешь только на основе предоставленного контекста."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
