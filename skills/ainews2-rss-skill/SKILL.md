---
name: ainews2-rss
trigger: /ainews2
description: "从本地 OPML 文件解析 RSS 源，抓取昨日更新内容，AI 总结成日报。输入 /ainews2 即可生成。"
---

# AI News 2 — AI日报生成器

> 从 BestBlogs OPML 订阅源自动抓取昨日内容，AI 总结成结构化日报

## 触发方式

- `/ainews2` — 生成昨日 RSS 日报
- `/ainews2 [天数]` — 生成最近 N 天的日报（如 `/ainews2 3`）

## 使用步骤

当用户输入 `/ainews2` 时，执行以下步骤：

1. **运行脚本**（依赖会自动安装）：
   ```bash
   python3 /home/node/.openclaw/workspace/skills/ainews2-rss-skill/scripts/generate_rss_report.py [天数，默认1]
   ```

2. **OPML 路径解析**（按优先级）：
   - 环境变量 `OPML_PATH`
   - `/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml`（Mac）
   - `/home/node/Downloads/BestBlogs_RSS_ALL.opml`（Docker）
   - `~/Downloads/BestBlogs_RSS_ALL.opml`（当前用户）

3. **读取输出 JSON**：脚本将文章数据保存到 `output/rss_data.json`

4. **AI 总结**：读取 JSON 文件，按模板生成结构化日报

5. **输出日报**：展示 Markdown 格式日报

---

## Workflow

```
Phase 1: 解析 OPML
  └─ 从 /Users/donghan/Downloads/BestBlogs_RSS_ALL.opml 提取所有 RSS URL
      ↓
Phase 2: 抓取 RSS Feed
  ├─ 并发请求所有 RSS 源（带超时控制）
  └─ 解析 XML，提取文章元数据（标题、链接、日期、摘要）
      ↓
Phase 3: 过滤昨日内容
  ├─ 计算昨日日期范围（00:00 - 23:59）
  └─ 过滤出发布时间在昨日的文章
      ↓
Phase 4: AI 总结
  ├─ 按来源分组
  ├─ 提取关键主题
  └─ 生成结构化日报
      ↓
Phase 5: 输出格式化日报
  └─ Markdown 格式，包含统计、分类、原文链接
```

---

## Phase 1: 解析 OPML

使用 Python 解析 OPML 文件，提取所有 RSS 源：

```python
import xml.etree.ElementTree as ET

def parse_opml(opml_path):
    """解析 OPML 文件，返回 RSS 源列表"""
    tree = ET.parse(opml_path)
    root = tree.getroot()

    feeds = []
    for outline in root.findall('.//outline[@type="rss"]'):
        feeds.append({
            'title': outline.get('title', outline.get('text', 'Unknown')),
            'url': outline.get('xmlUrl')
        })

    return feeds

# 使用示例
opml_path = '/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml'
feeds = parse_opml(opml_path)
print(f"找到 {len(feeds)} 个 RSS 源")
```

---

## Phase 2: 抓取 RSS Feed

使用 `feedparser` 库并发抓取所有 RSS 源：

```python
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pytz

def fetch_feed(feed_info, timeout=10):
    """抓取单个 RSS 源"""
    try:
        feed = feedparser.parse(feed_info['url'], timeout=timeout)

        articles = []
        for entry in feed.entries:
            # 提取发布时间
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6], tzinfo=pytz.UTC)

            articles.append({
                'title': entry.get('title', 'No Title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': pub_date,
                'source': feed_info['title']
            })

        return {'source': feed_info['title'], 'articles': articles, 'error': None}

    except Exception as e:
        return {'source': feed_info['title'], 'articles': [], 'error': str(e)}

def fetch_all_feeds(feeds, max_workers=20):
    """并发抓取所有 RSS 源"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_feed, feed): feed for feed in feeds}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            # 实时反馈进度
            success = len([r for r in results if not r['error']])
            print(f"进度: {len(results)}/{len(feeds)} | 成功: {success}")

    return results
```

**依赖安装**：
```bash
pip install feedparser pytz
```

---

## Phase 3: 过滤昨日内容

```python
from datetime import datetime, timedelta
import pytz

def filter_yesterday_articles(all_results, days_back=1):
    """过滤出昨日（或最近 N 天）的文章"""

    # 计算目标日期范围
    now = datetime.now(pytz.UTC)
    start_date = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    filtered = []

    for result in all_results:
        if result['error']:
            continue

        for article in result['articles']:
            if article['published'] and start_date <= article['published'] <= end_date:
                filtered.append(article)

    # 按时间倒序排序
    filtered.sort(key=lambda x: x['published'], reverse=True)

    return filtered, start_date, end_date
```

---

## Phase 4: AI 总结

将过滤后的文章发送给 AI 进行总结：

```python
def prepare_summary_prompt(articles, start_date, end_date):
    """准备 AI 总结的 prompt"""

    # 按来源分组统计
    source_stats = {}
    for article in articles:
        source = article['source']
        source_stats[source] = source_stats.get(source, 0) + 1

    # 构建文章列表
    articles_text = []
    for i, article in enumerate(articles[:100], 1):  # 限制前 100 篇
        pub_time = article['published'].strftime('%Y-%m-%d %H:%M')
        articles_text.append(
            f"{i}. **{article['title']}**\n"
            f"   来源: {article['source']} | 时间: {pub_time}\n"
            f"   链接: {article['link']}\n"
            f"   摘要: {article['summary'][:200]}...\n"
        )

    prompt = f"""
你是一位专业的 AI 资讯编辑，请根据以下 RSS 订阅源的昨日更新内容，生成一份结构化日报。

**时间范围**: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}
**文章总数**: {len(articles)} 篇
**来源数量**: {len(source_stats)} 个

**来源分布 Top 10**:
{chr(10).join([f"- {source}: {count} 篇" for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)[:10]])}

---

**文章列表**:

{chr(10).join(articles_text)}

---

**任务要求**:

1. **识别核心主题**（3-5 个），如：大模型发布、AI 应用、行业动态、技术突破等
2. **每个主题下选出 3-5 篇最重要的文章**，提供：
   - 标题（保留原标题）
   - 原文链接
   - 一句话总结（15-30 字）
3. **生成「今日要点」**（3 条，每条 1 句话概括最重要的信息）
4. **输出格式**严格遵循以下模板

---

**输出模板**:

```markdown
# 📰 AI资讯 日报 · {date}

