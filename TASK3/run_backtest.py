# -*- coding: utf-8 -*-
"""
TASK3 双均线策略：多标的 × 多周期回测主程序
作者：张哲铭

流程：
1) 加载 8 个标的数据
2) 对每个标的运行 短线(5/20)、中线(20/60)、长线(60/120) 三组均线参数回测
3) 绘图：
   - signal_<code>.png  价格+双均线+金叉死叉买卖点（中线参数示范）
   - equity_<code>.png   三组参数策略净值 vs 买入持有基准
   - summary_excess.png  各标的中线策略超额年化收益对比
4) 汇总所有指标为 CSV，供文档引用
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from strategy import run_backtest, compute_ma, gen_signals

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

UNIVERSE = {
    "sh600900": "长江电力",
    "hk00700": "腾讯控股",
    "sh518880": "黄金ETF",
    "sh515450": "红利低波50ETF",
    "sz159941": "纳指ETF",
    "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF",
    "sh510500": "中证500ETF",
}

# 三组均线参数（短线/中线/长线）
PERIODS = {
    "短线": (5, 20),
    "中线": (20, 60),
    "长线": (60, 120),
}
DEMO_PERIOD = (20, 60)  # 信号示范图用中线参数

RED = "#c0392b"      # A股惯例：红涨
GREEN = "#27ae60"    # 绿跌
BLUE = "#2980b9"
ORANGE = "#e67e22"
PURPLE = "#8e44ad"
GRAY = "#7f8c8d"


def setup_font():
    sim_hei = r"C:\Windows\Fonts\simhei.ttf"
    if os.path.exists(sim_hei):
        font_manager.fontManager.addfont(sim_hei)
        # SimHei 缺少 U+2212 减号字形，回退到 DejaVu Sans 渲染负号，避免告警
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def load(code):
    df = pd.read_csv(os.path.join(DATA, f"{code}.csv"))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def plot_signal(code, name, df, short, long):
    """价格 + 双均线 + 金叉(买入)/死叉(卖出)标记。"""
    setup_font()
    d = run_backtest(df, short, long)["df"]
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    ax.plot(d["date"], d["close"], color="#34495e", lw=1.1, label="收盘价", alpha=0.9)
    ax.plot(d["date"], d["ma_short"], color=ORANGE, lw=1.2, label=f"MA{short}（短）")
    ax.plot(d["date"], d["ma_long"], color=BLUE, lw=1.2, label=f"MA{long}（长）")

    buys = d[d["cross"] == 1]
    sells = d[d["cross"] == -1]
    ax.scatter(buys["date"], buys["close"], marker="^", s=90, color=RED,
               edgecolors="white", linewidths=0.6, zorder=5, label="金叉买入")
    ax.scatter(sells["date"], sells["close"], marker="v", s=90, color=GREEN,
               edgecolors="white", linewidths=0.6, zorder=5, label="死叉卖出")

    ax.set_title(f"{name}（{code}）双均线交易信号　MA{short}×MA{long}",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("交易日期"); ax.set_ylabel("价格")
    ax.grid(alpha=0.3, ls="--"); ax.legend(loc="best", fontsize=9, ncol=2)
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"signal_{code}.png"), bbox_inches="tight")
    plt.close(fig)


def plot_equity(code, name, df):
    """三组参数策略净值 vs 买入持有基准。"""
    setup_font()
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    colors = {"短线": ORANGE, "中线": RED, "长线": PURPLE}
    bench_plotted = False
    for label, (s, l) in PERIODS.items():
        res = run_backtest(df, s, l)
        d = res["df"]
        ax.plot(d["date"], d["equity"], lw=1.4, color=colors[label],
                label=f"{label}策略 MA{s}×MA{l}")
        if not bench_plotted:
            ax.plot(d["date"], d["bench_equity"], lw=1.4, color=GRAY, ls="--",
                    label="买入持有（基准）")
            bench_plotted = True
    ax.axhline(1.0, color="#bbb", lw=0.8)
    ax.set_title(f"{name}（{code}）双均线策略净值曲线对比",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("交易日期"); ax.set_ylabel("净值（初始=1）")
    ax.grid(alpha=0.3, ls="--"); ax.legend(loc="best", fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"equity_{code}.png"), bbox_inches="tight")
    plt.close(fig)


def plot_summary_excess(all_metrics):
    """各标的中线策略超额年化收益对比柱状图。"""
    setup_font()
    mid = [m for m in all_metrics if m["period_label"] == "中线"]
    names = [UNIVERSE[m["code"]] for m in mid]
    excess = [m["excess_annual"] * 100 for m in mid]
    order = np.argsort(excess)[::-1]
    names = [names[i] for i in order]
    excess = [excess[i] for i in order]
    colors = [RED if v >= 0 else GREEN for v in excess]

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    bars = ax.bar(names, excess, color=colors, alpha=0.85, width=0.6)
    ax.axhline(0, color="#333", lw=0.9)
    for b, v in zip(bars, excess):
        ax.annotate(f"{v:+.1f}%", (b.get_x() + b.get_width() / 2, v),
                    textcoords="offset points",
                    xytext=(0, 6 if v >= 0 else -14),
                    ha="center", fontsize=9, fontweight="bold",
                    color=RED if v >= 0 else GREEN)
    ax.set_title("各标的中线双均线策略（MA20×MA60）超额年化收益对比",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("超额年化收益（%）＝策略年化 减 买入持有年化")
    ax.grid(alpha=0.3, ls="--", axis="y")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIG, "summary_excess.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    all_metrics = []
    for code, name in UNIVERSE.items():
        df = load(code)
        for label, (s, l) in PERIODS.items():
            res = run_backtest(df, s, l)
            m = res["metrics"]
            m["code"] = code; m["name"] = name; m["period_label"] = label
            all_metrics.append(m)
        # 出图
        plot_signal(code, name, df, *DEMO_PERIOD)
        plot_equity(code, name, df)
        print(f"[图] {code} {name} 完成")

    plot_summary_excess(all_metrics)

    # 汇总指标 CSV
    cols = ["code", "name", "period_label", "short", "long", "n_days", "years",
            "strat_total", "strat_annual", "bench_total", "bench_annual",
            "excess_annual", "excess_total", "sharpe", "mdd", "bench_mdd",
            "n_trades", "win_rate", "pl_ratio"]
    dfm = pd.DataFrame(all_metrics)[cols]
    dfm.to_csv(os.path.join(BASE, "backtest_results.csv"),
               index=False, encoding="utf-8-sig")

    # 打印概览
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    show = dfm.copy()
    for c in ["strat_total", "strat_annual", "bench_total", "bench_annual",
              "excess_annual", "excess_total", "mdd", "bench_mdd", "win_rate"]:
        show[c] = (show[c] * 100).round(1)
    show["sharpe"] = show["sharpe"].round(2)
    show["pl_ratio"] = show["pl_ratio"].round(2)
    print("\n===== 回测指标汇总（收益/回撤/胜率为%）=====")
    print(show.to_string(index=False))
    print("\n已保存 backtest_results.csv 与全部图形。")


if __name__ == "__main__":
    main()
