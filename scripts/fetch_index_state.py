#!/usr/bin/env python3
"""
读取飞书多维表里三个指数策略的最新信号，导出为静态 JSON，供 homepage 投资板块「估值策略」页的信号卡展示。

2026-10（阶段 3C 补充）起：
- 不再在本脚本里按旧阈值重算档位（沪深300 PE 六档、红利股息率六档、恒指股息率五档均已废止）；
- 只读取引擎写入飞书表的新规则字段：档名 + 公开信号字段（综合便宜度、动作、与月末卡片同一句话的结论、
  各尺子读数、临时 / 正式读数、规则版本），规则见《规则说明书_宽基v1.1》《规则说明书_行业与策略v1.1》；
- 本仓库是**公开仓库**：导出前用 assert_public() 检查，出现持仓 / 仓位 / 金额类字段或金额数值即报错。

- 只读飞书，不写任何表。
- 数据源：飞书多维表  →  输出：invest/strategy/data/{csi300,hongli,hsi}.json

所需环境变量（与引擎仓库同名，可直接复用同一组 secrets）：
    FEISHU_APP_ID / FEISHU_APP_SECRET            飞书应用凭证
    沪深300：FEISHU_APP_TOKEN_300 / FEISHU_PE_HISTORY_TABLE_ID（pe_history 表）
    中证红利：FEISHU_APP_TOKEN_922 / FEISHU_DATA_TABLE_922（PEPBDIV 表）
    恒生指数：FEISHU_APP_TOKEN_HSI / FEISHU_HISTORY_TABLE_HSI / FEISHU_DIVIDEND_TABLE_HSI（有默认值）
"""
import os
import re
import json
import sys
from datetime import datetime, timedelta, timezone

import requests

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "invest", "strategy", "data")

# 引擎写入的公开信号字段（见 csi300-valuation-engine/index_rules/cards.py 的 PUBLIC_FIELDS）
PUBLIC_FIELDS = ("composite", "action", "summary", "rulers", "reading_kind", "rule_version")

# 档名 → 网页色（与飞书卡片模板色一致：便宜 red / 偏便宜 orange / 中性 green / 偏贵 blue / 贵 purple）
TIER_HEX = {
    "便宜":   "#C0392B",
    "偏便宜": "#CB6B1E",
    "中性":   "#2B7A4B",
    "偏贵":   "#2F5FAE",
    "贵":     "#7D3C98",
}
COLOR_HEX = {"red": "#C0392B", "orange": "#CB6B1E", "yellow": "#B8902A", "green": "#2B7A4B", "blue": "#2F5FAE"}

# ─────────────────────────────────────────────
# 隐私：公开仓库，持仓金额、卖出金额等绝对值不得进入 JSON（比例允许，2026-10-13 起）
# ─────────────────────────────────────────────
# 2026-10-13 起：允许比例、禁止绝对值（与 csi300-valuation-engine / hsi-monitor 的 index_rules/privacy.py 相同，
# 由 tests/privacy_rules.json 固定副本 + 哈希核对）
KEY_TOKENS_ABSOLUTE = ("amount", "asset", "金额", "市值", "资产")
KEY_TOKENS_CONTEXT = ("holding", "position", "仓位", "持仓")
RATIO_MARKERS = ("pct", "ratio", "percent", "weight", "比例", "占比", "比重")
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"\d[\d.,]*\s*[万亿]"),                                         # “36.5 万”“3 亿”
    re.compile(r"\d[\d.,]*\s*(?:元|块钱|港元|港币|美元|RMB|CNY|HKD|USD)"),      # “10000 元”
    re.compile(r"[¥￥$]\s*\d"),                                                 # “¥5000”
    re.compile(r"\d[\d.,]*\s*(?:股|份)(?![息价票指债利])"),                     # “持仓 100 股”（不误伤“股息率”）
    re.compile(r"(?:总资产|市值|金额|本金|资金|持仓|仓位)\s*[:：为约是]?\s*\d[\d.,]*(?![\d.,])(?!\s*[%％/倍成])"),
)


def key_problem(key):
    low = str(key).lower()
    for t in KEY_TOKENS_ABSOLUTE:
        if t in low:
            return t
    for t in KEY_TOKENS_CONTEXT:
        if t in low and not any(m in low for m in RATIO_MARKERS):
            return t
    return None


def rules_dict():
    return {"key_tokens_absolute": list(KEY_TOKENS_ABSOLUTE), "key_tokens_context": list(KEY_TOKENS_CONTEXT),
            "ratio_markers": list(RATIO_MARKERS), "value_patterns": [p.pattern for p in FORBIDDEN_VALUE_PATTERNS]}


