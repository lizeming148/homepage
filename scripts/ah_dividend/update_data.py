"""更新 AH 股息比价工具的数据文件：tools/ah-dividend/ah_pairs.json 与 fx.json。

用法（在仓库根目录）：
    python scripts/ah_dividend/update_data.py            # 更新名单 + 汇率
    python scripts/ah_dividend/update_data.py --fx-only  # 只更新汇率（名单数据源故障时用）
    python scripts/ah_dividend/update_data.py --dry-run  # 只取数和打印报告，不写文件

数据源（AkShare 1.19.1 实测）：
- AH 名单：stock_zh_ah_name（腾讯）定名单，但它只有 H 股代码和港股简称；
  A 股代码来自东方财富 F10 的 A/H 代码对照，再用 stock_info_a_code_name（沪深北在市 A 股）
  过滤掉 B 股、新三板、旧代码，并取 A 股简称作名称。
  （AkShare 的 stock_zh_ah_spot_em 虽然自带两边代码，但它的 push2 域名本机直连被封、走代理 502。）
- 注册地：stock_hk_company_profile_em（东方财富港股公司资料的「注册地」），用来找境外注册公司。
- 汇率：优先港股通参考汇率（上交所 → 深交所，取买入价/卖出价中值），
  都取不到时用人民币汇率中间价 currency_boc_safe（外管局，港元列为每 100 港元）。

规则：
- 已有公司的人工字段 h_tax / h_tax_status / note / verified 永不覆盖，只更新名称等基础信息。
- 名单里消失的公司不删除，只在报告里提示。
- 任一必需数据源失败、或结果看起来残缺，就不写任何文件，报错退出（退出码 1）。
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "tools" / "ah-dividend"
PAIRS_FILE = DATA_DIR / "ah_pairs.json"
FX_FILE = DATA_DIR / "fx.json"

DEFAULT_H_TAX = 0.20
# 每条记录的字段与缺省值；h_tax / h_tax_status / note / verified 是人工字段，已有公司永不覆盖
FIELD_DEFAULTS = {
    "name": "",
    "a_code": "",
    "h_code": "",
    "h_tax": DEFAULT_H_TAX,
    "h_tax_status": "default",
    "note": "",
    "verified": "",
    "domicile": "",
}
TAX_STATUSES = ("default", "pending", "verified")

# 任务书指定的红筹种子（H 股代码），首次出现时标 pending
SEED_PENDING = {
    "00941": "中国移动",
    "00883": "中国海洋石油",
    "00981": "中芯国际",
    "06160": "百济神州",
}

# 名单少于这么多只，或比上次少了 20% 以上，视为取数残缺
MIN_PAIRS = 100
MAX_SHRINK = 0.8

# 东方财富等国内数据源走本机代理时常报 502，先直连，失败再走代理
DOMESTIC_HOSTS = "eastmoney.com,gtimg.cn,qq.com,sse.com.cn,szse.cn,bse.cn,safe.gov.cn"


class DataError(Exception):
    pass


def log(msg=""):
    print(msg, flush=True)


def with_proxy_fallback(label, fn):
    """先绕过代理直连国内数据源，失败再按系统代理设置重试一次。"""
    saved = {k: os.environ.get(k) for k in ("NO_PROXY", "no_proxy")}
    errors = []
    for mode in ("直连", "代理"):
        if mode == "直连":
            extra = ",".join(x for x in (saved["NO_PROXY"] or saved["no_proxy"], DOMESTIC_HOSTS) if x)
            os.environ["NO_PROXY"] = os.environ["no_proxy"] = extra
        else:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 —— 数据源报错种类很多，统一兜住
            errors.append(f"{mode}：{type(e).__name__}: {str(e)[:150]}")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    raise DataError(f"{label} 获取失败\n  " + "\n  ".join(errors))


# ---------- 读旧文件 ----------

def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        # 旧文件坏了不能当成“没有”，否则会冲掉人工数据
        raise DataError(f"{path.name} 无法解析（{e}），请先手动修好再运行") from e


def load_old_pairs():
    data = load_json(PAIRS_FILE)
    if data is None:
        return None
    if not isinstance(data.get("pairs"), list):
        raise DataError(f"{PAIRS_FILE.name} 缺少 pairs 列表，请先手动修好再运行")
    old = {}
    for p in data["pairs"]:
        code = str(p.get("a_code", ""))
        if not code:
            raise DataError(f"{PAIRS_FILE.name} 有一条缺 a_code：{p}")
        old[code] = p
    return old


# ---------- 取数 ----------

def fetch_h_codes():
    """腾讯 AH 名单：只有 H 股代码和港股简称。分页按股价排序，末页会重复首页几只，去重即可。"""
    import akshare as ak

    df = with_proxy_fallback("AH 名单（腾讯 stock_zh_ah_name）", ak.stock_zh_ah_name)
    if "代码" not in df.columns:
        raise DataError(f"腾讯 AH 名单字段变了：期望含 '代码'，实际 {list(df.columns)}")
    codes = {str(c).strip().zfill(5) for c in df["代码"]}
    bad = [c for c in codes if not re.fullmatch(r"\d{5}", c)]
    if bad:
        raise DataError(f"腾讯 AH 名单有异常代码：{bad[:10]}")
    return codes


def fetch_listed_a():
    """当前在市 A 股代码 → 简称（沪深北交易所官方列表）。"""
    import akshare as ak

    df = with_proxy_fallback("A 股代码列表（stock_info_a_code_name）", ak.stock_info_a_code_name)
    if not {"code", "name"}.issubset(df.columns):
        raise DataError(f"A 股列表字段变了：期望含 code/name，实际 {list(df.columns)}")
    return {str(c).strip().zfill(6): str(n) for c, n in zip(df["code"], df["name"])}


def fetch_ah_code_map():
    """东方财富 F10 公司资料里登记了 H 股代码的 A 股公司，返回 [(a_code, h_code)]。

    AkShare 里唯一同时给出 A/H 代码的接口 stock_zh_ah_spot_em 走 push2.eastmoney.com，
    本机直连会被封、走代理报 502，所以直接查同一家的数据中心接口（F10 用的 datacenter 域名）。
    结果里混有 B 股、新三板、未上市代码和旧代码，后面用在市 A 股列表过滤。
    """
    import requests

    def get():
        r = requests.get(
            "https://datacenter.eastmoney.com/securities/api/data/v1/get",
            params={
                "reportName": "RPT_F10_BASIC_ORGINFO",
                "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,STR_CODEH",
                "filter": '(STR_CODEH>"0")',
                "pageNumber": 1,
                "pageSize": 2000,
                "source": "HSF10",
                "client": "PC",
            },
            timeout=30,
        )
        r.raise_for_status()
        js = r.json()
        if not js.get("success"):
            raise DataError(f"接口返回失败：{js.get('message')}")
        res = js["result"]
        if res.get("pages", 1) > 1:
            raise DataError(f"结果超过一页（共 {res.get('count')} 条），需要加分页")
        return res["data"]

    rows = with_proxy_fallback("A/H 代码对照（东方财富 F10）", get)
    out = []
    for r in rows:
        for h in str(r.get("STR_CODEH") or "").split(","):
            h = h.strip().removesuffix(".HK")
            if re.fullmatch(r"\d{5}", h):
                out.append((str(r["SECURITY_CODE"]), h, clean_name(r.get("SECURITY_NAME_ABBR"))))
    return out


def clean_name(name):
    """全角转半角，去掉空格和交易所临时加的除权除息前缀（XD/XR/DR）。"""
    name = unicodedata.normalize("NFKC", str(name or "")).replace(" ", "")
    return re.sub(r"^(XD|XR|DR)", "", name)


def fetch_ah_list():
    """合并三份数据：腾讯定名单（H 股代码），F10 对照补 A 股代码，在市 A 股列表过滤并给出简称。"""
    h_codes = fetch_h_codes()
    listed = fetch_listed_a()
    code_map = fetch_ah_code_map()

    by_h, f10_names = {}, {}
    for a_code, h_code, f10_name in code_map:
        if h_code in h_codes and a_code in listed:
            by_h.setdefault(h_code, set()).add(a_code)
            f10_names[a_code] = f10_name

    unresolved = sorted(h for h in h_codes if len(by_h.get(h, ())) != 1)
    rows = {}
    for h_code, a_codes in by_h.items():
        if len(a_codes) == 1:
            a_code = next(iter(a_codes))
            # 交易所列表的简称在除息日会变成「XD中国太」这类截断名，优先用 F10 简称
            name = f10_names[a_code] or clean_name(listed[a_code])
            rows[a_code] = {"name": name, "a_code": a_code, "h_code": h_code}
    return rows, {h: sorted(by_h.get(h, ())) for h in unresolved}


def fetch_domicile(h_code):
    """返回注册地字符串；查不到返回 None（只用于提示，不影响主流程）。"""
    import akshare as ak

    try:
        df = with_proxy_fallback(f"{h_code} 注册地", lambda: ak.stock_hk_company_profile_em(symbol=h_code))
        val = str(df["注册地"].iloc[0]).strip()
        return val or None
    except Exception:  # noqa: BLE001
        return None


def is_offshore(domicile):
    if not domicile:
        return False
    if any(x in domicile for x in ("香港", "澳门", "台湾")):
        return True
    return not domicile.startswith("中国")


def fetch_fx():
    import akshare as ak

    errors = []
    for label, fn in (
        ("上交所港股通参考汇率", ak.stock_sgt_reference_exchange_rate_sse),
        ("深交所港股通参考汇率", ak.stock_sgt_reference_exchange_rate_szse),
    ):
        try:
            df = with_proxy_fallback(label, fn)
            df = df[df["货币种类"].astype(str).str.upper() == "HKD"].copy()
            df["适用日期"] = df["适用日期"].astype(str)
            latest = df[df["适用日期"] == df["适用日期"].max()]
            # 上交所偶有同一适用日期两条记录（更新日期不同、数值不同），AkShare 丢了更新日期，无法判断取哪条
            if len(latest[["参考汇率买入价", "参考汇率卖出价"]].drop_duplicates()) > 1:
                raise DataError(f"{latest['适用日期'].iloc[0]} 有多条不一致的记录：\n{latest.to_string()}")
            row = latest.iloc[-1]
            rate = round((float(row["参考汇率买入价"]) + float(row["参考汇率卖出价"])) / 2, 4)
            return {
                "rate": rate,
                "date": row["适用日期"][:10],
                "source": f"{label}（买入价 {row['参考汇率买入价']} / 卖出价 {row['参考汇率卖出价']} 的中值）",
            }
        except Exception as e:  # noqa: BLE001
            errors.append(f"{label}：{e}")

    try:
        df = with_proxy_fallback("人民币汇率中间价", ak.currency_boc_safe)
        df = df.dropna(subset=["港元"])
        df["日期"] = df["日期"].astype(str)
        row = df.sort_values("日期").iloc[-1]
        return {
            "rate": round(float(row["港元"]) / 100, 5),
            "date": row["日期"][:10],
            "source": "外汇管理局人民币汇率中间价（港股通参考汇率取不到时的备用源）",
        }
    except Exception as e:  # noqa: BLE001
        errors.append(f"人民币汇率中间价：{e}")
    raise DataError("汇率全部数据源失败\n  " + "\n  ".join(str(x) for x in errors))


# ---------- 合并 ----------

def merge_pairs(old, fresh):
    """old: 旧文件 {a_code: pair} 或 None；fresh: 新名单 {a_code: 基础信息}。返回 (pairs, report)。"""
    old = old or {}
    report = {"added": [], "missing": [], "renamed": [], "offshore_new": [], "domicile_unknown": []}
    merged = {}

    for a_code, base in fresh.items():
        prev = old.get(a_code)
        if prev is not None:
            p = dict(prev)  # 保留人工字段和其他已有字段
            if prev.get("name") != base["name"] or prev.get("h_code") != base["h_code"]:
                report["renamed"].append((prev.get("name"), prev.get("h_code"), base["name"], base["h_code"]))
            p["name"] = base["name"]
            p["h_code"] = base["h_code"]
            if not p.get("domicile"):
                p["domicile"] = fetch_domicile(base["h_code"]) or ""
        else:
            domicile = fetch_domicile(base["h_code"]) or ""
            p = {**FIELD_DEFAULTS, **base, "domicile": domicile}
            if base["h_code"] in SEED_PENDING or is_offshore(domicile):
                p["h_tax_status"] = "pending"
                where = f"境外注册（{domicile}）" if is_offshore(domicile) else "红筹"
                p["note"] = f"{where}，税率可能为 28%，待按最近分红公告核实"
                report["offshore_new"].append(p)
            if not domicile:
                report["domicile_unknown"].append(p)
            report["added"].append(p)
        merged[a_code] = p

    for a_code, prev in old.items():
        if a_code not in fresh:
            merged[a_code] = prev  # 不自动删除
            report["missing"].append(prev)

    pairs = []
    for a_code in sorted(merged):
        p = {**FIELD_DEFAULTS, **merged[a_code]}
        # 字段顺序固定，便于人工查看和比对；人工加的其他字段排在后面
        pairs.append({k: p[k] for k in FIELD_DEFAULTS} | {k: v for k, v in p.items() if k not in FIELD_DEFAULTS})
    return pairs, report


def validate_pairs(pairs, fresh_count, old_count):
    if fresh_count < MIN_PAIRS:
        raise DataError(f"AH 名单只有 {fresh_count} 只（少于 {MIN_PAIRS}），疑似取数残缺，未写入")
    if old_count and fresh_count < old_count * MAX_SHRINK:
        raise DataError(f"AH 名单从 {old_count} 只降到 {fresh_count} 只，疑似取数残缺，未写入")
    for p in pairs:
        if p["h_tax_status"] not in TAX_STATUSES:
            raise DataError(f"{p['name']} 的 h_tax_status={p['h_tax_status']!r} 不是 {TAX_STATUSES} 之一，请手动修正")
        try:
            tax = float(p["h_tax"])
        except (TypeError, ValueError):
            raise DataError(f"{p['name']} 的 h_tax={p['h_tax']!r} 不是数字，请手动修正") from None
        if not 0 <= tax < 1:
            raise DataError(f"{p['name']} 的 h_tax={tax} 超出范围，应写成 0.20 或 0.28 这样的小数")


def validate_fx(fx):
    if not 0.6 < fx["rate"] < 1.2:
        raise DataError(f"汇率 {fx['rate']} 不在合理范围（0.6–1.2），未写入")


# ---------- 写文件 ----------

def write_json_atomic(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------- 报告 ----------

def fmt_pair(p):
    return f"{p['name']}（A {p['a_code']} / H {p['h_code']}）"


def print_report(report, pairs, fx, old_fx, fx_only):
    log()
    log("=" * 56)
    log("变化报告")
    log("=" * 56)

    if not fx_only:
        log(f"\n【新增公司】{len(report['added'])} 家")
        for p in report["added"]:
            log(f"  + {fmt_pair(p)}  注册地：{p.get('domicile') or '未查到'}  状态：{p['h_tax_status']}")

        log(f"\n【名单中消失的公司】{len(report['missing'])} 家（仍保留在文件中，请人工决定是否删除）")
        for p in report["missing"]:
            log(f"  - {fmt_pair(p)}")

        if report["unresolved"]:
            log(f"\n【对不上 A 股代码的 H 股】{len(report['unresolved'])} 只（未加入；若长期存在请手动补进 ah_pairs.json）")
            for h_code, a_codes in report["unresolved"].items():
                log(f"  ? H {h_code}  候选 A 股：{'、'.join(a_codes) or '无'}")

        if report["renamed"]:
            log(f"\n【名称或 H 股代码有变】{len(report['renamed'])} 家")
            for old_name, old_h, new_name, new_h in report["renamed"]:
                log(f"  * {old_name}（H {old_h}） → {new_name}（H {new_h}）")

        if report["offshore_new"]:
            log(f"\n【本次新标为 pending 的境外注册/红筹公司】{len(report['offshore_new'])} 家")
            for p in report["offshore_new"]:
                log(f"  ! {fmt_pair(p)}  注册地：{p.get('domicile') or '未查到'}")

        pending = [p for p in pairs if p["h_tax_status"] == "pending"]
        log(f"\n【当前所有 pending 公司】{len(pending)} 家（税率仍按 {DEFAULT_H_TAX:.0%}，请核实后修改）")
        for p in pending:
            log(f"  ? {fmt_pair(p)}  注册地：{p.get('domicile') or '未查到'}")

        # 注册地在境外、但状态仍是 default 的（比如之前注册地没查到）
        suspect = [p for p in pairs if p["h_tax_status"] == "default" and is_offshore(p.get("domicile"))]
        if suspect:
            log(f"\n【注意】以下公司注册地在境外，但状态仍是 default，建议核实：")
            for p in suspect:
                log(f"  ! {fmt_pair(p)}  注册地：{p['domicile']}")

        unknown = [p for p in pairs if not p.get("domicile")]
        if unknown:
            log(f"\n【注册地未查到】{len(unknown)} 家（下次运行会再查）：")
            log("  " + "、".join(p["name"] for p in unknown))

        verified = sum(p["h_tax_status"] == "verified" for p in pairs)
        log(f"\n名单合计 {len(pairs)} 家：default {sum(p['h_tax_status'] == 'default' for p in pairs)}"
            f" / pending {len(pending)} / verified {verified}")

    log("\n【汇率】")
    log(f"  新：1 港元 = {fx['rate']} 人民币（{fx['date']}，{fx['source']}）")
    if old_fx and isinstance(old_fx.get("hkd_cny"), (int, float)):
        diff = fx["rate"] - old_fx["hkd_cny"]
        log(f"  旧：{old_fx['hkd_cny']}（{old_fx.get('updated', '?')}）  差值：{diff:+.4f}（{diff / old_fx['hkd_cny']:+.2%}）")
    else:
        log("  旧：无")
    age = (dt.date.today() - dt.date.fromisoformat(fx["date"])).days
    if age > 7:
        log(f"  ⚠ 汇率数据日期距今 {age} 天，数据源可能停更")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="更新 AH 股息比价工具的数据文件")
    ap.add_argument("--fx-only", action="store_true", help="只更新汇率")
    ap.add_argument("--dry-run", action="store_true", help="只打印报告，不写文件")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    try:
        old_fx = load_json(FX_FILE)
        old_pairs = None if args.fx_only else load_old_pairs()

        # 先把所有数据取齐，任何一步失败都不写文件
        pairs, report = None, None
        if not args.fx_only:
            log("获取 AH 名单…")
            fresh, unresolved = fetch_ah_list()
            log(f"  取到 {len(fresh)} 家" + (f"，另有 {len(unresolved)} 只 H 股对不上 A 股代码" if unresolved else ""))
            log("合并并查询新公司注册地…")
            pairs, report = merge_pairs(old_pairs, fresh)
            report["unresolved"] = unresolved
            validate_pairs(pairs, len(fresh), len(old_pairs or {}))
        log("获取汇率…")
        fx = fetch_fx()
        validate_fx(fx)
    except DataError as e:
        log(f"\n✗ 失败：{e}\n原文件未改动。")
        return 1

    print_report(report, pairs, fx, old_fx, args.fx_only)

    if args.dry_run:
        log("\n（--dry-run：未写文件）")
        return 0

    if pairs is not None:
        write_json_atomic(PAIRS_FILE, {"updated": today, "default_h_tax": DEFAULT_H_TAX, "pairs": pairs})
    write_json_atomic(FX_FILE, {"updated": fx["date"], "hkd_cny": fx["rate"], "source": fx["source"]})
    log(f"\n✓ 已写入：{FX_FILE.relative_to(REPO)}" + ("" if pairs is None else f"、{PAIRS_FILE.relative_to(REPO)}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
