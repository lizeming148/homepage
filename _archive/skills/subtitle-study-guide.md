---
name: subtitle-study-guide
description: >
  Generate an HTML study guide from English movie/TV subtitle files for ESL learners.
  Use this skill whenever the user uploads a subtitle file (.srt, .txt, or plain text dialogue)
  and wants to create an English learning page, study guide, or reading material from it.
  Also trigger when the user mentions: movie subtitles for English study, subtitle reading practice,
  Trancy-compatible study page, English dialogue study, or film script study guide.
  This skill produces a standardized HTML page with a fixed layout, style, and structure
  that is compatible with browser translation extensions like Trancy.
---

# Subtitle Study Guide Generator

Create a clean, standardized HTML study page from English subtitle files. The output is designed for ESL (English as a Second Language) learners who use browser extensions like Trancy to click-translate unfamiliar words.

## When to Use

- User uploads an `.srt` subtitle file or plain text dialogue file
- User asks to create English study material from a movie or TV show
- User wants a Trancy-compatible reading page from subtitles
- User wants to study English through movie/TV dialogue

## Input Formats

The skill accepts these input types:

1. **SRT files (English only)**
2. **SRT files (bilingual Chinese-English)** — saves ~38% token consumption
3. **Plain text dialogue**
4. **Separate English + Chinese files**

## Workflow

### Step 1: Parse the Subtitle File

- Auto-detect bilingual input (CJK characters in Unicode range 一-鿿)
- Strip numbers and timestamps from SRT
- For bilingual: separate EN/CN lines, pair as {en, cn} tuples, skip translation

### Step 2: Divide into Scenes

Split into 8–12 scenes. Each scene needs:
- English title describing the scene
- Chinese summary (1–2 sentences)

### Step 3: Build Vocabulary Table

Select 80–120 key words/phrases in 5 categories:
1. Domain-Specific Terms 专业术语
2. Everyday Expressions & Idioms 日常表达与习语
3. Useful Verbs 实用动词
4. Descriptive Words 描述性词汇
5. Places & Culture 地点与文化背景

Each entry: English | IPA | Chinese definition

### Step 4: Generate HTML

**Critical rules for Trancy compatibility:**
- No external font imports — system fonts only (Georgia, Arial, sans-serif)
- No JavaScript — pure HTML + CSS only
- No sticky/fixed positioning
- No custom ::selection
- No z-index layering
- Minimal CSS — only basic typography and table styling
- All text must be plain, selectable, clickable

Page structure:
1. Title + subtitle + usage instructions (bilingual)
2. Table of Contents with anchor links (vocabulary first, then scenes)
3. Vocabulary tables (5 categories)
4. Scene-by-scene dialogue in two-column bilingual layout (English left, Chinese right)
5. "Back to top" links after each scene

### Step 5: Save and Present

Save to: `/mnt/user-data/outputs/index.html`
Present via: `present_files` tool

## Critical Rules

1. Bilingual dialogue in two columns — English prominent (serif, dark), Chinese subdued (sans-serif, smaller, light gray)
2. HTML must be extension-friendly — no CSS or JS blocking word-level click detection
3. Consistent structure every time
4. File named `index.html`
5. Vocabulary table comes before dialogue

## Deployment Note

这个 Skill 生成的页面供用户在本地浏览器用 Trancy 打开，或上传到 GitHub Pages。
上传路径遵循 add-movie.md 里的目录规范：
- 单集文件放到 `{movie-dir}/s{NN}/e{NN}/index.html`
- 上传后在对应季列表页把该集状态从"即将上线"改为"已上线"并加链接
- 具体部署流程参考 D:\projects\skills\add-movie.md
