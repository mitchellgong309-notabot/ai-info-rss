"""RSS fetcher：httpx 拉取 + feedparser 解析。"""
from __future__ import annotations

from datetime import datetime, timezone
from time import mktime

import feedparser

from ..config import SourceConfig
from ..models import Article, FetchResult
from .base import Fetcher, make_client


def _entry_date(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        st = getattr(entry, key, None)
        if st:
            return datetime.fromtimestamp(mktime(st), tz=timezone.utc)
    for key in ("published", "updated"):
        raw = getattr(entry, key, None)
        if raw:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _entry_content(entry) -> str:
    if getattr(entry, "content", None):
        return entry.content[0].get("value", "")
    return ""


class RSSFetcher(Fetcher):
    def fetch(self) -> FetchResult:
        try:
            with make_client() as client:
                resp = client.get(self.source.url)
                resp.raise_for_status()
        except Exception as e:
            return FetchResult(self.source.id, False, [], error=f"HTTP 请求失败: {e}")

        parsed = feedparser.parse(resp.text)
        if parsed.bozo and not parsed.entries:
            return FetchResult(self.source.id, False, [],
                               error=f"RSS 解析失败: {parsed.bozo_exception}")

        articles = []
        for entry in parsed.entries[:60]:
            url = getattr(entry, "link", "")
            title = getattr(entry, "title", "") or "(无标题)"
            if not url:
                continue
            content = _entry_content(entry)
            summary = getattr(entry, "summary", "") or ""
            # RSS 全文判定：content 存在且明显长于摘要
            if content and len(content) > max(len(summary) * 1.2, 500):
                status, body = "full", content
            else:
                status, body = "summary_only", ""
            articles.append(Article(
                title=title,
                url=url,
                author=getattr(entry, "author", "") or "",
                published_at=_entry_date(entry),
                summary=summary,
                content_html=body,
                content_status=status,
                source_id=self.source.id,
                source_name=self.source.name,
                category=self.source.category,
            ))
        self.log(f"RSS 解析到 {len(articles)} 篇")
        if not articles:
            return FetchResult(self.source.id, False, [],
                               error="RSS 中无有效条目", degraded=True)
        return FetchResult(self.source.id, True, articles)
