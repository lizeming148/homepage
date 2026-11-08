---
name: add-movie-to-english-hub
description: 为李泽民的"用电影学英语"项目添加一部新电影的学习页面。当用户上传一组英文电影字幕文件（通常按章节命名如 01_movie.txt、02_movie.txt），并表达想为这部电影制作学习页面、加入到 english.lizeming.net 时触发。任务包括：解析字幕、生成单部电影的学习 HTML 页面、更新英语库索引页、指导用户上传到 GitHub。
---

# 用电影学英语 · 添加新电影 Skill

## 1. 项目背景（必读）

李泽民经营两个 GitHub Pages 站点：

| 站点 | URL | GitHub 仓库 | 用途 |
|------|-----|------------|------|
| 个人主页 | https://www.lizeming.net/ | `lizeming148/homepage` | 个人主页，不需要改 |
| 英语库 | https://english.lizeming.net/ | `lizeming148/english` | 电影学习项目 |

**`english` 仓库的结构**：

```
english/
├── index.html              ← 索引页（列出所有电影）
├── 12-angry-men/
│   └── index.html          ← 第一部电影学习页
└── {新电影目录}/
    └── index.html          ← 你这次要生成的页面
```

每部电影一个子目录，子目录名是电影英文标题的 **kebab-case**（小写连字符），如 `pursuit-of-happyness`、`forrest-gump`。

## 2. 用户会提供什么

- 一组 `.txt` 文件，纯英文对白（无时间戳，可能无说话人标识）
- 命名格式通常是 `NN_movie_title.txt`，按章节顺序
- 可能会有重复文件（用户上传时误传），需要自动去重
- 用户**可能不会**主动告诉你电影完整信息（年份、导演等），你需要：
  - 优先从字幕推断
  - 必要时用 web_search 确认（电影名 + 年份 + 导演）

## 3. 执行流程

### Step 1：理解输入

1. 读所有字幕文件，按文件名前缀的章节号排序
2. **去重**：如果章节 01 和 02 内容完全相同，保留一份并告知用户
3. 通读全部对白，理解电影核心剧情
4. 确认电影的中英文名、上映年份、导演、类型（必要时网搜）

### Step 2：和用户确认

在生成代码前，**先用文字向用户汇报以下信息**：

- 电影识别结果（中文名、英文名、年份、导演）
- 章节数（去重后）
- 计划的子目录名（kebab-case 英文）
- 计划生成的内容板块（剧情简介、双语对白、词汇、习语等）

让用户确认后再生成 HTML。**绝对不要在没确认电影信息的情况下直接生成几千行代码**。

### Step 3：生成电影学习页面

按下方"页面设计规范"生成 `{kebab-case-name}/index.html`。

### Step 4：生成更新后的索引页

读懂下方"索引页规范"，生成新的 `english/index.html`（仓库根目录），把新电影加入电影库网格，并删除旧的"即将上线"占位卡（如果占位卡指向的就是这部电影的话）。

### Step 5：指导用户上传

给用户清晰的上传步骤：

1. 在 GitHub 的 `english` 仓库点击 **"Add file" → "Create new file"**
2. 文件路径输入：`{kebab-case-name}/index.html`（输入斜杠会自动创建文件夹）
3. 粘贴生成的电影页 HTML，commit
4. 然后**覆盖**根目录的 `index.html`（点击文件 → 编辑按钮 → 全选删除 → 粘贴新内容 → commit）
5. 等 1-2 分钟 GitHub Pages 部署完成
6. 验证两个 URL：`https://english.lizeming.net/`（索引页应该出现新卡片）和 `https://english.lizeming.net/{kebab-case-name}/`（新电影页）

---

## 4. 页面设计规范（电影学习页）

### 设计原则

- **简约不简陋**：低密度、留白充分，但每个元素都有信息含量
- **视觉延续**：与个人主页和英语索引页用同一套设计语言
- **学习导向**：每个章节都要让学习者带走点东西（词汇、表达、文化点）

### 字体

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

- 中文标题/正文：`Noto Serif SC`
- 英文 UI 元素：`Inter`

### CSS 变量（必须照搬）

