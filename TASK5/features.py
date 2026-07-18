# -*- coding: utf-8 -*-
"""
TASK5/6 共享特征工程模块 features.py
====================================
职责：
  1. 从 OHLCV 前复权日线衍生技术因子（动量/波动/量价/均线偏离/RSI/MACD/KDJ/BOLL 等）
  2. 生成预测标签：
       - 分类标签 y_cls：下一交易日收益 > 0 记为 1，否则 0
       - 回归标签 y_reg：下一交易日收益率（未来 1 日 pct_change）
  3. 财务因子对齐（个股 600900/00700）：季度财务指标按“信息发布日”前向对齐到日频，
       严格避免未来函数（只使用发布日<=当日的最新一期财务）。
  4. 时间序列划分：按时间顺序切分 train/val/test，绝不随机打乱，
       训练集永远在验证集之前、验证集永远在测试集之前，杜绝用未来预测过去。

设计原则（对应作业要求）：
  * 无未来函数：所有滚动/移动窗口只用当日及以前的数据；标签用 shift(-1) 定义在“下一日”，
    但特征构造完成后会 dropna，并在划分时保证 X 的时间戳严格早于其标签实现时刻。
  * 可计算性：因子全部由 OHLCV 可复现，缺失做前向/丢弃处理。
  * 稳定性：使用比率、对数收益、标准化偏离等无量纲/弱趋势特征，避免绝对价格量纲漂移。
  * 相关性：包含动量、波动率、量价背离等与短期收益有经济学关联的因子（Gu-Kelly-Xiu 2020
    指出主导信号为动量/流动性/波动率）。
作者：张哲铭
"""
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

CODES = ["sh600900", "hk00700", "sh518880", "sh515450",
         "sz159941", "sh588000", "sh510300", "sh510500"]

NAME = {
    "sh600900": "长江电力", "hk00700": "腾讯控股", "sh518880": "黄金ETF",
    "sh515450": "红利低波50ETF", "sz159941": "纳指ETF", "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF", "sh510500": "中证500ETF",
}
# 拥有财务数据的个股（ETF 无财务报表）
STOCK_WITH_FIN = {"sh600900", "hk00700"}


# ============ 技术指标底层函数 ============
def _ema(s, span):
    return s.ewm(span=span, adjust=False).mean()


def _rsi(close, n=14):
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1.0 / n, adjust=False).mean()
    roll_down = down.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    return 100.0 - 100.0 / (1.0 + rs)


def _macd(close, fast=12, slow=26, signal=9):
    dif = _ema(close, fast) - _ema(close, slow)
    dea = _ema(dif, signal)
    hist = (dif - dea) * 2.0
    return dif, dea, hist


