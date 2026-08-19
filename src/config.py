"""加载并校验 feeds.yaml。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

VALID_FETCHERS = {"rss", "html"}
VALID_FULLTEXT = {"auto", "always_fetch", "never"}


@dataclass
class SourceConfig:
    id: str
    name: str
    category: str
    fetcher: str
    url: str
    fulltext: str = "auto"
    include: Optional[str] = None
    exclude: Optional[str] = None

    @property
    def store_path(self) -> str:
        return f"{self.id}.json"


@dataclass
class AppConfig:
    sources: list[SourceConfig]
    max_per_source: int = 200
    max_age_days: int = 180
    site_name: str = "AI 简报"
    site_description: str = ""
    tz: str = "Asia/Shanghai"
    root: Path = field(default_factory=lambda: Path("."))

    def source_by_id(self, sid: str) -> Optional[SourceConfig]:
        for s in self.sources:
            if s.id == sid:
                return s
        return None


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = []
    seen = set()
    for item in raw.get("sources", []):
        sid = item.get("id")
        if not sid or sid in seen:
            raise ValueError(f"无效或重复的 source id: {sid!r}")
        seen.add(sid)
        fetcher = item.get("fetcher")
        if fetcher not in VALID_FETCHERS:
            raise ValueError(f"source {sid}: fetcher 必须是 {VALID_FETCHERS}")
        fulltext = item.get("fulltext", "auto")
        if fulltext not in VALID_FULLTEXT:
            raise ValueError(f"source {sid}: fulltext 必须是 {VALID_FULLTEXT}")
        pattern = item.get("link_pattern") or {}
        sources.append(SourceConfig(
            id=sid,
            name=item.get("name", sid),
            category=item.get("category", ""),
            fetcher=fetcher,
            url=item["url"],
            fulltext=fulltext,
            include=pattern.get("include"),
            exclude=pattern.get("exclude"),
        ))
    retention = raw.get("retention", {})
    site = raw.get("site", {})
    return AppConfig(
        sources=sources,
        max_per_source=int(retention.get("max_per_source", 200)),
        max_age_days=int(retention.get("max_age_days", 180)),
        site_name=site.get("name", "AI 简报"),
        site_description=site.get("description", ""),
        tz=site.get("tz", "Asia/Shanghai"),
        root=path.parent,
    )
