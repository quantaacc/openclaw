---
name: ai-recorder-news
description: "Use when user asks for daily competitor intelligence on AI recording card hardware devices (卡片式AI录音设备), wearable AI notetakers, AI recorder pins/pendants. Triggers on: 'AI录音卡竞品', '录音卡动态', 'AI录音硬件', 'recorder news', 'PLAUD', '钉钉录音卡', or /recorder-news command."
---

# AI录音卡竞品每日动态

每日追踪国内外卡片式/可穿戴 AI 录音硬件设备的竞品动态。

## 命令

### `/recorder-news`

运行每日竞品动态分析。

---

## 竞品监控范围

### 国外竞品

| 产品 | 公司 | 形态 | 价格 |
|------|------|------|------|
| PLAUD Note Pro | PLAUD | 卡片式，4麦 | $179 |
| PLAUD NotePin / NotePin S | PLAUD | 可穿戴吊坠 | $159–179 |
| Anker Soundcore Work | Anker | 硬币大小 | $159 |
| Mobvoi TicNote | Mobvoi | 可穿戴，3麦 | $159 |
| Comulytic Note Pro | Comulytic | 小型录音卡 | $159 |
| Omi Pendant | Omi | 开源吊坠 | $89 |
| Viaim RecDot | Viaim | 耳机+录音 | $200 |
| Rewind Pendant | Rewind | 可穿戴 | — |

### 国内竞品

| 产品 | 公司 | 备注 |
|------|------|------|
| 钉钉录音卡 | 阿里/钉钉 | 企业场景 |
| 讯飞智能录音笔 SR系列 | 科大讯飞 | 硬件+转写 |
| HONOR × PLAUD 联名 | 荣耀 | 原生AI录音功能 |
| 搜狗录音笔 | 搜狗/腾讯 | 硬件录音 |

---

## 环境配置

```bash
export TAVILY_API_KEY="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"
```

Tavily 脚本路径：`TAVILY_DIR` = tavily skill 的 `scripts/` 目录（参考 tavily skill 的 `{baseDir}`）

---

## 执行流程

搜索策略：**Tavily（主）+ Chrome 搜索（补充）**

- Tavily `--topic news --days 3`：抓取最新新闻，结果干净适合 AI 处理
- Chrome 搜索：用于中文内容、国内平台（微信公众号、36kr、少数派等）Tavily 覆盖不到的内容

### Phase 1: 国外竞品 — Tavily

```bash
# 新品上市 + 功能更新
TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "PLAUD Note recorder new product launch update" --topic news --days 3

TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "Anker Soundcore Work Mobvoi TicNote Comulytic AI recorder news" --topic news --days 3

TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "wearable AI recorder card new release price change 2026" --topic news --days 3

# 价格变动专项
TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "PLAUD Omi Viaim Rewind AI recorder price discount sale" --topic news --days 7
```

### Phase 2: 国内竞品 — Chrome 搜索

Chrome 搜索以下关键词（中文内容 Tavily 覆盖有限）：

```
钉钉录音卡 新功能 发布 2026
讯飞智能录音笔 新品 价格
AI录音卡 国内 新品 上市
AI录音硬件 融资 发布
```

同时用 Tavily 补充英文报道：

```bash
TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "DingTalk AI recorder iFlytek voice recorder China new product" --topic news --days 7
```

### Phase 3: 新品上市专项 — Tavily

```bash
TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "AI notetaker recorder hardware new product launch 2026" --topic news --days 7 -n 10

TAVILY_API_KEY=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 \
node {TAVILY_DIR}/search.mjs "AI voice recorder card funding acquisition 2026" --topic news --days 14
```

### Phase 4: 深度阅读

对搜索结果中的重要文章，用 Tavily extract 获取全文：

```bash
TAVILY_API_KEY=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 \
node {TAVILY_DIR}/extract.mjs "https://article-url"
```

### Phase 5: 内容过滤

**保留**：
- 🆕 新品上市（新型号、新系列）
- 💰 价格变动（涨价、降价、促销、订阅费调整）
- ✨ 功能更新（固件、App、转写精度）
- 💵 融资/收购/合作
- 📊 用户数据/市场份额

**过滤**：重复报道、3天以上旧闻（重大事件除外）、纯营销软文

---

## 输出格式

```markdown
# 🎙️ AI录音卡竞品每日动态

**日期**: [当前日期]  |  **数据时间**: 最近 72 小时

---

## 🆕 新品上市

> 无新品时省略此节

### [产品名] — [型号/系列名]

**发布信息**: [价格、规格、上市时间]
**核心卖点**: [1-2句]
**竞争影响**: [对现有格局的冲击]

📅 来源: [媒体] · [日期]  🔗 [链接]

---

## 💰 价格变动

> 无变动时省略此节

### [产品名] — [涨价/降价/促销/订阅调整]

**变动详情**: [原价 → 新价，或促销内容]
**生效时间**: [日期]
**可能原因**: [竞争压力/新品替代/季节促销等]

📅 来源: [媒体] · [日期]  🔗 [链接]

---

## 🌍 国外其他动态

### [产品名] — [标题]

**摘要**: [一句话概述]
**关键信息**:
- [要点1]
- [要点2]

**竞争影响**: [1句]

📅 来源: [媒体] · [日期]  🔗 [链接]

---

## 🇨🇳 国内动态

### [产品名] — [标题]

[同上格式]

---

## 📊 今日洞察

**新品/价格动向**: [今日最值得关注的新品或价格变化]
**国外趋势**: [1-2句]
**国内趋势**: [1-2句]
**战略建议**: [对自身产品的1条启示]

---
**生成时间**: [时间戳]
```

---

## 无新动态处理

搜索无结果时直接标注：

```
## 🇨🇳 国内动态
> 今日暂无重大竞品动态（最近72小时内）
```

不捏造内容。

---

## 深度追踪

用户追问时，用 `WebFetch` 抓取原文做深度分析：
- "详细分析 [产品] 这次更新"
- "这对我们产品有什么影响？"
- "找 [产品] 最近一个月的动态"
