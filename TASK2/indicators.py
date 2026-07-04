# -*- coding: utf-8 -*-
"""
TASK2 数据炼金术：数据诊断与构造交易指标
作者：张哲铭

流程：
1) 加载 TASK1 存储的股价数据（长江电力 600900.SH）
2) 数据诊断：缺失值检查 + 描述性统计
3) 计算技术指标：RSI、MACD、布林带（Bollinger Bands）、KDJ（扩展）
4) 绘制各指标可视化图形并保存
所有指标均手工实现，便于理解其计算逻辑。
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "600900_daily.csv")
STOCK_NAME = "长江电力"
TS_CODE = "600900.SH"


def setup_font():
    """注册中文字体，避免乱码。"""
    sim_hei = r"C:\Windows\Fonts\simhei.ttf"
    if os.path.exists(sim_hei):
        font_manager.fontManager.addfont(sim_hei)
        matplotlib.rcParams["font.family"] = "SimHei"
    matplotlib.rcParams["axes.unicode_minus"] = False


# ============ 1. 加载数据 ============
def load_data():
    df = pd.read_csv(CSV_PATH)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


# ============ 2. 数据诊断 ============
def diagnose(df):
    """缺失值检查与描述性统计，返回文本报告并存 CSV。"""
    lines = []
    lines.append(f"数据形状：{df.shape[0]} 行 × {df.shape[1]} 列")
    lines.append(f"时间区间：{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")

    # 缺失值
    miss = df.isnull().sum()
    lines.append("\n【缺失值检查】")
    if miss.sum() == 0:
        lines.append("  所有字段均无缺失值，数据完整。")
    else:
        for k, v in miss[miss > 0].items():
            lines.append(f"  {k}: {v} 个缺失")

    # 重复值
    dup = df.duplicated(subset=["trade_date"]).sum()
    lines.append(f"\n【重复交易日】：{dup} 条")

    # 描述性统计（价格与量能核心字段）
    cols = ["open", "high", "low", "close", "vol", "amount", "pct_chg"]
    desc = df[cols].describe().T
    desc = desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    desc.to_csv(os.path.join(BASE_DIR, "describe_stats.csv"), encoding="utf-8-sig")

    lines.append("\n【描述性统计（核心字段）】")
    lines.append(desc.round(3).to_string())

    report = "\n".join(lines)
    print(report)
    return desc


# ============ 3. 指标计算 ============
def calc_rsi(close, period=14):
    """RSI 相对强弱指标。RSI = 100 - 100/(1+RS)，RS = 平均涨幅/平均跌幅。"""
    delta = close.diff()
    gain = delta.clip(lower=0)          # 上涨部分
    loss = -delta.clip(upper=0)         # 下跌部分（取正）
    # 用 Wilder 平滑（等价于 alpha=1/period 的指数移动平均）
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi


def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD。DIF=EMA12-EMA26，DEA=DIF的9日EMA，柱=（DIF-DEA)*2。"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist


def calc_boll(close, period=20, k=2):
    """布林带。中轨=20日SMA，上下轨=中轨±k倍标准差。"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + k * std
    lower = mid - k * std
    return upper, mid, lower


def calc_kdj(df, n=9, m1=3, m2=3):
    """KDJ 随机指标（扩展指标）。"""
    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


# ============ 4. 绘图 ============
def plot_rsi(df):
    setup_font()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), dpi=150,
                                   sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(df["trade_date"], df["close"], color="#c0392b", lw=1.4, label="收盘价")
    ax1.set_title(f"{STOCK_NAME}（{TS_CODE}）收盘价与 RSI(14) 指标", fontsize=14, fontweight="bold")
    ax1.set_ylabel("收盘价（元）"); ax1.legend(loc="upper right"); ax1.grid(alpha=.3, ls="--")

    ax2.plot(df["trade_date"], df["rsi"], color="#2c3e50", lw=1.2, label="RSI(14)")
    ax2.axhline(70, color="#c0392b", ls="--", lw=1, label="超买线 70")
    ax2.axhline(30, color="#27ae60", ls="--", lw=1, label="超卖线 30")
    ax2.fill_between(df["trade_date"], 70, 100, color="#c0392b", alpha=.06)
    ax2.fill_between(df["trade_date"], 0, 30, color="#27ae60", alpha=.06)
    ax2.set_ylabel("RSI"); ax2.set_ylim(0, 100); ax2.set_xlabel("交易日期")
    ax2.legend(loc="upper right", ncol=3, fontsize=8); ax2.grid(alpha=.3, ls="--")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(BASE_DIR, "rsi.png"), bbox_inches="tight")
    plt.close(fig)


