# app/fetchers/news_fetcher.py
#
# Obtiene noticias de ciberseguridad desde feeds RSS publicos.
# No requiere API key ni autenticacion.
#
# Fuentes incluidas:
#   - The Hacker News      (thehackernews.com)
#   - BleepingComputer     (bleepingcomputer.com)
#   - Krebs on Security    (krebsonsecurity.com)
#   - SecurityWeek         (securityweek.com)
#   - CISA Advisories      (cisa.gov)

import feedparser
import httpx
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    {
        "name": "The Hacker News",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "category": "general",
    },
    {
        "name": "BleepingComputer",
        "url": "https://www.bleepingcomputer.com/feed/",
        "category": "general",
    },
    {
        "name": "Krebs on Security",
        "url": "https://krebsonsecurity.com/feed/",
        "category": "investigative",
    },
    {
        "name": "SecurityWeek",
        "url": "https://feeds.feedburner.com/securityweek",
        "category": "general",
    },
    {
        "name": "CISA Advisories",
        "url": "https://www.cisa.gov/feeds/advisories.xml",
        "category": "advisory",
    },
]


async def fetch_news() -> list[dict]:
    """
    Recorre todos los feeds RSS, parsea las entradas y devuelve
    una lista unificada de noticias ordenadas por fecha descendente.
    """
    all_news = []

    async with httpx.AsyncClient(timeout=15) as client:
        for feed_info in FEEDS:
            try:
                # Descargamos el XML del feed
                resp = await client.get(
                    feed_info["url"],
                    headers={"User-Agent": "CyberFeed/1.0 (RSS Aggregator)"},
                    follow_redirects=True,
                )
                resp.raise_for_status()

                # feedparser parsea el XML de RSS/Atom
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:5]:  # Maximo 5 por fuente
                    news_item = _parse_entry(entry, feed_info)
                    if news_item:
                        all_news.append(news_item)

            except Exception as e:
                print(f"[News Fetcher] Error en feed {feed_info['name']}: {e}")
                continue

    # Ordenar por fecha, mas reciente primero
    all_news.sort(key=lambda x: x["timestamp"], reverse=True)

    return all_news[:25]  # Maximo 25 noticias totales


def _parse_entry(entry: dict, feed_info: dict) -> dict | None:
    """
    Extrae los campos relevantes de una entrada RSS.
    Devuelve None si la entrada no tiene titulo o link.
    """
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()

    if not title or not link:
        return None

    # Resumen: intentamos summary, luego description, luego cortamos el titulo
    summary = (
        entry.get("summary", "")
        or entry.get("description", "")
        or title
    )

    # Limpiamos HTML basico del resumen
    summary = _strip_html(summary)
    if len(summary) > 250:
        summary = summary[:250] + "..."

    # Fecha de publicacion
    timestamp = datetime.now(timezone.utc)
    pub_date_str = "Hoy"

    if hasattr(entry, "published"):
        try:
            timestamp = parsedate_to_datetime(entry.published)
            pub_date_str = timestamp.strftime("%d %b %Y")
        except Exception:
            pass
    elif hasattr(entry, "updated"):
        try:
            timestamp = parsedate_to_datetime(entry.updated)
            pub_date_str = timestamp.strftime("%d %b %Y")
        except Exception:
            pass

    # Tags/categorias de la noticia
    tags = []
    if hasattr(entry, "tags"):
        tags = [t.term for t in entry.tags[:3] if hasattr(t, "term")]

    return {
        "type": "news",
        "id": link,
        "title": title,
        "severity": "news",
        "source": feed_info["name"],
        "category": feed_info["category"],
        "summary": summary,
        "published": pub_date_str,
        "timestamp": timestamp.isoformat(),
        "url": link,
        "tags": tags,
    }


def _strip_html(text: str) -> str:
    """
    Elimina tags HTML basicos de un string.
    No usamos BeautifulSoup para mantener las dependencias minimas.
    """
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return clean.strip()
