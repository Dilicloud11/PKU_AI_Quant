# -*- coding: utf-8 -*-
"""
TASK4 海龟策略：多标的 × 多参数回测主程序 + 全部可视化
作者：张哲铭

流程：
1) 加载 8 个标的（含论文验证标的：黄金ETF/纳指ETF；宽基对照：沪深300/中证500）
2) 对每个标的运行 System1(20/10) 与 System2(55/20) 两套海龟参数
3) 通道周期敏感性扫描：entry∈{10,20,30,40,55,80} 观察收益/夏普/回撤随周期变化
4) 绘图：
   - signal_<code>.png   价格 + 高低点通道 + ATR + 买入/加仓/止损/离场标记
   - equity_<code>.png    S1/S2 策略净值 vs 买入持有
   - summary_excess.png   各标的超额年化收益对比
   - risk_compare.png      策略 vs 买入持有 最大回撤对比
   - sharpe_compare.png    8标的×2系统 夏普热力图
   - param_scan.png        通道周期敏感性（黄金ETF 示范）
   - return_risk.png       收益—回撤散点（全部组合）
5) 汇总指标 CSV
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

from turtle_strategy import run_turtle
from metrics import compute_metrics

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

UNIVERSE = {
    "sh518880": "黄金ETF",
    "sz159941": "纳指ETF",
    "hk00700": "腾讯控股",
    "sh600900": "长江电力",
    "sh515450": "红利低波50ETF",
    "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF",
    "sh510500": "中证500ETF",
}

# 两套经典海龟参数
SYSTEMS = {
    "System1": dict(entry_n=20, exit_n=10),   # 短期：20日突破 / 10日离场
    "System2": dict(entry_n=55, exit_n=20),   # 长期：55日突破 / 20日离场
}
DEMO_SYS = dict(entry_n=20, exit_n=10)        # 信号示范图用 System1
SCAN_ENTRY = [10, 20, 30, 40, 55, 80]         # 通道周期敏感性扫描

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
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False


def load(code):
    df = pd.read_csv(os.path.join(DATA, f"{code}.csv"))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


# ============================================================
# 图 1：价格 + 高低点通道 + ATR + 交易信号
# ============================================================
def plot_signal(code, name, df, entry_n, exit_n):
    setup_font()
    res = run_turtle(df, entry_n=entry_n, exit_n=exit_n)
    d = res["df"]

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 7), dpi=150, sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})

    # 上图：价格 + 通道
    ax.plot(d["date"], d["close"], color="#2c3e50", lw=1.0, label="收盘价", zorder=2)
    ax.plot(d["date"], d["dc_upper"], color=RED, lw=1.0, ls="--",
            label=f"上轨（{entry_n}日最高·入场线）", alpha=0.8)
    ax.plot(d["date"], d["dc_exit"], color=GREEN, lw=1.0, ls="--",
            label=f"离场下轨（{exit_n}日最低）", alpha=0.8)
    ax.fill_between(d["date"], d["dc_exit"], d["dc_upper"], color="#f0f3f4",
                    alpha=0.6, zorder=1)

    ev = d.set_index(d.index)
    buys = d[d["event"] == "buy"]
    adds = d[d["event"] == "add"]
    stops = d[d["event"] == "stop"]
    exits = d[d["event"] == "exit"]
    ax.scatter(buys["date"], buys["close"], marker="^", s=95, color=RED,
               edgecolors="white", linewidths=0.6, zorder=6, label="入场（突破上轨）")
    ax.scatter(adds["date"], adds["close"], marker="+", s=70, color=ORANGE,
               linewidths=1.6, zorder=6, label="加仓（+0.5ATR）")
    ax.scatter(stops["date"], stops["close"], marker="x", s=70, color=PURPLE,
               linewidths=1.6, zorder=6, label="止损（-2ATR）")
    ax.scatter(exits["date"], exits["close"], marker="v", s=95, color=GREEN,
               edgecolors="white", linewidths=0.6, zorder=6, label="离场（跌破下轨）")

    ax.set_title(f"{name}（{code}）海龟策略交易信号　入场{entry_n}日/离场{exit_n}日通道",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("价格")
    ax.grid(alpha=0.3, ls="--")
    ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)

    # 下图：ATR
    ax2.plot(d["date"], d["atr"], color=BLUE, lw=1.1)
    ax2.fill_between(d["date"], 0, d["atr"], color=BLUE, alpha=0.15)
    ax2.set_ylabel("ATR(20)")
    ax2.set_xlabel("交易日期")
    ax2.grid(alpha=0.3, ls="--")

    fig.autofmt_xdate()
    fig.savefig(os.path.join(FIG, f"signal_{code}.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 2：策略净值 vs 买入持有
# ============================================================
def plot_equity(code, name, df):
    setup_font()
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    colors = {"System1": ORANGE, "System2": RED}
    bench_done = False
    for sysname, p in SYSTEMS.items():
        res = run_turtle(df, **p)
        d = res["df"]
        ax.plot(d["date"], d["equity"], lw=1.5, color=colors[sysname],
                label=f"{sysname}（{p['entry_n']}/{p['exit_n']}）策略净值")
        if not bench_done:
            ax.plot(d["date"], d["bench_equity"], lw=1.5, color=GRAY, ls="--",
                    label="买入持有（基准）")
            bench_done = True
    ax.axhline(1.0, color="#bbb", lw=0.8)
    ax.set_title(f"{name}（{code}）海龟策略净值曲线对比",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("交易日期"); ax.set_ylabel("净值（初始=1）")
    ax.grid(alpha=0.3, ls="--"); ax.legend(loc="best", fontsize=9)
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"equity_{code}.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 3：各标的超额年化收益对比（System2）
# ============================================================
def plot_summary_excess(all_m):
    setup_font()
    sub = [m for m in all_m if m["system"] == "System2"]
    names = [m["name"] for m in sub]
    excess = [m["excess_annual"] * 100 for m in sub]
    order = np.argsort(excess)[::-1]
    names = [names[i] for i in order]; excess = [excess[i] for i in order]
    colors = [RED if v >= 0 else GREEN for v in excess]

    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    bars = ax.bar(names, excess, color=colors, alpha=0.85, width=0.6)
    ax.axhline(0, color="#333", lw=0.9)
    for b, v in zip(bars, excess):
        ax.annotate(f"{v:+.1f}%", (b.get_x() + b.get_width() / 2, v),
                    textcoords="offset points", xytext=(0, 6 if v >= 0 else -14),
                    ha="center", fontsize=9, fontweight="bold",
                    color=RED if v >= 0 else GREEN)
    ax.set_title("各标的海龟策略（System2 · 55/20）超额年化收益对比",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("超额年化收益（%）＝策略年化 减 买入持有年化")
    ax.grid(alpha=0.3, ls="--", axis="y")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(FIG, "summary_excess.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 4：最大回撤对比（策略 vs 买入持有）
# ============================================================
def plot_risk_compare(all_m):
    setup_font()
    sub = [m for m in all_m if m["system"] == "System2"]
    names = [m["name"] for m in sub]
    smdd = [abs(m["mdd"]) * 100 for m in sub]
    bmdd = [abs(m["bench_mdd"]) * 100 for m in sub]
    order = np.argsort(bmdd)[::-1]
    names = [names[i] for i in order]
    smdd = [smdd[i] for i in order]; bmdd = [bmdd[i] for i in order]

    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
    ax.bar(x - w/2, bmdd, w, label="买入持有 最大回撤", color=GRAY, alpha=0.85)
    ax.bar(x + w/2, smdd, w, label="海龟策略 最大回撤", color=BLUE, alpha=0.9)
    for i in range(len(names)):
        ax.annotate(f"{bmdd[i]:.0f}%", (x[i]-w/2, bmdd[i]), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8, color=GRAY)
        ax.annotate(f"{smdd[i]:.0f}%", (x[i]+w/2, smdd[i]), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8, color=BLUE, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_title("海龟策略 vs 买入持有：最大回撤对比（System2 · 越低越好）",
                 fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("最大回撤绝对值（%）")
    ax.grid(alpha=0.3, ls="--", axis="y"); ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "risk_compare.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 5：夏普比率热力图（8标的 × 2系统）
# ============================================================
def plot_sharpe_heatmap(all_m):
    setup_font()
    codes = list(UNIVERSE.keys())
    names = [UNIVERSE[c] for c in codes]
    systems = ["System1", "System2"]
    mat = np.zeros((len(codes), len(systems)))
    for i, c in enumerate(codes):
        for j, s in enumerate(systems):
            m = next(x for x in all_m if x["code"] == c and x["system"] == s)
            mat[i, j] = m["sharpe"]

    cmap = LinearSegmentedColormap.from_list(
        "gr", [GREEN, "#f4f6f6", RED])   # 绿(低)->白->红(高)，A股审美
    fig, ax = plt.subplots(figsize=(6.5, 7), dpi=150)
    vmax = max(abs(mat.min()), abs(mat.max()), 0.5)
    im = ax.imshow(mat, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(systems)))
    ax.set_xticklabels([f"{s}\n({'20/10' if s=='System1' else '55/20'})" for s in systems])
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names)
    for i in range(len(codes)):
        for j in range(len(systems)):
            ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center",
                    fontsize=10, fontweight="bold",
                    color="#222" if abs(mat[i,j]) < vmax*0.6 else "white")
    ax.set_title("海龟策略夏普比率热力图\n（红=高，绿=低）", fontsize=13,
                 fontweight="bold", pad=12)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="夏普比率")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "sharpe_compare.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 6：通道周期敏感性扫描（黄金ETF）
# ============================================================
def plot_param_scan(code="sh518880"):
    setup_font()
    df = load(code); name = UNIVERSE[code]
    ann, shp, dd = [], [], []
    for en in SCAN_ENTRY:
        ex = max(5, en // 2)
        m = compute_metrics(run_turtle(df, entry_n=en, exit_n=ex))
        ann.append(m["strat_annual"] * 100)
        shp.append(m["sharpe"])
        dd.append(abs(m["mdd"]) * 100)

    fig, ax1 = plt.subplots(figsize=(10.5, 5.2), dpi=150)
    x = np.arange(len(SCAN_ENTRY))
    ax1.bar(x, ann, width=0.5, color=RED, alpha=0.5, label="年化收益（左轴）")
    ax1.plot(x, dd, color=GREEN, marker="s", lw=1.6, label="最大回撤（左轴）")
    ax1.set_ylabel("年化收益 / 最大回撤（%）")
    ax1.set_xticks(x); ax1.set_xticklabels([f"{en}日\n(离场{max(5,en//2)})" for en in SCAN_ENTRY])
    ax1.set_xlabel("入场通道周期")
    ax2 = ax1.twinx()
    ax2.plot(x, shp, color=BLUE, marker="o", lw=2, label="夏普比率（右轴）")
    ax2.set_ylabel("夏普比率")
    ax1.set_title(f"{name}（{code}）通道周期敏感性：周期越长交易越少、越稳",
                  fontsize=13, fontweight="bold", pad=10)
    l1, la1 = ax1.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, la1 + la2, loc="upper center", fontsize=9, ncol=3)
    ax1.grid(alpha=0.3, ls="--", axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "param_scan.png"), bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 图 7：收益—回撤散点（全部组合）
# ============================================================
def plot_return_risk(all_m):
    setup_font()
    fig, ax = plt.subplots(figsize=(10.5, 6), dpi=150)
    markers = {"System1": "o", "System2": "s"}
    for m in all_m:
        x = abs(m["mdd"]) * 100
        y = m["strat_annual"] * 100
        c = RED if m["excess_annual"] >= 0 else GREEN
        ax.scatter(x, y, marker=markers[m["system"]], s=90, color=c,
                   edgecolors="#333", linewidths=0.5, alpha=0.85)
        ax.annotate(m["name"][:4], (x, y), textcoords="offset points",
                    xytext=(5, 4), fontsize=7.5, color="#555")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlabel("最大回撤绝对值（%）—— 越靠左风险越小")
    ax.set_ylabel("策略年化收益（%）—— 越靠上收益越高")
    ax.set_title("海龟策略收益—回撤分布（红=跑赢基准 绿=跑输 ●S1 ■S2）",
                 fontsize=13, fontweight="bold", pad=10)
    ax.grid(alpha=0.3, ls="--")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "return_risk.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    all_m = []
    for code, name in UNIVERSE.items():
        df = load(code)
        for sysname, p in SYSTEMS.items():
            res = run_turtle(df, **p)
            m = compute_metrics(res)
            m.update(code=code, name=name, system=sysname,
                     entry_n=p["entry_n"], exit_n=p["exit_n"])
            all_m.append(m)
        plot_signal(code, name, df, **DEMO_SYS)
        plot_equity(code, name, df)
        print(f"[图] {code} {name} 完成")

    plot_summary_excess(all_m)
    plot_risk_compare(all_m)
    plot_sharpe_heatmap(all_m)
    plot_param_scan("sh518880")
    plot_return_risk(all_m)
    print("[图] 汇总图完成")

    cols = ["code", "name", "system", "entry_n", "exit_n", "n_days", "years",
            "strat_total", "strat_annual", "bench_total", "bench_annual",
            "excess_annual", "excess_total", "sharpe", "mdd", "bench_mdd",
            "calmar", "n_trades", "win_rate", "pl_ratio", "avg_win", "avg_loss",
            "avg_hold"]
    dfm = pd.DataFrame(all_m)[cols]
    dfm.to_csv(os.path.join(BASE, "backtest_results.csv"),
               index=False, encoding="utf-8-sig")

    # 通道周期扫描结果也存一份
    scan_rows = []
    for code in ["sh518880", "sz159941", "sh510300"]:
        df = load(code)
        for en in SCAN_ENTRY:
            ex = max(5, en // 2)
            m = compute_metrics(run_turtle(df, entry_n=en, exit_n=ex))
            scan_rows.append(dict(
                code=code, name=UNIVERSE[code], entry_n=en, exit_n=ex,
                strat_annual=m["strat_annual"], sharpe=m["sharpe"],
                mdd=m["mdd"], n_trades=m["n_trades"], win_rate=m["win_rate"]))
    pd.DataFrame(scan_rows).to_csv(
        os.path.join(BASE, "param_scan_results.csv"),
        index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
    show = dfm.copy()
    for c in ["strat_total", "strat_annual", "bench_total", "bench_annual",
              "excess_annual", "excess_total", "mdd", "bench_mdd", "win_rate"]:
        show[c] = (show[c] * 100).round(1)
    show["sharpe"] = show["sharpe"].round(2); show["calmar"] = show["calmar"].round(2)
    show["pl_ratio"] = show["pl_ratio"].round(2)
    print("\n===== 海龟策略回测指标汇总（收益/回撤/胜率为%）=====")
    print(show[["name", "system", "strat_annual", "bench_annual", "excess_annual",
                "sharpe", "mdd", "bench_mdd", "calmar", "n_trades", "win_rate",
                "pl_ratio"]].to_string(index=False))
    print("\n已保存 backtest_results.csv / param_scan_results.csv 与全部图形。")


if __name__ == "__main__":
    main()
