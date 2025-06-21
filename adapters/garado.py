# adapters/gardo.py
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup
import json
import re

HEADERS = {"User-Agent": "MangaNotifyBot/1.2"}

async def latest_gardo(url: str):
    """
    Return (chapter_id, title, full_link) for comic-gardo.com
    Uses RSS + episode-json to resolve series_id and track latest
    """
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=HEADERS, timeout=20) as resp:
            html = await resp.text()

    # Step 1: Extract series_id from <script id="episode-json">
    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", {"id": "episode-json", "type": "text/json"})
    if script and script.get("data-value"):
        data = json.loads(script["data-value"])
        series_id = data["readableProduct"]["series"]["id"]
    else:
        # Fallback: use embedded JS
        match = re.search(r'giga_series"\s*:\s*"(\d+)"', html)
        if not match:
            raise ValueError("Series ID not found in episode page.")
        series_id = match.group(1)

    # Step 2: Pull RSS to get latest chapter
    rss_url = f"https://comic-gardo.com/rss/series/{series_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(rss_url, headers=HEADERS) as resp:
            xml = await resp.text()
    soup = BeautifulSoup(xml, "xml")
    item = soup.find("item")
    if not item:
        raise ValueError("No chapters found in RSS.")
    
    link = item.find("link").text
    title = item.find("title").text
    chap_id = link.rstrip("/").split("/")[-1]
    
    return chap_id, title, link
