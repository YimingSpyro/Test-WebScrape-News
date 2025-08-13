import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from datetime import datetime

# near imports in src/scraper.py
from urllib.parse import urljoin
import urllib.robotparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



HEADERS = {
    "User-Agent": "news-summarizer-demo/1.0 (+https://example.com)"
}

def is_allowed_by_robots(url, user_agent=HEADERS["User-Agent"], timeout=5):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # if robots unreachable, be conservative and allow (or decide to block)
        return True

def _build_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET", "POST"])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.headers.update(HEADERS)
    return s

def fetch_article(url, timeout=10):
    """
    Returns: dict {title, date, author, url, text}
    Very small heuristic-based extractor for demo use.
    """
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = (soup.find("meta", property="og:title") or
             soup.find("meta", attrs={"name":"og:title"}) or
             soup.find("title"))
    title_text = title.get("content") if title and title.has_attr("content") else (title.text.strip() if title else "")

    # Date: try common meta tags
    date = None
    for tag in ["article:published_time", "pubdate", "publishdate", "og:article:published_time", "date"]:
        meta = soup.find("meta", property=tag) or soup.find("meta", attrs={"name": tag})
        if meta and meta.has_attr("content"):
            date = meta["content"]
            break

    # Main article text heuristics
    article_tag = soup.find("article")
    if article_tag:
        paragraphs = [p.get_text(separator=" ", strip=True) for p in article_tag.find_all("p")]
    else:
        # fallback: choose largest block of <p> in <body>
        body = soup.find("body")
        if body:
            paragraphs = [p.get_text(separator=" ", strip=True) for p in body.find_all("p")]
        else:
            paragraphs = []

    # join paragraphs and filter short bits
    text = "\n\n".join([p for p in paragraphs if len(p) > 40])

    # final fallback using regex to strip tags
    if not text:
        text = re.sub(r"<[^>]+>", "", html)

    return {
        "title": title_text,
        "date": date or datetime.utcnow().isoformat(),
        "author": None,
        "url": url,
        "text": text
    }
