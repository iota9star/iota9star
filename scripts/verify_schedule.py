#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套餐调度验证脚本
================
验证 GitHub Actions cron 触发时刻是否最大化套餐用量。

套餐模型（硬约束）:
  - 额度池每 5 小时刷新一次（每 5h 一个独立额度池）
  - 高峰段 14:00-18:00 (北京) 消耗系数 2.0  (额度烧得快)
  - 其余时段非高峰系数 0.67 (额度耐用约 1.5 倍)
  - 5h 窗口内高峰用量预算上限 = 2h

核心结论: 额度每 5h 刷新 → 触发频率超过 1 次/5h 不会增加总用量;
真正决定用量的是「每个 5h 窗口起点 t 落在哪个时段」。
最优起点满足 overlap(t) ∈ {0, 2}, 即 t ∈ (-∞,11] ∪ [16,+∞)。

用法:
  python scripts/verify_schedule.py                 # 默认: 对比多种策略
  python scripts/verify_schedule.py "0 8 * * *"      # 验证单个 cron 表达式
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

# 所有时刻均为北京时间 (UTC+8), 与套餐规则描述的时段一致
PEAK_START = 14.0   # 高峰起点 (小时, 24h 制)
PEAK_END = 18.0     # 高峰终点
WINDOW = 5.0        # 套餐刷新周期 = 单次用量窗口长度
PEAK_MULT = 2.0     # 高峰消耗系数
OFF_MULT = 0.67     # 非高峰消耗系数
PEAK_BUDGET = 2.0   # 每 5h 窗口高峰用量上限 (小时)


# ---------------------------------------------------------------------------
# 核心: 单个窗口的用量评分
# ---------------------------------------------------------------------------

def overlap_with_peak(t: float) -> float:
    """窗口 [t, t+WINDOW] 与高峰段 [PEAK_START, PEAK_END] 的重叠小时数。"""
    lo = max(t, PEAK_START)
    hi = min(t + WINDOW, PEAK_END)
    return max(0.0, hi - lo)


def window_score(t: float) -> tuple[float, float, str]:
    """
    返回 (用量得分, 高峰重叠, 结构说明)。

    用量得分定义:
      - overlap ≤ PEAK_BUDGET (2h): 高峰预算够用, 实际得 2h 高峰 + 其余非高峰,
        得分 = 高峰占额度比的反向收益 = 2*PEAK_MULT + (5-2)*OFF_MULT
      - overlap > PEAK_BUDGET: 超出预算的部分按非高峰"折损"计 (高峰额度超限
        无法使用, 视为浪费), 得分下降。
    得分越高 = 单位额度的有效产出越大 → 越接近"最大化用量"。
    """
    ov = overlap_with_peak(t)
    if ov <= PEAK_BUDGET:
        # 预算内: 高峰用满 ov (≤2), 非高峰用 (5-ov)
        peak_used = ov
        off_used = WINDOW - ov
        score = peak_used * PEAK_MULT + off_used * OFF_MULT
        note = f"高峰{peak_used:.1f}h + 非高峰{off_used:.1f}h"
    else:
        # 超预算: 高峰只能用 PEAK_BUDGET, 超出部分 (ov-2) 浪费
        peak_used = PEAK_BUDGET
        off_used = WINDOW - ov          # 窗口里非高峰的部分照常可用
        wasted = ov - PEAK_BUDGET       # 高峰额度超限, 不可用
        score = peak_used * PEAK_MULT + off_used * OFF_MULT - wasted
        note = f"⚠ 高峰{ov:.1f}h 超预算, 浪费 {wasted:.1f}h"
    return score, ov, note


# ---------------------------------------------------------------------------
# cron 解析 (轻量, 仅支持本项目需要的 5 字段格式)
# ---------------------------------------------------------------------------

@dataclass
class Trigger:
    """单个触发时刻 (一天内的小时, 北京时间)。"""
    hour_utc: float
    hour_beijing: float

    @property
    def window(self) -> str:
        s = self.hour_beijing
        e = (s + WINDOW) % 24
        return f"[{s:05.2f} → {e:05.2f}]".replace(".", ":")


