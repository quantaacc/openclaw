#!/usr/bin/env python3
"""
RSS 日报生成器
从 OPML 文件解析 RSS 源，抓取昨日内容，生成 AI 总结日报
"""

import subprocess
import sys

# 自动安装缺失依赖
def _ensure_deps():
    required = {'feedparser': 'feedparser', 'pytz': 'pytz'}
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(required[module])

    if not missing:
        return

    print(f"📦 安装依赖: {', '.join(missing)}")

    def run(*cmd):
        """执行命令，任何异常都返回 1（失败）"""
        try:
            return subprocess.call(
                list(cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except (FileNotFoundError, PermissionError, OSError):
            return 1

    # 1. python -m pip
    if run(sys.executable, '-m', 'pip', 'install', '--quiet', *missing) == 0:
        print("✅ 依赖安装完成\n"); return

    # 2. ensurepip 引导后再装
    if run(sys.executable, '-m', 'ensurepip', '--upgrade') == 0:
        if run(sys.executable, '-m', 'pip', 'install', '--quiet', *missing) == 0:
            print("✅ 依赖安装完成\n"); return

    # 3. apt-get 装 pip 后再装
    print("⚙️  尝试 apt-get install python3-pip ...")
    if run('apt-get', 'install', '-y', '-q', 'python3-pip') == 0:
        if run(sys.executable, '-m', 'pip', 'install', '--quiet', *missing) == 0:
            print("✅ 依赖安装完成\n"); return

    # 4. apt-get 直接装系统包
    apt_map = {'feedparser': 'python3-feedparser', 'pytz': 'python3-tz'}
    apt_pkgs = [apt_map[m] for m in missing if m in apt_map]
    if apt_pkgs:
        print(f"⚙️  尝试 apt-get install {' '.join(apt_pkgs)} ...")
        if run('apt-get', 'install', '-y', '-q', *apt_pkgs) == 0:
            print("✅ 依赖安装完成\n"); return

    print("❌ 无法自动安装依赖，请手动执行：")
    print(f"   apt-get install -y python3-pip && pip3 install {' '.join(missing)}")
    sys.exit(1)

_ensure_deps()

import xml.etree.ElementTree as ET
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pytz
import json
from pathlib import Path


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


def fetch_feed(feed_info, timeout=10):
    """抓取单个 RSS 源"""
    try:
        feed = feedparser.parse(feed_info['url'])

        articles = []
        for entry in feed.entries:
            # 提取发布时间
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
                except:
                    pass
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=pytz.UTC)
                except:
                    pass

            # 提取摘要
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary
            elif hasattr(entry, 'description'):
                summary = entry.description

            # 清理 HTML 标签（简单处理）
            import re
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary.strip()

            articles.append({
                'title': entry.get('title', 'No Title'),
                'link': entry.get('link', ''),
                'summary': summary,
                'published': pub_date,
                'source': feed_info['title']
            })

        return {'source': feed_info['title'], 'articles': articles, 'error': None}

    except Exception as e:
        return {'source': feed_info['title'], 'articles': [], 'error': str(e)}


def fetch_all_feeds(feeds, max_workers=20):
    """并发抓取所有 RSS 源"""
    results = []
    total = len(feeds)

    print(f"开始抓取 {total} 个 RSS 源...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_feed, feed): feed for feed in feeds}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)

            # 实时反馈进度
            success = len([r for r in results if not r['error']])
            failed = len([r for r in results if r['error']])
            print(f"进度: {i}/{total} | 成功: {success} | 失败: {failed}", end='\r')

    print()  # 换行
    return results


def filter_yesterday_articles(all_results, days_back=1):
    """过滤出昨日（或最近 N 天）的文章"""

    # 计算目标日期范围（使用本地时区）
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    start_date = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    filtered = []

    for result in all_results:
        if result['error']:
            continue

        for article in result['articles']:
            if article['published']:
                # 转换为本地时区
                local_time = article['published'].astimezone(pytz.timezone('Asia/Shanghai'))
                if start_date <= local_time <= end_date:
                    article['published_local'] = local_time
                    filtered.append(article)

    # 按时间倒序排序
    filtered.sort(key=lambda x: x['published'], reverse=True)

    return filtered, start_date, end_date


def prepare_articles_json(articles, start_date, end_date):
    """准备文章数据的 JSON 格式，供 AI 总结"""

    # 按来源分组统计
    source_stats = {}
    for article in articles:
        source = article['source']
        source_stats[source] = source_stats.get(source, 0) + 1

    # 构建文章列表（限制前 150 篇）
    articles_data = []
    for article in articles[:150]:
        pub_time = article['published_local'].strftime('%Y-%m-%d %H:%M')
        articles_data.append({
            'title': article['title'],
            'source': article['source'],
            'time': pub_time,
            'link': article['link'],
            'summary': article['summary'][:300]  # 限制摘要长度
        })

    # 来源统计 Top 15
    top_sources = sorted(source_stats.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        'meta': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
            'total_articles': len(articles),
            'total_sources': len(source_stats),
            'top_sources': [{'name': s[0], 'count': s[1]} for s in top_sources]
        },
        'articles': articles_data
    }


def generate_ai_prompt(data):
    """生成 AI 总结的 prompt"""

    meta = data['meta']
    articles = data['articles']

    # 构建文章列表文本
    articles_text = []
    for i, article in enumerate(articles, 1):
        articles_text.append(
            f"{i}. **{article['title']}**\n"
            f"   来源: {article['source']} | 时间: {article['time']}\n"
            f"   链接: {article['link']}\n"
            f"   摘要: {article['summary']}\n"
        )

    # 来源统计
    sources_text = '\n'.join([f"- {s['name']}: {s['count']} 篇" for s in meta['top_sources']])

    prompt = f"""你是一位专业的 AI 资讯编辑，请根据以下 RSS 订阅源的昨日更新内容，生成一份结构化日报。

**时间范围**: {meta['start_date']} 至 {meta['end_date']}
**文章总数**: {meta['total_articles']} 篇
**来源数量**: {meta['total_sources']} 个

**来源分布 Top 15**:
{sources_text}

---

**文章列表**:

{chr(10).join(articles_text)}

---

**任务要求**:

1. **识别核心主题**（4-6 个），如：大模型发布、AI 应用、开源项目、行业动态、技术突破、政策监管等
2. **每个主题下选出 3-5 篇最重要的文章**，提供：
   - 标题（保留原标题）
   - 原文链接（必须使用上面提供的真实链接）
   - 一句话总结（20-40 字，提炼核心信息）
3. **生成「今日要点」**（3-5 条，每条 1 句话概括最重要的信息）
4. **输出格式**严格遵循以下模板

---

**输出模板**:

```markdown
# 📰 RSS 日报 · {meta['start_date']}

**时间范围**: {meta['start_date']} 00:00 - {meta['end_date']}
**文章总数**: {meta['total_articles']} 篇
**来源数量**: {meta['total_sources']} 个

---

## 🔥 [主题 1 名称，如：大模型发布]

### 1. [文章标题]
🔗 [原文链接]
📝 [一句话总结，20-40字]

### 2. [文章标题]
🔗 [原文链接]
📝 [一句话总结]

---

## 🔬 [主题 2 名称，如：技术突破]

### 1. [文章标题]
🔗 [原文链接]
📝 [一句话总结]

---

## 💡 [主题 3 名称]

...

---

## 🎯 今日要点

1. [最重要的信息，1 句话，30-50字]
2. [第二重要，1 句话]
3. [第三重要，1 句话]
4. [值得关注的趋势，1 句话]

---

## 📊 来源统计 Top 15

| 来源 | 文章数 |
|------|--------|
{chr(10).join([f"| {s['name']} | {s['count']} |" for s in meta['top_sources']])}

---
*生成时间: {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}*
```

**注意事项**:
- 不要臆造内容，所有信息必须来自上述文章列表
- 链接必须使用原文链接，不得修改或伪造
- 主题分类要合理，避免过于分散或重叠
- 如果某个主题文章不足 3 篇，可以只列出实际数量
- 一句话总结要精炼，突出核心价值，不要只是重复标题
- 今日要点要提炼最有价值的信息，不是简单罗列
"""

    return prompt


def resolve_opml_path():
    """按优先级查找 OPML 文件路径"""
    import os
    candidates = [
        os.environ.get('OPML_PATH', ''),                          # 1. 环境变量
        str(Path(__file__).parent.parent / 'BestBlogs_RSS_ALL.opml'),  # 2. skill 目录（最可靠）
        '/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml',        # 3. Mac 本地路径
        '/home/node/Downloads/BestBlogs_RSS_ALL.opml',            # 4. Docker 容器路径
        '/root/Downloads/BestBlogs_RSS_ALL.opml',                 # 5. root 用户路径
        str(Path.home() / 'Downloads' / 'BestBlogs_RSS_ALL.opml'),# 6. 当前用户 Downloads
        str(Path(__file__).parent.parent / 'BestBlogs_RSS_ALL.opml'),  # 6. skill 目录
    ]
    for path in candidates:
        if path and Path(path).exists():
            return path
    return None


def main():
    """主函数"""

    days_back = 1

    # 支持命令行参数：python3 generate_rss_report.py [天数] [opml路径]
    if len(sys.argv) > 1:
        try:
            days_back = int(sys.argv[1])
        except:
            print(f"无效的天数参数: {sys.argv[1]}，使用默认值 1")

    # 解析 OPML 路径
    opml_path = sys.argv[2] if len(sys.argv) > 2 else resolve_opml_path()
    if not opml_path:
        print("❌ 找不到 OPML 文件，请通过以下方式指定路径：")
        print("   1. 环境变量: export OPML_PATH=/path/to/file.opml")
        print("   2. 命令行参数: python3 generate_rss_report.py 1 /path/to/file.opml")
        sys.exit(1)

    print("=" * 60)
    print("📰 RSS 日报生成器")
    print("=" * 60)
    print()

    # Phase 1: 解析 OPML
    print("📖 Phase 1: 解析 OPML...")
    feeds = parse_opml(opml_path)
    print(f"✅ 找到 {len(feeds)} 个 RSS 源\n")

    # Phase 2: 抓取 RSS Feed
    print("🌐 Phase 2: 抓取 RSS Feed...")
    results = fetch_all_feeds(feeds, max_workers=30)

    success_count = len([r for r in results if not r['error']])
    failed_count = len([r for r in results if r['error']])
    total_articles = sum([len(r['articles']) for r in results if not r['error']])

    print(f"✅ 抓取完成: 成功 {success_count} | 失败 {failed_count} | 总文章数 {total_articles}\n")

    # Phase 3: 过滤昨日内容
    print(f"🔍 Phase 3: 过滤最近 {days_back} 天的内容...")
    filtered_articles, start_date, end_date = filter_yesterday_articles(results, days_back)
    print(f"✅ 找到 {len(filtered_articles)} 篇文章\n")

    if len(filtered_articles) == 0:
        print("⚠️  没有找到符合条件的文章，请检查日期范围或 RSS 源")
        return

    # Phase 4: 准备数据
    print("📊 Phase 4: 准备数据...")
    data = prepare_articles_json(filtered_articles, start_date, end_date)

    # 保存数据到临时文件
    output_dir = Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True)

    data_file = output_dir / 'rss_data.json'
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 数据已保存到: {data_file}\n")

    # Phase 5: 生成 AI Prompt
    print("🤖 Phase 5: 生成 AI Prompt...")
    prompt = generate_ai_prompt(data)

    prompt_file = output_dir / 'ai_prompt.txt'
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"✅ Prompt 已保存到: {prompt_file}\n")

    print("=" * 60)
    print("✅ 数据准备完成！")
    print("=" * 60)
    print()
    print("📝 下一步：将 ai_prompt.txt 的内容发送给 AI 模型进行总结")
    print()

    # 输出 prompt（供 Claude 直接使用）
    print("=" * 60)
    print("AI PROMPT (可直接复制使用)")
    print("=" * 60)
    print()
    print(prompt)


if __name__ == '__main__':
    main()
