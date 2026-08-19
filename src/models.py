"""Article / FetchResult 模型 + URL 规范化 + ID 生成。"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|igshid)")


def normalize_url(url: str) -> str:
    """去 fragment、去跟踪参数、host 小写、去尾斜杠。"""
    url = url.strip()
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not _TRACKING_PARAMS.match(k.lower())]
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                       urlencode(query), ""))


def make_id(url: str) -> str:
    return hashlib.sha1(normalize_url(url).encode("utf-8")).hexdigest()[:16]


class Article:
    __slots__ = ("id", "title", "url", "author", "published_at", "summary",
                 "content_html", "content_status", "source_id", "source_name",
                 "category", "fetched_at")

    def __init__(self, *, title: str, url: str, source_id: str,
                 source_name: str, category: str,
                 author: str = "", published_at: Optional[datetime] = None,
                 summary: str = "", content_html: str = "",
                 content_status: str = "summary_only",
                 fetched_at: Optional[datetime] = None):
        self.id = make_id(url)
        self.title = title
        self.url = url
        self.author = author
        self.published_at = published_at or datetime.now(timezone.utc)
        self.summary = summary
        self.content_html = content_html
        self.content_status = content_status  # full | fetched | summary_only
        self.source_id = source_id
        self.source_name = source_name  # 冗余存储防配置变更
        self.category = category
        self.fetched_at = fetched_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at.astimezone(timezone.utc).isoformat(),
            "summary": self.summary,
            "content_html": self.content_html,
            "content_status": self.content_status,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "category": self.category,
            "fetched_at": self.fetched_at.astimezone(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Article":
        a = cls.__new__(cls)
        a.id = d["id"]
        a.title = d["title"]
        a.url = d["url"]
        a.author = d.get("author", "")
        a.published_at = datetime.fromisoformat(d["published_at"])
        if a.published_at.tzinfo is None:
            a.published_at = a.published_at.replace(tzinfo=timezone.utc)
        a.summary = d.get("summary", "")
        a.content_html = d.get("content_html", "")
        a.content_status = d.get("content_status", "summary_only")
        a.source_id = d["source_id"]
        a.source_name = d.get("source_name", d["source_id"])
        a.category = d.get("category", "")
        a.fetched_at = datetime.fromisoformat(d.get("fetched_at", d["published_at"]))
        return a


class FetchResult:
    def __init__(self, source_id: str, ok: bool, articles: list[Article],
                 error: str = "", degraded: bool = False):
        self.source_id = source_id
        self.ok = ok
        self.articles = articles
        self.error = error
        self.degraded = degraded
