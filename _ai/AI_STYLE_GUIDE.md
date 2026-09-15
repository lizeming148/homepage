# lizeming.net 网页风格规范（给 AI 的背景文件）

> **使用方式**：把本文件作为背景 / 项目知识交给 AI。
> 当我说「**上传个人主页**」「**套用主页风格**」「**做成主页风格的网页**」时，
> 你生成的所有网页必须严格遵守本规范，不需要再问我要样式。
> 本规范优先级高于你自己的审美偏好；规范没覆盖到的地方，按「克制、留白、像纸质研究笔记」的原则自行延伸。

---

## 0. 一句话风格

**暖白纸面 + 墨绿点缀 + 宋体标题 + 细边圆角白卡片**。安静、克制、像一本排版考究的研究笔记——不是科技感 Dashboard，不是营销落地页。

---

## 1. 交付格式（硬性要求）

1. **单文件 `index.html`**，CSS 和 JS 全部内联在这个文件里（只允许下面第 2 节列出的外链）。
2. `<html lang="zh-CN">`，UTF-8，必须有 viewport meta。
3. `<body class="site-report">`。
4. **不要**使用 Tailwind、Bootstrap 或任何 CSS 框架；**不要**用 React/Vue 等需要构建的框架。原生 HTML + CSS + 少量原生 JS。
5. 图表优先用**纯 CSS 条形图 / HTML 表格 / 内联 SVG**；确实需要复杂交互图表时可用 ECharts 或 Chart.js 的 CDN，但配色必须用第 3 节的令牌色。
6. 站内链接一律用**根绝对路径**（如 `/invest/`、`/english/`），不要写 `../` 相对路径。
7. 图片如需使用，用相对文件名（如 `chart1.png`）并在回复里告诉我需要一起上传哪些图片；小图标用内联 SVG，**不要用 emoji 当图标**。
8. 回复里告诉我：**建议放在哪个 URL 路径**（见第 8 节），以及页面标题。

---

## 2. `<head>` 固定模板（原样复制）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>页面标题</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- 全站共享样式：提供 --site-* 令牌、顶栏、页脚、基础排版。必须引入，不要内联复制它 -->
<link rel="stylesheet" href="https://www.lizeming.net/assets/site.css">
<style>
  /* 页面自己的样式写在这里，颜色/字体只能引用 var(--site-*) */
</style>
<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "46ed83a374df48dc91468350119d7d78"}'></script><!-- End Cloudflare Web Analytics -->
</head>
```

说明：`site.css` 用完整域名引用，这样在任何地方预览都能加载到真实样式；它已经定义好了第 3 节的所有令牌以及 `.site-topbar`、`.site-footer`、`.site-kicker` 等组件，**直接用类名即可，不要重新定义这些类**。

---

## 3. 设计令牌（只能用这些颜色）

以下变量已由 `site.css` 定义，页面里写 `var(--site-xxx)` 即可。**禁止随手写新的十六进制颜色**，确需扩展的颜色在页面 `:root` 里起名并注释用途。

### 3.1 基础色

| 变量 | 值 | 用途 |
|---|---|---|
| `--site-bg` | `#FAFAF8` | 页面底色（暖白） |
| `--site-card` | `#FFFFFF` | 卡片 / 表格底 |
| `--site-text` | `#1C1C1C` | 正文、标题 |
| `--site-text-2` | `#5A5A58` | 次要文字、段落说明 |
| `--site-text-3` | `#8A8A88` | 注释、标签、日期、面包屑 |
| `--site-accent` | `#2B5B4B` | **唯一主强调色（墨绿）**：链接悬停、激活态、表头文字 |
| `--site-accent-soft` | `#E8F0EC` | 墨绿浅底：表头底、标签底、行动建议框 |
| `--site-border` | `#E5E5E0` | 卡片边框、分隔线 |
| `--site-border-soft` | `#EFEFEA` | 表格行线、卡片内分隔 |
| `--site-warm` | `#F5F2EC` | 暖灰底：code、引用、占位块 |

### 3.2 语义色（低饱和，贴合暖白底）

