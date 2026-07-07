# -*- coding: utf-8 -*-
"""
TASK3 补充分析图：风险调整维度与周期对比
作者：张哲铭

1) risk_compare.png    各标的中线策略 vs 买入持有的「最大回撤」对比（策略普遍更浅）
2) sharpe_compare.png  各标的三组周期策略的夏普比率热力对比
3) period_effect.png   以黄金ETF为例，短/中/长线三组参数的收益-回撤散点
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")

RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2980b9"
ORANGE = "#e67e22"; PURPLE = "#8e44ad"; GRAY = "#7f8c8d"


def setup_font():
    sim_hei = r"C:\Windows\Fonts\simhei.ttf"
    if os.path.exists(sim_hei):
        font_manager.fontManager.addfont(sim_hei)
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def plot_risk_compare(df):
    """中线策略 vs 买入持有 最大回撤对比（回撤取绝对值，越低越好）。"""
    setup_font()
    mid = df[df["period_label"] == "中线"].copy()
    mid = mid.sort_values("bench_mdd")  # 基准回撤从深到浅
    names = mid["name"].tolist()
    strat = (-mid["mdd"] * 100).tolist()
    bench = (-mid["bench_mdd"] * 100).tolist()

    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    b1 = ax.bar(x - w/2, bench, w, label="买入持有回撤", color=GRAY, alpha=0.85)
    b2 = ax.bar(x + w/2, strat, w, label="双均线策略回撤", color=RED, alpha=0.85)
    for bars in (b1, b2):
        for b in bars:
            ax.annotate(f"{b.get_height():.0f}",
                        (b.get_x()+b.get_width()/2, b.get_height()),
                        textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("最大回撤幅度（%，越低越好）")
    ax.set_title("双均线策略 vs 买入持有：最大回撤对比（中线 MA20×MA60）",
                 fontsize=14, fontweight="bold", pad=10)
    ax.grid(alpha=0.3, ls="--", axis="y"); ax.legend(loc="best", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "risk_compare.png"), bbox_inches="tight")
    plt.close(fig)


def plot_sharpe_heat(df):
    """各标的 × 三组周期 夏普比率热力图。"""
    setup_font()
    order = ["黄金ETF", "腾讯控股", "科创50ETF", "中证500ETF", "纳指ETF",
             "沪深300ETF", "长江电力", "红利低波50ETF"]
    labels = ["短线", "中线", "长线"]
    mat = np.zeros((len(order), len(labels)))
    for i, nm in enumerate(order):
        for j, lb in enumerate(labels):
            row = df[(df["name"] == nm) & (df["period_label"] == lb)]
            mat[i, j] = row["sharpe"].values[0] if len(row) else np.nan

    fig, ax = plt.subplots(figsize=(7.5, 6.5), dpi=150)
    im = ax.imshow(mat, cmap="RdYlGn", aspect="auto", vmin=-0.1, vmax=1.1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
    for i in range(len(order)):
        for j in range(len(labels)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color="#222")
    ax.set_title("双均线策略夏普比率（越高越好）", fontsize=13,
                 fontweight="bold", pad=10)
    fig.colorbar(im, ax=ax, shrink=0.8, label="夏普比率")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "sharpe_compare.png"), bbox_inches="tight")
    plt.close(fig)


def plot_period_effect(df):
    """收益-回撤散点：横轴最大回撤，纵轴年化收益，点为各标的各周期。"""
    setup_font()
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    markers = {"短线": "o", "中线": "s", "长线": "^"}
    colors = {"短线": ORANGE, "中线": RED, "长线": PURPLE}
    for lb in ["短线", "中线", "长线"]:
        sub = df[df["period_label"] == lb]
        ax.scatter(-sub["mdd"]*100, sub["strat_annual"]*100,
                   s=90, marker=markers[lb], color=colors[lb],
                   alpha=0.8, edgecolors="white", linewidths=0.6, label=lb)
    # 标注黄金ETF
    for lb in ["短线", "中线", "长线"]:
        r = df[(df["name"] == "黄金ETF") & (df["period_label"] == lb)]
        ax.annotate(f"黄金-{lb}", (-r["mdd"].values[0]*100, r["strat_annual"].values[0]*100),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color="#b8860b")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlabel("最大回撤（%，越左越好）")
    ax.set_ylabel("策略年化收益（%，越上越好）")
    ax.set_title("双均线策略：收益—回撤分布（8标的×3周期，共24组）",
                 fontsize=13, fontweight="bold", pad=10)
    ax.grid(alpha=0.3, ls="--"); ax.legend(title="均线周期", loc="best", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "period_effect.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    df = pd.read_csv(os.path.join(BASE, "backtest_results.csv"))
    plot_risk_compare(df)
    plot_sharpe_heat(df)
    plot_period_effect(df)
    print("已生成补充分析图：risk_compare.png / sharpe_compare.png / period_effect.png")


if __name__ == "__main__":
    main()
