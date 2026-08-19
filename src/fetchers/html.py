"""HTML fetcher：两阶段——列表页链接发现 → 逐篇增量抓取（trafilatura 提取）。

列表页结构变化导致链接数为 0 时标记 degraded，写入 health.json 而非硬失败。
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import trafilatura
from bs4 import BeautifulSoup

from ..models import Article, FetchResult, normalize_url
from .base import Fetcher, make_client

_LIST_LIMIT = 40       # 列表页最多纳入的链接数
_MAX_NEW_PER_RUN = 8   # 每次构建最多逐篇抓取的新文章数（防 CI 超时）


class HTMLFetcher(Fetcher):
    def __init__(self, source, verbose: bool = False,
                 existing_urls: set[str] | None = None):
        super().__init__(source, verbose)
        self.existing_urls = existing_urls or set()

    def _discover_links(self, html: str) -> list[str]:
        """返回去重后的候选 URL，新链接在前、已存在的在后（各保持页面顺序）。"""
        soup = BeautifulSoup(html, "html.parser")
        include = re.compile(self.source.include) if self.source.include else None
        exclude = re.compile(self.source.exclude) if self.source.exclude else None
        fresh: list[str] = []
        known: list[str] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue
            full = urljoin(self.source.url, href)
            parts = urlsplit(full)
            if parts.scheme not in ("http", "https"):
                continue
            if include and not (include.search(full) or include.search(parts.path)):
                continue
            if exclude and (exclude.search(full) or exclude.search(parts.path)):
                continue
            norm = normalize_url(full)
            if norm in seen:
                continue
            seen.add(norm)
            (known if norm in self.existing_urls else fresh).append(norm)
        return (fresh + known)[:_LIST_LIMIT]

    def _fetch_article(self, client, url: str) -> Article:
        resp = client.get(url)
        resp.raise_for_status()
        extracted = trafilatura.extract(
            resp.text, url=url, output_format="html", favor_recall=True) or ""
        title = ""
        meta = trafilatura.extract_metadata(resp.text)
        if meta and meta.title:
            title = meta.title
        if not title:
            soup = BeautifulSoup(resp.text, "html.parser")
            if soup.title:
                title = soup.title.get_text(strip=True)
        status = "fetched" if len(extracted) > 400 else "summary_only"
        return Article(
            title=title or "(无标题)",
            url=url,
            published_at=datetime.now(timezone.utc),  # 列表页无日期，用抓取时间
            summary="",
            content_html=extracted,
            content_status=status,
            source_id=self.source.id,
            source_name=self.source.name,
            category=self.source.category,
        )

    def fetch(self) -> FetchResult:
        try:
            client = make_client()
            with client:
                resp = client.get(self.source.url)
                resp.raise_for_status()
                links = self._discover_links(resp.text)
                if not links:
                    return FetchResult(
                        self.source.id, False, [],
                        error="列表页未发现任何链接（正则过期或页面结构变化？）",
                        degraded=True)

                articles = []
                errors = []
                for url in links[:_MAX_NEW_PER_RUN]:
                    if url in self.existing_urls:
                        break  # 新链接在前，遇到已存在即止
                    try:
                        self.log(f"抓取文章: {url}")
                        articles.append(self._fetch_article(client, url))
                    except Exception as e:
                        errors.append(f"{url}: {e}")
                        self.log(f"文章抓取失败: {e}")

        except Exception as e:
            return FetchResult(self.source.id, False, [],
                               error=f"列表页请求失败: {e}")

        if not articles and errors:
            # 列表发现成功但逐篇全失败：降级标记而非硬失败（如对方页面存在死链）
            return FetchResult(self.source.id, True, [], degraded=True,
                               error="; ".join(errors[:3]))
        self.log(f"发现 {len(links)} 链接，抓取 {len(articles)} 篇新文章"
                 + (f"，{len(errors)} 篇失败" if errors else ""))
        return FetchResult(self.source.id, True, articles)