```css
:root {
    --bg: #FAFAF8;
    --text: #1C1C1C;
    --text-secondary: #5A5A58;
    --text-tertiary: #8A8A88;
    --accent: #2B5B4B;
    --accent-soft: #E8F0EC;
    --card-bg: #FFFFFF;
    --border: #E5E5E0;
    --border-soft: #EFEFEA;
    --quote-bg: #F5F2EC;
}
```

### 页面结构

```
┌─────────────────────────────────────────────────┐
│ ← 用电影学英语                                  │ ← 面包屑
├─────────────────────────────────────────────────┤
│                                                 │
│  电影中文标题（大）                              │
│  English Title (斜体)                            │
│  2006 · 加布里埃莱·穆奇诺 · 传记/励志             │ ← 元信息
│                                                 │
│  电影简介（中文，2-3 句）                        │
│                                                 │
├─────────────────────────────────────────────────┤
│ [章节1] [章节2] [章节3] ...      [全片词汇]      │ ← 章节导航（sticky）
├─────────────────────────────────────────────────┤
│                                                 │
│  ## 第一章：标题                                │
│  剧情简介（中文 1-2 句）                         │
│                                                 │
│  ┌─────────────────┬─────────────────┐         │
│  │ 英文对白         │ 中文对照         │         │ ← 双语对照
│  │ ...              │ ...              │         │
│  └─────────────────┴─────────────────┘         │
│                                                 │
│  ### 重点词汇                                   │
│  ┌──────┬──────┬──────┐                        │
│  │ 词1   │ 词2   │ 词3   │                       │ ← 词汇卡片
│  └──────┴──────┴──────┘                        │
│                                                 │
│  ### 关键句赏析                                  │
│  "I'd love to..." — 解释                       │ ← 引用块样式
│                                                 │
│  ─────────────────────────────────             │ ← 章节分隔
│                                                 │
│  ## 第二章：标题                                │
│  ...                                            │
│                                                 │
│  ─────────────────────────────────             │
│                                                 │
│  ## 全片词汇总览                                 │
│  按主题分组                                     │
│                                                 │
├─────────────────────────────────────────────────┤
│ © 2025 · 返回主页                               │
└─────────────────────────────────────────────────┘
```

### 关键组件 CSS 参考

**容器**：
```css
.container { max-width: 860px; margin: 0 auto; padding: 64px 24px 100px; }
```

**面包屑**：
```css
.breadcrumb a { 
    color: var(--text-tertiary); 
    border-bottom: 1px dotted var(--text-tertiary); 
    text-decoration: none; 
}
```
链接指向 `https://english.lizeming.net/`，文案 `← 用电影学英语`。

**Hero**：电影标题 `font-family: 'Noto Serif SC'; font-size: 2.4rem; font-weight: 700`。英文副标题斜体灰色。元信息用 · 分隔。

**章节导航**：`position: sticky; top: 0`，半透明白色背景（`backdrop-filter: blur(8px)`），下边框 1px。每个 tab 是按钮，激活态下边框 2px solid var(--accent)。点击切换章节（用 JavaScript 控制章节区域 display）。

**双语对照对白**：CSS Grid `grid-template-columns: 1fr 1fr`。每条对白一行，英文左中文右，中间细分隔。移动端堆叠成单列。

**词汇卡片**：`grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px`。每张卡片：
- 顶部：词/词组（粗体）+ 词性（小字斜体灰色）
- 中部：中文释义
- 底部：原句例句（引用样式，小一号字号）

**关键句赏析**：左侧 3px solid var(--accent) 竖线，背景 var(--quote-bg)，内边距 16px 20px。

**章节分隔**：上下各 64px margin，中间一条 1px 灰色细线。

### 移动端适配

```css
@media (max-width: 720px) {
    .container { padding: 48px 20px 80px; }
    .hero h1 { font-size: 1.8rem; }
    .dialogue-row { grid-template-columns: 1fr; } /* 双语对照堆叠 */
}
```

---

## 5. 内容生成规范

### 章节标题
不要直接抄字幕第一句。**根据剧情概括出一个章节主题**，如：
- 第一章：父亲的早晨（讲 Chris 早上送儿子上学的开场）
- 第二章：兜售扫描仪的日常（讲他做推销员的窘境）

