# -*- coding: utf-8 -*-
"""
TASK7 通用回测引擎与绩效指标
- 支持单标的择时（双均线、小市值择时）与多标的轮动（ETF）
- 统一按"信号当日盘后产生、次日以收盘价成交"处理，杜绝未来函数
- 交易成本：ETF/指数按单边万5（0.0005）计
"""
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
COST = 0.0005            # 单边交易成本 万5
TRADING_DAYS = 244       # A股年化交易日近似


def load(code):
    df = pd.read_csv(os.path.join(DATA, f"{code}.csv"), encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True).set_index("date")


def load_close(code):
    return load(code)["close"]


# ---------------- 绩效指标 ----------------

def perf_metrics(nav, rf=0.0):
    """
    nav: pandas.Series 以日期为索引的净值序列（起点=1）
    返回 dict: 总收益/年化/年化波动/夏普/最大回撤/卡玛/胜率
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return dict(total=0, cagr=0, vol=0, sharpe=0, mdd=0, calmar=0, win=0, days=len(nav))
    ret = nav.pct_change().dropna()
    total = nav.iloc[-1] / nav.iloc[0] - 1
    years = len(nav) / TRADING_DAYS
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
    vol = ret.std() * np.sqrt(TRADING_DAYS)
    sharpe = (ret.mean() * TRADING_DAYS - rf) / vol if vol > 1e-9 else 0
    roll_max = nav.cummax()
    dd = nav / roll_max - 1
    mdd = dd.min()
    calmar = cagr / abs(mdd) if mdd < -1e-9 else 0
    win = (ret > 0).mean()
    return dict(total=total, cagr=cagr, vol=vol, sharpe=sharpe, mdd=mdd,
                calmar=calmar, win=win, days=len(nav))


def drawdown(nav):
    return nav / nav.cummax() - 1


# ---------------- 通用：由“目标仓位序列”生成净值 ----------------

def nav_from_position(close, target_pos, cost=COST):
    """
    close: 收盘价 Series
    target_pos: 目标仓位 Series（0~1），与 close 对齐；代表"当日盘后决定、次日生效"
    次日按收盘计收益，换仓在次日按目标仓位调整并计成本。
    返回 (nav, pos_used, turnover_series)
    """
    close = close.copy()
    ret = close.pct_change().fillna(0)
    # 次日生效：今日信号 shift(1) 后作用于今日收益
    pos = target_pos.reindex(close.index).ffill().fillna(0).shift(1).fillna(0)
    # 换手（仓位变化）产生成本，成本记在仓位变化当日
    turnover = pos.diff().abs().fillna(pos.abs())
    strat_ret = pos * ret - turnover * cost
    nav = (1 + strat_ret).cumprod()
    return nav, pos, turnover


def buy_hold_nav(close):
    return close / close.iloc[0]
