# adapters/walker.py
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

async def latest_walker(url: str):
    """
    Return (chapter_id, title, full_link) for comic-walker.com
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html, "lxml")
    # ComicWalker lists episodes in <li class="episodeList__item"><a ...>
    item = soup.select_one("li.episodeList__item a")
    if not item:
        raise ValueError("No episode link found")
    rel = item["href"]
    full = urljoin("https://comic-walker.com", rel)
    chap_id = rel.rstrip("/").split("/")[-1]
    title = item.get_text(strip=True)
    return chap_id, title, full
