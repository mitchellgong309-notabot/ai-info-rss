# AI_INFO_RSS — 个人 AI 简报聚合静态站

聚合 9 个高质量 AI 信息源（7 RSS + 2 自定义 HTML 抓取），GitHub Actions 定时构建，
部署到 GitHub Pages，支持全文沉浸式阅读。

## 快速开始

```bash
pip install -r requirements.txt
python build.py --verbose          # 全量构建
python build.py --only a16z-ai -v  # 只构建单个源（调试）
python build.py --serve            # 构建后本地预览 http://127.0.0.1:8000
python scripts/verify_links.py dist/  # 校验内部链接
```

## 架构

- `feeds.yaml` — 唯一配置：源的 id/分类/fetcher/URL/链接正则/全文策略/保留策略
- `src/fetchers/` — RSS（httpx+feedparser）与 HTML（列表发现 → 逐篇 trafilatura 提取）
- `src/fulltext.py` — 三级全文策略：RSS 全文直用 → 抓原文 → summary_only 回退（模板提示去原文）
- `src/sanitize.py` — nh3 白名单消毒 + 相对 URL 绝对化
- `src/store.py` — 每源 JSON 持久化，URL 规范化（去 utm_*/fragment/尾斜杠）后 sha1[:16] 为 ID 去重
- `src/generator/site.py` — Jinja2 全量重建 `dist/` + `search-index.json`（全站相对路径，Pages 子路径安全）
- `src/summarizer.py` — AI 摘要预留接口（NoopSummarizer 占位）

## 数据与容错

- `data/` 提交回仓库（构建产物增量累积）；`dist/` 不入库
- 单源失败仅写 `data/health.json` 并在 CI Summary 展示，不阻塞构建
- 保留策略：每源最多 200 篇 / 180 天
- 幂等：数据无变化时二次构建 `git status data/` 干净

## 部署（GitHub Pages）

1. 新建公开空仓库，push 本项目
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**
3. Actions 手动触发 `Build & Deploy`，或等待 cron（每 6 小时）

## 本地限制

Stratechery / First Round Review 在部分本地网络不可达，构建时自动标记失败；
GitHub Actions 海外网络可达，CI 中会正常抓取。
