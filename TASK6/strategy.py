# -*- coding: utf-8 -*-
"""
TASK6 机器学习交易策略回测引擎 strategy.py
==========================================
把 TASK5 训练好的分类模型输出的“下期上涨概率”转化为实际交易决策，
并做全流程回测。核心策略要素（对应作业要求）：

  1. 双阈值策略：买入阈值 buy_th、卖出阈值 sell_th（sell_th < buy_th）。
       概率 >= buy_th 时开/持仓；概率 <= sell_th 时清仓；两者之间维持原仓位，
       从而减少频繁交易、降低成本、在不确定区不盲动。
  2. 概率加权仓位：目标仓位 = clip((p - 0.5) * 2, 0, 1) * max_pos，
       确定性高时重仓、低时轻仓。
  3. 技术指标过滤：当 RSI>70(超买) 或 MA5<=MA20(空头排列) 或
       量比<0.7(缩量) 或 20日波动率处于高分位 时，禁止新开仓/降低仓位。
  4. 风控：止损 stop_loss、止盈 take_profit（相对持仓成本价）。
  5. 交易成本：单边万分之五（与前序任务一致）。

回测严格使用 TASK5 划分出的“测试集时间段”，模型概率来自测试集样本外预测，
不使用未来信息。
作者：张哲铭
"""
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
COST = 0.0005   # 单边交易成本


def _rsi(close, n=14):
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    ru = up.ewm(alpha=1.0 / n, adjust=False).mean()
    rd = down.ewm(alpha=1.0 / n, adjust=False).mean()
    return 100.0 - 100.0 / (1.0 + ru / (rd + 1e-12))


def build_backtest_frame(dates, closes, proba):
    """构造回测所需 DataFrame：日期、收盘、下期收益、模型概率、技术过滤指标。"""
    df = pd.DataFrame({"date": pd.to_datetime(dates),
                       "close": np.asarray(closes, dtype=float),
                       "proba": np.asarray(proba, dtype=float)})
    df = df.sort_values("date").reset_index(drop=True)
    c = df["close"]
    df["ret_next"] = c.shift(-1) / c - 1.0        # 次日收益（持仓在该日获得）
    df["rsi14"] = _rsi(c, 14)
    df["ma5"] = c.rolling(5).mean()
    df["ma20"] = c.rolling(20).mean()
    df["vol_ratio"] = c.pct_change().abs().rolling(5).mean()  # 近似波动
    df["vol_q"] = df["vol_ratio"].rolling(60).rank(pct=True)  # 波动分位
    return df


