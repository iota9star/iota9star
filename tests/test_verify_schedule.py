#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_schedule.py 的单元测试 (零依赖, 用标准库 unittest)。

运行:
  python3 -m unittest tests.test_verify_schedule -v
  # 或
  python3 tests/test_verify_schedule.py
"""
import os
import sys
import unittest

# 让脚本能 import 到 scripts/verify_schedule.py
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import verify_schedule as vs  # noqa: E402


class TestOverlapWithPeak(unittest.TestCase):
    """窗口 [t, t+5] 与高峰段 [14,18] 的重叠计算。"""

    def test_before_peak_no_overlap(self):
        """窗口完全在高峰前 → 0 重叠。"""
        for t in [-1, 0, 2, 6, 9]:
            with self.subTest(t=t):
                self.assertEqual(vs.overlap_with_peak(t), 0.0)

    def test_after_peak_no_overlap(self):
        """窗口完全在高峰后 → 0 重叠。"""
        for t in [18, 19, 21, 23]:
            with self.subTest(t=t):
                self.assertEqual(vs.overlap_with_peak(t), 0.0)

    def test_partial_overlap_entering_peak(self):
        """窗口部分进入高峰 (从左侧)。"""
        # [11, 16] 与 [14, 18] → 重叠 [14,16] = 2h
        self.assertAlmostEqual(vs.overlap_with_peak(11), 2.0)
        # [13, 18] → 重叠 [14,18] = 4h
        self.assertAlmostEqual(vs.overlap_with_peak(13), 4.0)
        # [9, 14] → 重叠恰好 [14,14] = 0h (边界)
        self.assertAlmostEqual(vs.overlap_with_peak(9), 0.0)

    def test_partial_overlap_leaving_peak(self):
        """窗口部分进入高峰 (从右侧)。"""
        # [16, 21] 与 [14, 18] → 重叠 [16,18] = 2h
        self.assertAlmostEqual(vs.overlap_with_peak(16), 2.0)
        # [17, 22] → 重叠 [17,18] = 1h
        self.assertAlmostEqual(vs.overlap_with_peak(17), 1.0)

    def test_window_covers_peak(self):
        """窗口完全覆盖高峰。"""
        # [13, 18] → 4h (整个高峰)
        self.assertAlmostEqual(vs.overlap_with_peak(13), 4.0)
        # [12, 17] → 重叠 [14,17] = 3h
        self.assertAlmostEqual(vs.overlap_with_peak(12), 3.0)

    def test_cross_midnight_window(self):
        """跨午夜窗口 (例如起点 22:00)。"""
        # [22, 27] = [22,24]+[0,3], 与 [14,18] 无重叠 → 0
        self.assertEqual(vs.overlap_with_peak(22), 0.0)
        self.assertEqual(vs.overlap_with_peak(23), 0.0)


class TestWindowScore(unittest.TestCase):
    """窗口得分 = 单位额度的有效产出。"""

    def test_zero_overlap_pure_offpeak(self):
        """overlap=0 → 5h 全非高峰, 得分 = 5 * 0.67。"""
        for t in [0, 1, 6, 21]:
            with self.subTest(t=t):
                score, ov, _ = vs.window_score(t)
                self.assertEqual(ov, 0.0)
                self.assertAlmostEqual(score, 5 * vs.OFF_MULT)

    def test_exactly_budget_peak(self):
        """overlap=2 → 高峰用满 2h + 非高峰 3h, 得分 = 2*2 + 3*0.67。"""
        expected = 2 * vs.PEAK_MULT + 3 * vs.OFF_MULT
        for t in [11, 16]:   # [11,16] 和 [16,21] 都是 overlap=2
            with self.subTest(t=t):
                score, ov, note = vs.window_score(t)
                self.assertAlmostEqual(ov, 2.0)
                self.assertAlmostEqual(score, expected, places=2)
                self.assertNotIn("浪费", note)

    def test_over_budget_wastes(self):
        """overlap > 2 → 高峰预算超限, 超出部分浪费, 得分下降。"""
        # [12,17] overlap=3, 浪费 1h
        score, ov, note = vs.window_score(12)
        self.assertAlmostEqual(ov, 3.0)
        self.assertIn("浪费", note)
        # 应小于 overlap=2 的得分
        score_ok, _, _ = vs.window_score(11)
        self.assertLess(score, score_ok)

    def test_score_monotonic_in_forbidden_zone(self):
        """禁区 (11,16) 内, 越靠近高峰中央得分越低 (浪费越多)。"""
        prev = None
        for t in [11.5, 12.0, 12.5, 13.0]:   # 逐步深入高峰中央
            score, _, _ = vs.window_score(t)
            if prev is not None:
                self.assertLess(score, prev,
                                f"t={t} 得分应小于前一个 (越深入越浪费)")
            prev = score


class TestFindBestAnchor(unittest.TestCase):
    """最优锚点求解器。"""

    def test_anchor_is_one(self):
        """最优锚点应为 1.0 (数学上 a∈(0,1] 内 overlap≤2 的唯一解)。"""
        self.assertAlmostEqual(vs.BEST_ANCHOR, 1.0, places=2)

    def test_all_starts_within_budget(self):
        """所有有效起点必须 overlap ≤ 预算 (无超预算窗口)。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(start=s):
                self.assertLessEqual(
                    vs.overlap_with_peak(s),
                    vs.PEAK_BUDGET + 1e-9,
                    f"起点 {s} 超出高峰预算",
                )

    def test_strict_five_hour_spacing(self):
        """相邻有效起点间隔必须严格为 5h (除 1 个不可避免的 4h 缺口)。"""
        starts = sorted(vs.VALID_STARTS_BJ)
        gaps = []
        for i in range(len(starts)):
            nxt = starts[(i + 1) % len(starts)]
            gap = (nxt - starts[i]) % 24
            gaps.append(gap)
        # 24 = 5*4 + 4, 故应有 4 个 5h 和 1 个 4h
        self.assertEqual(len(gaps), 5)
        five_count = sum(1 for g in gaps if abs(g - 5) < 1e-9)
        four_count = sum(1 for g in gaps if abs(g - 4) < 1e-9)
        self.assertEqual(five_count, 4, f"应有 4 个 5h 间隔, 实际 gaps={gaps}")
        self.assertEqual(four_count, 1, f"应有 1 个 4h 缺口, 实际 gaps={gaps}")

    def test_four_hour_gap_at_night(self):
        """那 1 个 4h 缺口应落在深夜 (21→01 附近, 不打扰使用)。"""
        starts = sorted(vs.VALID_STARTS_BJ)
        for i in range(len(starts)):
            nxt = starts[(i + 1) % len(starts)]
            gap = (nxt - starts[i]) % 24
            if abs(gap - 4) < 1e-9:
                # 缺口的起点应在 20-22 之间 (深夜)
                self.assertGreaterEqual(starts[i], 20.0,
                                        f"4h 缺口起点 {starts[i]} 应在深夜")
                self.assertLessEqual(starts[i], 22.0,
                                     f"4h 缺口起点 {starts[i]} 应在深夜")

    def test_expected_starts(self):
        """有效起点应为 [01, 06, 11, 16, 21]。"""
        self.assertEqual(
            [round(s) for s in vs.VALID_STARTS_BJ],
            [1, 6, 11, 16, 21],
        )

    def test_peak_fully_covered(self):
        """高峰段 4h 应被两个窗口各 2h 精确切分, 无浪费。"""
        total_cov = sum(min(vs.overlap_with_peak(s), vs.PEAK_BUDGET)
                        for s in vs.VALID_STARTS_BJ)
        # 高峰段共 4h, 每个窗口最多贡献 2h, 应恰好用满 4h
        self.assertAlmostEqual(total_cov, 4.0, places=6)


