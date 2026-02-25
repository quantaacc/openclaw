# /ainews2 — RSS 日报生成器

从本地 OPML 文件解析 RSS 源，自动抓取昨日更新内容，AI 总结成结构化日报。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 使用方式

在 Claude Code 中输入：

```
/ainews2
```

或指定天数：

```
/ainews2 3
```

## 工作流程

1. **解析 OPML** — 从 `/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml` 提取所有 RSS 源
2. **并发抓取** — 使用 20 线程并发抓取所有 RSS Feed
3. **过滤昨日** — 筛选出昨日 00:00 - 现在的文章
4. **AI 总结** — 将文章数据发送给 AI，生成结构化日报
5. **输出日报** — Markdown 格式，包含主题分类、原文链接、统计数据

## 输出格式

```markdown
# 📰 RSS 日报 · 2026-02-20

**时间范围**: 2026-02-20 00:00 - 2026-02-21 10:30
**文章总数**: 156 篇
**来源数量**: 42 个

---

## 🔥 大模型发布

### 1. DeepSeek-V3 开源发布
🔗 [原文链接](...)
📝 DeepSeek 发布 V3 版本，671B MoE 架构，性能超越 GPT-4

### 2. ...

---

## 🔬 技术突破

### 1. ...

---

## 🎯 今日要点

1. DeepSeek-V3 开源，MoE 架构突破性能瓶颈
2. OpenAI 推出 GPT-5 预览版，多模态能力大幅提升
3. AI 监管政策密集出台，行业进入规范化阶段

---

## 📊 来源统计 Top 15

| 来源 | 文章数 |
|------|--------|
| 机器之心 | 12 |
| AI前线 | 8 |
| ...

---
*生成时间: 2026-02-21 10:30*
```

## 技术细节

### OPML 解析

使用 `xml.etree.ElementTree` 解析 OPML 文件，提取所有 `<outline type="rss">` 节点的 `xmlUrl` 属性。

### RSS 抓取

- 使用 `feedparser` 库解析 RSS/Atom Feed
- 并发抓取（20 线程），单个源超时 10 秒
- 自动处理多种日期格式（`published_parsed`、`updated_parsed`）

### 日期过滤

- 使用 `pytz` 处理时区（默认 Asia/Shanghai）
- 昨日定义：昨天 00:00 到现在
- 支持自定义天数（如最近 3 天）

### AI 总结

- 将文章数据转换为 JSON 格式
- 限制前 150 篇文章（避免 token 超限）
- 提供结构化 prompt，要求 AI 按主题分类、提取要点

## 文件结构

```
ainews2-rss-skill/
├── SKILL.md                    # Skill 文档
├── _meta.json                  # Skill 元数据
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
└── scripts/
    └── generate_rss_report.py  # 核心脚本
```

## 依赖

- Python 3.8+
- feedparser 6.0.10+
- pytz 2024.1+

## 常见问题

### Q: 为什么有些 RSS 源抓取失败？

A: 可能原因：
- 网络超时（默认 10 秒）
- RSS 源失效或格式错误
- 防爬虫限制

脚本会自动跳过失败的源，不影响整体流程。

### Q: 如何修改 OPML 文件路径？

A: 编辑 `scripts/generate_rss_report.py`，修改 `DEFAULT_OPML_PATH` 变量。

### Q: 如何调整抓取的天数？

A: 使用 `/ainews2 [天数]`，如 `/ainews2 3` 抓取最近 3 天。

### Q: 输出的日报保存在哪里？

A: 脚本会将文章数据保存为 JSON 文件（`rss_articles_[date].json`），AI 总结的日报直接输出到终端。

## 许可

MIT License
