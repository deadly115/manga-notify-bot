# adapters/mangaup.py
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

async def latest_mangaup(url: str):
    """
    Return (chapter_id, title, full_link) for www.manga-up.com
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "lxml")
    # Manga-Up chapters often in <ul class="chapters"><li><a ...>
    a = soup.select_one("ul.chapters li a")
    if not a:
        raise ValueError("No chapter link found")
    rel = a["href"]
    full = urljoin(url, rel)
    chap_id = rel.rstrip("/").split("/")[-1]
    title = a.get_text(strip=True)
    return chap_id, title, full
