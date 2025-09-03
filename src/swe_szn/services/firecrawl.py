import time
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from firecrawl import Firecrawl

from swe_szn.config import settings
from swe_szn.services.cache import load_json, md5_digest, save_json


def _normalize_url(url: str) -> str:
    """Remove common tracking params (utm_*, ref, etc.) from the URL."""
    try:
        parts = urlsplit(url)
        query_items = parse_qsl(parts.query, keep_blank_values=True)

        def is_tracking(key: str) -> bool:
            if key.startswith("utm_"):
                return True
            return key.lower() in {
                "utm",
                "ref",
                "ref_source",
                "referrer",
            }

        filtered = [(k, v) for k, v in query_items if not is_tracking(k)]
        new_query = urlencode(filtered, doseq=True)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
        )
    except Exception:
        # if anything goes wrong, fall back to the original
        return url


def scrape_job(
    url: str, api_key: Optional[str] = None, cache_dir: Optional[str] = None
) -> str:
    """scrape a given url using Firecrawl"""
    key = api_key or settings().require_firecrawl_key()

    # select cache directory
    cache_path = Path(cache_dir) if cache_dir else settings().cache_dir("firecrawl")

    # normalize URL (strip tracking params) and generate cache key
    normalized_url = _normalize_url(url)
    url_hash = md5_digest(normalized_url)
    cache_file = cache_path / f"{url_hash}.json"

    # check if we have cached result
    if cache_file.exists():
        cached_data = load_json(cache_file)
        if cached_data is not None:
            print(f"Using cached result for {normalized_url}")
            return cached_data.get("markdown", "")

    # scrape fresh content
    print(f"Scraping {normalized_url}...")
    client = Firecrawl(api_key=key)
    doc = client.scrape(
        normalized_url,
        formats=["markdown"],
        only_main_content=True,
    )

    # extract markdown content
    markdown = getattr(doc, "markdown", None)
    if not markdown and isinstance(doc, dict):
        markdown = doc.get("markdown", "")

    markdown = markdown or ""

    # cache the result
    try:
        cache_data = {
            "url": normalized_url,
            "markdown": markdown,
            "timestamp": time.time(),
        }
        save_json(cache_file, cache_data)
        # TODO :: update prints
        print(f"Cached result to {cache_file}")
    except Exception as e:
        print(f"Cache write error: {e}")

    return markdown
