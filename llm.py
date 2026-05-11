"""
LLM integration via Mistral API — deduplication and notification formatting.
"""
import re
import requests

from scrapers import Article
from categories import categorizar, SKIP_NOTIFY

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

_DEDUP_PROMPT = """\
Estas son noticias de medios chilenos. Identifica grupos que cubran el mismo hecho \
y conserva solo la mejor versión de cada grupo (la más completa o informativa).

{numbered}

Responde ÚNICAMENTE con los índices de los artículos a conservar, separados por comas.
Ejemplo: 0, 2, 5, 7, 12\
"""

_NOTIFY_PROMPT = """\
Eres editor de un resumen noticioso chileno. Estas son las noticias del día:

{headlines}

Tarea:
1. Selecciona las 5-7 más importantes e interesantes (descarta triviales, repetidas o de bajo impacto).
2. Escribe el resumen como texto plano para una notificación push.
3. Agrupa por categoría con el formato: "── Categoría ──" seguido de los titulares con "•".
4. Máximo 700 caracteres en total.
5. Sin emojis, sin markdown, solo texto plano.\
"""


def deduplicate_articles(articles: list[Article], api_key: str, model: str = "mistral-small-latest") -> list[Article]:
    """
    Sends all scraped articles to Mistral and returns the deduplicated subset.
    The LLM picks the best article from each group of duplicates.
    Falls back to the original list if the call fails or parsing fails.
    """
    if len(articles) < 2:
        return articles

    numbered = "\n".join(
        f"{i}. [{a.source}] {a.title}" + (f" — {a.summary[:80]}" if a.summary else "")
        for i, a in enumerate(articles)
    )

    try:
        resp = requests.post(
            _MISTRAL_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": _DEDUP_PROMPT.format(numbered=numbered)}],
                "max_tokens": 300,
                "temperature": 0.0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        indices = [int(n) for n in re.findall(r"\d+", content) if int(n) < len(articles)]
        if not indices:
            print("LLM dedup: no se pudieron parsear índices, sin deduplicar")
            return articles
        return [articles[i] for i in indices]
    except Exception as e:
        print(f"LLM dedup error, sin deduplicar: {e}")
        return articles


def curate_notification(articles: list[Article], api_key: str, model: str = "mistral-small-latest") -> str | None:
    """
    Asks Mistral to pick the most relevant articles and format them as a
    push notification body. Returns None on failure so the caller can fall back.
    """
    filtered = [a for a in articles if categorizar(a.title) not in SKIP_NOTIFY]
    if not filtered:
        return None

    headlines = "\n".join(
        f"[{categorizar(a.title)}] {a.title}" + (f" — {a.summary}" if a.summary else "")
        for a in filtered
    )

    try:
        resp = requests.post(
            _MISTRAL_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": _NOTIFY_PROMPT.format(headlines=headlines)}],
                "max_tokens": 350,
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM notify error, usando formato estándar: {e}")
        return None