def assert_public(payload, where="payload"):
    """导出前的隐私检查：键名或取值里出现持仓金额 / 绝对数量即抛 ValueError（比例允许）。"""
    def walk(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                t = key_problem(k)
                if t:
                    raise ValueError(f"{where}：字段名 {path}{k} 含隐私敏感词“{t}”（只允许比例字段）")
                walk(v, f"{path}{k}.")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk(v, f"{path}{i}.")
        elif isinstance(obj, str):
            for p in FORBIDDEN_VALUE_PATTERNS:
                m = p.search(obj)
                if m:
                    raise ValueError(f"{where}：{path.rstrip('.')} 的取值含绝对金额 / 数量“{m.group(0)}”")
    walk(payload, "")
    return payload


# ─────────────────────────────────────────────
# 飞书通用读取
# ─────────────────────────────────────────────
def get_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
    return res.json().get("tenant_access_token")


def fetch_all(token, app_token, table_id, fields=None):
    """读取一张表的全部记录（自动翻页）"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    items, page_token = [], None
    while True:
        params = {"page_size": 500}
        if fields:
            params["field_names"] = json.dumps(fields, ensure_ascii=False)
        if page_token:
            params["page_token"] = page_token
        res = requests.get(url, headers=headers, params=params, timeout=15).json()
        if res.get("code") not in (0, None):
            raise RuntimeError(f"读取飞书表 {table_id} 失败：{res.get('msg')}")
        data = res.get("data", {})
        items.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return items


# 飞书日期字段按北京时间解读（与引擎 index_rules/bjtime.py 一致）：引擎写入北京中午，
# 旧记录是 UTC 零点 / 中午写入的，按北京日期读回都是正确日期；不能用运行机器的本地时区（Actions 是 UTC）。
BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")


def ms_to_date(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=BEIJING).strftime("%Y-%m-%d")


def latest_by_date(items, date_field="Date"):
    """返回日期最新的一条记录的 (date_ms, fields)，无则 None"""
    best = None
    for it in items:
        f = it.get("fields", {})
        d = f.get(date_field)
        if d and (best is None or d > best[0]):
            best = (d, f)
    return best


def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _plain_text(field_value):
    """飞书文本字段可能是字符串，也可能是 [{type:'text', text:'...'}] 结构。"""
    if isinstance(field_value, list) and field_value:
        first = field_value[0]
        if isinstance(first, dict):
            return "".join(x.get("text", "") or "" for x in field_value if isinstance(x, dict))
    return field_value or ""


# ─────────────────────────────────────────────
# 新规则信号卡（三个指数共用）
# ─────────────────────────────────────────────
def record_problems(tier_field, fields):
    """一条记录作为新规则信号是否齐全；返回问题列表（空 = 齐全）。"""
    problems = []
    tier = _plain_text(fields.get(tier_field)).strip()
    if tier not in TIER_HEX:
        problems.append(f"{tier_field}={tier!r} 不是新规则档名")
    missing = [k for k in PUBLIC_FIELDS if fields.get(k) in (None, "", [])]
    if missing:
        problems.append(f"缺少新字段 {missing}")
    elif safe_float(fields.get("composite")) is None:
        problems.append(f"composite 不是数值：{fields.get('composite')!r}")
    return problems


def latest_complete(items, tier_field, name, date_field="Date"):
    """取日期最新、且新规则字段齐全的一条记录 → (date_ms, fields)。
    最新几条不全时跳过并打印日志（页面显示的是所取记录自己的日期）；全部记录都不全时才报错。"""
    rows = sorted(((it.get("fields", {}).get(date_field), it.get("fields", {})) for it in items
                   if it.get("fields", {}).get(date_field)), key=lambda x: x[0], reverse=True)
    if not rows:
        raise RuntimeError(f"{name}：表为空")
    for i, (ms, f) in enumerate(rows):
        if not record_problems(tier_field, f):
            if i:
                print(f"⚠️ {name}：最近 {i} 条记录新字段不全（最新 {ms_to_date(rows[0][0])}：{record_problems(tier_field, rows[0][1])}），"
                      f"改用 {ms_to_date(ms)} 的记录")
            return ms, f
    raise RuntimeError(f"{name}：全部 {len(rows)} 条记录都缺新规则字段（最新一条：{record_problems(tier_field, rows[0][1])}）"
                       "——请先在飞书表建好字段，并等引擎切换后写入")


def signal_payload(name, code, date_ms, tier_field, fields):
    """由一条齐全的记录组装信号卡 JSON。缺少新字段时显式报错（不按旧阈值兜底）。"""
    tier = _plain_text(fields.get(tier_field)).strip()
    if tier not in TIER_HEX:
        raise RuntimeError(f"{name}：最新一行 {tier_field}={tier!r} 不是新规则档名（引擎尚未切换？）")
    missing = [k for k in PUBLIC_FIELDS if fields.get(k) in (None, "", [])]
    if missing:
        raise RuntimeError(f"{name}：最新一行缺少新字段 {missing}——请先在飞书表建好这些字段，并等引擎切换后写入")
    composite = safe_float(fields.get("composite"))
    if composite is None:
        raise RuntimeError(f"{name}：composite 不是数值：{fields.get('composite')!r}")
    return {
        "name": name,
        "code": code,
        "date": ms_to_date(date_ms),
        "status": tier,
        "color": TIER_HEX[tier],
        "metric_label": "综合便宜度",
        "metric_value": f"{composite:.0f}",
        "action": _plain_text(fields.get("action")),
        "summary": _plain_text(fields.get("summary")),
        "rulers": _plain_text(fields.get("rulers")),
        "reading_kind": _plain_text(fields.get("reading_kind")),
        "rule_version": _plain_text(fields.get("rule_version")),
        "extra": "",
        # 除息重叠标注生效中：引擎在 rulers 里注明“（折算；原始 x%，除息重叠标注）”，网站据此显示标签
        "dy_overlap": "除息重叠标注" in _plain_text(fields.get("rulers")),
    }


def build_csi300(token):
    app = os.environ.get("FEISHU_APP_TOKEN_300")
    table = os.environ.get("FEISHU_PE_HISTORY_TABLE_ID")
    if not (app and table):
        raise RuntimeError("未配置 FEISHU_APP_TOKEN_300 / FEISHU_PE_HISTORY_TABLE_ID")
    ms, f = latest_complete(fetch_all(token, app, table, ["Date", "Zone", *PUBLIC_FIELDS]), "Zone", "沪深300 pe_history")
    return signal_payload("沪深300", "000300.SH", ms, "Zone", f)


def build_hongli(token):
    app = os.environ.get("FEISHU_APP_TOKEN_922")
    table = os.environ.get("FEISHU_DATA_TABLE_922")
    if not (app and table):
        raise RuntimeError("未配置 FEISHU_APP_TOKEN_922 / FEISHU_DATA_TABLE_922")
    ms, f = latest_complete(fetch_all(token, app, table, ["Date", "tier", *PUBLIC_FIELDS]), "tier", "中证红利 PEPBDIV")
    return signal_payload("中证红利", "000922.CSI", ms, "tier", f)


HSI_APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN_HSI", "Wp3XbNSkMaPwBbs17pbcMFjhnEf")
HSI_HISTORY_TABLE = os.environ.get("FEISHU_HISTORY_TABLE_HSI", "tblLddXoap38WKC0")
HSI_DIVIDEND_TABLE = os.environ.get("FEISHU_DIVIDEND_TABLE_HSI", "tbl7rO4ph0sQIdYU")
# 分红质量：只作风险提示，不调整买入倍数（审计 4.9）
HSI_DQ_GRADE = {
    "GREEN":  ("🟢 健康", "green"),
    "YELLOW": ("🟡 关注", "yellow"),
    "ORANGE": ("🟠 承压", "orange"),
    "RED":    ("🔴 恶化", "red"),
}


def fetch_hsi_dividend(token):
    """读飞书分红质量表最新一条，返回给网页展示的 dq_* 字段（不含已停用的打折系数）。"""
    latest = latest_by_date(fetch_all(token, HSI_APP_TOKEN, HSI_DIVIDEND_TABLE,
                                      ["date", "grade", "weighted_payout", "alerts"]), date_field="date")
    if not latest:
        return None
    ms, f = latest
    grade = _plain_text(f.get("grade")).strip().upper()
    if not grade:
        return None
    label, color = HSI_DQ_GRADE.get(grade, (grade, "blue"))
    payout = safe_float(f.get("weighted_payout"))
    return {
        "dq_grade": grade,
        "dq_label": label,
        "dq_color": COLOR_HEX.get(color, "#B8902A"),
        "dq_payout": round(payout, 1) if payout is not None else None,
        "dq_alerts": _plain_text(f.get("alerts")).strip(),
        "dq_date": ms_to_date(ms),
    }


def build_hsi(token):
    ms, f = latest_complete(fetch_all(token, HSI_APP_TOKEN, HSI_HISTORY_TABLE,
                                      ["date", "tier", "spread_dy_cn", "erp_cn", *PUBLIC_FIELDS]),
                            "tier", "恒生指数 hsi_history", date_field="date")
    payload = signal_payload("恒生指数", "HSI.HK", ms, "tier", f)
    erp = safe_float(f.get("erp_cn"))   # 股债差已在尺子读数里，这里只补 ERP（仅展示）
    payload["extra"] = f"ERP（仅展示）{erp:+.2f}%" if erp is not None else ""
    try:
        dq = fetch_hsi_dividend(token)
        if dq:
            payload.update(dq)
    except Exception as e:  # noqa: BLE001 — 分红质量只是风险提示，缺失不影响信号
        print(f"⚠️ 恒生分红质量读取失败（跳过该字段）：{e}")
    return payload


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
def write_json(name, payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    payload["updated_at"] = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M")
    assert_public(payload, f"{name}.json")
    path = os.path.join(OUT_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    print(f"✅ 写入 {path}")


def main():
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not (app_id and app_secret):
        print("❌ 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")
        sys.exit(1)
    token = get_token(app_id, app_secret)
    if not token:
        print("❌ 飞书认证失败")
        sys.exit(1)

    failed = []
    for name, builder in (("csi300", build_csi300), ("hongli", build_hongli), ("hsi", build_hsi)):
        try:
            write_json(name, builder(token))
        except Exception as e:  # noqa: BLE001 — 逐个指数处理，最后统一报错
            print(f"❌ {name} 导出失败（保留旧 JSON）：{e}")
            failed.append(name)
    if failed:
        sys.exit(f"❌ 导出失败：{failed}")
    print("✅ 完成")


if __name__ == "__main__":
    main()
