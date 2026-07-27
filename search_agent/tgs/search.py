"""Web search — encounter with the Other."""
from __future__ import annotations
import time, urllib.request, html.parser
from dataclasses import dataclass
try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

@dataclass
class Page:
    title: str; url: str; body: str; full_text: str = ""
    def text(self) -> str:
        content = self.full_text if self.full_text else self.body
        return f"[{self.title}]\n{content}\nSource: {self.url}"

def _fetch_full_text(url: str, timeout: int = 5) -> str:
    try:
        class TextExtractor(html.parser.HTMLParser):
            def __init__(self):
                super().__init__()
                self._text, self._skip = [], False
                self._skip_tags = {'script', 'style', 'nav', 'header', 'footer'}
            def handle_starttag(self, tag, attrs):
                if tag in self._skip_tags: self._skip = True
            def handle_endtag(self, tag):
                if tag in self._skip_tags: self._skip = False
            def handle_data(self, data):
                if not self._skip and data.strip(): self._text.append(data.strip())
            def get_text(self): return "\n".join(self._text)

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; TGSAgent/1.0)'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(50_000).decode('utf-8', errors='ignore')
        extractor = TextExtractor()
        extractor.feed(raw)
        return extractor.get_text()[:2000] if extractor.get_text() else ""
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e): return "[ACCESS DENIED: Anti-bot protection]"
        return ""

def search(query: str, max_results: int = 5, retries: int = 3, pause: float = 2.0, fetch_full: bool = False) -> list[Page]:
    for attempt in range(1, retries + 1):
        try:
            pages = []
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=max_results):
                    page = Page(title=result.get("title", ""), url=result.get("href", ""), body=result.get("body", ""))
                    if fetch_full and page.url: page.full_text = _fetch_full_text(page.url)
                    pages.append(page)
            return pages
        except Exception as e:
            if attempt < retries:
                print(f"  [search] attempt {attempt} failed: {e}\n  [search] retrying in {pause}s ...")
                time.sleep(pause)
            else:
                print(f"  [search] all {retries} attempts failed: {e}")
    return []
