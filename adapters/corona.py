# adapters/corona.py
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

async def latest_corona(url: str):
    """
    Return (chapter_id, title, full_link) for to-corona-ex.com
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "lxml")
    a = soup.select_one("a[href*='/episodes/']")
    if not a:
        raise ValueError("No episode link found")
    rel = a["href"]
    full = urljoin(url, rel)
    chap_id = rel.rsplit("/", 1)[-1]
    title = a.get_text(strip=True)
    return chap_id, title, full