class TestGenStarts(unittest.TestCase):
    """锚点 → 有效起点序列生成。"""

    def test_five_starts(self):
        """24/5 向上取整 → 5 个起点。"""
        self.assertEqual(len(vs._gen_starts(0)), 5)
        self.assertEqual(len(vs._gen_starts(1)), 5)

    def test_sorted_ascending(self):
        """起点序列应升序排列 (便于阅读)。"""
        starts = vs._gen_starts(3.5)
        self.assertEqual(starts, sorted(starts))

    def test_spacing_is_five(self):
        """步长必须严格 5h (除跨午夜的那个)。"""
        starts = sorted(vs._gen_starts(1))
        # 计算相邻差, 至少 4 个应是 5
        diffs = []
        for i in range(len(starts) - 1):
            diffs.append(starts[i + 1] - starts[i])
        five_count = sum(1 for d in diffs if abs(d - 5) < 1e-9)
        self.assertGreaterEqual(five_count, 4)


class TestNearestStart(unittest.TestCase):
    """最近有效起点查找 (含环形距离)。"""

    def test_exact_match(self):
        """恰在有效起点上 → 距离 0。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                nearest, d = vs._nearest_start(s)
                self.assertAlmostEqual(nearest, s, places=6)
                self.assertAlmostEqual(d, 0.0, places=6)

    def test_within_tolerance(self):
        """有效起点 ±0.5h 内 → 距离 < 0.5。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                _, d_plus = vs._nearest_start(s + 0.3)
                _, d_minus = vs._nearest_start(s - 0.3)
                self.assertLess(d_plus, 0.5)
                self.assertLess(d_minus, 0.5)

    def test_circular_distance_midnight(self):
        """跨午夜环形距离: 23.8 离 01:00 最近 (距离 1.2h, 非 22.8)。"""
        nearest, d = vs._nearest_start(23.8)
        self.assertAlmostEqual(nearest, 1.0, places=1)
        # 24 - 23.8 + 1.0 = 1.2 (环形最短距离)
        self.assertAlmostEqual(d, 1.2, places=1)
        # 应小于直线距离 |23.8 - 1| = 22.8
        self.assertLess(d, 22.8)

    def test_midpoint_picks_closer(self):
        """两点中间 (如 13.5) 应选更近的那个。"""
        # 11 和 16 之间, 13.5 离两者都 2.5h
        nearest, d = vs._nearest_start(13.5)
        self.assertAlmostEqual(d, 2.5, places=1)


