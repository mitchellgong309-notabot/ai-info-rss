"""每源 JSON 持久化：读写/合并去重/保留策略裁剪。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import SourceConfig
from .models import Article


class Store:
    def __init__(self, root: Path, max_per_source: int, max_age_days: int):
        self.dir = root / "data" / "articles"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_per_source = max_per_source
        self.max_age_days = max_age_days

    def path_for(self, source: SourceConfig) -> Path:
        return self.dir / f"{source.id}.json"

    def load(self, source: SourceConfig) -> list[Article]:
        p = self.path_for(source)
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return [Article.from_dict(d) for d in data.get("articles", [])]
        except Exception:
            return []

    def merge(self, source: SourceConfig, fetched: list[Article]) -> list[Article]:
        """合并新文章（按 id 去重，新数据优先保留较新 content_status），再裁剪。"""
        existing = {a.id: a for a in self.load(source)}
        for a in fetched:
            old = existing.get(a.id)
            if old is None:
                existing[a.id] = a
            else:
                # 更新元数据但保留已有的更好正文
                if old.content_status == "summary_only" and a.content_status != "summary_only":
                    existing[a.id] = a
                else:
                    old.title = a.title or old.title
                    old.author = a.author or old.author
        articles = self._prune(list(existing.values()))
        articles.sort(key=lambda a: a.published_at, reverse=True)
        payload = {
            "source_id": source.id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(articles),
            "articles": [a.to_dict() for a in articles],
        }
        # 幂等：文章数据无变化时不重写（避免 updated_at 造成虚假变更）
        p = self.path_for(source)
        if p.exists():
            try:
                old = json.loads(p.read_text(encoding="utf-8"))
                if old.get("articles") == payload["articles"]:
                    return articles
            except Exception:
                pass
        p.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return articles

    def _prune(self, articles: list[Article]) -> list[Article]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)
        kept = [a for a in articles if a.published_at >= cutoff]
        if len(kept) > self.max_per_source:
            kept.sort(key=lambda a: a.published_at, reverse=True)
            kept = kept[:self.max_per_source]
        return kept

    def existing_urls(self, source: SourceConfig) -> set[str]:
        from .models import normalize_url
        return {normalize_url(a.url) for a in self.load(source)}