**时间范围**: {start} - {end}
**文章总数**: {total} 篇
**来源数量**: {sources} 个

---

## 🔥 [主题 1 名称]

### 1. [文章标题]
🔗 [原文链接]
📝 [一句话总结]

### 2. [文章标题]
...

---

## 🔬 [主题 2 名称]

### 1. [文章标题]
...

---

## 🎯 今日要点

1. [最重要的信息，1 句话]
2. [第二重要，1 句话]
3. [值得关注的趋势，1 句话]

---

## 📊 来源统计 Top 10

| 来源 | 文章数 |
|------|--------|
| [来源名] | [数量] |
...

---
*生成时间: {timestamp}*
```

**注意**:
- 不要臆造内容，所有信息必须来自上述文章列表
- 链接必须使用原文链接，不得修改
- 主题分类要合理，避免过于分散
- 如果某个主题文章不足 3 篇，可以只列出实际数量
"""

    return prompt
```

---

## Phase 5: 输出格式化日报

完整执行流程：

```python
def generate_rss_report(opml_path, days_back=1):
    """完整流程：生成 RSS 日报"""

    print("📖 Phase 1: 解析 OPML...")
    feeds = parse_opml(opml_path)
    print(f"✅ 找到 {len(feeds)} 个 RSS 源\n")

    print("🌐 Phase 2: 抓取 RSS Feed...")
    results = fetch_all_feeds(feeds, max_workers=20)
    success_count = len([r for r in results if not r['error']])
    print(f"✅ 成功抓取 {success_count}/{len(feeds)} 个源\n")

    print("🔍 Phase 3: 过滤昨日内容...")
    articles, start_date, end_date = filter_yesterday_articles(results, days_back)
    print(f"✅ 找到 {len(articles)} 篇昨日文章\n")

    if len(articles) == 0:
        return "⚠️ 未找到昨日更新的文章，请检查 RSS 源或调整时间范围。"

    print("🤖 Phase 4: AI 总结中...")
    prompt = prepare_summary_prompt(articles, start_date, end_date)

    # 这里返回 prompt，由 Claude 执行总结
    return prompt

# 执行
opml_path = '/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml'
prompt = generate_rss_report(opml_path, days_back=1)
print(prompt)
```

---

## 使用说明

### 1. 安装依赖

```bash
pip install feedparser pytz
```

### 2. 执行命令

用户输入 `/ainews2` 后，执行以下步骤：

1. 运行 Python 脚本，生成 AI 总结 prompt
2. 将 prompt 发送给 Claude
3. Claude 根据 prompt 生成格式化日报
4. 输出最终日报

### 3. 自定义时间范围

```bash
/ainews2 3  # 生成最近 3 天的日报
```

---

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| OPML 文件不存在 | 提示用户检查路径 |
| RSS 源无法访问 | 跳过，记录失败源 |
| 解析 XML 失败 | 跳过，继续处理其他源 |
| 无昨日文章 | 提示扩大时间范围 |
| 文章数量过多 | 只取前 100 篇进行总结 |

---

## 输出示例

```markdown
# 📰 RSS 日报 · 2026-02-20

**时间范围**: 2026-02-20 00:00 - 2026-02-21 00:00
**文章总数**: 87 篇
**来源数量**: 34 个

---

## 🔥 大模型发布

### 1. DeepSeek 发布 R2 推理模型
🔗 https://example.com/deepseek-r2
📝 DeepSeek 推出新一代推理模型，性能超越 GPT-4

### 2. Anthropic Claude 3.5 Sonnet 更新
🔗 https://example.com/claude-update
📝 Claude 3.5 Sonnet 新增多模态能力和更长上下文

---

## 🎯 今日要点

1. DeepSeek R2 推理模型发布，推理能力大幅提升
2. 多家 AI 公司宣布融资，总额超 5 亿美元
3. 欧盟 AI 法案正式生效，影响全球 AI 监管

---

## 📊 来源统计 Top 10

| 来源 | 文章数 |
|------|--------|
| 机器之心 | 12 |
| AI前线 | 8 |
| 宝玉 | 7 |
...

---
*生成时间: 2026-02-21 09:30*
```

---

## 技术细节

### RSS 日期解析优先级

1. `published_parsed` — 首选
2. `updated_parsed` — 备选
3. 如果都没有，跳过该文章

### 并发控制

- 默认 20 个并发线程
- 每个请求超时 10 秒
- 失败的源不影响其他源

### 性能优化

- 只解析前 100 篇文章（避免 token 超限）
- 摘要截断至 200 字符
- 按时间倒序排序，优先展示最新内容

---

## 后续扩展

- **导出功能**: 保存为 Markdown 文件
- **邮件推送**: 每日自动发送到邮箱
- **主题订阅**: 只关注特定主题（如"大模型"）
- **去重优化**: 识别同一事件的不同报道
