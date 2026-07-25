# -*- coding: utf-8 -*-
"""
TASK8 增强图表：聚焦 ETF 双重动量轮动策略，生成尽可能多的适用图表。
ETF 轮动是规则型动量策略（非机器学习），故绘制：
  图A 资产曲线对比、图B 回撤曲线、图C 月度收益热力图、图D 收益分布直方图、
  图E 滚动夏普比率曲线、图F 持仓轮动信号图（ETF 版“买卖点验证”）。
（特征重要性/混淆矩阵仅适用于机器学习策略，此处不适用，故不绘制。）
数据来自 TASK7 的 ETF 轮动净值与重跑的持仓权重。
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__))
AI = os.path.dirname(BASE)
FIG = os.path.join(BASE, "figures")
T7 = os.path.join(AI, "TASK7")
os.makedirs(FIG, exist_ok=True)
sys.path.insert(0, T7)   # 复用 TASK7 的回测模块

for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]; break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2c6fbf"; GRAY = "#888888"; ORANGE = "#e67e22"; PURPLE = "#8e44ad"

TRADING_DAYS = 244


def perf(nav):
    ret = nav.pct_change().dropna()
    total = nav.iloc[-1] / nav.iloc[0] - 1
    yrs = len(nav) / TRADING_DAYS
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    vol = ret.std() * np.sqrt(TRADING_DAYS)
    sharpe = ret.mean() * TRADING_DAYS / vol if vol > 1e-9 else 0
    mdd = (nav / nav.cummax() - 1).min()
    return dict(total=total, cagr=cagr, vol=vol, sharpe=sharpe, mdd=mdd)


def load_nav():
    df = pd.read_csv(os.path.join(T7, "data", "etf_rotation_nav.csv"), encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index("date")
    # 规范列名（文件里 v1.1 列旧标签为“v1.1双周+熔断”，实际是无熔断双周版）
    ren = {}
    for c in df.columns:
        if "v1.1" in c: ren[c] = "v1.1双周"
        elif "v1.0" in c: ren[c] = "v1.0周度"
        elif "等权" in c: ren[c] = "等权持有"
        elif "沪深" in c: ren[c] = "沪深300"
    return df.rename(columns=ren)


def get_weights():
    """重跑 ETF 轮动 v1.1 拿每日持仓权重（用于持仓轮动图）。"""
    from strat_etf_rotation import build_price_panel, momentum_score, backtest_rotation, POOL, BENCH_CODE
    from engine import load_close
    px = build_price_panel(list(POOL.keys()))
    bench = load_close(BENCH_CODE).reindex(px.index).ffill()
    score, wmom = momentum_score(px)
    nav, w = backtest_rotation(px, score, wmom, rebal_days=10, topn=3, use_circuit=False, bench=bench)
    return w, POOL


def main():
    nav = load_nav()
    v11 = nav["v1.1双周"]; v10 = nav["v1.0周度"]; eq = nav["等权持有"]; hs = nav["沪深300"]
    m11 = perf(v11); m10 = perf(v10); meq = perf(eq); mhs = perf(hs)

    # ============ 图 A：资产曲线对比（对数坐标可选）============
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(v11.index, v11, color=RED, lw=1.9, label=f"ETF轮动 v1.1双周 (总收益{m11['total']*100:.0f}%, 年化{m11['cagr']*100:.1f}%)")
    ax.plot(v10.index, v10, color=ORANGE, lw=1.3, label=f"ETF轮动 v1.0周度 ({m10['total']*100:.0f}%, {m10['cagr']*100:.1f}%)")
    ax.plot(eq.index, eq, color=BLUE, lw=1.2, label=f"等权持有基准 ({meq['total']*100:.0f}%, {meq['cagr']*100:.1f}%)")
    ax.plot(hs.index, hs, color=GRAY, lw=1.2, ls="--", label=f"沪深300 ({mhs['total']*100:.0f}%, {mhs['cagr']*100:.1f}%)")
    ax.set_title("ETF 轮动策略资产曲线对比（策略 vs 基准，2019–2026）", fontsize=12, fontweight="bold")
    ax.set_ylabel("净值（起点=1）"); ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_A_equity.png"), dpi=135, bbox_inches="tight"); plt.close()

    # ============ 图 B：回撤曲线 ============
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for s, c, lab, m in [(v11, RED, "v1.1双周", m11), (v10, ORANGE, "v1.0周度", m10), (eq, BLUE, "等权持有", meq)]:
        dd = (s / s.cummax() - 1) * 100
        ax.plot(dd.index, dd, color=c, lw=1.2, label=f"{lab}（最大回撤 {m['mdd']*100:.1f}%）")
    ax.fill_between(v11.index, (v11 / v11.cummax() - 1) * 100, 0, color=RED, alpha=0.12)
    ax.set_title("ETF 轮动策略回撤曲线（风险特征）", fontsize=12, fontweight="bold")
    ax.set_ylabel("回撤 (%)"); ax.legend(fontsize=9, loc="lower left"); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_B_drawdown.png"), dpi=135, bbox_inches="tight"); plt.close()

    # ============ 图 C：月度收益热力图（v1.1）============
    mret = v11.resample("ME").last().pct_change().dropna()
    tab = pd.DataFrame({"year": mret.index.year, "month": mret.index.month, "ret": mret.values * 100})
    pivot = tab.pivot(index="year", columns="month", values="ret")
    fig, ax = plt.subplots(figsize=(11, 4.6))
    vmax = np.nanmax(np.abs(pivot.values))
    im = ax.imshow(pivot.values, cmap="RdYlGn_r", aspect="auto", vmin=-vmax, vmax=vmax)
    # 注意：中国习惯红涨绿跌 → 用 RdYlGn_r 使正收益偏红、负收益偏绿
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels([f"{m}月" for m in pivot.columns], fontsize=9)
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index, fontsize=9)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                        color="black")
    ax.set_title("ETF 轮动 v1.1 月度收益热力图（%，红涨绿跌，时间分布）", fontsize=12, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="月度收益 (%)")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_C_monthly_heatmap.png"), dpi=135, bbox_inches="tight"); plt.close()

    # ============ 图 D：日收益分布直方图（v1.1 vs 沪深300）============
    r11 = v11.pct_change().dropna() * 100
    rhs = hs.pct_change().dropna() * 100
    fig, ax = plt.subplots(figsize=(11, 4.8))
    bins = np.linspace(-6, 6, 61)
    ax.hist(r11, bins=bins, color=RED, alpha=0.55, label=f"v1.1双周（日均{r11.mean():.3f}%, 标准差{r11.std():.2f}%）", density=True)
    ax.hist(rhs, bins=bins, color=GRAY, alpha=0.4, label=f"沪深300（日均{rhs.mean():.3f}%, 标准差{rhs.std():.2f}%）", density=True)
    ax.axvline(r11.mean(), color=RED, ls="--", lw=1.2)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_title("ETF 轮动 v1.1 日收益分布直方图（收益特征）", fontsize=12, fontweight="bold")
    ax.set_xlabel("单日收益 (%)"); ax.set_ylabel("概率密度"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_D_return_hist.png"), dpi=135, bbox_inches="tight"); plt.close()

    # ============ 图 E：滚动 1 年夏普比率曲线（稳定性）============
    win = TRADING_DAYS
    def roll_sharpe(s):
        r = s.pct_change()
        return (r.rolling(win).mean() * TRADING_DAYS) / (r.rolling(win).std() * np.sqrt(TRADING_DAYS))
    rs11 = roll_sharpe(v11); rseq = roll_sharpe(eq)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.plot(rs11.index, rs11, color=RED, lw=1.4, label="v1.1双周 滚动1年夏普")
    ax.plot(rseq.index, rseq, color=BLUE, lw=1.1, label="等权持有 滚动1年夏普")
    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(1, color=GREEN, ls=":", lw=1.0, label="夏普=1 参考线")
    ax.fill_between(rs11.index, rs11, 0, where=(rs11 >= 0), color=RED, alpha=0.08)
    ax.set_title("ETF 轮动 v1.1 滚动 1 年夏普比率（策略稳定性）", fontsize=12, fontweight="bold")
    ax.set_ylabel("滚动夏普比率"); ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_E_rolling_sharpe.png"), dpi=135, bbox_inches="tight"); plt.close()

    # ============ 图 F：持仓轮动信号图（ETF 版“买卖点验证”）============
    w, POOL = get_weights()
    wm = w.resample("ME").last().fillna(0)
    held = wm[(wm > 0).any(axis=0).index[(wm > 0).any(axis=0).values]]  # 只保留出现过的列
    held = wm.loc[:, (wm > 0).any(axis=0)]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ncol = held.shape[1]
    cmap = plt.cm.tab20(np.linspace(0, 1, max(ncol, 1)))
    bottom = np.zeros(len(held))
    for k, col in enumerate(held.columns):
        ax.bar(range(len(held)), held[col].values, bottom=bottom, width=1.0,
               color=cmap[k], label=POOL.get(col, col))
        bottom += held[col].values
    ax.set_title("ETF 轮动 v1.1 月度持仓轮动图（选中标的与权重，信号验证）", fontsize=12, fontweight="bold")
    ax.set_ylabel("持仓权重"); ax.set_xlim(-0.5, len(held) - 0.5); ax.set_ylim(0, 1.05)
    step = max(1, len(held) // 12)
    ax.set_xticks(range(0, len(held), step))
    ax.set_xticklabels([held.index[i].strftime("%Y-%m") for i in range(0, len(held), step)], rotation=45, fontsize=8)
    ax.legend(fontsize=7, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.13))
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "etf_F_holdings.png"), dpi=135, bbox_inches="tight"); plt.close()

    # 保存关键指标供报告引用
    pd.DataFrame([
        ["v1.1双周", m11["total"], m11["cagr"], m11["vol"], m11["sharpe"], m11["mdd"]],
        ["v1.0周度", m10["total"], m10["cagr"], m10["vol"], m10["sharpe"], m10["mdd"]],
        ["等权持有", meq["total"], meq["cagr"], meq["vol"], meq["sharpe"], meq["mdd"]],
        ["沪深300", mhs["total"], mhs["cagr"], mhs["vol"], mhs["sharpe"], mhs["mdd"]],
    ], columns=["方案", "总收益", "年化", "年化波动", "夏普", "最大回撤"]).to_csv(
        os.path.join(BASE, "etf_metrics.csv"), index=False, encoding="utf-8-sig")

    print("已生成 6 张 ETF 轮动图表：A资产曲线/B回撤/C月度热力/D收益直方/E滚动夏普/F持仓轮动")
    print(f"v1.1: 总收益{m11['total']*100:.0f}% 年化{m11['cagr']*100:.1f}% 夏普{m11['sharpe']:.2f} 回撤{m11['mdd']*100:.1f}%")


if __name__ == "__main__":
    main()