def plot_macd(df):
    setup_font()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), dpi=150,
                                   sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(df["trade_date"], df["close"], color="#c0392b", lw=1.4, label="收盘价")
    ax1.set_title(f"{STOCK_NAME}（{TS_CODE}）收盘价与 MACD(12,26,9) 指标", fontsize=14, fontweight="bold")
    ax1.set_ylabel("收盘价（元）"); ax1.legend(loc="upper right"); ax1.grid(alpha=.3, ls="--")

    ax2.plot(df["trade_date"], df["dif"], color="#2980b9", lw=1.1, label="DIF")
    ax2.plot(df["trade_date"], df["dea"], color="#e67e22", lw=1.1, label="DEA")
    # 红涨绿跌的柱状图
    colors = ["#c0392b" if v >= 0 else "#27ae60" for v in df["macd_hist"]]
    ax2.bar(df["trade_date"], df["macd_hist"], color=colors, width=1.0, label="MACD 柱")
    ax2.axhline(0, color="#888", lw=.8)
    ax2.set_ylabel("MACD"); ax2.set_xlabel("交易日期")
    ax2.legend(loc="upper right", ncol=3, fontsize=8); ax2.grid(alpha=.3, ls="--")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(BASE_DIR, "macd.png"), bbox_inches="tight")
    plt.close(fig)


def plot_boll(df):
    setup_font()
    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    ax.plot(df["trade_date"], df["close"], color="#c0392b", lw=1.4, label="收盘价")
    ax.plot(df["trade_date"], df["boll_mid"], color="#2980b9", lw=1.1, ls="-", label="中轨(20日均线)")
    ax.plot(df["trade_date"], df["boll_up"], color="#e67e22", lw=1.0, ls="--", label="上轨(+2σ)")
    ax.plot(df["trade_date"], df["boll_low"], color="#27ae60", lw=1.0, ls="--", label="下轨(-2σ)")
    ax.fill_between(df["trade_date"], df["boll_low"], df["boll_up"], color="#3498db", alpha=.06)
    ax.set_title(f"{STOCK_NAME}（{TS_CODE}）布林带 Bollinger Bands(20,2)", fontsize=14, fontweight="bold")
    ax.set_ylabel("价格（元）"); ax.set_xlabel("交易日期")
    ax.legend(loc="best", fontsize=9); ax.grid(alpha=.3, ls="--")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(BASE_DIR, "boll.png"), bbox_inches="tight")
    plt.close(fig)


def plot_kdj(df):
    setup_font()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), dpi=150,
                                   sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(df["trade_date"], df["close"], color="#c0392b", lw=1.4, label="收盘价")
    ax1.set_title(f"{STOCK_NAME}（{TS_CODE}）收盘价与 KDJ(9,3,3) 指标", fontsize=14, fontweight="bold")
    ax1.set_ylabel("收盘价（元）"); ax1.legend(loc="upper right"); ax1.grid(alpha=.3, ls="--")

    ax2.plot(df["trade_date"], df["kdj_k"], color="#2980b9", lw=1.1, label="K")
    ax2.plot(df["trade_date"], df["kdj_d"], color="#e67e22", lw=1.1, label="D")
    ax2.plot(df["trade_date"], df["kdj_j"], color="#8e44ad", lw=1.0, label="J")
    ax2.axhline(80, color="#c0392b", ls="--", lw=1)
    ax2.axhline(20, color="#27ae60", ls="--", lw=1)
    ax2.set_ylabel("KDJ"); ax2.set_xlabel("交易日期")
    ax2.legend(loc="upper right", ncol=3, fontsize=8); ax2.grid(alpha=.3, ls="--")
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(os.path.join(BASE_DIR, "kdj.png"), bbox_inches="tight")
    plt.close(fig)


def main():
    df = load_data()
    print("=" * 60)
    print("【第 1 部分】数据诊断")
    print("=" * 60)
    diagnose(df)

    print("\n" + "=" * 60)
    print("【第 2 部分】指标计算")
    print("=" * 60)
    df["rsi"] = calc_rsi(df["close"])
    df["dif"], df["dea"], df["macd_hist"] = calc_macd(df["close"])
    df["boll_up"], df["boll_mid"], df["boll_low"] = calc_boll(df["close"])
    df["kdj_k"], df["kdj_d"], df["kdj_j"] = calc_kdj(df)

    # 打印最新一日各指标值
    last = df.iloc[-1]
    print(f"最新交易日 {last['trade_date'].date()} 各指标：")
    print(f"  收盘价={last['close']:.2f}")
    print(f"  RSI(14)={last['rsi']:.2f}")
    print(f"  DIF={last['dif']:.3f}  DEA={last['dea']:.3f}  MACD柱={last['macd_hist']:.3f}")
    print(f"  布林：上轨={last['boll_up']:.2f} 中轨={last['boll_mid']:.2f} 下轨={last['boll_low']:.2f}")
    print(f"  KDJ：K={last['kdj_k']:.2f} D={last['kdj_d']:.2f} J={last['kdj_j']:.2f}")

    # 保存带指标的完整数据
    df.to_csv(os.path.join(BASE_DIR, "600900_with_indicators.csv"),
              index=False, encoding="utf-8-sig")

    print("\n【第 3 部分】绘制指标图形 ...")
    plot_rsi(df); plot_macd(df); plot_boll(df); plot_kdj(df)
    print("已生成：rsi.png / macd.png / boll.png / kdj.png")
    print("全部完成。")


if __name__ == "__main__":
    main()
