# adapters/mangaup.py
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

def extract_series_url(url: str) -> str:
    """
    Convert chapter URL to series URL (e.g. /titles/506/chapters/100487 → /titles/506)
    """
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if "titles" in parts and "chapters" in parts:
        idx = parts.index("titles")
        series_id = parts[idx + 1]
        return urljoin(url, f"/titles/{series_id}")
    return url

async def latest_mangaup(url: str):
    """
    Return (chapter_id, title, full_link) for www.manga-up.com
    """
    # Redirect chapter URLs to series page
    series_url = extract_series_url(url)

    async with aiohttp.ClientSession() as sess:
        async with sess.get(series_url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()

    soup = BeautifulSoup(html, "lxml")

    # Manga UP likely uses a list of chapters
    a = soup.select_one("ul.chapter-list li a")
    if not a:
        raise ValueError("No chapter link found")

    rel = a["href"]
    full = urljoin(series_url, rel)
    chap_id = rel.rstrip("/").split("/")[-1]
    title = a.get_text(strip=True)
    return chap_id, title, full
