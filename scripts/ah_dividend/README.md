# AH 股息比价工具 · 运维说明

线上地址：<https://www.lizeming.net/tools/ah-dividend/>

这个工具由以下文件组成（本说明就是 `scripts/ah_dividend/README.md`）：

| 文件 | 作用 | 谁来改 |
|---|---|---|
| `tools/ah-dividend/index.html` | 网页本身（页面 + 计算） | 一般不用动 |
| `tools/ah-dividend/ah_pairs.json` | AH 股名单 + 每家公司的 H 股税率 | 脚本更新名单；**税率由你手动改** |
| `tools/ah-dividend/fx.json` | 港元兑人民币汇率 | 脚本更新 |
| `scripts/ah_dividend/update_data.py` | 更新上面两个 JSON 的脚本 | 一般不用动 |

下面所有命令都在**仓库根目录** `D:\projects\homepage` 里运行（PowerShell 或命令提示符都行）。

---

## 一、安装依赖（只需一次）

```
python -m pip install -r scripts/ah_dividend/requirements.txt
```

AkShare 升级后接口偶尔会变。如果脚本突然报"字段变了"之类的错误，先试试升级：

```
python -m pip install -U akshare
```

---

## 二、运行脚本更新数据

```
python scripts/ah_dividend/update_data.py
```

整个过程大约 1–2 分钟（腾讯名单要翻 11 页，比较慢）。屏幕上会先滚过一些进度条，属于正常现象。

其他用法：

- `python scripts/ah_dividend/update_data.py --fx-only`：只更新汇率。名单数据源坏了、但又想更新汇率时用。
- `python scripts/ah_dividend/update_data.py --dry-run`：只取数、打印报告，不写文件。想先看看变化时用。

### 数据从哪来

- **AH 名单**：腾讯的 AH 股列表（AkShare `stock_zh_ah_name`）。它只给 H 股代码，所以脚本再用东方财富 F10 的"A 股—H 股代码对照"补上 A 股代码，并用沪深北交易所的在市 A 股列表过滤掉 B 股、新三板和旧代码。
- **注册地**：东方财富港股公司资料。只对新出现的公司查一次，用来自动发现境外注册（红筹等）公司。
- **汇率**：优先使用上交所**港股通参考汇率**，取买入价和卖出价的中值。取不到时依次改用深交所参考汇率、外汇管理局人民币汇率中间价。实际用了哪个来源，会写进 `fx.json` 的 `source` 字段，网页上也会显示。

### 看懂变化报告

运行结束后会打印一份报告，各栏含义如下：

| 栏目 | 意思 | 你要做什么 |
|---|---|---|
| 【新增公司】 | 新进入 AH 名单的公司，按默认税率 20% 写入 | 留意注册地，境外注册的会自动标为 pending |
| 【名单中消失的公司】 | 上次有、这次没有的公司（比如 A 股或 H 股退市） | 脚本**不会删除**这些公司。确认真的退市后，手动从 `ah_pairs.json` 里删掉那一段 |
| 【对不上 A 股代码的 H 股】 | 腾讯名单里有、但找不到对应 A 股的 H 股 | 偶尔出现可以不管；如果长期存在，就手动补一条进去 |
| 【名称或 H 股代码有变】 | 公司改名或换代码 | 看一眼即可，脚本已自动更新 |
| 【当前所有 pending 公司】 | 税率待你核实的公司 | 见下一节 |
| 【注意】注册地在境外但状态仍是 default | 注册地是后来才查到的，没被自动标记 | 按下一节核实 |
| 【汇率】 | 新汇率、旧汇率和两者的差值 | 差值一般很小，突然变化很大时要怀疑数据源 |

最后一行显示 `✓ 已写入` 才说明文件已更新。出现 `✗ 失败` 时，**原文件不会被改动**，可以放心重试。

---

## 三、手动修改某家公司的税率

打开 `tools/ah-dividend/ah_pairs.json`（用 VS Code 或记事本都可以），搜索公司名或代码，找到这样一段：

```json
{
  "name": "中国移动",
  "a_code": "600941",
  "h_code": "00941",
  "h_tax": 0.2,
  "h_tax_status": "pending",
  "note": "境外注册（中国香港特别行政区），税率可能为 28%，待按最近分红公告核实",
  "verified": "",
  "domicile": "中国香港特别行政区"
}
```

核实之后，改这 4 个字段：

