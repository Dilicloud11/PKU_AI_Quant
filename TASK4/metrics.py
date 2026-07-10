# -*- coding: utf-8 -*-
"""
TASK4 回测指标体系
作者：张哲铭

一整套用于评估海龟策略的量化指标（对应报告"设计一系列回测指标"）：
  · 总收益率 Total Return          —— 期末净值 − 1
  · 年化收益率 Annualized Return   —— 折算到每年（252 交易日）
  · 基准年化（买入持有 Buy&Hold）
  · 超额收益 Excess Return         —— 策略年化 − 基准年化（剥离标的 β，看策略 α）
  · 夏普比率 Sharpe Ratio          —— 风险调整后收益，年化
  · 最大回撤 MDD                   —— 净值从高点回落的最大跌幅
  · 卡玛比率 Calmar Ratio          —— 年化收益 / |最大回撤|，收益回撤性价比
  · 胜率 Win Rate                  —— 盈利交易 / 总交易（按逐笔回合）
  · 盈亏比 Profit/Loss Ratio       —— 平均盈利 / |平均亏损|
  · 交易次数 / 平均持有天数
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
RISK_FREE = 0.0


def compute_metrics(res: dict) -> dict:
    """输入 run_turtle 的返回，输出完整指标字典。"""
    d = res["df"]
    trades = res["trades"]

    n = len(d)
    years = n / TRADING_DAYS if n > 0 else np.nan

    strat_total = d["equity"].iloc[-1] - 1
    bench_total = d["bench_equity"].iloc[-1] - 1
    strat_annual = (1 + strat_total) ** (1 / years) - 1 if years > 0 else np.nan
    bench_annual = (1 + bench_total) ** (1 / years) - 1 if years > 0 else np.nan
    excess_annual = strat_annual - bench_annual
    excess_total = strat_total - bench_total

    # 夏普比率（年化）
    daily = d["strat_ret"]
    rf_daily = RISK_FREE / TRADING_DAYS
    ex_daily = daily - rf_daily
    sharpe = (ex_daily.mean() / ex_daily.std() * np.sqrt(TRADING_DAYS)
              if ex_daily.std() > 0 else np.nan)

    # 最大回撤（策略 / 基准）
    roll_max = d["equity"].cummax()
    mdd = (d["equity"] / roll_max - 1).min()
    b_roll = d["bench_equity"].cummax()
    bench_mdd = (d["bench_equity"] / b_roll - 1).min()

    # 卡玛比率
    calmar = (strat_annual / abs(mdd)) if mdd < 0 else np.nan

    # 逐笔交易统计
    if trades:
        tr = pd.DataFrame(trades)
        wins = tr[tr["ret"] > 0]["ret"]
        losses = tr[tr["ret"] <= 0]["ret"]
        win_rate = len(wins) / len(tr)
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = losses.mean() if len(losses) else 0.0
        pl_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else np.nan
        avg_hold = tr["hold_days"].mean()
    else:
        win_rate = pl_ratio = avg_win = avg_loss = np.nan
        avg_hold = np.nan

    return {
        "n_days": n, "years": round(years, 2),
        "strat_total": strat_total, "strat_annual": strat_annual,
        "bench_total": bench_total, "bench_annual": bench_annual,
        "excess_annual": excess_annual, "excess_total": excess_total,
        "sharpe": sharpe, "mdd": mdd, "bench_mdd": bench_mdd, "calmar": calmar,
        "n_trades": len(trades), "win_rate": win_rate, "pl_ratio": pl_ratio,
        "avg_win": avg_win, "avg_loss": avg_loss, "avg_hold": avg_hold,
    }
