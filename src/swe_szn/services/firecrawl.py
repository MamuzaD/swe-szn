import time
from typing import Optional
from pathlib import Path

from firecrawl import Firecrawl

from swe_szn.config import settings
from swe_szn.services.cache import md5_digest, load_json, save_json


def scrape_job(
    url: str, api_key: Optional[str] = None, cache_dir: Optional[str] = None
) -> str:
    """scrape a given url using Firecrawl"""
    key = api_key or settings().require_firecrawl_key()

    # select cache directory
    cache_path = Path(cache_dir) if cache_dir else settings().cache_dir("firecrawl")

    # generate cache key from URL
    url_hash = md5_digest(url)
    cache_file = cache_path / f"{url_hash}.json"

    # check if we have cached result
    if cache_file.exists():
        cached_data = load_json(cache_file)
        if cached_data is not None:
            print(f"Using cached result for {url}")
            return cached_data.get("markdown", "")

    # scrape fresh content
    print(f"Scraping {url}...")
    client = Firecrawl(api_key=key)
    doc = client.scrape(url, formats=["markdown"])

    # extract markdown content
    markdown = getattr(doc, "markdown", None)
    if not markdown and isinstance(doc, dict):
        markdown = doc.get("markdown", "")

    markdown = markdown or ""

    # cache the result
    try:
        cache_data = {
            "url": url,
            "markdown": markdown,
            "timestamp": time.time(),
        }
        save_json(cache_file, cache_data)
        # TODO :: update prints
        print(f"Cached result to {cache_file}")
    except Exception as e:
        print(f"Cache write error: {e}")

    return markdown
