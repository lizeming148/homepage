"""scripts/fetch_index_state.py 的测试（阶段 3C 补充）。

homepage 是公开仓库：导出的 JSON 里不得出现任何持仓金额、仓位比例、卖出金额。
运行：python -m unittest discover -s tests
"""
import glob
import json
import os
import sys
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fetch_index_state as fis  # noqa: E402

DATA = os.path.join(ROOT, "invest", "strategy", "data")
MS = int(datetime(2026, 9, 30, 12, tzinfo=fis.BEIJING).timestamp() * 1000)   # 引擎写入北京中午
ROW = {
    "Zone": "中性",
    "composite": 55.3,
    "action": "不买入，持有",
    "summary": "沪深300｜2026-09｜综合便宜度 55（中性）｜历史上同档买入持有 2 年：中位数 +4%，最差 1/10：亏 13% 以上，独立样本数 4 → 不买入，持有",
    "rulers": "PE 13.20（38） / PB 1.39（62） / 股息率 2.90%（67）",
    "reading_kind": "月末正式读数",
    "rule_version": "宽基v1.1(方案D+②b)+行业与策略v1.1",
}


class TestPrivacy(unittest.TestCase):
    """2026-10-13 起：允许比例、禁止绝对值。"""

    def test_forbidden_keys(self):
        for key in ("holdings", "position", "仓位", "卖出金额", "持仓市值", "total_assets", "amount"):
            with self.assertRaises(ValueError, msg=key):
                fis.assert_public({"name": "x", key: 1})
        with self.assertRaises(ValueError):
            fis.assert_public({"nested": [{"Holdings": 1}]})
        for key in ("position_pct", "持仓比例", "仓位占比"):
            fis.assert_public({"name": "x", key: 30})

    def test_forbidden_values(self):
        for v in ("本月应卖出约 10.0 万", "医药 105.1 万，占 28.5%", "总资产 369.2", "默认 10000 元", "¥5000",
                  "持仓 100 股", "市值：36.5", "3 亿"):
            with self.assertRaises(ValueError, msg=v):
                fis.assert_public({"summary": v})

    def test_ratios_and_rule_texts_pass(self):
        for v in ("仓位 30%", "占 28.5%", "仓位提醒", "持仓快照 2026-10-09", "仓位 3 成",
                  "卖出进入贵档时持仓的 1/12（本轮贵档已卖 3/12），卖出资金回资金池",
                  "PE 10.65（48） / PB 1.13（43） / 股息率 3.76%（53） / 股债差 2.09%（82）"):
            fis.assert_public({"summary": v})
        fis.assert_public(fis.signal_payload("沪深300", "000300.SH", MS, "Zone", ROW))

    def test_committed_json_files_are_public_safe(self):
        files = sorted(glob.glob(os.path.join(DATA, "*.json")))
        self.assertEqual([os.path.basename(f) for f in files], ["csi300.json", "hongli.json", "hsi.json"])
        for f in files:
            with open(f, encoding="utf-8") as fp:
                fis.assert_public(json.load(fp), os.path.basename(f))

    def test_write_json_refuses_private_payload(self):
        with self.assertRaises(ValueError):
            fis.write_json("should_not_exist", {"name": "x", "holdings": [1]})
        self.assertFalse(os.path.exists(os.path.join(DATA, "should_not_exist.json")))


