#!/usr/bin/env python3
"""
读取飞书多维表里两个指数策略的最新状态，导出为静态 JSON，
供 homepage 投资板块「估值策略」tab 展示。

- 只读飞书，不写任何表（与 csi300-valuation-engine 的写入引擎解耦）。
- 复用两个引擎完全相同的分档 / 文案逻辑，保证主页显示与飞书推送一致。
- 数据源：飞书多维表  →  输出：invest/strategy/data/{csi300,hongli}.json

所需环境变量（与引擎仓库同名，可直接复用同一组 secrets）：
    FEISHU_APP_ID / FEISHU_APP_SECRET            飞书应用凭证
    沪深300：
        FEISHU_APP_TOKEN_300                     沪深300 base
        FEISHU_PE_HISTORY_TABLE_ID               pe_history 表
    中证红利：
        FEISHU_APP_TOKEN_922                     红利 base
        FEISHU_DATA_TABLE_922                    PEPBDIV 估值表
未配置某个指数的变量时，自动跳过该指数（保留上一份 JSON）。
"""
import os
import json
import sys
from datetime import datetime

import requests

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "invest", "strategy", "data")

# 飞书卡片 template 色 → 网页 hex（与飞书卡片视觉对齐）
COLOR_HEX = {
    "red":    "#C0392B",
    "orange": "#CB6B1E",
    "yellow": "#B8902A",
    "green":  "#2B7A4B",
    "blue":   "#2F5FAE",
    "purple": "#7D3C98",
}


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
        data = res.get("data", {})
        items.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return items