### 剧情简介
1-2 句中文，**点明该章发生了什么、谁推动了情节**。不要剧透下一章。

### 双语对照对白

- **保留英文原句**，**不要篡改**
- 中文翻译要自然、口语化，不必字字对应
- **省略环境音、舞台指示**（如果字幕里有 [phone ringing] 之类）
- 太长的独白可以适度分段（每段 1-3 句）
- 每条对白英文在左，中文在右

### 重点词汇（每章 5-8 个）

**选择标准**：
- ✅ 实用：日常高频，地道
- ✅ 有学习价值：习语、phrasal verbs、文化用语
- ❌ 不要选过分生僻的（除非是电影的标志性用语）

**每条格式**：
```
to make up one's mind  (phr.)
下定决心
原句："I made up my mind as a young kid that..."
```

### 关键句赏析（每章 2-3 句）

挑出**真正值得品味**的句子：
- 哲理性台词（"happiness is something we can only pursue"）
- 地道表达（"don't ever let somebody tell you you can't do something"）
- 文化典故（独立宣言、Thomas Jefferson 等）

每条：句子原文 + 1-2 句解读（语言点 + 情感/文化含义）。

### 全片词汇总览

电影所有重点词汇按主题分组，比如《当幸福来敲门》可能是：
- 商业 & 金融（broker, intern, commission, portfolio...）
- 家庭 & 情感（pursuit, struggle, hope...）
- 日常表达（gotta, gonna 这类口语缩略）
- 习语 & 谚语

每组 5-10 个词，简单列表，不必再展开例句（章节里已经有了）。

---

## 6. 索引页规范（更新根 index.html）

**索引页位于 `english/index.html`**。它的结构完整 HTML 已经存在，你的任务是：

### 6.1 在 `.movies-grid` 区域**新增一张电影卡片**

新电影卡片用**已上线**的样式（不是 `.coming`）。模板：

```html
<a class="movie-card" href="/{kebab-case-name}/">
    <div class="movie-poster {variant-class}">
        <div>
            <div class="poster-title">{电影中文名}</div>
            <div class="poster-year">{年份}</div>
        </div>
    </div>
    <h3>{电影中文名}</h3>
    <p class="english-title">{English Title}</p>
    <p class="desc">{2-3 句中文剧情简介}</p>
    <div class="meta">
        <span class="meta-info">{类型} · {标签} · {年份}</span>
        <span class="arrow">开始学习 →</span>
    </div>
</a>
```

**海报变体**（让每部电影海报色调不同）：
- 默认（深绿）：第一部 `12 Angry Men` 使用
- `variant-warm`（暖橙）：`Pursuit of Happyness` 这种励志/温暖系
- `variant-deep`（深紫蓝）：`Forrest Gump` 这种深度叙事系
- 自己根据电影气质选择

### 6.2 删除占位卡（如果有）

如果索引页里有 `class="movie-card coming"` 的占位卡，**且其指向的电影就是你这次要添加的**，删除它。

### 6.3 不要改动索引页其他部分

页面标题、Hero、Footer 等保持原样。只动 `.movies-grid` 里的内容。

---

## 7. 交付物清单

完成任务后，你交付给用户的应该是：

1. **一个新文件**：`{kebab-case-name}/index.html`（电影学习页，单文件包含所有内容和 CSS/JS）
2. **一个覆盖文件**：`index.html`（更新后的英语库索引页）
3. **一段清晰的上传指南**（GitHub Web 界面操作步骤，因为李泽民倾向 GUI 而非 Git CLI）

不要交付：
- 多个零散的 CSS/JS 文件（始终单文件 HTML）
- 部分章节的 HTML（必须完整生成）
- 任何需要本地编译的产物（如 React/Vue 源码）

---

## 8. 常见陷阱

