"""
Canales de notificación. Por ahora: ntfy.sh
"""
from datetime import date

import requests

from scrapers import Article
from categories import categorizar, ORDEN


def notify_ntfy(topic: str, articles: list[Article]) -> None:
    """
    Envía un resumen push via ntfy.sh.
    En el teléfono: instalar app ntfy y suscribirse al mismo topic.
    """
    # Agrupar por categoría
    by_cat: dict[str, list[Article]] = {}
    for a in articles:
        by_cat.setdefault(categorizar(a.title), []).append(a)

    cats_ordenadas = sorted(by_cat.keys(), key=lambda c: ORDEN.index(c) if c in ORDEN else 99)

    sections = []
    for cat in cats_ordenadas:
        lines = [f"── {cat} ──"]
        lines += [f"• {a.title}" for a in by_cat[cat]]
        sections.append("\n".join(lines))

    body = f"{len(articles)} noticias · {date.today().strftime('%d/%m')}\n\n" + "\n\n".join(sections)

    # ntfy tiene límite de 4096 bytes
    body = body.encode("utf-8")[:4096].decode("utf-8", errors="ignore")

    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=body.encode("utf-8") if isinstance(body, str) else body,
            headers={
                "Title": f"DailyNews · {date.today().strftime('%d/%m')}",
                "Priority": "default",
                "Tags": "newspaper",
            },
            timeout=10,
        )
        print(f"Notificación enviada a ntfy.sh/{topic}")
    except Exception as e:
        print(f"Error notificación: {e}")
