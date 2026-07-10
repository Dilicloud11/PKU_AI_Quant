# -*- coding: utf-8 -*-
"""
TASK4 海龟交易法则（Turtle Trading）回测引擎
作者：张哲铭

严格按经典海龟法则 + 用户提供的完整交易流程图实现
------------------------------------------------------------------
交易流程（对应报告流程图）：
  ① 选择市场（高流动性标的）
  ② 计算 N 日 ATR（Wilder 平滑，N 默认 20）
  ③ 计算单位头寸 Unit = 风险资本 /(N_ATR × 价值因子)
     —— 即“每次波动 1 个 ATR，账户波动 = 设定的风险比例”
  ④ 监控突破信号：价格突破 N 日最高价（做多）/ N 日最低价（做空，本文只做多）
  ⑤ 入场：突破确认后建立 1 个单位头寸
  ⑥ 判断价格是否上涨 0.5 ATR：
        是 → 加仓（每涨 0.5 ATR 加 1 单位，最多 4 单位）
        否 → 判断是否跌破止损线（入场后每单位 2 ATR 止损）：
                是 → 止损离场
                否 → 判断是否跌破 N_exit 日最低（离场通道）：
                        是 → 止盈/趋势结束离场
                        否 → 继续持有，循环判断

关键工程约束
------------------------------------------------------------------
· 只做多（A 股/ETF 现货无法便捷做空），符合国内可实践场景。
· 规避未来函数：第 t 日收盘判定的突破/离场，在第 t+1 日开盘（近似用次日收盘）执行。
· 单位头寸法：账户风险预算 RISK_PCT（默认 1%），单位规模使得
  “价格逆行 1 个 ATR 时账户回撤 = RISK_PCT”。等价于头寸金额 = 权益×RISK_PCT×价格/ATR。
· 计入单边交易成本（默认万分之五），在仓位变动当日按变动金额扣除。
· 逐日按“持仓市值权重”计算组合日收益，得到净值曲线，可与买入持有基准对比。

经典参数（Richard Dennis / Curtis Faith《海龟交易法则》）
------------------------------------------------------------------
  System 1（短期）：入场 20 日突破，离场 10 日反向突破
  System 2（长期）：入场 55 日突破，离场 20 日反向突破
  ATR 周期 N = 20；止损 = 2 ATR；加仓间隔 = 0.5 ATR；单市场最多 4 单位
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252
DEFAULT_COST = 0.0005      # 单边交易成本（万分之五）
RISK_FREE = 0.0            # 无风险年化利率（教学取 0）


# ============================================================
# 1) 指标计算：ATR 与 唐奇安通道（高低点通道）
# ============================================================
def compute_atr(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """
    计算 N 日平均真实波幅 ATR（Wilder 平滑法，海龟原版口径）。
    真实波幅 TR = max( 当日最高-当日最低,
                      |当日最高 - 昨收|,
                      |当日最低 - 昨收| )
    ATR = TR 的 N 日 Wilder 移动平均（首值用简单均值，之后递推平滑）。
    """
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder 平滑：ATR_t = (ATR_{t-1}*(N-1) + TR_t) / N
    atr = tr.copy()
    atr.iloc[:n] = tr.iloc[:n].mean()
    for i in range(n, len(tr)):
        atr.iloc[i] = (atr.iloc[i - 1] * (n - 1) + tr.iloc[i]) / n
    return atr


def compute_donchian(df: pd.DataFrame, entry_n: int, exit_n: int):
    """
    计算唐奇安（高低点）通道。
    上轨 = 过去 entry_n 日最高价（入场做多的突破线）
    下轨 = 过去 entry_n 日最低价（做空/参考）
    离场下轨 = 过去 exit_n 日最低价（多头趋势结束离场线）
    注意：用 shift(1) 取“不含当日”的历史极值，避免用当日信息判断当日突破（未来函数）。
    """
    upper = df["high"].rolling(entry_n).max().shift(1)      # N 日最高（入场上轨）
    lower = df["low"].rolling(entry_n).min().shift(1)       # N 日最低（入场下轨）
    exit_lower = df["low"].rolling(exit_n).min().shift(1)   # 离场下轨（跌破止盈离场）
    return upper, lower, exit_lower


# ============================================================
# 2) 海龟策略核心：逐日状态机（含加仓/止损/离场）
# ============================================================
def run_turtle(df: pd.DataFrame,
               entry_n: int = 20, exit_n: int = 10, atr_n: int = 20,
               risk_pct: float = 0.01, stop_atr: float = 2.0,
               add_atr: float = 0.5, max_units: int = 4,
               cost: float = DEFAULT_COST) -> dict:
    """
    对单标的运行一次海龟策略回测（只做多）。
    df 需含列：date, open, high, low, close（按日期升序）。

    返回：
      df   —— 含通道/ATR/仓位/净值等计算列的明细
      trades —— 逐笔完整交易（进出场、收益、持有天数、单位数）
      metrics —— 后续由 metrics 模块统一计算
    """
    d = df.copy().reset_index(drop=True)
    close = d["close"].values
    high = d["high"].values

    # 指标
    d["atr"] = compute_atr(d, atr_n)
    d["dc_upper"], d["dc_lower"], d["dc_exit"] = compute_donchian(d, entry_n, exit_n)
    atr = d["atr"].values
    dc_upper = d["dc_upper"].values
    dc_exit = d["dc_exit"].values

    n = len(d)
    # 目标持仓权重（0~1，1 表示满仓 max_units 单位）；t 日决策，t+1 日生效
    target_w = np.zeros(n)
    # 记录信号事件用于绘图：'buy'首次入场, 'add'加仓, 'stop'止损, 'exit'止盈离场
    event = [""] * n

    units = 0                    # 当前持有单位数
    entry_price = np.nan         # 首次入场价
    last_add_price = np.nan      # 上一次加/建仓价（用于 0.5ATR 加仓判定）
    stop_price = np.nan          # 当前止损线
    entry_atr = np.nan           # 入场时的 ATR（用于单位规模与止损）
    entry_idx = None
    trades = []

    warmup = max(entry_n, exit_n, atr_n)

    for i in range(n):
        if i < warmup or np.isnan(dc_upper[i]) or np.isnan(atr[i]):
            target_w[i] = 0.0
            continue

        price = close[i]

        if units == 0:
            # —— ④⑤ 监控突破 & 入场：收盘突破 N 日最高 → 建 1 单位 ——
            if high[i] > dc_upper[i] or price > dc_upper[i]:
                units = 1
                entry_price = price
                last_add_price = price
                entry_atr = atr[i]
                stop_price = price - stop_atr * entry_atr
                entry_idx = i
                event[i] = "buy"
        else:
            # 已持仓：优先判止损，再判离场，再判加仓（保守顺序，先保护本金）
            # —— 止损离场：跌破止损线 ——
            if price < stop_price:
                _close_trade(trades, d, entry_idx, i, entry_price, price,
                             units, "stop")
                event[i] = "stop"
                units = 0
                entry_price = last_add_price = stop_price = entry_atr = np.nan
                entry_idx = None
            # —— 止盈/趋势结束离场：跌破 exit_n 日最低 ——
            elif price < dc_exit[i]:
                _close_trade(trades, d, entry_idx, i, entry_price, price,
                             units, "exit")
                event[i] = "exit"
                units = 0
                entry_price = last_add_price = stop_price = entry_atr = np.nan
                entry_idx = None
            else:
                # —— ⑥ 加仓：每上涨 0.5 ATR 加 1 单位，最多 max_units ——
                if units < max_units and price >= last_add_price + add_atr * entry_atr:
                    units += 1
                    last_add_price = price
                    # 海龟法则：每加一仓，止损线整体上移（跟随最新单位 2ATR）
                    stop_price = price - stop_atr * entry_atr
                    event[i] = "add"

        target_w[i] = units / max_units      # 归一化为 0~1 的目标权重

    # 末尾仍持仓：按最后一日收盘平仓计入
    if units > 0 and entry_idx is not None:
        _close_trade(trades, d, entry_idx, n - 1, entry_price, close[-1],
                     units, "eod")

    d["units"] = (target_w * max_units).round().astype(int)
    d["target_w"] = target_w

    # —— 仓位次日生效，规避未来函数 ——
    d["position"] = pd.Series(target_w).shift(1).fillna(0.0)

    # —— 逐日收益与净值 ——
    d["ret"] = d["close"].pct_change().fillna(0.0)                 # 标的日收益（基准）
    d["turnover"] = d["position"].diff().abs().fillna(d["position"])  # 仓位变化幅度
    d["cost"] = d["turnover"] * cost                              # 交易成本
    d["strat_ret"] = d["position"] * d["ret"] - d["cost"]        # 策略日收益（已扣成本）
    d["equity"] = (1 + d["strat_ret"]).cumprod()                # 策略净值
    d["bench_equity"] = (1 + d["ret"]).cumprod()                # 买入持有净值

    # 事件列（供绘图打点）
    d["event"] = event
    return {"df": d, "trades": trades}


def _close_trade(trades, d, entry_idx, exit_idx, entry_price, exit_price,
                 units, reason):
    """记录一笔完整交易（进出场、净收益、单位数、离场原因）。"""
    gross = exit_price / entry_price - 1
    net = gross - 2 * DEFAULT_COST            # 扣双边成本近似
    trades.append({
        "entry_date": pd.Timestamp(d["date"].iloc[entry_idx]).date(),
        "exit_date": pd.Timestamp(d["date"].iloc[exit_idx]).date(),
        "hold_days": int(exit_idx - entry_idx),
        "units": int(units),
        "ret": float(net),
        "reason": reason,
    })
