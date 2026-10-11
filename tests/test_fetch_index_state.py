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
MS = int(datetime(2026, 9, 30, 12).timestamp() * 1000)
ROW = {
    "Zone": "中性",
    "composite": 55.3,
    "action": "不买入，持有",
    "summary": "沪深300｜2026-09｜综合便宜度 55（中性）｜历史上同档买入持有 2 年：中位数 +4%，最差 10% −13%，4 段独立行情 → 不买入，持有",
    "rulers": "PE 13.20（38） / PB 1.39（62） / 股息率 2.90%（67）",
    "reading_kind": "月末正式读数",
    "rule_version": "宽基v1.1(方案D+②b)+行业与策略v1.1",
}


class TestPrivacy(unittest.TestCase):
    def test_forbidden_keys(self):
        for key in ("holdings", "position_pct", "仓位", "卖出金额", "持仓市值", "total_assets", "amount"):
            with self.assertRaises(ValueError, msg=key):
                fis.assert_public({"name": "x", key: 1})
        with self.assertRaises(ValueError):
            fis.assert_public({"nested": [{"Holdings": 1}]})

    def test_forbidden_values(self):
        for v in ("本月应卖出约 10.0 万", "医药 105.1 万，占 28.5%", "仓位提醒", "总资产 369.2", "持仓快照 2026-10-09"):
            with self.assertRaises(ValueError, msg=v):
                fis.assert_public({"summary": v})

    def test_rule_texts_pass(self):
        # 规则动作里的“持仓”（如②b 的“进入贵档时持仓的 1/12”）不是金额，允许
        fis.assert_public({"action": "卖出进入贵档时持仓的 1/12（本轮贵档已卖 3/12），卖出资金回资金池"})
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