def _kdj(high, low, close, n=9):
    low_n = low.rolling(n).min()
    high_n = high.rolling(n).max()
    rsv = (close - low_n) / (high_n - low_n + 1e-12) * 100.0
    k = rsv.ewm(alpha=1.0 / 3, adjust=False).mean()
    d = k.ewm(alpha=1.0 / 3, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def _atr(high, low, close, n=14):
    prev_close = close.shift(1)
    tr = pd.concat([(high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


# ============ 特征工程主函数 ============
def build_features(df):
    """输入含 date/open/high/low/close/volume 的日线 DataFrame，输出带特征与标签的 DataFrame。
    所有特征仅使用当日及历史信息；标签使用未来 1 日收益（下一交易日）。"""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    ret1 = c.pct_change()  # 当日收益（用于滚动统计，非标签）
    logret = np.log(c / c.shift(1))

    feat = pd.DataFrame(index=df.index)
    feat["date"] = df["date"]

    # --- 1) 动量类：过去 N 日累计收益 ---
    for n in [1, 3, 5, 10, 20, 60]:
        feat[f"mom_{n}"] = c.pct_change(n)
    # 过去收益的对数版（更稳定）
    feat["logret_1"] = logret
    feat["logret_5"] = np.log(c / c.shift(5))

    # --- 2) 均线偏离类：价格相对均线的标准化偏离 ---
    for n in [5, 10, 20, 60]:
        ma = c.rolling(n).mean()
        feat[f"ma_bias_{n}"] = (c - ma) / (ma + 1e-12)   # 乖离率
    feat["ma5_ma20"] = c.rolling(5).mean() / (c.rolling(20).mean() + 1e-12) - 1.0
    feat["ma10_ma60"] = c.rolling(10).mean() / (c.rolling(60).mean() + 1e-12) - 1.0

    # --- 3) 波动率类 ---
    for n in [5, 10, 20]:
        feat[f"vol_{n}"] = ret1.rolling(n).std()
    feat["atr_14"] = _atr(h, l, c, 14) / (c + 1e-12)          # 归一化 ATR
    feat["hl_range"] = (h - l) / (c + 1e-12)                   # 当日振幅
    feat["hl_range_ma5"] = feat["hl_range"].rolling(5).mean()

    # --- 4) 量价类 ---
    feat["vol_chg_1"] = v.pct_change()
    feat["vol_ratio_5"] = v / (v.rolling(5).mean() + 1e-12)    # 量比(5日)
    feat["vol_ratio_20"] = v / (v.rolling(20).mean() + 1e-12)
    # 量价相关性（20日滚动）：价涨量增/价跌量缩的动量确认
    feat["pv_corr_20"] = ret1.rolling(20).corr(v.pct_change())

    # --- 5) RSI / MACD / KDJ / BOLL ---
    feat["rsi_6"] = _rsi(c, 6)
    feat["rsi_14"] = _rsi(c, 14)
    dif, dea, hist = _macd(c)
    feat["macd_dif"] = dif / (c + 1e-12)
    feat["macd_dea"] = dea / (c + 1e-12)
    feat["macd_hist"] = hist / (c + 1e-12)
    k, d, j = _kdj(h, l, c)
    feat["kdj_k"], feat["kdj_d"], feat["kdj_j"] = k, d, j
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    feat["boll_pctb"] = (c - (ma20 - 2 * std20)) / (4 * std20 + 1e-12)  # %B
    feat["boll_width"] = (4 * std20) / (ma20 + 1e-12)                   # 带宽

    # --- 6) 位置类：过去 N 日价格分位 ---
    for n in [20, 60]:
        roll_min = c.rolling(n).min()
        roll_max = c.rolling(n).max()
        feat[f"pos_{n}"] = (c - roll_min) / (roll_max - roll_min + 1e-12)

    # --- 7) 隔夜/日内 ---
    feat["overnight"] = df["open"] / (c.shift(1) + 1e-12) - 1.0
    feat["intraday"] = c / (df["open"] + 1e-12) - 1.0

    # ============ 标签（未来 1 日） ============
    fwd_ret = c.shift(-1) / c - 1.0     # 下一交易日收益率
    feat["y_reg"] = fwd_ret             # 回归目标：下期收益率
    # 分类目标：下期不跌(>=0)记为 1。之所以用 >=0 而非 >0，是因为纳指/红利低波等
    # 跨境或低波 ETF 存在大量“平盘日”(收益恰为 0，占比可达 40%)，若把平盘归为“跌”
    # 会造成标签严重失衡且不符合择时语义（不跌即可持有）。
    feat["y_cls"] = (fwd_ret >= 0).astype(int)  # 分类目标：下期不跌=1

    # 附加：辅助回测用的当日收盘价与下一日收益（不作为特征）
    feat["close"] = c.values
    return feat


# ============ 财务因子对齐（个股） ============
def _parse_fin_md(path):
    """解析 westock finance 命令输出的 markdown 表格，返回 DataFrame。"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        return None
    header = [x.strip() for x in lines[0].strip("|").split("|")]
    rows = []
    for ln in lines[2:]:
        cells = [x.strip() for x in ln.strip("|").split("|")]
        if len(cells) == len(header):
            rows.append(cells)
    return pd.DataFrame(rows, columns=header)


def add_financial_factors(feat, code):
    """对个股把季度财务因子按发布日前向对齐到日频，避免未来函数。
    ETF 或无财务文件时原样返回。"""
    if code not in STOCK_WITH_FIN:
        return feat
    path = os.path.join(DATA, f"fin_raw_{code}.md")
    fin = _parse_fin_md(path)
    if fin is None:
        return feat

    def to_num(s):
        return pd.to_numeric(s, errors="coerce")

    # 发布日：财务信息真正对市场可见的时间（关键：用它对齐，杜绝未来函数）
    pub_col = "InfoPublDate"
    if pub_col not in fin.columns:
        return feat
    fin["pub"] = pd.to_datetime(fin[pub_col].str.split().str[0], errors="coerce")
    fin = fin.dropna(subset=["pub"]).sort_values("pub")

    out = pd.DataFrame({"pub": fin["pub"].values})
    if code == "sh600900":   # A股利润表字段
        out["fin_eps"] = to_num(fin.get("BasicEPS")).values
        rev = to_num(fin.get("OperatingRevenueTTM"))
        npf = to_num(fin.get("NPParentCompanyOwnersTTM"))
        out["fin_rev_ttm"] = rev.values
        out["fin_np_ttm"] = npf.values
        out["fin_npm"] = (npf / (rev + 1e-9)).values          # TTM 净利率
    else:                     # 腾讯港股综合损益表字段
        out["fin_eps"] = to_num(fin.get("BasicEPS")).values
        out["fin_roe"] = to_num(fin.get("RoeWeighted")).values
        out["fin_np_gr"] = to_num(fin.get("NpParentCompanyGr1y")).values  # 净利同比
        out["fin_rev_gr"] = to_num(fin.get("OperatingRevenueGr1y")).values

    # 衍生：EPS 同比变化（用发布序列差分，稳定的增速信号）
    out["fin_eps_chg"] = out["fin_eps"].pct_change()
    out = out.dropna(subset=["pub"]).drop_duplicates("pub").sort_values("pub")

    # merge_asof：把每个交易日对齐到“发布日<=该交易日”的最近一期财务（前向对齐）
    feat = feat.sort_values("date")
    merged = pd.merge_asof(feat, out, left_on="date", right_on="pub",
                           direction="backward")
    merged = merged.drop(columns=["pub"])
    fin_cols = [c for c in out.columns if c != "pub"]
    # 财务因子早期可能缺失，用 0 填充并标注（模型可容忍）
    for col in fin_cols:
        if col in merged.columns:
            merged[col] = merged[col].ffill().fillna(0.0)
    return merged


def get_feature_columns(feat):
    """返回参与建模的特征列（排除 date/标签/辅助列）。"""
    exclude = {"date", "y_reg", "y_cls", "close"}
    return [c for c in feat.columns if c not in exclude]


# ============ 时间序列划分 ============
def time_split(feat, train=0.6, val=0.2):
    """按时间顺序切分，绝不打乱。返回 (train_df, val_df, test_df)。
    train:val:test 默认 0.6:0.2:0.2。"""
    feat = feat.dropna().reset_index(drop=True)
    n = len(feat)
    i1 = int(n * train)
    i2 = int(n * (train + val))
    return feat.iloc[:i1].copy(), feat.iloc[i1:i2].copy(), feat.iloc[i2:].copy()


def load_symbol(code, with_fin=True):
    """加载单标的，构造特征与标签，可选叠加财务因子。"""
    df = pd.read_csv(os.path.join(DATA, f"{code}.csv"))
    feat = build_features(df)
    if with_fin:
        feat = add_financial_factors(feat, code)
    return feat


if __name__ == "__main__":
    # 自检：打印每个标的的样本量与特征维度
    for code in CODES:
        feat = load_symbol(code)
        feat_clean = feat.dropna()
        cols = get_feature_columns(feat_clean)
        tr, va, te = time_split(feat)
        print(f"{code} {NAME[code]:<12} 有效样本={len(feat_clean):>5} "
              f"特征数={len(cols):>3} 划分 train/val/test={len(tr)}/{len(va)}/{len(te)} "
              f"涨占比={feat_clean['y_cls'].mean():.3f}")
