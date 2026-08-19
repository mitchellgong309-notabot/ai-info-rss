"""构建入口：python build.py [--verbose] [--only <source_id>] [--serve]"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Windows/CI 一致性：显式 UTF-8
if sys.platform == "win32":
    os.system("")  # 启用 ANSI
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="AI_INFO_RSS 构建器")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--only", help="只构建指定 source_id（调试用）")
    parser.add_argument("--serve", action="store_true", help="构建后本地预览 dist/")
    args = parser.parse_args()

    from src.config import load_config
    from src.pipeline import run_build

    cfg = load_config(ROOT / "feeds.yaml")
    if args.only:
        if not cfg.source_by_id(args.only):
            print(f"未知 source_id: {args.only}")
            return 2
        cfg.sources = [s for s in cfg.sources if s.id == args.only]

    result = run_build(cfg, verbose=args.verbose)

    if args.serve:
        serve(ROOT / "dist")
    return 0


def serve(dist: Path) -> None:
    if not dist.exists():
        print("dist/ 不存在")
        return
    os.chdir(dist)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", 8000), handler) as httpd:
        print("预览: http://127.0.0.1:8000/ (Ctrl+C 退出)")
        httpd.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