def ms_to_date(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


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


# ─────────────────────────────────────────────
# 沪深300（与 update_csi300.py 一致）
# ─────────────────────────────────────────────
CSI_LADDER = "≤11 买×3 ｜ 11~11.5 买×1.5 ｜ 11.5~12 买×0.2 ｜ 12~14 持仓 ｜ ≥14 卖×1 ｜ ≥14.5 全清"
CSI_COLOR = {
    "买入×3.0": "red", "买入×1.5": "orange", "买入×0.2": "yellow",
    "持仓": "green", "卖出中": "blue", "清仓": "purple",
}
CSI_ACTION = {
    "买入×0.2": "本月定投 0.2 倍基数", "买入×1.5": "本月定投 1.5 倍基数",
    "买入×3.0": "本月定投 3.0 倍基数", "卖出中": "本月卖出 1 倍基数份额",
    "清仓": "立即全部清仓", "持仓": "持仓不动，无需操作",
}


def csi_hint(zone, pe):
    hints = {
        "持仓":     f"距卖出线(14.0)还有 {round(14.0 - pe, 2)} 个 PE",
        "买入×0.2": f"距加仓线(11.5)还有 {round(pe - 11.5, 2)} 个 PE",
        "买入×1.5": f"距加仓线(11.0)还有 {round(pe - 11.0, 2)} 个 PE",
        "买入×3.0": "已至最高档，等待市场回暖",
        "卖出中":   f"距全清线(14.5)还有 {round(14.5 - pe, 2)} 个 PE",
        "清仓":     "已触发全清条件",
    }
    return hints.get(zone, "")


def build_csi300(token):
    app = os.environ.get("FEISHU_APP_TOKEN_300")
    table = os.environ.get("FEISHU_PE_HISTORY_TABLE_ID")
    if not (app and table):
        print("💡 未配置沪深300变量，跳过")
        return None
    items = fetch_all(token, app, table, ["Date", "PE_csindex", "PE_converted", "Zone"])
    latest = latest_by_date(items)
    if not latest:
        print("⚠️ 沪深300 pe_history 为空")
        return None
    ms, f = latest
    pe = safe_float(f.get("PE_converted"))
    zone = f.get("Zone") or ""
    print(f"📊 沪深300 最新：{ms_to_date(ms)}  PE={pe}  zone={zone}")
    return {
        "name": "沪深300",
        "code": "000300.SH",
        "date": ms_to_date(ms),
        "status": zone,
        "color": COLOR_HEX.get(CSI_COLOR.get(zone, "blue"), "#2F5FAE"),
        "metric_label": "PE · 投资网口径",
        "metric_value": f"{pe:.2f}" if pe is not None else "—",
        "action": CSI_ACTION.get(zone, ""),
        "hint": csi_hint(zone, pe) if pe is not None else "",
        "extra": "",
        "ladder": CSI_LADDER,
    }


# ─────────────────────────────────────────────
# 中证红利（与 update_hongli.py 一致）
# ─────────────────────────────────────────────
HONGLI_LADDER = ("≥5.8% 重仓×3 ｜ 5.0~5.8% 加仓×2 ｜ 4.5~5.0% 定投×0.5 ｜ "
                 "3.8~4.5% 持有 ｜ 3.5~3.8% 预警 ｜ <3.5% 止盈")
# threshold, tier_id, name, action, color —— 与引擎 TIERS 顺序一致
HONGLI_TIERS = [
    (5.8, "5",   "极度便宜",   "重仓买入 3 个定投基数",  "red"),
    (5.0, "4",   "明显便宜",   "积极加仓 2 个定投基数",  "orange"),
    (4.5, "3",   "合理偏便宜", "标准定投 0.5 个定投基数", "blue"),
    (3.8, "2",   "中性",       "持有不动",               "green"),
    (3.5, "1.5", "偏贵预警",   "准备减仓 0.5 个定投基数", "yellow"),
    (0.0, "1",   "止盈区",     "分批止盈 1 个定投基数",   "purple"),
]
# 各档向更优（更便宜）方向需要突破的阈值
HONGLI_UPWARD = {"1": 3.5, "1.5": 3.8, "2": 4.5, "3": 5.0, "4": 5.8}
HONGLI_NAME_BY_THR = {5.8: "极度便宜", 5.0: "明显便宜", 4.5: "合理偏便宜",
                      3.8: "中性", 3.5: "偏贵预警"}


def hongli_tier(div_pct):
    for thr, tid, name, action, color in HONGLI_TIERS:
        if div_pct >= thr:
            return tid, name, action, color
    last = HONGLI_TIERS[-1]
    return last[1], last[2], last[3], last[4]


def hongli_hint(tier_id, div_pct):
    target = HONGLI_UPWARD.get(tier_id)
    if target is None:
        return "已达最高档，等待市场回暖"
    name = HONGLI_NAME_BY_THR.get(target, "")
    return f"距{name}({target}%) ↑{round(target - div_pct, 2)}%"


def build_hongli(token):
    app = os.environ.get("FEISHU_APP_TOKEN_922")
    table = os.environ.get("FEISHU_DATA_TABLE_922")
    if not (app and table):
        print("💡 未配置中证红利变量，跳过")
        return None
    items = fetch_all(token, app, table,
                      ["Date", "PE", "PB", "pe_perc", "dividendr", "div_perc",
                       "close", "implied_roe"])
    latest = latest_by_date(items)
    if not latest:
        print("⚠️ 中证红利 估值表为空")
        return None
    ms, f = latest
    div_raw = safe_float(f.get("dividendr"))
    if div_raw is None:
        print("⚠️ 中证红利 股息率缺失")
        return None
    div_pct = round(div_raw * 100, 2)
    pe = safe_float(f.get("PE"))
    pe_perc = safe_float(f.get("pe_perc"))
    implied_roe = safe_float(f.get("implied_roe"))
    tier_id, tier_name, action, color = hongli_tier(div_pct)
    print(f"📊 中证红利 最新：{ms_to_date(ms)}  股息率={div_pct}%  {tier_id}档({tier_name})")

    extra_parts = []
    if pe is not None:
        s = f"PE {pe:.2f}"
        if pe_perc is not None:
            s += f" ({pe_perc * 100:.0f}%)"
        extra_parts.append(s)
    if implied_roe is not None:
        extra_parts.append(f"隐含ROE {implied_roe:.1f}%")

    return {
        "name": "中证红利",
        "code": "000922.CSI",
        "date": ms_to_date(ms),
        "status": f"{tier_id}档 · {tier_name}",
        "color": COLOR_HEX.get(color, "#2B7A4B"),
        "metric_label": "股息率",
        "metric_value": f"{div_pct:.2f}%",
        "action": action,
        "hint": hongli_hint(tier_id, div_pct),
        "extra": " · ".join(extra_parts),
        "ladder": HONGLI_LADDER,
    }


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
def write_json(name, payload):
    os.makedirs(OUT_DIR, exist_ok=True)
    payload["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    ok = False
    for name, builder in (("csi300", build_csi300), ("hongli", build_hongli)):
        try:
            payload = builder(token)
            if payload:
                write_json(name, payload)
                ok = True
        except Exception as e:
            print(f"⚠️ {name} 导出失败（保留旧 JSON）：{e}")

    if not ok:
        print("❌ 两个指数都未导出，请检查配置")
        sys.exit(1)
    print("✅ 完成")


if __name__ == "__main__":
    main()