| 变量 | 值 | 用途 |
|---|---|---|
| `--site-pos` / `--site-pos-soft` | `#2E7D4F` / `#E7F2EA` | 好 / 上涨 / 低估 / 通过 |
| `--site-neg` / `--site-neg-soft` | `#B5412F` / `#F8EAE6` | 坏 / 下跌 / 高估 / 风险 |
| `--site-warn` / `--site-warn-soft` | `#A8731F` / `#F7F0E1` | 中性 / 警示 / 需关注 |

> 注意：本站 **绿色 = 好，红色 = 坏**（不是 A 股的红涨绿跌）。数值涨跌如按"好坏"含义着色即可。

### 3.3 专题识别色（仅在对应主题中使用）

| 变量 | 值 | 对象 |
|---|---|---|
| `--site-gree` / `-soft` | `#A0662A` / `#F5EDE2` | 格力 |
| `--site-midea` / `-soft` | `#0B7A4E` / `#E5F1EA` | 美的 |
| `--site-haier` / `-soft` | `#2F5FAE` / `#E8EEF7` | 海尔 |

新对象（公司、指数、电影等）需要识别色时，选**一个低饱和、偏暗的颜色** + 一个极浅的同色底，在页面 `:root` 里定义为 `--co` / `--co-soft`，只用于顶条、左边线、小标签，**不要大面积铺色**。

### 3.4 数据图表的多色序列

