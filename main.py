"""
DailyNews - Resumen diario de portadas chilenas
Fuentes: The Clinic, La Tercera, El Mercurio Digital
"""
import argparse
import html as html_module
import os
from datetime import date

from scrapers import Article, scrape_theclinic, scrape_latercera, scrape_elmercurio
from categories import categorizar
from notifications import notify_ntfy


# ─── Round-robin ──────────────────────────────────────────────────────────────

def interleave(articles: list[Article], limit: int) -> list[Article]:
    """Mezcla artículos en round-robin por fuente."""
    by_source: dict[str, list[Article]] = {}
    for a in articles:
        by_source.setdefault(a.source, []).append(a)

    result = []
    queues = list(by_source.values())
    while any(queues) and len(result) < limit:
        for q in queues:
            if q and len(result) < limit:
                result.append(q.pop(0))

    return result


# ─── Render HTML ──────────────────────────────────────────────────────────────

_MONTHS = {
    "January": "enero", "February": "febrero", "March": "marzo",
    "April": "abril", "May": "mayo", "June": "junio", "July": "julio",
    "August": "agosto", "September": "septiembre", "October": "octubre",
    "November": "noviembre", "December": "diciembre",
}


def render_html(articles: list[Article]) -> str:
    today_str = date.today().strftime("%d de %B de %Y")
    for en, es in _MONTHS.items():
        today_str = today_str.replace(en, es)

    items_html = ""
    for a in articles:
        cat = categorizar(a.title)
        title_esc = html_module.escape(a.title)
        title_html = f'<a href="{a.url}" target="_blank">{title_esc}</a>' if a.url else title_esc

        meta = f'<span class="source">{html_module.escape(a.source)}</span>'
        meta += f' · <span class="category">{cat}</span>'

        summary_html = f'<p class="summary">{html_module.escape(a.summary)}</p>' if a.summary else ""

        items_html += f"""
        <div class="article">
            <div class="meta">{meta}</div>
            <h2>{title_html}</h2>
            {summary_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DailyNews · {today_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f9f7f2; color: #1a1a1a; padding: 2rem 1rem; }}
  .container {{ max-width: 680px; margin: 0 auto; }}
  header {{ border-bottom: 2px solid #1a1a1a; padding-bottom: 1rem; margin-bottom: 2rem; }}
  header h1 {{ font-size: 1.8rem; }}
  header p {{ color: #666; margin-top: 0.3rem; font-size: 0.9rem; font-family: monospace; }}
  .article {{ padding: 1.2rem 0; border-bottom: 1px solid #ddd; }}
  .article:last-child {{ border-bottom: none; }}
  .meta {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 0.4rem; font-family: monospace; }}
  .source {{ font-weight: bold; color: #555; }}
  .category {{ color: #aaa; }}
  h2 {{ font-size: 1.05rem; line-height: 1.4; font-weight: normal; }}
  h2 a {{ color: #1a1a1a; text-decoration: none; }}
  h2 a:hover {{ text-decoration: underline; }}
  .summary {{ margin-top: 0.5rem; font-size: 0.88rem; color: #444; line-height: 1.5; }}
  footer {{ margin-top: 2rem; font-size: 0.8rem; color: #aaa; font-family: monospace; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>DailyNews</h1>
    <p>{today_str} · {len(articles)} noticias</p>
  </header>
  {items_html}
  <footer>The Clinic · La Tercera · El Mercurio</footer>
</div>
</body>
</html>"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DailyNews - resumen de portadas")
    parser.add_argument("--limit", type=int, default=25, help="Máximo de artículos (default: 25)")
    parser.add_argument("--notify", metavar="TOPIC", help="Topic de ntfy.sh para notificación push")
    parser.add_argument(
        "--mistral-key", metavar="KEY",
        default=os.environ.get("MISTRAL_API_KEY"),
        help="Mistral API key para deduplicar y curar notificación (o env MISTRAL_API_KEY)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Imprime la notificación sin enviarla")
    args = parser.parse_args()

    # ─── Scraping ─────────────────────────────────────────────────────────────
    print("Scrapeando fuentes...")
    sources = [
        ("The Clinic",          scrape_theclinic),
        ("La Tercera",          scrape_latercera),
        ("El Mercurio Digital", scrape_elmercurio),
    ]
    all_raw: list[Article] = []
    for label, fn in sources:
        print(f"  → {label}...")
        items = fn()
        print(f"     {len(items)} artículos")
        all_raw.extend(items)

    # ─── Antes del LLM ────────────────────────────────────────────────────────
    print(f"\n─── Antes del LLM ({len(all_raw)} artículos) " + "─" * 30)
    for a in all_raw:
        print(f"  [{a.source:<22}] [{categorizar(a.title):<12}] {a.title[:65]}")

    # ─── Deduplicación con LLM ────────────────────────────────────────────────
    if args.mistral_key:
        from llm import deduplicate_articles
        print(f"\nDeduplicando con LLM ({len(all_raw)} artículos)...")
        deduped = deduplicate_articles(all_raw, args.mistral_key)
    else:
        print("\nSin MISTRAL_API_KEY — omitiendo deduplicación")
        deduped = all_raw

    kept_titles = {a.title for a in deduped}
    removed = [a for a in all_raw if a.title not in kept_titles]

    # ─── Después del LLM ──────────────────────────────────────────────────────
    print(f"\n─── Después del LLM ({len(deduped)} artículos, -{len(removed)} duplicados) " + "─" * 20)
    for a in deduped:
        print(f"  [OK  ] [{a.source:<22}] [{categorizar(a.title):<12}] {a.title[:55]}")
    if removed:
        print()
        for a in removed:
            print(f"  [DROP] [{a.source:<22}] [{categorizar(a.title):<12}] {a.title[:55]}")

    # ─── Selección final + HTML ───────────────────────────────────────────────
    final = interleave(deduped, args.limit)

    output_path = f"digest_{date.today().isoformat()}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(render_html(final))
    print(f"\nDigest: {output_path} ({len(final)} artículos)")

    if args.notify:
        notify_ntfy(args.notify, final, llm_key=args.mistral_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
