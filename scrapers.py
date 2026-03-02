"""
Scrapers por fuente. Cada función devuelve una lista de Article.
"""
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


@dataclass
class Article:
    source: str
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None


def scrape_theclinic() -> list[Article]:
    """RSS feed de The Clinic."""
    feed = feedparser.parse("https://www.theclinic.cl/feed/")
    articles = []
    for entry in feed.entries[:15]:
        summary_raw = entry.get("summary", "")
        summary_clean = BeautifulSoup(summary_raw, "html.parser").get_text(strip=True)
        summary_clean = summary_clean[:200] if summary_clean else None
        articles.append(Article(
            source="The Clinic",
            title=entry.title.strip(),
            url=entry.get("link"),
            summary=summary_clean,
        ))
    return articles


def scrape_latercera() -> list[Article]:
    """Portada de La Tercera via requests + BeautifulSoup."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.get("https://www.latercera.com", headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[latercera] Error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    seen_titles = set()

    for card in soup.find_all("div", class_="story-card")[:40]:
        h2 = card.find("h2", class_="story-card__headline")
        if not h2:
            continue
        a = h2.find("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        url = a.get("href", "")
        if url and not url.startswith("http"):
            url = "https://www.latercera.com" + url

        overline = card.find("div", class_="story-card__overline")
        category = overline.get_text(strip=True) if overline else None

        articles.append(Article(
            source="La Tercera",
            title=title,
            url=url or None,
            category=category,
        ))

    return articles


def scrape_elmercurio() -> list[Article]:
    """Portada de El Mercurio Digital (edición del día). Requiere Playwright (JS)."""
    today = date.today()
    url = f"https://digital.elmercurio.com/{today.strftime('%Y/%m/%d')}/A"

    skip_patterns = re.compile(
        r"(alguna duda|suscripci|contactar|soporte|formulario|problemas con su)", re.I
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"[elmercurio] Error Playwright: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen = set()

    for h in soup.find_all("h2"):
        text = h.get_text(strip=True)
        if not text or len(text) < 20:
            continue
        if skip_patterns.search(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        articles.append(Article(source="El Mercurio", title=text, url=url))

    return articles