class TestGuard(unittest.TestCase):
    """guard 门控逻辑。"""

    def test_run_at_valid_starts(self):
        """5 个有效起点上 → should_run=True。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                g = vs.guard(s)
                self.assertTrue(g["should_run"], f"{s} 应 RUN")
                self.assertTrue(g["within_tolerance"])
                self.assertAlmostEqual(g["distance"], 0.0, places=6)

    def test_skip_in_forbidden_zone(self):
        """禁区 (11,16) 内 (非有效起点) → should_run=False。"""
        for t in [12, 13, 14, 15]:
            with self.subTest(t=t):
                g = vs.guard(t)
                self.assertFalse(g["should_run"], f"{t} 应 SKIP")

    def test_skip_between_starts(self):
        """有效起点之间的中段 (超容差) → SKIP。"""
        for t in [3, 4, 8, 9, 13, 18, 19]:
            with self.subTest(t=t):
                g = vs.guard(t)
                self.assertFalse(g["should_run"], f"{t} 应 SKIP")

    def test_run_at_tolerance_boundary(self):
        """有效起点 ±0.5h 边界 → 仍 RUN。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                self.assertTrue(vs.guard(s + 0.5)["should_run"])
                self.assertTrue(vs.guard(s - 0.5)["should_run"])

    def test_skip_just_outside_tolerance(self):
        """有效起点 +0.6h → 超容差 → SKIP。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                self.assertFalse(vs.guard(s + 0.6)["should_run"])

    def test_refresh_gap_field(self):
        """guard 返回的 refresh_gap 应 = 到下一有效起点的间隔。"""
        # 起点 1.0 → 下一个 6.0, gap=5
        g = vs.guard(1.0)
        self.assertAlmostEqual(g["refresh_gap"], 5.0)
        # 起点 21.0 → 下一个 1.0 (跨午夜), gap=4
        g = vs.guard(21.0)
        self.assertAlmostEqual(g["refresh_gap"], 4.0)

    def test_structure_note_present(self):
        """guard 应返回结构说明字符串。"""
        g = vs.guard(11)
        self.assertIsInstance(g["structure"], str)
        self.assertGreater(len(g["structure"]), 0)

    def test_run_count_over_24h(self):
        """一天 24 整点触发, 应恰有 5 次 RUN。"""
        run_count = sum(1 for h in range(24) if vs.guard(float(h))["should_run"])
        self.assertEqual(run_count, 5, "一天应有 5 次 RUN (对应 5 个额度池)")

    def test_run_hours_match(self):
        """RUN 的时刻应恰为 01/06/11/16/21。"""
        run_hours = sorted(
            h for h in range(24) if vs.guard(float(h))["should_run"]
        )
        self.assertEqual(run_hours, [1, 6, 11, 16, 21])

    def test_guard_without_arg_uses_now(self):
        """guard() 无参数应能返回结果 (使用当前时刻, 不报错)。"""
        g = vs.guard()
        self.assertIn("should_run", g)
        self.assertIsInstance(g["should_run"], bool)


class TestParseCronHours(unittest.TestCase):
    """cron 表达式解析。"""

    def test_single_hour(self):
        trigs = vs.parse_cron_hours("0 18 * * *")
        self.assertEqual(len(trigs), 1)
        # UTC 18:00 → 北京 02:00
        self.assertAlmostEqual(trigs[0].hour_beijing, 2.0)

    def test_multiple_hours(self):
        trigs = vs.parse_cron_hours("0 18,23,3,8,13 * * *")
        self.assertEqual(len(trigs), 5)
        bj_hours = sorted(round(t.hour_beijing) for t in trigs)
        self.assertEqual(bj_hours, [2, 7, 11, 16, 21])

    def test_every_hour(self):
        trigs = vs.parse_cron_hours("0 * * * *")
        self.assertEqual(len(trigs), 24)

    def test_with_minutes(self):
        trigs = vs.parse_cron_hours("30 0 * * *")
        self.assertEqual(len(trigs), 1)
        # UTC 00:30 → 北京 08:30 = 8.5
        self.assertAlmostEqual(trigs[0].hour_beijing, 8.5)

    def test_step(self):
        """*/2 → 0,2,4,...,22。"""
        trigs = vs.parse_cron_hours("0 */2 * * *")
        self.assertEqual(len(trigs), 12)

    def test_invalid_field_count(self):
        with self.assertRaises(ValueError):
            vs.parse_cron_hours("0 18 * *")       # 4 字段
        with self.assertRaises(ValueError):
            vs.parse_cron_hours("0 18 * * * *")   # 6 字段

    def test_sorted_by_beijing_time(self):
        """触发序列应按北京时刻升序。"""
        trigs = vs.parse_cron_hours("0 18,23,3,8,13 * * *")
        bj = [t.hour_beijing for t in trigs]
        self.assertEqual(bj, sorted(bj))


class TestEvaluate(unittest.TestCase):
    """策略评估。"""

    def test_recommended_strategy_no_over_budget(self):
        """推荐策略不应有任何超预算窗口。"""
        rep = vs.evaluate("推荐", "0 17,22,3,8,13 * * *")
        self.assertEqual(rep.over_budget_windows, 0)
        self.assertAlmostEqual(rep.peak_coverage, 4.0, places=6)

    def test_hourly_has_over_budget(self):
        """每小时策略必然产生超预算窗口 (13/14 点 overlap=4)。"""
        rep = vs.evaluate("每小时", "0 * * * *")
        self.assertGreater(rep.over_budget_windows, 0)

    def test_single_trigger_low_coverage(self):
        """单次触发 → 高峰覆盖 0 (完全没用上高峰预算)。"""
        rep = vs.evaluate("单次", "0 18 * * *")
        self.assertAlmostEqual(rep.peak_coverage, 0.0, places=6)


class TestMainCLI(unittest.TestCase):
    """命令行入口。"""

    def test_guard_mode_run(self):
        """--guard 11.0 → 退出码 0 (RUN)。"""
        rc = vs.main(["verify_schedule.py", "--guard", "11.0"])
        self.assertEqual(rc, 0)

    def test_guard_mode_skip(self):
        """--guard 13.0 → 退出码 2 (SKIP)。"""
        rc = vs.main(["verify_schedule.py", "--guard", "13.0"])
        self.assertEqual(rc, 2)

    def test_guard_mode_all_valid_starts(self):
        """所有有效起点 → 退出码 0。"""
        for s in vs.VALID_STARTS_BJ:
            with self.subTest(s=s):
                rc = vs.main(["verify_schedule.py", "--guard", str(s)])
                self.assertEqual(rc, 0)

    def test_cron_expr_mode(self):
        """单 cron 表达式模式 → 退出码 0。"""
        rc = vs.main(["verify_schedule.py", "0 8 * * *"])
        self.assertEqual(rc, 0)

    def test_default_mode(self):
        """无参数 → 对比表, 退出码 0。"""
        rc = vs.main(["verify_schedule.py"])
        self.assertEqual(rc, 0)


class TestInvariants(unittest.TestCase):
    """跨函数不变量 (回归测试)。"""

    def test_model_constants(self):
        """套餐模型常量应符合需求描述。"""
        self.assertEqual(vs.WINDOW, 5.0)        # 5 小时刷新
        self.assertEqual(vs.PEAK_START, 14.0)   # 高峰 14 点开始
        self.assertEqual(vs.PEAK_END, 18.0)     # 18 点结束
        self.assertEqual(vs.PEAK_MULT, 2.0)     # 高峰 2x 消耗
        self.assertEqual(vs.OFF_MULT, 0.67)     # 非高峰 0.67x
        self.assertEqual(vs.PEAK_BUDGET, 2.0)   # 每 5h 高峰预算 2h

    def test_24_mod_5_leaves_4(self):
        """数学不变量: 24 = 5*4 + 4。"""
        self.assertEqual(24, 5 * 4 + 4)

    def test_tolerance_half_hour(self):
        """容差 ±30 分钟 (抵消 Actions 抖动)。"""
        self.assertEqual(vs.TOLERANCE_H, 0.5)

    def test_starts_include_both_peak_windows(self):
        """有效起点必须包含 11 和 16 (吃高峰的两个窗口)。"""
        rounded = {round(s) for s in vs.VALID_STARTS_BJ}
        self.assertIn(11, rounded)
        self.assertIn(16, rounded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
