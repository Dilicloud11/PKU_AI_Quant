# -*- coding: utf-8 -*-
"""
策略三：ETF 双重动量轮动策略（复现 v1.0 并分析改进空间）
复现《ETF轮动策略_v1.0_20260507.md》核心：
  综合动量得分 = 风险调整动量 × 趋势系数
  加权动量 = 0.5*R20 + 0.3*R60 + 0.2*R10；风险调整 = 加权动量 / 20日波动率
  趋势系数：收盘>MA20且>MA60 →1.0；>MA20但<MA60 →0.7；<MA20 →剔除
  每周调仓，选 Top3 等权；绝对动量过滤 + 避险仓（全部为负→黄金/持币）。

改进版（本任务提出并经参数网格验证的 v1.1）：
  核心改进 = 调仓降频（周度→双周）。回测显示：仅此一项即全面优于原版——
    收益更高、夏普更高、回撤更小、换手成本减半。原因是周度调仓被短期噪声反复
    "扫损"且成本高，双周过滤噪声、保留中期动量。
  另测大盘熔断(沪深300破MA60转避险)反而"误伤"、拖累收益——绝对动量过滤已足够，
    过度叠加择时是画蛇添足（这是重要的反直觉教训，见报告分析）。
对比：等权买入持有(基准) vs v1.0周度 vs v1.1双周(无熔断)。
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

# ETF 轮动池（宽基+行业+风格+跨境+商品），黄金/纳指兼作避险/对冲
POOL = {
    "sh510300": "沪深300", "sh510500": "中证500", "sh512100": "中证1000",
    "sz159915": "创业板", "sh512000": "券商", "sh512010": "医药",
    "sh512690": "酒", "sh512800": "银行", "sh518880": "黄金", "sz159941": "纳指",
}
SAFE = ["sh518880"]     # 避险优先：黄金
BENCH_CODE = "sh000300"


def build_price_panel(codes):
    s = {c: load_close(c) for c in codes}
    df = pd.DataFrame(s).dropna(how="all")
    df = df.ffill()
    # 只保留所有标的都有数据的公共区间起点
    start = max(x.dropna().index[0] for x in s.values())
    return df.loc[df.index >= start].dropna()


def momentum_score(px):
    """给定价格面板，返回每日各标的的最终得分 DataFrame。"""
    r10 = px.pct_change(10); r20 = px.pct_change(20); r60 = px.pct_change(60)
    wmom = 0.5 * r20 + 0.3 * r60 + 0.2 * r10
    vol = px.pct_change().rolling(20).std()
    risk_adj = wmom / vol.replace(0, np.nan)
    ma20 = px.rolling(20).mean(); ma60 = px.rolling(60).mean()
    # 趋势系数
    trend = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    trend = trend.mask((px > ma20) & (px > ma60), 1.0)
    trend = trend.mask((px > ma20) & (px <= ma60), 0.7)
    trend = trend.mask(px <= ma20, np.nan)   # 剔除
    score = risk_adj * trend
    return score, wmom


def backtest_rotation(px, score, wmom, rebal_days, topn=3,
                      use_circuit=False, bench=None, cost=COST):
    """
    按 rebal_days 周期调仓：每个调仓日按 score 排序选 Top N 等权。
    绝对动量过滤：score 为 NaN（跌破MA20）不入选；若可选<topn，剩余仓位转避险(黄金)或持币。
    use_circuit: 沪深300跌破MA60 → 当期强制全避险(持币)。
    返回 净值 Series。
    """
    dates = px.index
    ma60_b = bench.rolling(60).mean() if bench is not None else None
    weights = pd.DataFrame(0.0, index=dates, columns=px.columns)
    cur_w = pd.Series(0.0, index=px.columns)
    last_rebal = -10**9
    for i, d in enumerate(dates):
        if i - last_rebal >= rebal_days and i >= 60:
            last_rebal = i
            circuit = False
            if use_circuit and bench is not None and not np.isnan(ma60_b.iloc[i]):
                if bench.iloc[i] < ma60_b.iloc[i]:
                    circuit = True
            new_w = pd.Series(0.0, index=px.columns)
            if not circuit:
                sc = score.iloc[i].dropna()
                # 只保留加权动量为正的（绝对动量过滤）
                sc = sc[wmom.iloc[i].reindex(sc.index) > 0]
                sc = sc.sort_values(ascending=False)
                picks = list(sc.index[:topn])
                if len(picks) > 0:
                    for p in picks:
                        new_w[p] = 1.0 / topn
                    # 不足 topn 的仓位 → 黄金避险
                    if len(picks) < topn:
                        safe = SAFE[0]
                        new_w[safe] = new_w.get(safe, 0) + (topn - len(picks)) / topn
                else:
                    new_w[SAFE[0]] = 1.0    # 全部负动量→全避险
            else:
                # 熔断：全避险（黄金），黄金本身若也弱则持币(权重0)
                if score.iloc[i].get(SAFE[0]) is not None and not np.isnan(score.iloc[i].get(SAFE[0], np.nan)):
                    new_w[SAFE[0]] = 1.0
            cur_w = new_w
        weights.iloc[i] = cur_w.values
    # 计算净值：权重次日生效
    ret = px.pct_change().fillna(0)
    w_shift = weights.shift(1).fillna(0)
    gross = (w_shift * ret).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1).fillna(0)
    net = gross - turnover * cost
    nav = (1 + net).cumprod()
    return nav, weights


def run():
    px = build_price_panel(list(POOL.keys()))
    bench = load_close(BENCH_CODE).reindex(px.index).ffill()
    score, wmom = momentum_score(px)

    # 基准：等权买入持有
    eq_ret = px.pct_change().fillna(0).mean(axis=1)
    nav_eq = (1 + eq_ret).cumprod(); m_eq = perf_metrics(nav_eq)

    # v1.0 周度(5日)
    nav_v10, w10 = backtest_rotation(px, score, wmom, rebal_days=5, topn=3, use_circuit=False, bench=bench)
    m_v10 = perf_metrics(nav_v10)
    # v1.1 双周(10日) 无熔断 —— 网格验证的最优改进
    nav_v11, w11 = backtest_rotation(px, score, wmom, rebal_days=10, topn=3, use_circuit=False, bench=bench)
    m_v11 = perf_metrics(nav_v11)
    # 另测：双周+熔断（用于报告说明"熔断误伤"）
    nav_circuit, _ = backtest_rotation(px, score, wmom, rebal_days=10, topn=3, use_circuit=True, bench=bench)
    m_circuit = perf_metrics(nav_circuit)
    # 沪深300基准
    nav_hs = bench / bench.iloc[0]; m_hs = perf_metrics(nav_hs)

    res = pd.DataFrame([
        ["v1.1双周(改进)", m_v11["total"], m_v11["cagr"], m_v11["vol"], m_v11["sharpe"], m_v11["mdd"], m_v11["calmar"]],
        ["v1.0周度(原版)", m_v10["total"], m_v10["cagr"], m_v10["vol"], m_v10["sharpe"], m_v10["mdd"], m_v10["calmar"]],
        ["双周+熔断(误伤对照)", m_circuit["total"], m_circuit["cagr"], m_circuit["vol"], m_circuit["sharpe"], m_circuit["mdd"], m_circuit["calmar"]],
        ["等权买入持有(基准)", m_eq["total"], m_eq["cagr"], m_eq["vol"], m_eq["sharpe"], m_eq["mdd"], m_eq["calmar"]],
        ["沪深300", m_hs["total"], m_hs["cagr"], m_hs["vol"], m_hs["sharpe"], m_hs["mdd"], m_hs["calmar"]],
    ], columns=["方案", "总收益", "年化", "年化波动", "夏普", "最大回撤", "卡玛"])
    res.to_csv(os.path.join(DATA, "etf_rotation_result.csv"), index=False, encoding="utf-8-sig")

    navdf = pd.DataFrame({"v1.1双周+熔断": nav_v11, "v1.0周度": nav_v10,
                          "等权持有": nav_eq, "沪深300": nav_hs})
    navdf.to_csv(os.path.join(DATA, "etf_rotation_nav.csv"), encoding="utf-8-sig")

    # 换手统计
    turn10 = w10.diff().abs().sum(axis=1)
    turn11 = w11.diff().abs().sum(axis=1)
    ann_turn10 = turn10.sum() / (len(px) / TRADING_DAYS)
    ann_turn11 = turn11.sum() / (len(px) / TRADING_DAYS)

    # ============ 绘图 四宫格 ============
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    ax = axes[0, 0]
    ax.plot(nav_v11.index, nav_v11, color=RED, lw=1.7, label=f"v1.1双周改进 ({m_v11['total']*100:.0f}%)")
    ax.plot(nav_v10.index, nav_v10, color=ORANGE, lw=1.3, label=f"v1.0周度原版 ({m_v10['total']*100:.0f}%)")
    ax.plot(nav_eq.index, nav_eq, color=BLUE, lw=1.1, ls="-", label=f"等权持有 ({m_eq['total']*100:.0f}%)")
    ax.plot(nav_hs.index, nav_hs, color=GRAY, lw=1.1, ls="--", label=f"沪深300 ({m_hs['total']*100:.0f}%)")
    ax.set_title("A. 净值对比：ETF轮动 vs 等权持有 vs 大盘", fontsize=11)
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    for nav, c, lab, m in [(nav_v11, RED, "v1.1双周", m_v11), (nav_v10, ORANGE, "v1.0周度", m_v10),
                            (nav_eq, BLUE, "等权持有", m_eq)]:
        dd = drawdown(nav)
        ax.plot(dd.index, dd * 100, color=c, lw=1.0, label=f"{lab} (MDD {m['mdd']*100:.1f}%)")
    ax.set_title("B. 回撤对比", fontsize=11); ax.set_ylabel("回撤 (%)")
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    # 持仓热力（v1.1 各标的权重堆叠）
    w11m = w11.resample("ME").last().fillna(0)
    bottom = np.zeros(len(w11m))
    cmap = plt.cm.tab20(np.linspace(0, 1, len(POOL)))
    for k, col in enumerate(POOL.keys()):
        ax.bar(range(len(w11m)), w11m[col].values, bottom=bottom, color=cmap[k],
               width=1.0, label=POOL[col])
        bottom += w11m[col].values
    ax.set_title("C. v1.1改进版月度持仓结构（堆叠权重）", fontsize=11)
    ax.set_ylabel("权重"); ax.set_xlim(-0.5, len(w11m) - 0.5)
    step = max(1, len(w11m)//10)
    ax.set_xticks(range(0, len(w11m), step))
    ax.set_xticklabels([w11m.index[i].strftime("%y-%m") for i in range(0, len(w11m), step)], rotation=45, fontsize=7)
    ax.legend(fontsize=6, ncol=2, loc="upper left")

    ax = axes[1, 1]
    labels = ["v1.1双周", "v1.0周度"]
    turns = [ann_turn11, ann_turn10]
    costs = [ann_turn11 * COST * 100, ann_turn10 * COST * 100]
    x = np.arange(len(labels))
    ax.bar(x - 0.2, turns, 0.4, color=BLUE, label="年换手(倍)")
    ax2 = ax.twinx()
    ax2.bar(x + 0.2, costs, 0.4, color=RED, label="年成本(%)")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("年换手率(倍)"); ax2.set_ylabel("年化交易成本(%)")
    ax.set_title("D. 换手率与交易成本：降频节省成本", fontsize=11)
    ax.legend(fontsize=8, loc="upper right"); ax2.legend(fontsize=8, loc="upper center")

    plt.suptitle("ETF双重动量轮动策略：v1.0周度 vs v1.1双周改进 2018-2026", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, "etf_rotation_4panel.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print(res.to_string(index=False))
    print(f"年换手 v1.0={ann_turn10:.1f}倍 v1.1={ann_turn11:.1f}倍")
    # 存换手供报告引用
    pd.DataFrame([["v1.0周度", ann_turn10, ann_turn10*COST*100],
                  ["v1.1双周", ann_turn11, ann_turn11*COST*100]],
                 columns=["方案", "年换手倍数", "年化成本%"]).to_csv(
        os.path.join(DATA, "etf_turnover.csv"), index=False, encoding="utf-8-sig")
    return res, navdf


if __name__ == "__main__":
    run()
