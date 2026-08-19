"""构建后校验 dist/ 内部链接与资源引用完整性。

用法: python scripts/verify_links.py [dist路径]
退出码非 0 表示存在断链。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def collect_targets(dist: Path) -> set[str]:
    # 用 as_posix 统一分隔符，避免 Windows/Posix Path 混用比较失败
    return {p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()}


def check_file(html: Path, dist: Path, targets: set[Path]) -> list[str]:
    text = html.read_text(encoding="utf-8", errors="replace")
    problems = []
    for m in re.finditer(r'(?:href|src)=["\']([^"\'#]+)["\']', text):
        url = m.group(1)
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or url.startswith("mailto:"):
            continue  # 外链/锚点不校验
        rel = unquote(parts.path)
        if not rel:
            continue
        target = html.parent / rel
        try:
            rel_target = target.resolve().relative_to(dist.resolve()).as_posix()
        except ValueError:
            problems.append(f"{html.name}: 指向站外路径 {url}")
            continue
        if rel_target not in targets:
            problems.append(f"{html.relative_to(dist)}: 断链 {url}")
    return problems


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    if not dist.exists():
        print(f"目录不存在: {dist}")
        return 2
    targets = collect_targets(dist)
    problems: list[str] = []
    for html in dist.rglob("*.html"):
        problems.extend(check_file(html, dist, targets))
    if problems:
        for p in problems:
            print("BROKEN:", p)
        print(f"共 {len(problems)} 个断链")
        return 1
    print(f"链接校验通过: {len(targets)} 个文件, "
          f"{sum(1 for t in targets if t.endswith('.html'))} 个 HTML 页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
