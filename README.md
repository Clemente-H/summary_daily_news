# DailyNews

Resumen diario de portadas chilenas. Scraping de The Clinic, La Tercera y El Mercurio Digital, con deduplicación por similitud TF-IDF y notificación push via ntfy.sh.

## Uso local

```bash
pip install -r requirements.txt
playwright install chromium

python main.py                        # genera digest_YYYY-MM-DD.html
python main.py --limit 20             # limitar cantidad de noticias
python main.py --notify mi-topic      # + notificación push al teléfono
```

## Notificaciones en el teléfono (ntfy.sh)

1. Instalar la app **ntfy** (Android / iOS)
2. Suscribirse a un topic único, ej: `dailynews-xyz123`
3. Agregar ese topic como secret en GitHub (ver abajo) o pasarlo con `--notify`

## GitHub Actions (ejecución automática diaria)

El workflow `.github/workflows/daily.yml` corre todos los días a las **8:00 AM hora chilena**.

### Setup

1. Ir a **Settings → Secrets and variables → Actions** en el repo
2. Crear secret `NTFY_TOPIC` con tu topic de ntfy
3. El workflow lo usa automáticamente — nada se guarda en el repo

También se puede disparar manualmente desde la pestaña **Actions → Run workflow**.
