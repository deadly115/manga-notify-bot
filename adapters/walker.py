# adapters/walker.py
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

def normalize_series_url(url: str) -> str:
    """
    Strip any /episodes/... and return series root URL
    """
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if "episodes" in parts:
        return urljoin(url, f"/detail/{parts[1]}/")
    return url

async def latest_walker(url: str):
    """
    Return (chapter_id, title, full_link) for comic-walker.com
    """
    url = normalize_series_url(url)

    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
            base_url = str(resp.url)

    soup = BeautifulSoup(html, "lxml")

    item = soup.select_one("li.episodeList__item a")
    if not item:
        raise ValueError("No episode link found – structure may have changed.")

    rel = item["href"]
    full = urljoin(base_url, rel)
    chap_id = rel.rstrip("/").split("/")[-1]
    title = item.get_text(strip=True)

    return chap_id, title, full