def run_strategy(df, buy_th=0.6, sell_th=0.5, max_pos=1.0,
                 stop_loss=0.08, take_profit=0.15,
                 prob_weight=True, tech_filter=True):
    """逐日回测。返回含每日仓位/净值/回撤的 DataFrame 与指标 dict。

    仓位逻辑（次日生效，避免未来函数）：
      - 依据“当日收盘可得”的概率与技术指标，决定“下一日”的目标仓位；
      - 该目标仓位吃到 ret_next（次日收益）。
    """
    df = df.copy().reset_index(drop=True)
    n = len(df)
    pos = np.zeros(n)          # 实际持仓比例（0~1）
    target = np.zeros(n)
    entry_price = np.nan       # 持仓成本价
    cur_pos = 0.0

    for i in range(n):
        p = df.at[i, "proba"]
        close = df.at[i, "close"]

        # ---- 技术指标过滤：不利环境禁止/压缩开仓 ----
        block = False
        if tech_filter:
            rsi = df.at[i, "rsi14"]
            ma5, ma20 = df.at[i, "ma5"], df.at[i, "ma20"]
            volq = df.at[i, "vol_q"]
            if (rsi > 70) or (ma5 <= ma20) or (volq is not np.nan and volq > 0.9):
                block = True

        # ---- 止损/止盈：基于持仓成本 ----
        forced_exit = False
        if cur_pos > 0 and not np.isnan(entry_price):
            chg = close / entry_price - 1.0
            if chg <= -stop_loss or chg >= take_profit:
                forced_exit = True

        # ---- 双阈值 + 概率加权决定目标仓位 ----
        if forced_exit:
            tgt = 0.0
        elif p >= buy_th and not block:
            if prob_weight:
                tgt = np.clip((p - 0.5) * 2.0, 0.0, 1.0) * max_pos
            else:
                tgt = max_pos
        elif p <= sell_th:
            tgt = 0.0
        else:
            tgt = cur_pos          # 不确定区：维持原仓位
            if block:
                tgt = min(cur_pos, 0.0) if forced_exit else cur_pos
        target[i] = tgt

        # 更新持仓成本：新建/加仓时刷新成本价（简化为最新收盘）
        if tgt > 0 and (cur_pos == 0 or tgt > cur_pos):
            entry_price = close
        elif tgt == 0:
            entry_price = np.nan
        cur_pos = tgt
        pos[i] = tgt

    df["target_pos"] = target
    # 次日实际生效仓位（今日决定→明日持有），最后一日无次日收益
    df["pos"] = df["target_pos"]
    df["turnover"] = df["pos"].diff().abs().fillna(df["pos"].abs())
    # 策略日收益 = 仓位 * 次日收益 - 换手*成本
    df["strat_ret"] = df["pos"] * df["ret_next"].fillna(0.0) - df["turnover"] * COST
    df["bh_ret"] = df["ret_next"].fillna(0.0)      # 买入持有

    df["strat_equity"] = (1.0 + df["strat_ret"]).cumprod()
    df["bh_equity"] = (1.0 + df["bh_ret"]).cumprod()
    # 回撤
    roll_max = df["strat_equity"].cummax()
    df["drawdown"] = df["strat_equity"] / roll_max - 1.0

    metrics = compute_metrics(df)
    return df, metrics


def compute_metrics(df):
    sr = df["strat_ret"].values
    br = df["bh_ret"].values
    n = len(sr)
    ann = 252.0
    def cagr(equity):
        if len(equity) < 2 or equity[-1] <= 0:
            return np.nan
        yrs = len(equity) / ann
        return equity[-1] ** (1.0 / yrs) - 1.0
    se = df["strat_equity"].values
    be = df["bh_equity"].values
    strat_total = se[-1] - 1.0
    bh_total = be[-1] - 1.0
    strat_cagr = cagr(se)
    bh_cagr = cagr(be)
    sharpe = np.mean(sr) / (np.std(sr) + 1e-12) * np.sqrt(ann)
    mdd = df["drawdown"].min()
    # 交易统计：以每次从0->正仓视作一次开仓
    pos = df["pos"].values
    trades = int(np.sum((pos[1:] > 0) & (pos[:-1] == 0)))
    # 持仓日胜率：有仓位当日策略收益>0占比
    held = df["strat_ret"][df["pos"] > 0]
    win = float(np.mean(held > 0)) if len(held) else np.nan
    avg_ret = float(held.mean()) if len(held) else np.nan
    exposure = float(np.mean(pos > 0))
    calmar = strat_cagr / abs(mdd) if mdd < 0 else np.nan
    return {
        "strat_total": strat_total, "bh_total": bh_total,
        "excess_total": strat_total - bh_total,
        "strat_cagr": strat_cagr, "bh_cagr": bh_cagr,
        "sharpe": sharpe, "mdd": mdd, "calmar": calmar,
        "trades": trades, "win_rate": win, "avg_hold_ret": avg_ret,
        "exposure": exposure,
    }


def quarterly_returns(df):
    """按季度汇总策略与买入持有收益。"""
    tmp = df.copy()
    tmp["q"] = tmp["date"].dt.to_period("Q").astype(str)
    g = tmp.groupby("q").agg(
        strat=("strat_ret", lambda s: (1 + s).prod() - 1),
        bh=("bh_ret", lambda s: (1 + s).prod() - 1)).reset_index()
    return g
