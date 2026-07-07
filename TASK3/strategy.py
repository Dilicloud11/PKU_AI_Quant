# -*- coding: utf-8 -*-
"""
TASK3 双均线策略回测引擎
作者：张哲铭

核心逻辑
--------
1) 双均线策略：计算短期均线(MA_short)与长期均线(MA_long)
   - 金叉：短均线上穿长均线 -> 买入并持有（满仓）
   - 死叉：短均线下穿长均线 -> 卖出并空仓
2) 为避免"未来函数"，第 t 日收盘后产生的信号在第 t+1 日才建/平仓
   （用 position = signal.shift(1) 实现），交易时按当日收益计入。
3) 计入单边交易成本（默认万分之五），在仓位发生变化的当日扣除。

评估指标
--------
- 累计收益 / 总收益率 Cumulative Return
- 年化收益率 Annualized Return
- 基准（买入持有）总收益率、年化收益率
- 超额收益 Excess Return（策略年化 − 基准年化）：衡量策略本身而非标的带来的收益
- 胜率 Win Rate（按完整买卖回合统计）
- 盈亏比 Profit/Loss Ratio（平均盈利 / 平均亏损）
- 最大回撤 MDD（Maximum Drawdown）
- 夏普比率 Sharpe Ratio（年化，无风险利率默认 0）
- 交易次数 Trades
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252          # 年化交易日（标准约定）
DEFAULT_COST = 0.0005       # 单边交易成本（万分之五，含佣金+冲击成本近似）
RISK_FREE = 0.0             # 无风险年化利率（教学场景取 0）


def compute_ma(close: pd.Series, short: int, long: int):
    """计算短、长两条简单移动平均线（SMA）。"""
    ma_short = close.rolling(short).mean()
    ma_long = close.rolling(long).mean()
    return ma_short, ma_long


def gen_signals(ma_short: pd.Series, ma_long: pd.Series):
    """
    生成交易信号。
    raw_signal：短均线在长均线之上记为持仓状态 1，否则 0。
    cross：+1 金叉当日、-1 死叉当日、0 无变化（用于图上打点）。
    """
    raw = (ma_short > ma_long).astype(int)
    raw[ma_long.isna()] = 0                 # 均线未形成期不持仓
    cross = raw.diff().fillna(0)            # 由 0->1 为金叉(+1)，1->0 为死叉(-1)
    return raw, cross


def run_backtest(df: pd.DataFrame, short: int, long: int,
                 cost: float = DEFAULT_COST) -> dict:
    """
    对单个标的运行一次双均线回测。
    df 需含列：date, close（按日期升序）。
    返回：包含带计算列的明细 DataFrame、逐笔交易记录与各项指标的字典。
    """
    d = df.copy().reset_index(drop=True)
    close = d["close"]

    # 1) 均线与信号
    d["ma_short"], d["ma_long"] = compute_ma(close, short, long)
    d["raw_signal"], d["cross"] = gen_signals(d["ma_short"], d["ma_long"])

    # 2) 仓位：信号次日生效，避免未来函数
    d["position"] = d["raw_signal"].shift(1).fillna(0)

    # 3) 收益
    d["ret"] = close.pct_change().fillna(0)                 # 标的日收益（基准）
    d["trade"] = d["position"].diff().abs().fillna(0)       # 仓位变化幅度（0->1 或 1->0 记 1）
    d["cost"] = d["trade"] * cost                            # 交易成本
    d["strat_ret"] = d["position"] * d["ret"] - d["cost"]   # 策略日收益（已扣成本）

    # 4) 净值曲线
    d["equity"] = (1 + d["strat_ret"]).cumprod()            # 策略净值
    d["bench_equity"] = (1 + d["ret"]).cumprod()            # 基准（买入持有）净值

    # ===== 指标计算 =====
    n = len(d)
    years = n / TRADING_DAYS

    strat_total = d["equity"].iloc[-1] - 1
    bench_total = d["bench_equity"].iloc[-1] - 1
    strat_annual = (1 + strat_total) ** (1 / years) - 1 if years > 0 else np.nan
    bench_annual = (1 + bench_total) ** (1 / years) - 1 if years > 0 else np.nan
    excess_annual = strat_annual - bench_annual             # 超额年化收益

    # 夏普比率（年化）
    daily = d["strat_ret"]
    rf_daily = RISK_FREE / TRADING_DAYS
    excess_daily = daily - rf_daily
    sharpe = (excess_daily.mean() / excess_daily.std() * np.sqrt(TRADING_DAYS)
              if excess_daily.std() > 0 else np.nan)

    # 最大回撤
    roll_max = d["equity"].cummax()
    drawdown = d["equity"] / roll_max - 1
    mdd = drawdown.min()

    # 基准最大回撤（用于对比）
    b_roll_max = d["bench_equity"].cummax()
    b_mdd = (d["bench_equity"] / b_roll_max - 1).min()

    # ===== 逐笔交易统计（胜率、盈亏比）=====
    trades = extract_trades(d)
    if trades:
        tr = pd.DataFrame(trades)
        wins = tr[tr["ret"] > 0]["ret"]
        losses = tr[tr["ret"] <= 0]["ret"]
        win_rate = len(wins) / len(tr)
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = losses.mean() if len(losses) else 0.0
        pl_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else np.nan
    else:
        win_rate, pl_ratio, avg_win, avg_loss = np.nan, np.nan, 0.0, 0.0

    metrics = {
        "short": short, "long": long, "n_days": n, "years": round(years, 2),
        "strat_total": strat_total, "strat_annual": strat_annual,
        "bench_total": bench_total, "bench_annual": bench_annual,
        "excess_annual": excess_annual,
        "excess_total": strat_total - bench_total,
        "sharpe": sharpe, "mdd": mdd, "bench_mdd": b_mdd,
        "n_trades": len(trades), "win_rate": win_rate, "pl_ratio": pl_ratio,
        "avg_win": avg_win, "avg_loss": avg_loss,
    }
    return {"df": d, "trades": trades, "metrics": metrics}


def extract_trades(d: pd.DataFrame):
    """
    从仓位序列提取完整买卖回合，计算每笔交易净收益（已含成本近似）。
    以进出场当日收盘价计算回合收益，并扣除两侧交易成本。
    """
    trades = []
    pos = d["position"].values
    close = d["close"].values
    dates = d["date"].values
    entry_i = None
    for i in range(len(d)):
        if pos[i] == 1 and (i == 0 or pos[i - 1] == 0):
            entry_i = i                     # 建仓日
        if entry_i is not None and (pos[i] == 0 and pos[i - 1] == 1):
            exit_i = i                      # 平仓日
            gross = close[exit_i] / close[entry_i] - 1
            net = gross - 2 * DEFAULT_COST  # 扣双边成本
            trades.append({
                "entry_date": pd.Timestamp(dates[entry_i]).date(),
                "exit_date": pd.Timestamp(dates[exit_i]).date(),
                "hold_days": exit_i - entry_i,
                "ret": net,
            })
            entry_i = None
    # 末尾仍持仓：按最后一日收盘平仓计入（浮动盈亏）
    if entry_i is not None:
        gross = close[-1] / close[entry_i] - 1
        trades.append({
            "entry_date": pd.Timestamp(dates[entry_i]).date(),
            "exit_date": pd.Timestamp(dates[-1]).date(),
            "hold_days": len(d) - 1 - entry_i,
            "ret": gross - DEFAULT_COST,
        })
    return trades
