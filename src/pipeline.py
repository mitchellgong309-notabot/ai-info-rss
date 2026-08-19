"""总编排：容错抓取 → 全文补全 → 合并去重 → 生成站点。单源失败不阻塞。"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig, SourceConfig
from .fetchers.html import HTMLFetcher
from .fetchers.rss import RSSFetcher
from .fulltext import ensure_fulltext
from .models import Article, FetchResult
from .store import Store
from .summarizer import NoopSummarizer


def _fetch_source(source: SourceConfig, cfg: AppConfig, store: Store,
                  verbose: bool) -> FetchResult:
    if source.fetcher == "rss":
        fetcher = RSSFetcher(source, verbose)
    else:
        fetcher = HTMLFetcher(source, verbose,
                              existing_urls=store.existing_urls(source))
    return fetcher.fetch()


def run_build(cfg: AppConfig, verbose: bool = False) -> dict:
    root = cfg.root
    store = Store(root, cfg.max_per_source, cfg.max_age_days)
    summarizer = NoopSummarizer()
    stats = {}
    health = {}
    all_articles: list[Article] = []

    for source in cfg.sources:
        print(f"[{source.id}] 抓取中 ({source.fetcher}) ...")
        try:
            result = _fetch_source(source, cfg, store, verbose)
        except Exception as e:
            traceback.print_exc()
            result = FetchResult(source.id, False, [], error=f"未捕获异常: {e}")

        fetched = result.articles
        if result.ok:
            for a in fetched:
                ensure_fulltext(a, source.fulltext, verbose)
                ai_summary = summarizer.summarize(a)
                if ai_summary:
                    a.summary = ai_summary

        merged = store.merge(source, fetched)
        all_articles.extend(merged)
        stats[source.id] = {
            "ok": result.ok,
            "degraded": result.degraded,
            "fetched": len(fetched),
            "total": len(merged),
            "full": sum(1 for a in merged if a.content_status == "full"),
            "fetched_ft": sum(1 for a in merged if a.content_status == "fetched"),
            "summary_only": sum(1 for a in merged if a.content_status == "summary_only"),
        }
        if result.ok:
            print(f"[{source.id}] OK: 新 {len(fetched)} 篇，库内共 {len(merged)} 篇")
            health[source.id] = {"status": "ok", "total": len(merged)}
        else:
            print(f"[{source.id}] WARN 失败（不影响其他源）: {result.error}")
            existing = store.load(source)
            all_articles = [a for a in all_articles if a.source_id != source.id]
            all_articles.extend(existing)
            stats[source.id]["total"] = len(existing)
            health[source.id] = {
                "status": "degraded" if result.degraded else "error",
                "error": result.error,
                "total": len(existing),
            }

    # 写 health.json / meta.json（内容无变化时不重写，保证幂等）
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    def _write_if_changed(path: Path, payload: dict, ts_key: str) -> None:
        if path.exists():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
                old.pop(ts_key, None)
                new = dict(payload)
                new.pop(ts_key, None)
                if old == new:
                    return
            except Exception:
                pass
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    _write_if_changed(data_dir / "health.json",
                      {"checked_at": now, "sources": health}, "checked_at")
    _write_if_changed(data_dir / "meta.json",
                      {"built_at": now, "total_articles": len(all_articles)},
                      "built_at")

    # 生成站点
    from .generator.site import generate_site
    all_articles.sort(key=lambda a: a.published_at, reverse=True)
    generate_site(root, cfg, all_articles, health)

    ok_count = sum(1 for s in stats.values() if s["ok"])
    print(f"完成: {ok_count}/{len(cfg.sources)} 源成功，共 {len(all_articles)} 篇文章")
    return {"stats": stats, "health": health, "total": len(all_articles)}
