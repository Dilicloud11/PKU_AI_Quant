# -*- coding: utf-8 -*-
"""
量化交易初体验：从零搭建数据引擎
作者：张哲铭

功能：
1) 通过 Tushare Pro 接口获取沪深A股某只股票过去一年的每日交易数据
2) 绘制每日收盘价曲线图
3) 将原始数据保存为 CSV，供后续任务复用

目标标的：长江电力（600900.SH），沪市大盘蓝筹、水电龙头，
数据完整、走势稳健，适合作为量化入门的教学样本。
"""

import os

import tushare as ts
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无界面后端，便于脚本化出图
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ============ 基础配置 ============
# Tushare Pro 的个人 token（身份凭证，请妥善保管，切勿硬编码到公开代码中）
# 从环境变量 TUSHARE_TOKEN 读取；本地运行前请先设置：
#   Windows(PowerShell): $env:TUSHARE_TOKEN="你的Token"
#   Linux/macOS:         export TUSHARE_TOKEN="你的Token"
TOKEN = os.environ.get("TUSHARE_TOKEN", "")

# 目标股票：长江电力（沪市A股）
TS_CODE = "600900.SH"
STOCK_NAME = "长江电力"

# 过去一年的时间区间
END_DATE = "20260704"    # 截止日期（今天）
START_DATE = "20250704"  # 一年前

# 输出路径（脚本所在目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "600900_daily.csv")
FIG_PATH = os.path.join(BASE_DIR, "close_price.png")


def setup_chinese_font():
    """注册系统中文字体，避免绘图中文乱码。"""
    sim_hei = r"C:\Windows\Fonts\simhei.ttf"
    if os.path.exists(sim_hei):
        font_manager.fontManager.addfont(sim_hei)
        matplotlib.rcParams["font.family"] = "SimHei"
    matplotlib.rcParams["axes.unicode_minus"] = False  # 正常显示负号


def fetch_daily_data():
    """调用 Tushare A股日线接口，获取过去一年的每日交易数据。"""
    if not TOKEN:
        raise RuntimeError(
            "未检测到 Tushare token。请先设置环境变量 TUSHARE_TOKEN 后再运行。"
        )
    ts.set_token(TOKEN)
    pro = ts.pro_api()

    # daily：A股日线行情（未复权）
    df = pro.daily(
        ts_code=TS_CODE,
        start_date=START_DATE,
        end_date=END_DATE,
    )

    if df is None or df.empty:
        raise RuntimeError(
            "未获取到数据。请确认 Tushare token 有效、积分满足调用要求，"
            "以及股票代码与日期区间正确。"
        )

    # 按交易日期升序排列，方便时间序列分析与绘图
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def save_csv(df: pd.DataFrame):
    """将原始数据保存为 CSV，供后续任务复用。"""
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[CSV] 已保存：{CSV_PATH}  共 {len(df)} 个交易日")


def plot_close_price(df: pd.DataFrame):
    """绘制每日收盘价曲线图。"""
    setup_chinese_font()

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)
    ax.plot(df["trade_date"], df["close"], color="#c0392b", linewidth=1.6,
            label="收盘价")

    ax.set_title(f"{STOCK_NAME}（{TS_CODE}）近一年每日收盘价走势",
                 fontsize=15, fontweight="bold", pad=12)
    ax.set_xlabel("交易日期", fontsize=11)
    ax.set_ylabel("收盘价（元）", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="best", fontsize=10)

    # 标注最高/最低点，增强可读性（A股惯例：红涨绿跌）
    max_row = df.loc[df["close"].idxmax()]
    min_row = df.loc[df["close"].idxmin()]
    ax.scatter([max_row["trade_date"]], [max_row["close"]], color="#c0392b", zorder=5)
    ax.annotate(f"最高 {max_row['close']:.2f}",
                (max_row["trade_date"], max_row["close"]),
                textcoords="offset points", xytext=(0, 10), fontsize=9,
                ha="center", color="#c0392b")
    ax.scatter([min_row["trade_date"]], [min_row["close"]], color="#27ae60", zorder=5)
    ax.annotate(f"最低 {min_row['close']:.2f}",
                (min_row["trade_date"], min_row["close"]),
                textcoords="offset points", xytext=(0, -14), fontsize=9,
                ha="center", color="#27ae60")

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIG_PATH, bbox_inches="tight")
    print(f"[FIG] 已保存收盘价曲线图：{FIG_PATH}")


def print_summary(df: pd.DataFrame):
    """打印数据概览，便于文档中引用关键统计量。"""
    print("=" * 50)
    print(f"标的：{STOCK_NAME}（{TS_CODE}）")
    print(f"区间：{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")
    print(f"交易日数：{len(df)}")
    print(f"期初收盘：{df['close'].iloc[0]:.2f}  期末收盘：{df['close'].iloc[-1]:.2f}")
    print(f"期间最高：{df['close'].max():.2f}  期间最低：{df['close'].min():.2f}")
    ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"区间涨跌幅：{ret:+.2f}%")
    print("=" * 50)


def main():
    print("开始获取数据 ...")
    df = fetch_daily_data()
    save_csv(df)
    plot_close_price(df)
    print_summary(df)
    print("全部完成。")


if __name__ == "__main__":
    main()
