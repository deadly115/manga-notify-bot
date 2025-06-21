# adapters/__init__.py
from urllib.parse import urlparse

from .corona import latest_corona
from .walker import latest_walker
from .garado  import latest_gardo
from .mangaup import latest_mangaup

async def get_latest(url: str):
    """
    Dispatch to the correct adapter based on the URL's domain.
    Returns (chapter_id, title, full_link).
    """
    host = urlparse(url).netloc.lower()
    if "to-corona-ex.com" in host:
        return await latest_corona(url)
    if "comic-walker.com" in host:
        return await latest_walker(url)
    if "comic-gardo.com" in host:
        return await latest_gardo(url)
    if "manga-up.com" in host:
        return await latest_mangaup(url)
    raise ValueError(f"No adapter for host: {host}")