需要多个系列时按顺序取：`--site-accent`(#2B5B4B) → `#4E86B0` → `--site-warn`(#A8731F) → `#7A6AA8` → `--site-neg`(#B5412F) → `#B5B5AE`(其他/灰)。

---

## 4. 字体与排版

| 变量 | 字体栈 | 用在哪 |
|---|---|---|
| `--site-serif` | Noto Serif SC → 宋体 | **所有标题 h1–h4**、胶囊按钮文字、引语、卡片标题 |
| `--site-sans` | Inter → 苹方 / 雅黑 | **数字**、英文小标签、日期、面包屑、KPI 大数字 |
| `--site-body` | Inter + Noto Serif SC | 正文（英文数字走 Inter，中文落到宋体） |

排版尺度：

- 正文 `15px`，行高 `1.8`；长段落说明可到 `1.95`。
- 页面主标题 h1：`2rem`（手机 `1.6rem`），粗 700，行高 1.35。
- 区块标题 h2 / h3：`1.1–1.2rem`，粗 700，下方 `1px solid var(--site-border)` 分隔线、`padding-bottom:10px`。
- 小标签（英文大写）：`0.72rem`，`letter-spacing:0.12em`，`text-transform:uppercase`，颜色 `--site-text-3`。
- 表格数字：`font-variant-numeric: tabular-nums`，右对齐；第一列左对齐加粗。
- 粗体只用 `700`，不要用 800/900。
- 页面内容宽度：默认 `920px`，数据密集的报告页可设 `--page-width:1000px`，**最大不超过 1100px**。左右内边距 `24px`（手机 `20px`）。

---

## 5. 形状、间距、质感

- 卡片：白底 + `1px solid var(--site-border)` + **圆角 14px**；小元素圆角 10px / 8px；胶囊 `999px`。
- **标志性细节——内缩顶条**：重点卡片顶部一条 3px 色条，左右各缩进 14px，下方圆角：
  ```css
  .card::before{content:'';position:absolute;top:0;left:14px;right:14px;height:3px;border-radius:0 0 3px 3px;background:var(--co,var(--site-accent))}
  ```
- 阴影：静止时**无阴影**；可点击卡片悬停时 `box-shadow:0 6px 24px rgba(0,0,0,.06); transform:translateY(-2px)`，过渡 0.2s。
- 区块间距：大区块 `margin-bottom:40–56px`；卡片网格 `gap:20px`。
- 链接：默认不加下划线；面包屑/页脚链接用 `border-bottom:1px dotted`，悬停变墨绿。

---

## 6. 页面骨架（完整起步模板）

所有内页都按这个结构写，按需删减组件：

```html
<body class="site-report">

<!-- ① 顶栏：面包屑 + （可选）同专题篇目导航 -->
<div class="site-topbar">
  <div class="site-crumb">
    <a href="/">主页</a><span class="sep">/</span>
    <a href="/invest/">做投资</a><span class="sep">/</span>
    <span class="here">当前页面名</span>
  </div>
  <!-- 同一专题有多篇时才加；当前篇加 class="on" -->
  <nav class="site-nav">
    <span class="kind">本专题 3 篇</span>
    <a href="/invest/topic/">总览</a>
    <a href="/invest/topic/a/" class="on">A 篇</a>
    <a href="/invest/topic/b/">B 篇</a>
  </nav>
</div>

<div class="container">

  <!-- ② 页头 -->
  <header class="page-head">
    <span class="site-kicker">专题名 · 副分类</span>
    <h1>页面主标题</h1>
    <div class="sub">一句话说明 · 数据范围 · 数据截至 YYYY-MM-DD</div>
  </header>

  <!-- ③ 核心结论卡（带内缩顶条） -->
  <div class="hero-card">
    <h2>核心结论</h2>
    <p><strong>结论先行的一句话。</strong>随后两三句展开依据。</p>
  </div>

  <!-- ④ KPI 快照 -->
  <div class="snapshot">
    <div class="snap-card">
      <div class="label">PE-TTM</div>
      <div class="val">14.9</div>
      <div class="sub">5年均值 13.4</div>
      <span class="pill pill-neg">5年分位 84.5%</span>
    </div>
    <!-- 更多 snap-card -->
  </div>

  <!-- ⑤ 标签页（内容多时使用） -->
  <div class="tab-bar" id="tabs">
    <button class="active" data-tab="p1">第一部分</button>
    <button data-tab="p2">第二部分</button>
  </div>

  <div class="panel active" id="p1">
    <section>
      <h3>区块标题</h3>
      <div class="tbl-wrap">
        <table>
          <tr><th>年份</th><th>指标</th><th>增速</th></tr>
          <tr><td>2025</td><td>4,585</td><td class="pos">+12.1%</td></tr>
        </table>
      </div>
      <div class="insight"><strong>关键发现：</strong>对表格的解读，一段话讲清楚。</div>
    </section>
  </div>
  <div class="panel" id="p2">…</div>

  <div class="src-note">数据来源：xxx · 仅供研究参考</div>
</div>

<!-- ⑥ 页脚 -->
<footer class="site-footer">
  <!-- 投资类页面必须带免责声明；其他板块可省略 .disc -->
  <div class="disc"><b>免责声明</b>：本页为个人研究笔记，基于公开资料整理，不构成任何投资建议。</div>
  <div class="row">
    <span><a href="/invest/">← 返回 做投资</a><span class="dot">·</span><a href="/">主页</a></span>
    <span>专题名 ｜ YYYY-MM-DD</span>
  </div>
</footer>

<script>
document.getElementById('tabs')?.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  document.querySelectorAll('#tabs button').forEach(x => x.classList.toggle('active', x === b));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === b.dataset.tab));
});
</script>
</body>
</html>
```

---

## 7. 组件样式库（复制到页面 `<style>` 中按需使用）

```css
*{margin:0;padding:0;box-sizing:border-box}
:root{--co:var(--site-accent);--co-soft:var(--site-accent-soft)} /* 专题识别色，按需改 */
.container{max-width:var(--page-width);margin:0 auto;padding:0 24px 40px}

/* 页头 */
.page-head{padding:30px 0 26px;border-bottom:1px solid var(--site-border);margin-bottom:44px}
.page-head h1{font-family:var(--site-serif);font-size:2rem;font-weight:700;line-height:1.35;letter-spacing:.01em;margin-bottom:10px}
.page-head .sub{font-size:.92rem;color:var(--site-text-2);line-height:1.75}

/* 区块 */
section{margin-bottom:40px}
section h3{font-size:1.1rem;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid var(--site-border)}
p{margin-bottom:.9em}

/* 核心结论卡：内缩顶条 */
.hero-card{position:relative;overflow:hidden;background:var(--site-card);border:1px solid var(--site-border);border-radius:14px;padding:30px 32px 28px;margin-bottom:44px}
.hero-card::before{content:'';position:absolute;top:0;left:14px;right:14px;height:3px;border-radius:0 0 3px 3px;background:var(--co)}
.hero-card h2{font-size:1.2rem;color:var(--co);margin-bottom:14px}
.hero-card p{font-size:.95rem;line-height:1.95;color:var(--site-text-2)}
.hero-card strong{color:var(--site-text)}

/* 普通卡片 & 网格 */
.card{position:relative;background:var(--site-card);border:1px solid var(--site-border);border-radius:14px;padding:24px 26px}
.card h4{font-family:var(--site-serif);font-size:1.05rem;margin-bottom:8px}
.card .desc{font-size:.88rem;color:var(--site-text-2);line-height:1.75}
a.card{display:block;text-decoration:none;color:inherit;transition:box-shadow .25s,transform .15s,border-color .2s}
a.card:hover{box-shadow:0 6px 24px rgba(0,0,0,.06);transform:translateY(-2px);border-color:var(--site-accent)}
.grid-2{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
.grid-3{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}
.card .more{display:block;margin-top:16px;padding-top:14px;border-top:1px solid var(--site-border-soft);font-size:.8rem;font-weight:500;color:var(--site-accent)}

/* KPI 快照 */
.snapshot{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px;margin-bottom:40px}
.snap-card{background:var(--site-card);border:1px solid var(--site-border);border-radius:14px;padding:16px 12px;text-align:center}
.snap-card .label{font-family:var(--site-sans);font-size:.74rem;color:var(--site-text-3);letter-spacing:.04em}
.snap-card .val{font-family:var(--site-sans);font-size:1.45rem;font-weight:600;margin:2px 0;font-variant-numeric:tabular-nums}
.snap-card .sub{font-size:.74rem;color:var(--site-text-3)}

/* 胶囊标签 */
.pill{display:inline-block;font-family:var(--site-sans);font-size:.72rem;font-weight:600;padding:1px 9px;border-radius:999px;margin-top:6px}
.pill-pos{background:var(--site-pos-soft);color:var(--site-pos)}
.pill-neg{background:var(--site-neg-soft);color:var(--site-neg)}
.pill-warn{background:var(--site-warn-soft);color:var(--site-warn)}
.pill-accent{background:var(--site-accent-soft);color:var(--site-accent)}
.pos{color:var(--site-pos)}.neg{color:var(--site-neg)}.warn{color:var(--site-warn)}

/* 标签页按钮（胶囊） */
.tab-bar{display:flex;gap:8px;margin-bottom:28px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.tab-bar::-webkit-scrollbar{display:none}
.tab-bar button{flex:0 0 auto;font-family:var(--site-serif);font-size:.88rem;font-weight:700;color:var(--site-text-2);background:transparent;border:1px solid var(--site-border);border-radius:999px;padding:6px 16px;cursor:pointer;white-space:nowrap;transition:background .2s,color .2s,border-color .2s}
.tab-bar button:hover{color:var(--site-accent);border-color:var(--site-accent)}
.tab-bar button.active{background:var(--site-accent);border-color:var(--site-accent);color:#fff}
.panel{display:none}.panel.active{display:block}

/* 表格 */
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0 20px;background:var(--site-card);border:1px solid var(--site-border);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.84rem;font-variant-numeric:tabular-nums}
th{background:var(--site-accent-soft);color:var(--site-accent);font-weight:600;padding:10px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--site-border)}
td{padding:9px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--site-border-soft)}
th:first-child,td:first-child{text-align:left}
td:first-child{font-weight:600}
tr:last-child td{border-bottom:0}
tbody tr:hover td,tr:hover td{background:#FAFAF6}

/* 解读 / 洞察框（左边线） */
.insight{background:var(--site-card);border:1px solid var(--site-border);border-left:3px solid var(--co);border-radius:0 10px 10px 0;padding:14px 18px;margin:16px 0;font-size:.9rem;color:var(--site-text-2);line-height:1.95}
.insight strong{color:var(--site-text)}

/* 行动建议框（墨绿浅底） */
.action{font-size:.92rem;font-weight:700;color:var(--site-accent);background:var(--site-accent-soft);border-radius:8px;padding:9px 14px;margin:12px 0}

/* 引用 */
blockquote{font-family:var(--site-serif);background:var(--site-warm);border-radius:10px;padding:14px 18px;margin:16px 0;color:var(--site-text-2);line-height:1.9}

/* 纯 CSS 横向条形图 */
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.bar-label{width:64px;font-size:.78rem;color:var(--site-text-2);flex-shrink:0}
.bar-track{flex:1;height:22px;background:var(--site-border-soft);border-radius:6px;overflow:hidden}
.bar-fill{height:100%;border-radius:6px;display:flex;align-items:center;padding-left:8px;font-family:var(--site-sans);font-size:.72rem;color:#fff;font-weight:600;min-width:36px;white-space:nowrap;background:var(--site-accent)}

/* 占位 / 即将上线 */
.coming-soon{border:1px dashed var(--site-border);border-radius:14px;padding:48px 24px;text-align:center;color:var(--site-text-3);font-size:.92rem;background:var(--site-card)}

.src-note{margin-top:8px;font-size:.78rem;color:var(--site-text-3);line-height:1.8}

@media (max-width:760px){
  .container{padding:0 20px 32px}
  .page-head{padding-top:22px;margin-bottom:32px}
  .page-head h1{font-size:1.6rem}
  .hero-card{padding:24px 20px 22px}
}
```

条形图用法：`<div class="bar-row"><div class="bar-label">暖通</div><div class="bar-track"><div class="bar-fill" style="width:42%">1,419亿 42%</div></div></div>`

---

## 8. 站点结构与放置位置

网站 `www.lizeming.net` 目前的板块：

| 路径 | 板块 | 面包屑写法 |
|---|---|---|
| `/` | 主页 | — |
| `/invest/` | 做投资 | `主页 / 做投资 / …` |
| `/invest/<专题>/` | 投资专题（如 `/invest/baidian/` 白电三巨头） | `主页 / 做投资 / 专题名 / 当前页` |
| `/invest/strategy/<指数>/` | 指数估值策略详解 | `主页 / 做投资 / 估值策略 / 当前页` |
| `/english/` | 学英语 | `主页 / 学英语 / …` |
| `/english/<作品>/` | 电影/剧集逐幕学习 | `主页 / 学英语 / 作品名` |

命名约定：**每个页面一个文件夹 + `index.html`**；文件夹名用**英文小写短名、连字符分隔**（如 `the-west-wing`、`midea`），**不要用中文文件名**。

---

## 9. 禁止事项（常见跑偏）

- ❌ 深色背景 / 暗黑主题 / 黑底大 Banner
- ❌ 大面积渐变、玻璃拟态、霓虹发光、彩色大色块铺底
- ❌ 蓝紫"科技风"配色、Tailwind 默认色（`blue-500`、`indigo` 之类）
- ❌ 除 Noto Serif SC 与 Inter 以外的字体（包括 Georgia、思源黑体做标题）
- ❌ emoji 当图标或装饰（✅ 🚀 📈 等）
- ❌ 重阴影、厚边框、圆角 > 16px 的卡片
- ❌ 居中铺满全屏的 Hero 大图、视差滚动、花哨入场动画
- ❌ 重新定义 `.site-topbar` / `.site-footer` / `.site-kicker` 或覆盖 `--site-*` 令牌的值
- ❌ 每个标题都加色、到处加粗；强调色在一屏里只应出现在少数关键位置

---

## 10. 交付前自检清单

生成完毕后，逐条自检并在回复末尾简单列出结果：

- [ ] `<head>` 引入了 Google Fonts、`site.css`、Cloudflare 统计脚本
- [ ] `body` 有 `class="site-report"`，有 `.site-topbar` 面包屑和 `.site-footer`
- [ ] 所有颜色都来自 `var(--site-*)`（或在 `:root` 注释过的扩展色）
- [ ] 标题用宋体（`--site-serif`），数字用 Inter，表格数字右对齐等宽
- [ ] 卡片为白底 + 1px 细边 + 14px 圆角，无静态阴影
- [ ] 站内链接为根绝对路径；给出了建议放置路径（英文短名文件夹）
- [ ] 在 400px 手机宽度下不横向滚动（表格除外，表格包在 `.tbl-wrap` 里）
- [ ] 投资类页面带免责声明
