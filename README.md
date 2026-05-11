# DailyNews

Resumen diario de portadas chilenas. Scraping de The Clinic, La Tercera y El Mercurio Digital, con deduplicación y formateo via LLM (Mistral) y notificación push via ntfy.sh.

## Cómo funciona

```
Scraping (3 fuentes)
    ↓
~70 artículos brutos
    ↓
Deduplicación con LLM        ← elimina solo artículos que cubren el mismo hecho concreto
    ↓
~55 artículos únicos
    ↓
Interleave round-robin       ← selecciona N artículos con cobertura equitativa por fuente
    ↓
digest_YYYY-MM-DD.html       ← HTML con todos los artículos seleccionados
    ↓
Formateo notificación con LLM ← agrupa por categoría, acorta títulos, filtra columnas de opinión
    ↓
ntfy.sh push notification
```

El LLM (Mistral Large) hace dos tareas:
1. **Dedup**: de ~70 artículos elimina los que reportan el mismo hecho concreto. Duda → conserva ambos.
2. **Formato notif**: toma los artículos seleccionados, los agrupa por categoría, acorta títulos con citas largas, y filtra columnas de opinión sin noticia (ej: "Vida en otros planetas"). No filtra por importancia.

Si el LLM falla, la notificación se envía igual con el formato estándar, con un aviso al inicio.

## Uso local

```bash
pip install -r requirements.txt
playwright install chromium

# Solo genera el HTML
python main.py

# HTML + notificación push
python main.py --notify mi-topic

# Con LLM (dedup + formateo)
MISTRAL_API_KEY=sk-... python main.py --notify mi-topic

# Probar sin enviar al teléfono (imprime la notificación en consola)
MISTRAL_API_KEY=sk-... python main.py --notify mi-topic --dry-run

# Limitar cantidad de artículos (default: 25)
python main.py --limit 20 --notify mi-topic
```

## Notificaciones en el teléfono (ntfy.sh)

1. Instalar la app **ntfy** (Android / iOS)
2. Suscribirse a un topic único, ej: `dailynews-xyz123`
3. Pasar el topic con `--notify` o como secret en GitHub (ver abajo)

Las categorías Farándula y Cultura se incluyen en el HTML pero no en la notificación push.

## GitHub Actions

### `develop` — test en cada push

El workflow `.github/workflows/test-develop.yml` se dispara en cada push a `develop`.
Corre el scraping completo con LLM y envía al topic de prueba (sin `--dry-run`).

Secrets necesarios:
| Secret | Descripción |
|---|---|
| `MISTRAL_API_KEY_DEV` | Mistral API key para desarrollo |
| `NTFY_TOPIC_DEV` | Topic de ntfy para pruebas (distinto al de producción) |

### Setup para producción (manual)

1. Ir a **Settings → Secrets and variables → Actions**
2. Crear `MISTRAL_API_KEY` y `NTFY_TOPIC` con los valores de producción
3. Crear un workflow de ejecución diaria apuntando a `main` cuando esté listo

## Estructura

```
main.py           — orquestador principal (scraping, dedup, HTML, notificación)
scrapers.py       — scrapers por fuente (RSS, requests+BS4, Playwright)
categories.py     — categorizador por keywords
llm.py            — integración Mistral (dedup + formato notificación)
notifications.py  — envío push via ntfy.sh
requirements.txt  — dependencias Python
```

## Fuentes

| Fuente | Método | Detalle |
|---|---|---|
| The Clinic | RSS | `https://www.theclinic.cl/feed/` — título + bajada |
| La Tercera | requests + BeautifulSoup | selector `div.story-card` — solo título y link |
| El Mercurio Digital | Playwright (JS) | `https://digital.elmercurio.com/YYYY/MM/DD/A` — solo titulares |
