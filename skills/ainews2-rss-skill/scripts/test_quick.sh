#!/bin/bash
# 快速测试脚本：只抓取前 10 个 RSS 源

cd "$(dirname "$0")"

echo "🧪 快速测试模式：只抓取前 10 个 RSS 源"
echo ""

python3 << 'PYTHON_EOF'
from generate_rss_report import parse_opml, fetch_all_feeds, filter_yesterday_articles, prepare_articles_json
import json

# 1. 解析 OPML
opml_path = '/Users/donghan/Downloads/BestBlogs_RSS_ALL.opml'
feeds = parse_opml(opml_path)
print(f"✅ 解析 OPML: 找到 {len(feeds)} 个源\n")

# 2. 只抓取前 10 个源
test_feeds = feeds[:10]
print(f"🌐 抓取前 {len(test_feeds)} 个源进行测试...\n")
results = fetch_all_feeds(test_feeds, max_workers=5)

# 3. 过滤昨日内容
filtered, start_date, end_date = filter_yesterday_articles(results, days_back=1)
print(f"\n✅ 过滤完成:")
print(f"   时间范围: {start_date.strftime('%Y-%m-%d %H:%M')} - {end_date.strftime('%Y-%m-%d %H:%M')}")
print(f"   昨日文章: {len(filtered)} 篇\n")

# 4. 准备数据并保存
if len(filtered) > 0:
    data = prepare_articles_json(filtered, start_date, end_date)
    
    # 保存为 JSON
    output_file = f"test_rss_articles_{start_date.strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"📊 数据统计:")
    print(f"   总文章数: {data['meta']['total_articles']}")
    print(f"   来源数量: {data['meta']['total_sources']}")
    print(f"   已保存到: {output_file}\n")
    
    print(f"📝 前 5 篇文章:")
    for i, article in enumerate(data['articles'][:5], 1):
        print(f"   {i}. {article['title'][:60]}...")
        print(f"      来源: {article['source']} | 时间: {article['time']}")
        print(f"      链接: {article['link'][:80]}...")
        print()
else:
    print("⚠️  没有找到昨日文章，尝试扩大时间范围：")
    print("   python3 generate_rss_report.py 3")

print("✅ 测试完成！")
PYTHON_EOF