def _expand_field(field: str, lo: int, hi: int) -> list[int]:
    out: list[int] = []
    for part in field.split(","):
        part = part.strip()
        if part == "*":
            out.extend(range(lo, hi + 1))
            continue
        step = 1
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
        else:
            base = part
        if base == "*":
            r = range(lo, hi + 1, step)
        elif "-" in base:
            a, b = base.split("-")
            r = range(int(a), int(b) + 1, step)
        else:
            r = range(int(base), int(base) + 1, step)
        out.extend(r)
    return sorted(set(out))


def parse_cron_hours(expr: str) -> list[Trigger]:
    """
    解析 cron, 返回一天内所有触发时刻 (北京小时, 含分钟小数)。
    支持: 0 18,23,3,8,13 * * *  /  0 */5 * * *  /  30 0 * * *
    """
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"cron 表达式需要 5 个字段, 收到 {len(parts)}: {expr!r}")
    minute_f, hour_f, *_ = parts
    minutes = _expand_field(minute_f, 0, 59)
    hours = _expand_field(hour_f, 0, 23)
    triggers: list[Trigger] = []
    for h in hours:
        for m in minutes:
            utc_h = h + m / 60.0
            bj_h = (utc_h + 8) % 24.0   # UTC → 北京
            triggers.append(Trigger(hour_utc=utc_h, hour_beijing=bj_h))
    triggers.sort(key=lambda x: x.hour_beijing)
    return triggers


# ---------------------------------------------------------------------------
# 可视化
# ---------------------------------------------------------------------------

BAR_WIDTH = 48   # 24h → 48 半小时格

def _hour_to_cell(h: float) -> int:
    return int(round(h / 24.0 * BAR_WIDTH)) % BAR_WIDTH


