# -*- coding: utf-8 -*-
"""
三策略横向对比 + 分年度(牛熊)表现
把 小市值优化版 / 银行股轮动 / ETF轮动v1.1 的净值统一到公共时间轴对比，
并计算各策略在不同市场阶段（牛/熊/震荡）的表现。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from engine import perf_metrics, drawdown, load_close, DATA

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]; break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2c6fbf"; GRAY = "#888888"; ORANGE = "#e67e22"; PURPLE = "#8e44ad"

# 市场阶段划分（依据沪深300/小盘走势的牛熊）
PHASES = [
    ("2018熊市", "2018-04-27", "2018-12-31"),
    ("2019-21牛市", "2019-01-01", "2021-12-31"),
    ("2022-24熊市", "2022-01-01", "2024-09-30"),
    ("2024Q4-26反弹", "2024-10-01", "2026-07-24"),
]


def load_nav(fn, col):
    df = pd.read_csv(os.path.join(DATA, fn), encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df.iloc[:, 0])
    return df.set_index("date")[col]


def run():
    # 各策略净值
    sc = load_nav("smallcap_nav.csv", "国证2000优化版")
    bk = load_nav("bank_nav.csv", "银行股轮动")
    etf_df = pd.read_csv(os.path.join(DATA, "etf_rotation_nav.csv"), encoding="utf-8-sig")
    etf_df["date"] = pd.to_datetime(etf_df.iloc[:, 0]); etf_df = etf_df.set_index("date")
    etf = etf_df[[c for c in etf_df.columns if "v1.1" in c][0]]
    hs = load_close("sh000300")

    # 公共时间轴（取最晚起点）
    start = max(sc.index[0], bk.index[0], etf.index[0])
    idx = sc.index[sc.index >= start]
    def rebase(s):
        s2 = s.reindex(idx).ffill()
        return s2 / s2.iloc[0]
    sc_r = rebase(sc); bk_r = rebase(bk); etf_r = rebase(etf); hs_r = rebase(hs)

    strategies = {"小市值优化版": (sc_r, RED), "ETF轮动v1.1": (etf_r, PURPLE),
                  "银行股轮动": (bk_r, BLUE), "沪深300基准": (hs_r, GRAY)}

    # 汇总指标
    rows = []
    for name, (nav, _) in strategies.items():
        m = perf_metrics(nav)
        rows.append([name, m["total"], m["cagr"], m["vol"], m["sharpe"], m["mdd"], m["calmar"]])
    summ = pd.DataFrame(rows, columns=["策略", "总收益", "年化", "年化波动", "夏普", "最大回撤", "卡玛"])
    summ.to_csv(os.path.join(DATA, "compare_summary.csv"), index=False, encoding="utf-8-sig")

    # 分阶段收益
    prows = []
    for pname, s, e in PHASES:
        row = [pname]
        for name, (nav, _) in strategies.items():
            seg = nav.loc[(nav.index >= s) & (nav.index <= e)]
            r = seg.iloc[-1] / seg.iloc[0] - 1 if len(seg) > 1 else np.nan
            row.append(r)
        prows.append(row)
    phase_df = pd.DataFrame(prows, columns=["阶段"] + list(strategies.keys()))
    phase_df.to_csv(os.path.join(DATA, "compare_phase.csv"), index=False, encoding="utf-8-sig")

    # ============ 图1：三策略净值总对比 ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    ax = axes[0, 0]
    for name, (nav, c) in strategies.items():
        m = perf_metrics(nav)
        ax.plot(nav.index, nav, color=c, lw=1.6 if "基准" not in name else 1.1,
                ls="--" if "基准" in name else "-",
                label=f"{name} ({m['total']*100:.0f}%, 夏普{m['sharpe']:.2f})")
    ax.set_title("A. 三策略净值总对比（统一起点，跨牛熊）", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3); ax.set_ylabel("净值")

    # 回撤
    ax = axes[0, 1]
    for name, (nav, c) in strategies.items():
        dd = drawdown(nav)
        ax.plot(dd.index, dd * 100, color=c, lw=1.1,
                ls="--" if "基准" in name else "-", label=name)
    ax.set_title("B. 三策略回撤对比", fontsize=11); ax.set_ylabel("回撤 (%)")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3)

    # 分阶段柱状
    ax = axes[1, 0]
    x = np.arange(len(PHASES)); w = 0.2
    names = list(strategies.keys())
    for k, name in enumerate(names):
        vals = phase_df[name].values * 100
        ax.bar(x + (k - 1.5) * w, vals, w, color=strategies[name][1], label=name)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels([p[0] for p in PHASES], fontsize=8)
    ax.set_title("C. 各市场阶段收益对比（牛熊分段）", fontsize=11); ax.set_ylabel("阶段收益 (%)")
    ax.legend(fontsize=7, loc="upper left"); ax.grid(alpha=0.3, axis="y")

    # 风险-收益散点
    ax = axes[1, 1]
    for name, (nav, c) in strategies.items():
        m = perf_metrics(nav)
        ax.scatter(m["vol"] * 100, m["cagr"] * 100, color=c, s=120, zorder=5)
        ax.annotate(name, (m["vol"] * 100, m["cagr"] * 100), fontsize=8,
                    xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("年化波动率 (%)"); ax.set_ylabel("年化收益 (%)")
    ax.set_title("D. 风险-收益散点（左上角最优）", fontsize=11); ax.grid(alpha=0.3)

    plt.suptitle("三策略综合对比：小市值 / 银行股轮动 / ETF轮动 — 跨牛熊公共窗口", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, "compare_4panel.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print("=== 汇总（公共窗口 %s 起）===" % idx[0].date())
    print(summ.to_string(index=False))
    print("\n=== 分阶段收益 ===")
    print(phase_df.to_string(index=False))
    return summ, phase_df


if __name__ == "__main__":
    run()
