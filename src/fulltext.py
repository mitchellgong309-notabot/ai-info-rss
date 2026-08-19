"""三级全文策略编排：
1. RSS 自带全文（content_status == "full"）直用；
2. trafilatura 抓原文提取；
3. 回退 summary_only（模板展示提示横幅 + 原文外链）。
"""
from __future__ import annotations

import trafilatura

from .fetchers.base import make_client
from .models import Article
from .sanitize import sanitize_html

_MIN_FULL_LEN = 400  # 提取结果低于此长度视为失败


def _try_fetch_fulltext(article: Article) -> str:
    with make_client() as client:
        resp = client.get(article.url)
        resp.raise_for_status()
    extracted = trafilatura.extract(
        resp.text, url=article.url, output_format="html", favor_recall=True)
    return extracted or ""


def ensure_fulltext(article: Article, mode: str = "auto",
                    verbose: bool = False) -> Article:
    """按策略补全文章正文（原地修改并返回）。"""
    def log(msg: str):
        if verbose:
            print(f"    [{article.source_id}/{article.id}] {msg}")

    if mode == "never":
        return article

    if article.content_status == "full" and mode == "auto":
        log("RSS 全文直用")
        article.content_html = sanitize_html(article.content_html, article.url)
        return article

    # summary_only 或 always_fetch：尝试抓原文
    try:
        log(f"抓取原文: {article.url}")
        html = _try_fetch_fulltext(article)
    except Exception as e:
        log(f"原文抓取失败: {e}")
        html = ""

    if len(html) >= _MIN_FULL_LEN:
        article.content_html = sanitize_html(html, article.url)
        article.content_status = "fetched"
        log(f"提取成功（{len(html)} 字符）")
    else:
        # 回退：保留已有全文或摘要
        if article.content_status == "full":
            article.content_html = sanitize_html(article.content_html, article.url)
        else:
            article.content_status = "summary_only"
            if article.summary:
                article.summary = sanitize_html(article.summary, article.url)
            log("回退 summary_only")
    return article
