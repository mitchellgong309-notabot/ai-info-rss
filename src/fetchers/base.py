"""Fetcher 抽象基类与共享 HTTP 工具。"""
from __future__ import annotations

import httpx

from ..config import SourceConfig
from ..models import FetchResult

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 30.0


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
        follow_redirects=True,
        timeout=TIMEOUT,
    )


class Fetcher:
    def __init__(self, source: SourceConfig, verbose: bool = False):
        self.source = source
        self.verbose = verbose

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"    [{self.source.id}] {msg}")

    def fetch(self) -> FetchResult:
        raise NotImplementedError
