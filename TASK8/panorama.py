# -*- coding: utf-8 -*-
"""
TASK8 全景对比图：汇总前七任务各类策略的代表性风险调整绩效。
因各任务标的/区间不同，采用【夏普比率】与【最大回撤】两个跨标的可比的风险调整指标横向对比，
并按策略类别归类。数据来自各任务已产出的回测结果 CSV。
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
AI = os.path.dirname(BASE)
os.makedirs(FIG, exist_ok=True)
for f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [f]; break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False
RED = "#c0392b"; GREEN = "#27ae60"; BLUE = "#2c6fbf"; GRAY = "#888888"; ORANGE = "#e67e22"; PURPLE = "#8e44ad"; TEAL = "#16a085"


def load(path):
    return pd.read_csv(os.path.join(AI, path), encoding="utf-8-sig")


def main():
    # --- 汇总各任务代表策略（夏普、最大回撤、类别）---
    rows = []  # (任务, 策略类别, 代表配置, 夏普, 最大回撤)

    # TASK3 双均线：取各标的长线(60/120)夏普的中位代表 + 最优
    t3 = load("TASK3/backtest_results.csv")
    t3l = t3[t3["period_label"] == "长线"]
    rows.append(("TASK3", "双均线(趋势跟随)", "长线60/120均值", t3l["sharpe"].mean(), t3l["mdd"].mean()))

    # TASK4 海龟：System2 均值
    t4 = load("TASK4/backtest_results.csv")
    t4s2 = t4[t4["system"] == "System2"]
    rows.append(("TASK4", "海龟(通道突破)", "System2均值", t4s2["sharpe"].mean(), t4s2["mdd"].mean()))

    # TASK6 ML策略：best_strategy 均值
    t6 = load("TASK6/data/best_strategy.csv")
    rows.append(("TASK6", "机器学习择时", "各标的最优均值", t6["sharpe"].mean(), t6["mdd"].mean()))

    # TASK7 三策略（公共窗口汇总）
    t7 = load("TASK7/data/compare_summary.csv")
    def g(k, c):
        return t7[t7["策略"] == k][c].iloc[0]
    rows.append(("TASK7", "小市值(风格择时)", "国证2000优化", g("小市值优化版", "夏普"), g("小市值优化版", "最大回撤")))
    rows.append(("TASK7", "银行股轮动(行业内)", "月度Top3+过滤", g("银行股轮动", "夏普"), g("银行股轮动", "最大回撤")))
    rows.append(("TASK7", "ETF轮动(大类动量)", "v1.1双周", g("ETF轮动v1.1", "夏普"), g("ETF轮动v1.1", "最大回撤")))
    rows.append(("基准", "买入持有(沪深300)", "被动持有", g("沪深300基准", "夏普"), g("沪深300基准", "最大回撤")))

    df = pd.DataFrame(rows, columns=["任务", "策略类别", "代表配置", "夏普", "最大回撤"])
    df.to_csv(os.path.join(BASE, "panorama_summary.csv"), index=False, encoding="utf-8-sig")

    # ============ 图：夏普 & 回撤 双栏对比 + 散点 ============
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    labels = df["策略类别"].tolist()
    colors = [ORANGE, TEAL, BLUE, RED, PURPLE, "#c0392b", GRAY]
    # 让ETF轮动突出
    colmap = {"ETF轮动(大类动量)": RED, "银行股轮动(行业内)": BLUE, "小市值(风格择时)": ORANGE,
              "机器学习择时": PURPLE, "海龟(通道突破)": TEAL, "双均线(趋势跟随)": "#95a5a6",
              "买入持有(沪深300)": GRAY}
    cols = [colmap[l] for l in labels]

    ax = axes[0]
    y = np.arange(len(labels))
    ax.barh(y, df["夏普"].values, color=cols)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    for i, v in enumerate(df["夏普"].values):
        ax.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_xlabel("夏普比率（越高越好）")
    ax.set_title("A. 各类策略夏普比率对比", fontsize=12, fontweight="bold")
    ax.grid(alpha=0.3, axis="x")

    ax = axes[1]
    ax.barh(y, (df["最大回撤"].values * 100), color=cols)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    for i, v in enumerate(df["最大回撤"].values * 100):
        ax.text(v - 1, i, f"{v:.1f}%", va="center", ha="right", fontsize=9, color="white")
    ax.set_xlabel("最大回撤（绝对值越小越好）")
    ax.set_title("B. 各类策略最大回撤对比", fontsize=12, fontweight="bold")
    ax.grid(alpha=0.3, axis="x")

    plt.suptitle("量化策略全景对比：前七任务各类策略的风险调整绩效", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(os.path.join(FIG, "panorama.png"), dpi=130, bbox_inches="tight")
    plt.close()

    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    main()