- **不要**直接生成代码就甩给用户，**先汇报电影识别 + 章节去重情况让用户确认**
- **不要**为了"AI生成感"添加 emoji 装饰（设计调性是克制的）
- **不要**在双语对照里用粗体或彩色高亮（保持纯文本，留白说话）
- **不要**生成超过 8 个章节的页面而不分段（如果电影章节多，确认用户是否要合并）
- **不要**使用 React/Vue/Tailwind 等需要构建的技术（必须是直接可挂的纯 HTML+CSS+原生 JS）
- **不要**忘记在面包屑导航中链接回 `https://english.lizeming.net/`

---

## 9. 风格示例片段（直接参考）

### 词汇卡片 HTML

```html
<div class="vocab-card">
    <div class="vocab-word">to make up one's mind <span class="vocab-pos">phr.</span></div>
    <div class="vocab-def">下定决心</div>
    <div class="vocab-example">"I made up my mind as a young kid that..."</div>
</div>
```

```css
.vocab-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
}
.vocab-word { font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; }
.vocab-pos { font-weight: 400; font-style: italic; color: var(--text-tertiary); font-size: 0.78rem; margin-left: 4px; }
.vocab-def { font-family: 'Noto Serif SC', serif; color: var(--text); margin-bottom: 10px; }
.vocab-example { font-size: 0.82rem; color: var(--text-secondary); font-style: italic; line-height: 1.6; }
```

### 关键句赏析 HTML

```html
<div class="key-quote">
    <p class="quote-text">"How did he know to put the 'pursuit' part in there?"</p>
    <p class="quote-comment">Chris 引用《独立宣言》中的 "pursuit of happiness"，思考 Jefferson 为何用 "pursuit"（追求）而非 "have"（拥有）。暗示幸福或许只能追逐，永远抵达不了——这是全片的精神锚点。</p>
</div>
```

```css
.key-quote {
    background: var(--quote-bg);
    border-left: 3px solid var(--accent);
    padding: 18px 22px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}
.quote-text { font-family: 'Noto Serif SC', serif; font-size: 1rem; margin-bottom: 8px; color: var(--text); }
.quote-comment { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.75; }
```

### 章节导航 HTML + JS

```html
<nav class="chapter-nav" id="chapterNav">
    <button class="chapter-tab active" data-chapter="1">第一章</button>
    <button class="chapter-tab" data-chapter="2">第二章</button>
    <!-- ... -->
    <button class="chapter-tab" data-chapter="vocab">全片词汇</button>
</nav>

<section class="chapter active" data-chapter="1">...</section>
<section class="chapter" data-chapter="2" style="display:none">...</section>

<script>
document.querySelectorAll('.chapter-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.chapter;
        document.querySelectorAll('.chapter-tab').forEach(b => b.classList.toggle('active', b === btn));
        document.querySelectorAll('.chapter').forEach(s => {
            s.style.display = s.dataset.chapter === target ? '' : 'none';
        });
        window.scrollTo({ top: document.querySelector('.chapter-nav').offsetTop, behavior: 'smooth' });
    });
});
</script>
```

```css
.chapter-nav {
    position: sticky;
    top: 0;
    background: rgba(250, 250, 248, 0.92);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 12px 0;
    display: flex;
    gap: 4px;
    overflow-x: auto;
    z-index: 10;
    margin: 0 -24px 32px;
    padding-left: 24px;
    padding-right: 24px;
}
.chapter-tab {
    background: none;
    border: none;
    padding: 8px 14px;
    font-family: 'Noto Serif SC', serif;
    font-size: 0.92rem;
    color: var(--text-secondary);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
}
.chapter-tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 700;
}
```

---

## 10. 完成自检清单

交付前，确认：

- [ ] 电影中英文名、年份、导演已网搜确认
- [ ] 字幕重复文件已合并，章节数已与用户确认
- [ ] 子目录名是 kebab-case 英文
- [ ] HTML 是单文件，CSS 内嵌，没有外部依赖（除了 Google Fonts）
- [ ] 面包屑 + Hero + 章节导航 + 各章节内容 + 全片词汇 + Footer，结构完整
- [ ] 移动端 media query 已加
- [ ] 章节切换 JS 已测试逻辑
- [ ] 索引页已加入新卡片、移除占位卡
- [ ] 上传步骤已写清（哪个仓库、哪个路径、新增还是覆盖）
- [ ] 没有 emoji 装饰、没有"AI 感"语句
