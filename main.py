"""
DailyNews - Resumen diario de portadas chilenas
Fuentes: The Clinic, La Tercera, El Mercurio Digital
"""
import argparse
import html as html_module
from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from scrapers import Article, scrape_theclinic, scrape_latercera, scrape_elmercurio
from notifications import notify_ntfy


# ─── Deduplicación ────────────────────────────────────────────────────────────

def deduplicate(articles: list[Article], threshold: float = 0.55) -> list[Article]:
    """
    Agrupa artículos similares por TF-IDF cosine similarity en títulos.
    De cada grupo conserva el mejor (con summary > sin summary).
    """
    if len(articles) < 2:
        return articles

    titles = [a.title for a in articles]
    tfidf = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(titles)
    sim = cosine_similarity(tfidf)

    parent = list(range(len(articles)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            if sim[i, j] >= threshold:
                parent[find(i)] = find(j)

    groups: dict[int, list[Article]] = {}
    for i, article in enumerate(articles):
        groups.setdefault(find(i), []).append(article)

    result = []
    for group in groups.values():
        best = max(group, key=lambda a: (a.summary is not None, a.source == "The Clinic", len(a.title)))
        sources = list({a.source for a in group})
        if len(sources) > 1:
            best = Article(
                source=" + ".join(sorted(sources)),
                title=best.title,
                url=best.url,
                summary=best.summary,
                category=best.category,
            )
        result.append(best)

    return result


# ─── Round-robin ──────────────────────────────────────────────────────────────

def interleave(articles: list[Article], limit: int) -> list[Article]:
    """Mezcla artículos en round-robin por fuente. Multi-fuente va primero."""
    multi = [a for a in articles if "+" in a.source]
    by_source: dict[str, list[Article]] = {}
    for a in articles:
        if "+" not in a.source:
            by_source.setdefault(a.source, []).append(a)

    result = []
    queues = list(by_source.values())
    while any(queues) and len(result) < limit - len(multi):
        for q in queues:
            if q:
                result.append(q.pop(0))

    return (multi + result)[:limit]


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
        title_esc = html_module.escape(a.title)
        title_html = f'<a href="{a.url}" target="_blank">{title_esc}</a>' if a.url else title_esc

        meta = f'<span class="source">{html_module.escape(a.source)}</span>'
        if a.category:
            meta += f' · <span class="category">{html_module.escape(a.category)}</span>'

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
    args = parser.parse_args()

    print("Scrapeando fuentes...")
    all_articles = []

    for label, fn in [
        ("The Clinic (RSS)", scrape_theclinic),
        ("La Tercera", scrape_latercera),
        ("El Mercurio Digital", scrape_elmercurio),
    ]:
        print(f"  → {label}...")
        items = fn()
        print(f"     {len(items)} artículos")
        all_articles.extend(items)

    print(f"\nTotal: {len(all_articles)} → ", end="")
    deduped = deduplicate(all_articles)
    print(f"{len(deduped)} tras deduplicar")

    final = interleave(deduped, args.limit)

    output_path = f"digest_{date.today().isoformat()}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(render_html(final))
    print(f"Digest: {output_path} ({len(final)} artículos)")

    if args.notify:
        notify_ntfy(args.notify, final)

    print("\n─── Preview ───────────────────────────────────────────")
    for a in final[:10]:
        print(f"[{a.source}] {a.title[:80]}")
        if a.summary:
            print(f"    {a.summary[:100]}")


if __name__ == "__main__":
    main()