| 字段 | 改成什么 | 例子 |
|---|---|---|
| `h_tax` | 小数形式的税率，只能是 `0.2` 或 `0.28` | `0.28` |
| `h_tax_status` | `"verified"` | `"verified"` |
| `verified` | 核实日期 | `"2026-11-05"` |
| `note` | 核实依据 | `"2026 年中期派息公告：港股通内地个人按 28% 代扣"` |

注意事项：

- 不要动 `name`、`a_code`、`h_code`、`domicile` 四个字段，它们由脚本维护。
- 引号、逗号要保持原样。最后一个字段后面不能加逗号。
- 改完后可以先运行一次 `python scripts/ah_dividend/update_data.py --dry-run`。文件格式有错时脚本会直接报出来，不会覆盖任何东西。
- 你改过的这 4 个字段，以后脚本**永远不会覆盖**。

`h_tax_status` 的三种取值：`default`（按默认 20%）、`pending`（待核实，网页上会显示 ⚠️）、`verified`（已核实）。

---

## 四、提交并发布（commit 和 push）

> **push 前必须先 `git pull --rebase origin main`。** `main` 分支每天都有 GitHub Actions 自动提交的指数数据，你本地的 `main` 几乎总是落后于远端。不先拉取的话，push 会被拒绝（non-fast-forward）。

顺序是：先 commit，再 pull --rebase，最后 push。如果还有没 commit 的改动，`git pull --rebase` 会拒绝执行。

```
git add tools/ah-dividend/ah_pairs.json tools/ah-dividend/fx.json
git commit -m "AH 股息工具：更新名单与汇率 2026-11-05"
git pull --rebase origin main
git push origin main
```

自动提交只改 `invest/strategy/data/` 下的文件，和这个工具的文件不重叠，所以 rebase 一般不会冲突。

push 之后等一两分钟，GitHub Pages 发布完成，再打开线上地址检查。浏览器如果还显示旧数据，按 Ctrl+F5 强制刷新。

---

## 五、常见报错

| 报错 | 原因 | 处理 |
|---|---|---|
| `No module named 'akshare'` | 没装依赖 | 运行第一节的安装命令 |
| `获取失败 … 直连：ConnectionError … 代理：502` | 数据源暂时不可用，或被限流 | 过半小时到几小时再试。急着更新汇率的话，用 `--fx-only` |
| `ah_pairs.json 无法解析` | 手动修改时 JSON 格式写错了（多了或少了逗号、引号） | 按提示的行号和列号去改；也可以用 `git diff` 查看改动，或用 `git checkout tools/ah-dividend/ah_pairs.json` 还原 |
| `h_tax_status=… 不是 … 之一` / `h_tax … 不是数字` | 手动修改时字段值写错了 | 按第三节的格式改正 |
| `AH 名单只有 N 只` / `从 X 只降到 Y 只，疑似取数残缺` | 数据源只返回了一部分数据 | 稍后重试，不要强行写入 |
| `字段变了` | AkShare 或数据源改了接口 | 先升级 AkShare，仍然不行就找 Claude 修脚本 |
| `git push` 被拒绝（non-fast-forward） | 远端有自动提交 | 先运行 `git pull --rebase origin main`，再 push |

关于代理：本机配置了代理（环境变量 `HTTPS_PROXY`），而东方财富等国内站点走本机代理时常常返回 502。所以脚本会**先绕过代理直连**国内数据源，直连失败后再改走代理重试，你不需要手动设置任何东西。

---

## 六、建议的更新频率

| 内容 | 频率 | 命令 |
|---|---|---|
| 汇率 | 每周一次 | `--fx-only` 即可，也可以直接跑完整脚本 |
| AH 名单 | 每月一次 | 完整运行脚本 |
| H 股税率 | 每年分红季前（大约 3–5 月）核实一次 | 对照各公司最近一次派息公告，按第三节修改 |

---

## 七、网页本身

- 股价需要手动输入，网页不会自动获取行情。
- 自测：打开 `…/tools/ah-dividend/?selftest=1`，页面底部会显示 4 个测试用例的结果，浏览器控制台里也会打印。
- 本地预览：在 `tools/ah-dividend` 目录下运行 `python -m http.server 8000`，然后打开 <http://localhost:8000/>。不能直接双击 html 文件打开，那样读不到 JSON 数据。
- 网页会在浏览器里记住你上次选的持股期限和最近查看的 5 只股票。这些只保存在你自己的浏览器里，不会上传到任何地方。
