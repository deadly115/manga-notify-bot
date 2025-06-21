# adapters/gardo.py
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

async def latest_gardo(url: str):
    """
    Return (chapter_id, title, full_link) for comic-gardo.com
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "lxml")
    # Gardo lists chapters under <div class="chapter-list"><a ...>
    link = soup.select_one("div.chapter-list a")
    if not link:
        raise ValueError("No chapter link found")
    rel = link["href"]
    full = urljoin(url, rel)
    chap_id = rel.rstrip("/").split("/")[-1]
    title = link.get_text(strip=True)
    return chap_id, title, full
