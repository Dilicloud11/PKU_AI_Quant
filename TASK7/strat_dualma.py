# -*- coding: utf-8 -*-
"""
策略二：双均线策略（优化版）
标的：沪深300指数(sh000300) —— 与聚宽"双均线策略"对齐（默认标的为沪深300 / 000300.XSHG）

原始双均线：短均线上穿长均线(金叉)满仓买入；下穿(死叉)清仓。缺陷=震荡市反复被"扫"。
优化点（参考 Faber 2007 择时均线 / 海龟法则 / Brock-Lakonishok-LeBaron 1992）：
  1) 参数优选：对(快线, 慢线)做网格，以夏普为目标，避免主观拍脑袋；
  2) 长周期趋势过滤：仅当价格在长期均线(MA200)之上才允许做多，过滤大级别熊市中的假金叉；
  3) 百分比止损：持仓浮亏达阈值即离场，控制单次趋势失败的回撤。
输出：最优参数、四图(净值/回撤/买卖点/参数热力)、金叉死叉版 vs 优化版 vs 买入持有 对比。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from engine import load, perf_metrics, drawdown, nav_from_position, buy_hold_nav, COST, DATA

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

# 中文字体
for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]; break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2c6fbf"; GRAY = "#888888"; ORANGE = "#e67e22"

CODE = "sh000300"
NAME = "沪深300"


def signal_dualma(close, fast, slow, use_trend=True, trend_win=200, stop=0.10):
    """生成目标仓位(0/1)。金叉且(过滤后)持有=1，死叉/止损=0。"""
    maf = close.rolling(fast).mean()
    mas = close.rolling(slow).mean()
    trend = close.rolling(trend_win).mean() if use_trend else None
    pos = pd.Series(0.0, index=close.index)
    holding = False
    entry = None
    for i in range(len(close)):
        c = close.iloc[i]
        if np.isnan(mas.iloc[i]) or (use_trend and np.isnan(trend.iloc[i])):
            pos.iloc[i] = 0.0; continue
        golden = maf.iloc[i] > mas.iloc[i]
        trend_ok = (c > trend.iloc[i]) if use_trend else True
        if holding:
            # 止损
            if stop and entry and c / entry - 1 <= -stop:
                holding = False; entry = None
            # 死叉离场
            elif not golden:
                holding = False; entry = None
        else:
            if golden and trend_ok:
                holding = True; entry = c
        pos.iloc[i] = 1.0 if holding else 0.0
    return pos


def run():
    df = load(CODE)
    close = df["close"]

    # ---- 参数网格搜索（优化版：带趋势过滤+止损）----
    fasts = [5, 10, 15, 20, 30]
    slows = [20, 30, 60, 90, 120]
    grid = []
    heat = pd.DataFrame(index=fasts, columns=slows, dtype=float)
    best = None
    for f in fasts:
        for s in slows:
            if f >= s:
                heat.loc[f, s] = np.nan; continue
            pos = signal_dualma(close, f, s, use_trend=True, trend_win=200, stop=0.10)
            nav, _, _ = nav_from_position(close, pos)
            m = perf_metrics(nav)
            grid.append((f, s, m["cagr"], m["sharpe"], m["mdd"], m["total"]))
            heat.loc[f, s] = m["sharpe"]
            score = m["sharpe"]
            if best is None or score > best[0]:
                best = (score, f, s, m, pos, nav)
    gdf = pd.DataFrame(grid, columns=["fast", "slow", "cagr", "sharpe", "mdd", "total"])
    gdf.to_csv(os.path.join(DATA, "dualma_grid.csv"), index=False, encoding="utf-8-sig")

    _, bf, bs, bm, bpos, bnav = best

    # ---- 对照：朴素金叉死叉（无过滤、无止损，用同一最优快慢线）----
    pos_naive = signal_dualma(close, bf, bs, use_trend=False, trend_win=200, stop=None)
    nav_naive, _, _ = nav_from_position(close, pos_naive)
    m_naive = perf_metrics(nav_naive)

    # ---- 买入持有 ----
    nav_bh = buy_hold_nav(close)
    m_bh = perf_metrics(nav_bh)

    # 保存结果
    res = pd.DataFrame([
        ["双均线优化版", bf, bs, bm["total"], bm["cagr"], bm["vol"], bm["sharpe"], bm["mdd"], bm["calmar"], bm["win"]],
        ["双均线朴素版", bf, bs, m_naive["total"], m_naive["cagr"], m_naive["vol"], m_naive["sharpe"], m_naive["mdd"], m_naive["calmar"], m_naive["win"]],
        ["买入持有", "-", "-", m_bh["total"], m_bh["cagr"], m_bh["vol"], m_bh["sharpe"], m_bh["mdd"], m_bh["calmar"], m_bh["win"]],
    ], columns=["方案", "快线", "慢线", "总收益", "年化", "年化波动", "夏普", "最大回撤", "卡玛", "日胜率"])
    res.to_csv(os.path.join(DATA, "dualma_result.csv"), index=False, encoding="utf-8-sig")

    # 保存净值序列
    navdf = pd.DataFrame({"优化版": bnav, "朴素版": nav_naive, "买入持有": nav_bh})
    navdf.to_csv(os.path.join(DATA, "dualma_nav.csv"), encoding="utf-8-sig")

    # ============ 绘图：四宫格 ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    maf = close.rolling(bf).mean(); mas = close.rolling(bs).mean()

    # A 价格+均线+买卖点
    ax = axes[0, 0]
    ax.plot(close.index, close, color=GRAY, lw=0.8, label=f"{NAME}收盘")
    ax.plot(maf.index, maf, color=RED, lw=1.0, label=f"MA{bf}")
    ax.plot(mas.index, mas, color=BLUE, lw=1.0, label=f"MA{bs}")
    pos_shift = bpos.shift(1).fillna(0)
    buys = close.index[(pos_shift == 0) & (bpos == 1)]  # 近似标记（实际次日成交）
    # 用仓位变点标记
    chg = bpos.diff().fillna(0)
    buy_pts = close[chg > 0]; sell_pts = close[chg < 0]
    ax.scatter(buy_pts.index, buy_pts.values, marker="^", color=RED, s=45, zorder=5, label="买入")
    ax.scatter(sell_pts.index, sell_pts.values, marker="v", color=GREEN, s=45, zorder=5, label="卖出")
    ax.set_title(f"A. 价格与均线信号（最优 MA{bf}/MA{bs}，含MA200趋势过滤）", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    # B 净值对比
    ax = axes[0, 1]
    ax.plot(bnav.index, bnav, color=RED, lw=1.6, label=f"优化版 (总收益{bm['total']*100:.1f}%)")
    ax.plot(nav_naive.index, nav_naive, color=ORANGE, lw=1.2, label=f"朴素金叉死叉 ({m_naive['total']*100:.1f}%)")
    ax.plot(nav_bh.index, nav_bh, color=GRAY, lw=1.2, ls="--", label=f"买入持有 ({m_bh['total']*100:.1f}%)")
    ax.set_title("B. 策略净值对比", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    # C 回撤
    ax = axes[1, 0]
    dd_opt = drawdown(bnav); dd_bh = drawdown(nav_bh)
    ax.fill_between(dd_opt.index, dd_opt * 100, 0, color=RED, alpha=0.4, label=f"优化版 (MDD {bm['mdd']*100:.1f}%)")
    ax.plot(dd_bh.index, dd_bh * 100, color=GRAY, lw=1.0, ls="--", label=f"买入持有 (MDD {m_bh['mdd']*100:.1f}%)")
    ax.set_title("C. 回撤曲线", fontsize=11); ax.set_ylabel("回撤 (%)")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3)

    # D 参数热力图（夏普）
    ax = axes[1, 1]
    hm = heat.astype(float).values
    im = ax.imshow(hm, cmap="RdYlGn", aspect="auto", origin="upper")
    ax.set_xticks(range(len(slows))); ax.set_xticklabels(slows)
    ax.set_yticks(range(len(fasts))); ax.set_yticklabels(fasts)
    ax.set_xlabel("慢线周期"); ax.set_ylabel("快线周期")
    for i in range(len(fasts)):
        for j in range(len(slows)):
            v = hm[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color="black")
    ax.set_title("D. 参数敏感性热力图（夏普比率）", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.suptitle(f"双均线策略（优化版）回测 — {NAME}指数 2018-2026", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, "dualma_4panel.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print(f"[双均线] 最优 MA{bf}/MA{bs}")
    print(res.to_string(index=False))
    return res, navdf


if __name__ == "__main__":
    run()
