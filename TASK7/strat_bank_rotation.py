# -*- coding: utf-8 -*-
"""
策略二（替换双均线）：银行股轮动策略
聚宽"银行股轮动策略"模板逻辑：在银行板块个股间，按某种打分（动量/估值）定期轮动、持有最强的 N 只。
银行股特性：低波动、高股息、板块内高相关，但个股间仍有明显的强弱分化（如招行/成长型城商行 vs 传统大行）。

本报告设计（相对动量轮动 + 绝对动量过滤 + 大盘趋势过滤）：
  轮动池 = 12 只主流银行股（国有大行/股份行/城商行）；
  Step1 打分：加权动量 = 0.5×R60 + 0.3×R120 + 0.2×R20（银行慢变量，用更长动量窗口）；
  Step2 绝对动量过滤：加权动量 ≤ 0 或 收盘 < MA60 的个股剔除；
  Step3 大盘趋势过滤（关键改进）：沪深300 跌破 MA120（大级别熊市）时当期全部空仓避险；
  Step4 每月调仓（20 交易日），选打分最高的 Top3 等权持有。
注：银行股是"高相关、低分化"板块，裸动量轮动因集中持仓反而放大回撤（Top3 无过滤回撤达 −45.9%、
    跑输等权持有）。加入大盘趋势过滤后，回撤被压到 −20.5%、夏普反超等权持有——这印证了
    "对高相关板块，控制系统性风险比板块内选股更重要"。
对比：银行股等权买入持有(基准) vs 银行轮动(动量+大盘过滤) vs 沪深300。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from engine import load_close, perf_metrics, drawdown, COST, DATA, TRADING_DAYS

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

BANKS = {
    "sh601398": "工商银行", "sh601939": "建设银行", "sh601288": "农业银行",
    "sh601988": "中国银行", "sh600036": "招商银行", "sh600000": "浦发银行",
    "sh601166": "兴业银行", "sh600016": "民生银行", "sz000001": "平安银行",
    "sh601169": "北京银行", "sh600926": "杭州银行", "sh601818": "光大银行",
}
BENCH_CODE = "sh000300"


def build_panel(codes):
    s = {c: load_close(c) for c in codes}
    df = pd.DataFrame(s).ffill()
    start = max(x.dropna().index[0] for x in s.values())
    return df.loc[df.index >= start].dropna()


def bank_score(px):
    r20 = px.pct_change(20); r60 = px.pct_change(60); r120 = px.pct_change(120)
    wmom = 0.5 * r60 + 0.3 * r120 + 0.2 * r20
    ma60 = px.rolling(60).mean()
    trend_ok = px > ma60
    score = wmom.where(trend_ok & (wmom > 0))   # 不满足绝对动量/趋势 → NaN 剔除
    return score, wmom


def backtest(px, score, rebal_days=20, topn=3, cost=COST, bench=None, trend_win=120):
    dates = px.index
    ma_b = bench.rolling(trend_win).mean() if bench is not None else None
    weights = pd.DataFrame(0.0, index=dates, columns=px.columns)
    cur = pd.Series(0.0, index=px.columns)
    last = -10**9
    for i, d in enumerate(dates):
        if i - last >= rebal_days and i >= 120:
            last = i
            new = pd.Series(0.0, index=px.columns)
            # 大盘趋势过滤：沪深300 < MA120 → 全空仓避险
            filt_ok = True
            if bench is not None and not np.isnan(ma_b.iloc[i]):
                filt_ok = bench.iloc[i] > ma_b.iloc[i]
            if filt_ok:
                sc = score.iloc[i].dropna().sort_values(ascending=False)
                picks = list(sc.index[:topn])
                for p in picks:
                    new[p] = 1.0 / topn
            # 若不满足过滤或可选不足，剩余空仓（现金），体现熊市降仓
            cur = new
        weights.iloc[i] = cur.values
    ret = px.pct_change().fillna(0)
    w_shift = weights.shift(1).fillna(0)
    gross = (w_shift * ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0)
    nav = (1 + gross - turnover * cost).cumprod()
    return nav, weights


def run():
    px = build_panel(list(BANKS.keys()))
    bench = load_close(BENCH_CODE).reindex(px.index).ffill()
    score, wmom = bank_score(px)

    # 银行股等权买入持有
    eq = (1 + px.pct_change().fillna(0).mean(axis=1)).cumprod(); m_eq = perf_metrics(eq)
    # 银行轮动（动量 + 大盘趋势过滤）
    nav, w = backtest(px, score, rebal_days=20, topn=3, bench=bench, trend_win=120); m = perf_metrics(nav)
    # 裸轮动对照（无大盘过滤）
    nav_raw, _ = backtest(px, score, rebal_days=20, topn=3, bench=None); m_raw = perf_metrics(nav_raw)
    # 沪深300
    hs = bench / bench.iloc[0]; m_hs = perf_metrics(hs)

    res = pd.DataFrame([
        ["银行股轮动(月度Top3+过滤)", m["total"], m["cagr"], m["vol"], m["sharpe"], m["mdd"], m["calmar"]],
        ["银行股裸轮动(无过滤对照)", m_raw["total"], m_raw["cagr"], m_raw["vol"], m_raw["sharpe"], m_raw["mdd"], m_raw["calmar"]],
        ["银行股等权买入持有", m_eq["total"], m_eq["cagr"], m_eq["vol"], m_eq["sharpe"], m_eq["mdd"], m_eq["calmar"]],
        ["沪深300(基准)", m_hs["total"], m_hs["cagr"], m_hs["vol"], m_hs["sharpe"], m_hs["mdd"], m_hs["calmar"]],
    ], columns=["方案", "总收益", "年化", "年化波动", "夏普", "最大回撤", "卡玛"])
    res.to_csv(os.path.join(DATA, "bank_result.csv"), index=False, encoding="utf-8-sig")

    navdf = pd.DataFrame({"银行股轮动": nav, "银行股等权持有": eq, "沪深300": hs})
    navdf.to_csv(os.path.join(DATA, "bank_nav.csv"), encoding="utf-8-sig")

    ann_turn = w.diff().abs().sum(axis=1).sum() / (len(px) / TRADING_DAYS)

    # ============ 四宫格 ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    ax = axes[0, 0]
    ax.plot(nav.index, nav, color=RED, lw=1.7, label=f"银行股轮动 ({m['total']*100:.0f}%)")
    ax.plot(eq.index, eq, color=ORANGE, lw=1.3, label=f"银行股等权持有 ({m_eq['total']*100:.0f}%)")
    ax.plot(hs.index, hs, color=GRAY, lw=1.2, ls="--", label=f"沪深300 ({m_hs['total']*100:.0f}%)")
    ax.set_title("A. 净值对比：银行股轮动 vs 等权持有 vs 大盘", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    for n, c, lab, mm in [(nav, RED, "轮动", m), (eq, ORANGE, "等权持有", m_eq), (hs, GRAY, "沪深300", m_hs)]:
        dd = drawdown(n)
        ax.plot(dd.index, dd * 100, color=c, lw=1.1, ls="--" if "沪深" in lab else "-",
                label=f"{lab} (MDD {mm['mdd']*100:.1f}%)")
    ax.set_title("B. 回撤对比", fontsize=11); ax.set_ylabel("回撤 (%)")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    wm = w.resample("ME").last().fillna(0)
    bottom = np.zeros(len(wm)); cmap = plt.cm.tab20(np.linspace(0, 1, len(BANKS)))
    for k, col in enumerate(BANKS.keys()):
        ax.bar(range(len(wm)), wm[col].values, bottom=bottom, color=cmap[k], width=1.0, label=BANKS[col])
        bottom += wm[col].values
    ax.set_title("C. 银行股轮动月度持仓结构（堆叠权重）", fontsize=11); ax.set_ylabel("权重")
    ax.set_xlim(-0.5, len(wm)-0.5)
    step = max(1, len(wm)//10)
    ax.set_xticks(range(0, len(wm), step))
    ax.set_xticklabels([wm.index[i].strftime("%y-%m") for i in range(0, len(wm), step)], rotation=45, fontsize=7)
    ax.legend(fontsize=6, ncol=3, loc="upper left")

    ax = axes[1, 1]
    # 个股累计涨幅排名（体现轮动来源=个股分化）
    tot = (px.iloc[-1] / px.iloc[0] - 1).sort_values() * 100
    names = [BANKS[c] for c in tot.index]
    colors = [RED if v >= 0 else GREEN for v in tot.values]
    ax.barh(range(len(tot)), tot.values, color=colors)
    ax.set_yticks(range(len(tot))); ax.set_yticklabels(names, fontsize=8)
    ax.set_title("D. 池内银行股区间总涨幅分化（轮动Alpha来源）", fontsize=11)
    ax.set_xlabel("区间总涨幅 (%)"); ax.axvline(0, color="black", lw=0.6); ax.grid(alpha=0.3, axis="x")

    plt.suptitle("银行股轮动策略回测 — 12只主流银行股 2018-2026", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, "bank_4panel.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print(res.to_string(index=False))
    print(f"银行轮动年换手={ann_turn:.1f}倍")
    return res, navdf


if __name__ == "__main__":
    run()
