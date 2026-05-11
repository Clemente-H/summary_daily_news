"""
LLM integration via Mistral API — deduplication and notification formatting.
"""
import re
import requests

from scrapers import Article
from categories import categorizar, SKIP_NOTIFY

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
_DEFAULT_MODEL = "mistral-large-latest"

_DEDUP_PROMPT = """\
Elimina duplicados de esta lista de noticias chilenas.

DUPLICADO = dos artículos que reportan EL MISMO HECHO CONCRETO
(mismo evento, misma jornada, mismos protagonistas).

Ejemplo de DUPLICADO real:
  "Crucero con hantavirus llega a Punta Arenas" (La Tercera)
  "Pasajeros del MV Hondius vuelan a casa tras brote" (El Mercurio)
  → mismo evento, quédate con el título más informativo

Ejemplos de NO DUPLICADO:
  Dos artículos sobre la megarreforma desde ángulos distintos → NO son duplicados
  Dos columnas de opinión sobre el mismo tema → NUNCA son duplicados

REGLA DE ORO: si hay duda, conserva AMBOS.

{numbered}

Responde ÚNICAMENTE con los índices a conservar, separados por comas.\
"""

_NOTIFY_PROMPT = """\
Formatea estas noticias chilenas para una notificación push.

FORMATO:
- Agrupa por categoría: "── Categoría ──" y bullets "•"
- Orden: Política, Economía, Mundo, Deportes, Ciencia, Tecnología, General
- No incluyas categorías vacías

TÍTULOS — acorta solo si tienen:
- Citas textuales largas dentro del título → recorta la cita, conserva el hecho
- Frases de relleno ("según dijo", "en declaraciones a", "tal como informó")
- NUNCA elimines: nombres, números, lugares, quién hizo qué a quién

ELIMINA solo estos tipos de artículo:
- Columnas de opinión sin noticia concreta (título vago sin hechos, ej: "Vida en otros planetas")
- Consejos/lifestyle ("X formas de...", "¿Cómo...?", "Por qué es importante...")
- Farándula que se haya colado

RECATEGORIZA si es obvio (ej: noticia de Perú en General → muévela a Mundo)

Todo lo demás: inclúyelo sin filtrar por importancia.
Sin emojis, sin markdown, solo texto plano.

{headlines}\
"""


def deduplicate_articles(articles: list[Article], api_key: str, model: str = _DEFAULT_MODEL) -> list[Article]:
    """
    Sends all scraped articles to Mistral and returns the deduplicated subset.
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


def curate_notification(articles: list[Article], api_key: str, model: str = _DEFAULT_MODEL) -> str | None:
    """
    Asks Mistral to format articles as a push notification body.
    Returns None on failure so the caller can fall back to default formatting.
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
                "max_tokens": 1024,
                "temperature": 0.2,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"LLM notify error, usando formato estándar: {e}")
        return None
