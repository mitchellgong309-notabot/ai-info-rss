"""AI 摘要预留接口：Summarizer 协议 + NoopSummarizer。

未来接入 LLM 时实现该协议，在 pipeline 中替换 NoopSummarizer 即可。
"""
from __future__ import annotations

from typing import Protocol

from .models import Article


class Summarizer(Protocol):
    def summarize(self, article: Article) -> str:
        """返回文章摘要（AI 生成），失败可返回空串回退原有 summary。"""
        ...


class NoopSummarizer:
    def summarize(self, article: Article) -> str:
        return ""
