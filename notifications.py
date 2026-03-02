"""
Canales de notificación. Por ahora: ntfy.sh
"""
from datetime import date

import requests

from scrapers import Article


def notify_ntfy(topic: str, articles: list[Article]) -> None:
    """
    Envía un resumen push via ntfy.sh.
    En el teléfono: instalar app ntfy y suscribirse al mismo topic.
    """
    headlines = "\n".join(f"• {a.title[:80]}" for a in articles[:5])
    body = f"{len(articles)} noticias hoy\n\n{headlines}"

    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=body.encode("utf-8"),
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
