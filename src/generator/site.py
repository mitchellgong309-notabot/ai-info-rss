"""Jinja2 全量重建 dist/ + search-index.json。所有资源相对路径引用。"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from ..config import AppConfig
from ..models import Article

MAX_INDEX_ITEMS = 60


def _fmt_dt(cfg: AppConfig) -> object:
    tz = ZoneInfo(cfg.tz)

    def _fmt(dt: datetime, with_time: bool = False) -> str:
        local = dt.astimezone(tz)
        if with_time:
            return local.strftime("%Y-%m-%d %H:%M")
        return local.strftime("%Y-%m-%d")
    return _fmt


def _group_key(cfg: AppConfig, article: Article) -> str:
    tz = ZoneInfo(cfg.tz)
    return article.published_at.astimezone(tz).strftime("%Y-%m-%d")


def generate_site(root: Path, cfg: AppConfig, articles: list[Article],
                  health: dict) -> None:
    dist = root / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    shutil.copytree(root / "static", dist / "static")

    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
    )
    env.filters["dt"] = _fmt_dt(cfg)
    env.globals["site_name"] = cfg.site_name
    env.globals["site_description"] = cfg.site_description
    env.globals["now"] = datetime.now(timezone.utc)

    sources_meta = {s.id: {"id": s.id, "name": s.name, "category": s.category}
                    for s in cfg.sources}
    categories = []
    for s in cfg.sources:
        if s.category not in categories:
            categories.append(s.category)

    # 首页：按日期分组
    groups: dict[str, list] = {}
    for a in articles[:MAX_INDEX_ITEMS]:
        groups.setdefault(_group_key(cfg, a), []).append(a)
    index_html = env.get_template("index.html").render(
        groups=[{"date": d, "entries": items} for d, items in groups.items()],
        categories=categories,
        sources=sources_meta,
        health=health,
        has_more=len(articles) > MAX_INDEX_ITEMS,
    )
    (dist / "index.html").write_text(index_html, encoding="utf-8")

    # 归档页：全量
    archive_groups: dict[str, list] = {}
    for a in articles:
        archive_groups.setdefault(_group_key(cfg, a), []).append(a)
    (dist / "archive.html").write_text(env.get_template("archive.html").render(
        groups=[{"date": d, "entries": items} for d, items in archive_groups.items()],
        categories=categories,
        sources=sources_meta,
    ), encoding="utf-8")

    # 文章页（含同源上一篇/下一篇）
    by_source: dict[str, list[Article]] = {}
    for a in articles:  # articles 已按时间倒序
        by_source.setdefault(a.source_id, []).append(a)
    arts_dir = dist / "articles"
    arts_dir.mkdir()
    for src_items in by_source.values():
        for i, a in enumerate(src_items):
            html = env.get_template("article.html").render(
                article=a,
                prev_in_source=src_items[i + 1] if i + 1 < len(src_items) else None,
                next_in_source=src_items[i - 1] if i > 0 else None,
            )
            (arts_dir / f"{a.id}.html").write_text(html, encoding="utf-8")

    # 搜索索引
    index_entries = [{
        "id": a.id,
        "title": a.title,
        "url": a.url,
        "source": a.source_name,
        "category": a.category,
        "date": _group_key(cfg, a),
        "status": a.content_status,
        "summary": (a.summary or "")[:300],
    } for a in articles]
    (dist / "search-index.json").write_text(
        json.dumps(index_entries, ensure_ascii=False), encoding="utf-8")
    print(f"站点生成完毕: {len(articles)} 篇文章页 + index + archive")