def render_timeline(triggers: list[Trigger]) -> str:
    """渲染 24h 时间轴: 高峰段 + 各触发窗口覆盖。"""
    cells = ["."] * BAR_WIDTH
    # 高峰段底色
    for i in range(_hour_to_cell(PEAK_START), _hour_to_cell(PEAK_END)):
        cells[i] = "▒"
    # 每个窗口
    for tr in triggers:
        s = _hour_to_cell(tr.hour_beijing)
        e = _hour_to_cell((tr.hour_beijing + WINDOW) % 24)
        if e > s:
            rng = range(s, e)
        else:  # 跨午夜
            rng = list(range(s, BAR_WIDTH)) + list(range(0, e))
        for i in rng:
            if cells[i] == "▒":
                cells[i] = "▓"   # 高峰被窗口覆盖
            else:
                cells[i] = "█"   # 非高峰被窗口覆盖
    bar = "".join(cells)
    # 刻度
    scale = "".join(str(h % 10) for h in range(BAR_WIDTH))
    tens = "".join(str((h * 24 // BAR_WIDTH) // 10 % 10) for h in range(BAR_WIDTH))
    return (
        f"  时间轴 (北京时间 0-24h, █窗口-非高峰 ▓窗口-高峰 ▒未覆盖高峰 .未覆盖):\n"
        f"  {tens}\n  {scale}\n  {bar}"
    )


# ---------------------------------------------------------------------------
# 策略评估
# ---------------------------------------------------------------------------

@dataclass
class StrategyReport:
    name: str
    cron: str
    triggers: list[Trigger]
    total_score: float
    peak_coverage: float       # 高峰段 4h 中被窗口(≤预算)覆盖的总时长
    over_budget_windows: int   # 高峰超预算的窗口数

    def render(self) -> str:
        lines = [
            f"\n━━━ {self.name} ━━━",
            f"  cron: {self.cron}",
            f"  触发 {len(self.triggers)} 次/天 | 总得分 {self.total_score:.2f} | "
            f"高峰覆盖 {self.peak_coverage:.1f}h/4h | 超预算窗口 {self.over_budget_windows}",
            render_timeline(self.triggers),
            "  明细:",
        ]
        for tr in self.triggers:
            score, ov, note = window_score(tr.hour_beijing)
            tag = "★" if ov == PEAK_BUDGET else ("·" if ov == 0 else "!")
            lines.append(
                f"    {tag} 北京 {tr.hour_beijing:5.2f}h  窗口 {tr.window:<22} "
                f"高峰重叠 {ov:.1f}h  得分 {score:4.2f}  {note}"
            )
        return "\n".join(lines)


def evaluate(name: str, cron: str) -> StrategyReport:
    triggers = parse_cron_hours(cron)
    total = 0.0
    peak_cov = 0.0
    over = 0
    for tr in triggers:
        score, ov, _ = window_score(tr.hour_beijing)
        total += score
        if ov > PEAK_BUDGET + 1e-9:
            over += 1
        else:
            peak_cov += min(ov, PEAK_BUDGET)
    return StrategyReport(name, cron, triggers, total, peak_cov, over)


# ---------------------------------------------------------------------------
# 门控模式: cron 每小时凭底触发, 由脚本判断「此刻是不是有效起点」
# ---------------------------------------------------------------------------
#
# 关键: 严格按「每 REFRESH_H 小时刷新一次」生成有效起点, 而不是硬编码。
#   24 不能被 5 整除 → 一天必然有 ⌈24/5⌉=5 个起点, 其中 1 个间隔是
#   24-5*4 = 4 小时 (而非 5)。我们搜索一个锚点 a, 使得:
#     序列 a, a+5, a+10, a+15, a+20  (均 mod 24)
#   全部满足 overlap ≤ PEAK_BUDGET, 且 4h 缺口落在非高峰段。
#
# 数学上: 高峰段禁区是 (11, 16) (起点落在此区间会让窗口高峰重叠 >2h)。
#   唯一解 a=1 → 序列 01, 06, 11, 16, 21, 4h 缺口 21→01 (深夜, 最不打扰)。

def _overlap_ok(t: float) -> bool:
    """窗口起点 t 是否满足高峰重叠 ≤ 预算 (即落在禁区之外)。"""
    return overlap_with_peak(t) <= PEAK_BUDGET + 1e-9


def _gen_starts(anchor: float) -> list[float]:
    """从锚点出发, 按 REFRESH_H 严格步进生成一天的有效起点 (mod 24, 升序)。"""
    n = int(round(24 / WINDOW))   # 24/5 = 4.8 → 5 个起点
    starts = sorted((anchor + i * WINDOW) % 24 for i in range(n))
    return starts


def find_best_anchor() -> float:
    """
    以 0.25h 步长暴力搜索最优锚点。
    最优 = 所有起点 overlap ≤ 预算的前提下, 最大化高峰覆盖 (即用满高峰预算)。
    若无锚点满足约束, 退化为 overlap 之和最小的锚点 (损失最小)。
    """
    best_a, best_cov, best_all_ok = 0.0, -1.0, False
    step = 0.25
    a = 0.0
    while a < 24.0:
        starts = _gen_starts(a)
        cov = sum(min(overlap_with_peak(s), PEAK_BUDGET) for s in starts)
        all_ok = all(_overlap_ok(s) for s in starts)
        # 优先: 全部满足约束; 其次: 覆盖越高越好
        if (all_ok and not best_all_ok) or \
           (all_ok == best_all_ok and cov > best_cov + 1e-9):
            best_a, best_cov, best_all_ok = a, cov, all_ok
        a += step
    return best_a


# 模块加载时自动求解最优锚点 (确定性, 可缓存)
BEST_ANCHOR = find_best_anchor()
VALID_STARTS_BJ = _gen_starts(BEST_ANCHOR)

# 容差: Actions cron 常有 ±15 分钟抖动, 允许此刻落在有效起点附近 ±30 分钟内
TOLERANCE_H = 0.5


def _now_beijing() -> float:
    """当前北京时间 (小时小数)。CI 上使用 TZ=Asia/Shanghai 更直观。"""
    import datetime
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    return now.hour + now.minute / 60.0 + now.second / 3600.0


def _nearest_start(now_h: float) -> tuple[float, float]:
    """返回 (最近的有效起点, 距离小时数, 环形最短距离)。"""
    best_s, best_d = VALID_STARTS_BJ[0], 24.0
    for s in VALID_STARTS_BJ:
        d = min(abs(now_h - s), 24 - abs(now_h - s))   # 跨午夜环形距离
        if d < best_d:
            best_s, best_d = s, d
    return best_s, best_d


def guard(now_h: float | None = None) -> dict:
    """
    判断「此刻是否应该真正消耗额度」。

    返回:
      {
        now, nearest_start, distance, within_tolerance,
        should_run, peak_overlap, structure, refresh_gap
      }
    cron 每小时凭底; 仅当 should_run=True 时才执行真正的用量步骤。
    refresh_gap: 该起点到「下一个」有效起点的间隔 (应 = REFRESH_H=5, 缺口处=4)。
    """
    now = now_h if now_h is not None else _now_beijing()
    s, d = _nearest_start(now)
    _, ov, note = window_score(s)
    # 计算该起点到下一个有效起点的间隔
    idx = VALID_STARTS_BJ.index(s)
    nxt = VALID_STARTS_BJ[(idx + 1) % len(VALID_STARTS_BJ)]
    gap = (nxt - s) % 24
    return {
        "now": now,
        "nearest_start": s,
        "distance": d,
        "within_tolerance": d <= TOLERANCE_H,
        "should_run": d <= TOLERANCE_H,
        "peak_overlap": ov,
        "structure": note,
        "refresh_gap": gap,
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

DEFAULT_STRATEGIES = [
    ("当前(单次, UTC18→北京02)", "0 18 * * *"),
    ("严格每5h (脚本求解, 北京01/06/11/16/21)", "0 17,22,3,8,13 * * *"),
    ("非严格每5h (旧, 含4h缺口在07→11)", "0 18,23,3,8,13 * * *"),
    ("每小时 (00-23 每整点)", "0 * * * *"),
    ("每2.5h (00,30 分)", "0,30 */2 * * *"),  # 近似 2.5h
]


def main(argv: list[str]) -> int:
    # guard 模式: 供 CI 每小时触发后调用, 判断是否该真正消耗额度
    if len(argv) >= 2 and argv[1] == "--guard":
        now_h = float(argv[2]) if len(argv) >= 3 else None
        g = guard(now_h)
        verdict = "RUN" if g["should_run"] else "SKIP"
        print(f"GUARD={verdict}")
        print(f"  now(北京)={g['now']:.2f}h  nearest_start={g['nearest_start']:.2f}h  "
              f"distance={g['distance']:.2f}h  tolerance={TOLERANCE_H}h")
        print(f"  peak_overlap={g['peak_overlap']:.1f}h  refresh_gap={g['refresh_gap']:.1f}h  "
              f"structure={g['structure']}")
        # CI: 通过退出码让 workflow 判断是否继续
        return 0 if g["should_run"] else 2

    if len(argv) >= 2 and argv[1].startswith("0 "):
        # 单 cron 表达式模式
        print(evaluate("自定义", " ".join(argv[1:])).render())
        return 0

    print("=" * 72)
    print(" 套餐调度验证 — 对比多种 cron 触发策略")
    print(f" 模型: 窗口 {WINDOW}h | 高峰 [{PEAK_START},{PEAK_END}] "
          f"系数 {PEAK_MULT}/{OFF_MULT} | 高峰预算 {PEAK_BUDGET}h/窗口")
    print(f" 严格刷新周期: 每 {WINDOW}h 一次 "
          f"(24/{int(WINDOW)}={24/int(WINDOW):.2f} → 5 起点, 1 个 4h 缺口)")
    print(f" 脚本求解最优锚点 a={BEST_ANCHOR:.2f}h "
          f"→ 有效起点 (北京) = {VALID_STARTS_BJ}")
    print("=" * 72)

    best: StrategyReport | None = None
    for name, cron in DEFAULT_STRATEGIES:
        rep = evaluate(name, cron)
        print(rep.render())
        if best is None or rep.total_score > best.total_score:
            best = rep

    print("\n" + "=" * 72)
    if best:
        print(f" 结论: 名义得分最高 = {best.name} ({best.total_score:.2f})")
    print(" 注: 得分为「名义产出」, 实际受 5h 额度池刷新限制——")
    print("     触发频率 > 1次/5h 不会增加总用量, 只增加触发次数/成本。")
    print("     高频策略的优势是「可补偿 + 时段精细」, 不是「多拿额度」。")
    print("=" * 72)
    print("\n💡 推荐生产用法: cron 每小时凭底 + 脚本 --guard 门控:")
    print("     python scripts/verify_schedule.py --guard")
    print(f"   有效起点 (北京, 严格每{int(WINDOW)}h) = {VALID_STARTS_BJ}, "
          f"容差 ±{TOLERANCE_H}h")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
