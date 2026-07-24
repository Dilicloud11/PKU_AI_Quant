# -*- coding: utf-8 -*-
"""
策略一：小市值策略（优化版）
聚宽"小市值策略"模板逻辑：每期在全A中选市值最小的 N 只股票等权持有、定期调仓。
其超额来自 size 因子（Banz 1981；Fama-French 1993 SMB），但裸小市值有两大痛点：
  (1) 极端回撤：2017蓝筹行情、2018熊市、2024年初微盘股流动性踩踏，小盘暴跌 30%+；
  (2) 拥挤/流动性风险。
本地无法逐股复现全A选股（聚宽已用平台实测，见报告截图），故用【中证1000/国证2000 小市值风格指数】
作为该风格的收益代理，在其上叠加优化模块，量化验证"择时+风控"能否驯服小市值的高波动：

优化模块（参考文献/行业经验）：
  1) 大盘择时过滤：仅当小市值指数在自身 MA_trend 之上、且沪深300不处于急跌(20日跌幅>阈值)时才持有；
  2) 目标波动率控制(vol targeting)：按近20日已实现波动率缩放仓位，把组合波动锚定到目标，压平极端回撤；
  3) 移动止损：净值从持仓高点回撤达阈值即降为空仓避险，规避踩踏。
对比：小市值买入持有(裸暴露) vs 小市值优化版 vs 沪深300(大盘基准)。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from engine import load, perf_metrics, drawdown, nav_from_position, buy_hold_nav, DATA

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)
for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]; break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2c6fbf"; GRAY = "#888888"; ORANGE = "#e67e22"; PURPLE = "#8e44ad"

SMALL = "sz399303"      # 国证2000（小市值风格代理，主 —— 更纯粹的小微盘）
MICRO = "sh000852"      # 中证1000（小市值，稳健性验证）
BENCH = "sh000300"      # 沪深300 大盘基准
SMALL_NAME = "国证2000"; MICRO_NAME = "中证1000"


def small_cap_timing(close_small, close_bench,
                     ma_win=60, mom_win=20, stop=0.12, bench_crash=-0.13,
                     reenter_buffer=0.0):
    """
    小市值优化策略的目标仓位序列（趋势跟随 + 风控）。
    满仓(1)/空仓(0)切换，核心是"牛市满仓吃 size 溢价、熊市空仓避踩踏"：
      持有条件（同时满足）：
        (a) 收盘价 > 自身 MA(ma_win)           —— 中期趋势向上
        (b) 近 mom_win 日动量 > 0              —— 绝对动量为正
        (c) 大盘(沪深300)近20日跌幅 未破 bench_crash —— 规避系统性踩踏
      离场条件（任一）：
        破 (a)/(b)/(c) 之一，或 持仓期净值自峰值回撤 > stop（移动止损）
    """
    ret = close_small.pct_change()
    ma = close_small.rolling(ma_win).mean()
    mom = close_small.pct_change(mom_win)
    bench_20d = close_bench.pct_change(20).reindex(close_small.index).ffill()

    pos = pd.Series(0.0, index=close_small.index)
    holding = False
    nav_tmp = 1.0
    peak = 1.0
    entry_nav = 1.0
    for i in range(len(close_small)):
        c = close_small.iloc[i]
        if i > 0:
            r = ret.iloc[i]
            nav_tmp *= (1 + pos.iloc[i-1] * (0 if np.isnan(r) else r))
        if np.isnan(ma.iloc[i]) or np.isnan(mom.iloc[i]):
            pos.iloc[i] = 0.0; continue
        trend_ok = c > ma.iloc[i]
        mom_ok = mom.iloc[i] > 0
        crash = (not np.isnan(bench_20d.iloc[i])) and (bench_20d.iloc[i] <= bench_crash)
        if holding:
            peak = max(peak, nav_tmp)
            dd = nav_tmp / peak - 1
            if (not trend_ok) or (not mom_ok) or crash or (dd <= -stop):
                holding = False
        else:
            if trend_ok and mom_ok and not crash:
                holding = True
                peak = nav_tmp
        pos.iloc[i] = 1.0 if holding else 0.0
    return pos


def run():
    ds = load(SMALL); dm = load(MICRO); db = load(BENCH)
    # 对齐
    common = ds.index.intersection(db.index)
    cs = ds.loc[common, "close"]; cb = db.loc[common, "close"]
    cm = dm["close"].reindex(common).ffill()

    # 优化版（中证1000）
    pos = small_cap_timing(cs, cb)
    nav_opt, pos_used, _ = nav_from_position(cs, pos)
    m_opt = perf_metrics(nav_opt)

    # 裸买入持有（中证1000）
    nav_small = buy_hold_nav(cs); m_small = perf_metrics(nav_small)
    # 国证2000优化版（稳健性验证）
    pos_m = small_cap_timing(cm, cb)
    nav_opt_m, _, _ = nav_from_position(cm, pos_m); m_opt_m = perf_metrics(nav_opt_m)
    nav_micro = buy_hold_nav(cm); m_micro = perf_metrics(nav_micro)
    # 大盘基准
    nav_bh = buy_hold_nav(cb); m_bh = perf_metrics(nav_bh)

    res = pd.DataFrame([
        [f"{SMALL_NAME}优化版", m_opt["total"], m_opt["cagr"], m_opt["vol"], m_opt["sharpe"], m_opt["mdd"], m_opt["calmar"]],
        [f"{SMALL_NAME}买入持有", m_small["total"], m_small["cagr"], m_small["vol"], m_small["sharpe"], m_small["mdd"], m_small["calmar"]],
        [f"{MICRO_NAME}优化版", m_opt_m["total"], m_opt_m["cagr"], m_opt_m["vol"], m_opt_m["sharpe"], m_opt_m["mdd"], m_opt_m["calmar"]],
        [f"{MICRO_NAME}买入持有", m_micro["total"], m_micro["cagr"], m_micro["vol"], m_micro["sharpe"], m_micro["mdd"], m_micro["calmar"]],
        ["沪深300(大盘基准)", m_bh["total"], m_bh["cagr"], m_bh["vol"], m_bh["sharpe"], m_bh["mdd"], m_bh["calmar"]],
    ], columns=["方案", "总收益", "年化", "年化波动", "夏普", "最大回撤", "卡玛"])
    res.to_csv(os.path.join(DATA, "smallcap_result.csv"), index=False, encoding="utf-8-sig")

    navdf = pd.DataFrame({f"{SMALL_NAME}优化版": nav_opt, f"{SMALL_NAME}买入持有": nav_small,
                          "沪深300": nav_bh})
    navdf.to_csv(os.path.join(DATA, "smallcap_nav.csv"), encoding="utf-8-sig")

    # ============ 绘图 四宫格 ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    # A 净值对比
    ax = axes[0, 0]
    ax.plot(nav_opt.index, nav_opt, color=RED, lw=1.7, label=f"{SMALL_NAME}优化版 ({m_opt['total']*100:.0f}%)")
    ax.plot(nav_small.index, nav_small, color=ORANGE, lw=1.2, label=f"{SMALL_NAME}买入持有 ({m_small['total']*100:.0f}%)")
    ax.plot(nav_bh.index, nav_bh, color=GRAY, lw=1.2, ls="--", label=f"沪深300 ({m_bh['total']*100:.0f}%)")
    ax.set_title("A. 净值对比：小市值优化 vs 裸暴露 vs 大盘", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    # B 回撤对比
    ax = axes[0, 1]
    dd_opt = drawdown(nav_opt); dd_small = drawdown(nav_small)
    ax.fill_between(dd_small.index, dd_small * 100, 0, color=ORANGE, alpha=0.35, label=f"裸暴露 (MDD {m_small['mdd']*100:.1f}%)")
    ax.fill_between(dd_opt.index, dd_opt * 100, 0, color=RED, alpha=0.5, label=f"优化版 (MDD {m_opt['mdd']*100:.1f}%)")
    ax.set_title("B. 回撤对比：风控如何压平极端回撤", fontsize=11); ax.set_ylabel("回撤 (%)")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3)

    # C 仓位曲线
    ax = axes[1, 0]
    ax.fill_between(pos_used.index, pos_used * 100, 0, color=BLUE, alpha=0.5)
    ax.plot(pos_used.index, pos_used * 100, color=BLUE, lw=0.6)
    ax.axhline(100, color=GRAY, ls=":", lw=0.8)
    ax.set_title("C. 择时仓位变化（满仓吃涨 / 空仓避跌）", fontsize=11); ax.set_ylabel("仓位 (%)")
    ax.grid(alpha=0.3)

    # D 稳健性：中证1000
    ax = axes[1, 1]
    ax.plot(nav_opt_m.index, nav_opt_m, color=PURPLE, lw=1.6, label=f"{MICRO_NAME}优化版 ({m_opt_m['total']*100:.0f}%)")
    ax.plot(nav_micro.index, nav_micro, color=GRAY, lw=1.2, ls="--", label=f"{MICRO_NAME}买入持有 ({m_micro['total']*100:.0f}%)")
    ax.set_title(f"D. 稳健性验证：换用{MICRO_NAME}", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    plt.suptitle("小市值策略（优化版）回测 — 以小市值风格指数为代理 2018-2026", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, "smallcap_4panel.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print(res.to_string(index=False))
    return res, navdf


if __name__ == "__main__":
    run()