class TestPrivacyRulesCopy(unittest.TestCase):
    """与 tests/privacy_rules.json（固定副本 + 哈希）比对。引擎仓库（csi300-valuation-engine / hsi-monitor 的
    index_rules/privacy.py）存有同一份副本并做同样的比对，所以 CI 只拉本仓库时也能保证两边规则一致。"""

    def test_rules_match_fixed_copy(self):
        import hashlib
        with open(os.path.join(ROOT, "tests", "privacy_rules.json"), encoding="utf-8") as f:
            fx = json.load(f)
        keys = ("key_tokens_absolute", "key_tokens_context", "ratio_markers", "value_patterns")
        canon = json.dumps({k: fx[k] for k in keys}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(hashlib.sha256(canon.encode("utf-8")).hexdigest(), fx["sha256"], "副本内容与哈希不符")
        self.assertEqual(fis.rules_dict(), {k: fx[k] for k in keys})


class TestOverlapAndPages(unittest.TestCase):
    def test_dy_overlap_flag_from_rulers(self):
        p = fis.signal_payload("恒生指数", "HSI.HK", MS, "Zone", dict(ROW, rulers="PE 10.65（48） / 股息率 3.58%（折算；原始 3.75%，除息重叠标注）（42）"))
        self.assertTrue(p["dy_overlap"])
        self.assertFalse(fis.signal_payload("沪深300", "000300.SH", MS, "Zone", ROW)["dy_overlap"])

    def test_pages_have_note_and_no_absolute_amounts(self):
        import re
        for slug in ("csi300", "hongli", "hsi"):
            with open(os.path.join(ROOT, "invest", "strategy", slug, "index.html"), encoding="utf-8") as f:
                t = f.read()
            self.assertIn("便宜分位：当前值在近 10 年", t, slug)
            self.assertIn("d.dy_overlap", t, slug)
            self.assertNotIn("默认 1 万元", t)
            self.assertNotIn("单月飙升", t)
        with open(os.path.join(ROOT, "invest", "index.html"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn("原值（便宜分位）", t)
        self.assertIn("便宜分位：当前值在近 10 年", t)
        # 估值策略页（含脚本）不得出现个人金额（“1 万元”“10000 元”“¥”）
        for slug in ("csi300", "hongli", "hsi"):
            with open(os.path.join(ROOT, "invest", "strategy", slug, "index.html"), encoding="utf-8") as f:
                t = f.read()
            self.assertIsNone(re.search(r"\d[\d.,]*\s*万元|\d[\d.,]*\s*元(?!/)|[¥￥]\s*\d", t), slug)


class TestTierColors(unittest.TestCase):
    def test_same_palette_as_feishu_cards(self):
        # 便宜深绿、偏便宜浅绿、中性灰、偏贵橙、贵红（与飞书卡片 green / lime / grey / orange / red 一致）
        self.assertEqual(fis.TIER_HEX, {"便宜": "#1E7A3E", "偏便宜": "#6BA539", "中性": "#8A8A88",
                                        "偏贵": "#CB6B1E", "贵": "#C0392B"})


class TestGuidePage(unittest.TestCase):
    def test_guide_filled_and_linked(self):
        import re
        with open(os.path.join(ROOT, "invest", "strategy", "guide", "index.html"), encoding="utf-8") as f:
            g = f.read()
        self.assertNotIn("待填", g)
        self.assertNotIn("todo", g)
        self.assertIn("3 倍基数", g)
        self.assertIn("1/12", g)
        self.assertIn("cloudflareinsights", g)
        # 第 3 节（动作规则）只写比例，不写绝对金额
        s3 = g[g.index('id="s3"'):g.index('id="s4"')]
        self.assertIsNone(re.search(r"\d[\d.,]*\s*(万|亿|元)|[¥￥]\s*\d", s3))
        for page in ("index.html", "strategy/csi300/index.html", "strategy/hongli/index.html", "strategy/hsi/index.html"):
            with open(os.path.join(ROOT, "invest", *page.split("/")), encoding="utf-8") as f:
                self.assertIn("/invest/strategy/guide/", f.read(), page)


class TestBeijingDates(unittest.TestCase):
    def test_ms_to_date_is_beijing_regardless_of_machine_tz(self):
        from datetime import timezone
        self.assertEqual(fis.ms_to_date(MS), "2026-09-30")                                   # 新记录：北京中午
        utc0 = int(datetime(2026, 9, 30, tzinfo=timezone.utc).timestamp() * 1000)            # 旧记录：UTC 零点
        self.assertEqual(fis.ms_to_date(utc0), "2026-09-30")
        self.assertEqual(fis.ms_to_date(int(datetime(2026, 9, 30, 23, 59, tzinfo=fis.BEIJING).timestamp() * 1000)), "2026-09-30")
        self.assertIsNone(fis.ms_to_date(None))


class TestSignalPayload(unittest.TestCase):
    def test_new_rule_card(self):
        p = fis.signal_payload("沪深300", "000300.SH", MS, "Zone", ROW)
        self.assertEqual((p["status"], p["metric_value"], p["metric_label"]), ("中性", "55", "综合便宜度"))
        self.assertEqual(p["date"], "2026-09-30")
        self.assertEqual(p["color"], fis.TIER_HEX["中性"])
        self.assertEqual(p["summary"], ROW["summary"])
        self.assertNotIn("ladder", p)

    def test_missing_new_fields_raise(self):
        row = dict(ROW)
        del row["summary"]
        with self.assertRaisesRegex(RuntimeError, "缺少新字段"):
            fis.signal_payload("沪深300", "000300.SH", MS, "Zone", row)
        with self.assertRaisesRegex(RuntimeError, "不是新规则档名"):
            fis.signal_payload("沪深300", "000300.SH", MS, "Zone", dict(ROW, Zone="卖出中"))   # 旧引擎档名

    def test_latest_complete_record_is_used(self):
        # 最新一条不全（例如引擎刚切换、或当天写了一半）→ 用最近一条齐全的，并显示它自己的日期
        day = 86400000
        items = [
            {"fields": dict(ROW, Date=MS - 2 * day)},                                  # 齐全，较早
            {"fields": dict(ROW, Date=MS - day, Zone="中性", composite=56.0)},          # 齐全，最近
            {"fields": {"Date": MS, "Zone": "中性", "composite": 57.0}},                # 最新，但缺 summary 等
            {"fields": {"Date": MS - 30 * day, "Zone": "卖出中"}},                      # 旧引擎记录
        ]
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            ms, f = fis.latest_complete(items, "Zone", "沪深300")
        self.assertEqual(ms, MS - day)
        self.assertIn("最近 1 条记录新字段不全", buf.getvalue())
        p = fis.signal_payload("沪深300", "000300.SH", ms, "Zone", f)
        self.assertEqual((p["date"], p["metric_value"]), ("2026-09-29", "56"))

    def test_all_incomplete_raises(self):
        items = [{"fields": {"Date": MS, "Zone": "卖出中", "PE_converted": 14.2}},
                 {"fields": {"Date": MS - 1, "Zone": "中性", "composite": "abc", **{k: "x" for k in fis.PUBLIC_FIELDS if k != "composite"}}}]
        with self.assertRaisesRegex(RuntimeError, "全部 2 条记录都缺新规则字段"):
            fis.latest_complete(items, "Zone", "沪深300")
        with self.assertRaisesRegex(RuntimeError, "表为空"):
            fis.latest_complete([], "Zone", "沪深300")

    def test_feishu_text_list_format(self):
        row = dict(ROW, Zone=[{"type": "text", "text": "中性"}], summary=[{"type": "text", "text": "a"}, {"type": "text", "text": "b"}])
        p = fis.signal_payload("沪深300", "000300.SH", MS, "Zone", row)
        self.assertEqual((p["status"], p["summary"]), ("中性", "ab"))

    def test_no_old_threshold_logic_left(self):
        with open(os.path.join(ROOT, "scripts", "fetch_index_state.py"), encoding="utf-8") as f:
            src = f.read()
        for old in ("CSI_LADDER", "HONGLI_TIERS", "HSI_TIERS", "止盈", "14.5", "4.03", "dq_discount"):
            self.assertNotIn(old, src, old)

    def test_builders_use_feishu_rows(self):
        calls = []

        def fake_fetch_all(token, app, table, fields=None):
            calls.append((table, tuple(fields)))
            if table == fis.HSI_DIVIDEND_TABLE:
                return [{"fields": {"date": MS, "grade": "YELLOW", "weighted_payout": 32.9, "alerts": "无"}}]
            base = dict(ROW)
            if "tier" in fields:
                base["tier"] = base.pop("Zone")
            older = {"Date": MS - 86400000, "date": MS - 86400000, "Zone": "卖出中", "tier": "②偏贵"}   # 旧行（旧档名）
            return [{"fields": older}, {"fields": dict(base, Date=MS, date=MS, spread_dy_cn=1.86, erp_cn=7.64)}]
        orig = fis.fetch_all
        os.environ.update({"FEISHU_APP_TOKEN_300": "a", "FEISHU_PE_HISTORY_TABLE_ID": "t1",
                           "FEISHU_APP_TOKEN_922": "b", "FEISHU_DATA_TABLE_922": "t2"})
        try:
            fis.fetch_all = fake_fetch_all
            for b in (fis.build_csi300, fis.build_hongli, fis.build_hsi):
                p = b("tok")
                self.assertEqual(p["status"], "中性")
                fis.assert_public(p)
            hsi = fis.build_hsi("tok")
            self.assertEqual(hsi["extra"], "ERP（仅展示）+7.64%")
            self.assertEqual(hsi["dq_grade"], "YELLOW")
        finally:
            fis.fetch_all = orig
        for _, fields in calls:
            for f in fields:
                for t in ("holding", "仓位", "金额"):
                    self.assertNotIn(t, f)


if __name__ == "__main__":
    unittest.main()
