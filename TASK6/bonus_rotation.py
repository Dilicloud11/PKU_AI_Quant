# -*- coding: utf-8 -*-
"""
TASK6 附加题：多标的机器学习组合轮动策略 bonus_rotation.py
========================================================
自选数据构建模型并设计投资策略（呼应原题“横截面选股”精神）：
  在 8 个标的（长江电力/腾讯/黄金/红利低波/纳指/科创50/沪深300/中证500）中，
  用随机森林对每个标的输出“下期上涨概率”，每个交易日选出概率最高的 Top-K 个
  标的等权持有（择优轮动），与“等权买入持有全部 8 标的”基准对比。

要点：
  * 每个标的独立训练随机森林（时间序列切分，测试段样本外概率）；
  * 取所有标的测试段的公共日期对齐，构成横截面；
  * 每日按概率排序选 Top-K（默认 3），等权配置，换仓计成本；
  * 输出净值对比、回撤、年化/夏普/最大回撤，绘图。
作者：张哲铭
"""
import os
import sys
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TASK5 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TASK5")
sys.path.insert(0, TASK5)
import features as F
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
COST = 0.0005
TOPK = 3


def oos_proba_and_ret(code):
    feat = F.load_symbol(code)
    tr, va, te = F.time_split(feat)
    cols = F.get_feature_columns(feat.dropna())
    trva = pd.concat([tr, va]).reset_index(drop=True)
    scaler = StandardScaler().fit(trva[cols].values)
    model = RandomForestClassifier(n_estimators=300, max_depth=6,
                                   min_samples_leaf=30, class_weight="balanced",
                                   random_state=42, n_jobs=-1)
    model.fit(scaler.transform(trva[cols].values), trva["y_cls"].values)
    proba = model.predict_proba(scaler.transform(te[cols].values))[:, 1]
    out = pd.DataFrame({"date": pd.to_datetime(te["date"].values),
                        f"proba_{code}": proba,
                        f"ret_{code}": te["y_reg"].values})
    return out.set_index("date")


def main():
    # 各标的测试段概率与次日收益，按日期对齐取交集
    frames = [oos_proba_and_ret(code) for code in F.CODES]
    df = pd.concat(frames, axis=1).dropna()
    print(f"横截面对齐后交易日数={len(df)}（各标的测试段公共日期）")

    proba_cols = [f"proba_{c}" for c in F.CODES]
    ret_cols = [f"ret_{c}" for c in F.CODES]
    P = df[proba_cols].values
    R = df[ret_cols].values
    n, k = P.shape

    # 每日选概率 Top-K 等权
    strat_ret = np.zeros(n)
    prev_w = np.zeros(k)
    for i in range(n):
        order = np.argsort(-P[i])         # 概率降序
        w = np.zeros(k)
        w[order[:TOPK]] = 1.0 / TOPK      # Top-K 等权
        turnover = np.sum(np.abs(w - prev_w))
        strat_ret[i] = np.sum(w * R[i]) - turnover * COST
        prev_w = w
    bench_ret = R.mean(axis=1)            # 等权持有全市场

    eq_s = np.cumprod(1 + strat_ret)
    eq_b = np.cumprod(1 + bench_ret)
    dd = eq_s / np.maximum.accumulate(eq_s) - 1

    def stats(r, eq):
        ann = 252
        cagr = eq[-1] ** (ann / len(eq)) - 1
        sharpe = r.mean() / (r.std() + 1e-12) * np.sqrt(ann)
        mdd = (eq / np.maximum.accumulate(eq) - 1).min()
        return cagr, sharpe, mdd

    cs, ss, ms = stats(strat_ret, eq_s)
    cb, sb, mb = stats(bench_ret, eq_b)
    summary = pd.DataFrame([
        {"策略": f"ML组合轮动(Top{TOPK})", "总收益": eq_s[-1]-1, "年化": cs,
         "夏普": ss, "最大回撤": ms},
        {"策略": "等权买入持有(全市场)", "总收益": eq_b[-1]-1, "年化": cb,
         "夏普": sb, "最大回撤": mb},
    ])
    summary.to_csv(os.path.join(DATA, "bonus_rotation.csv"),
                   index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))

    # 绘图
    dts = df.index
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1]})
    axes[0].plot(dts, eq_s, color="#c0392b", linewidth=1.7,
                 label=f"ML组合轮动 Top{TOPK}（年化{cs*100:.1f}% 夏普{ss:.2f}）")
    axes[0].plot(dts, eq_b, color="#7f8c8d", linewidth=1.5, linestyle="--",
                 label=f"等权买入持有（年化{cb*100:.1f}% 夏普{sb:.2f}）")
    axes[0].set_title(f"附加题：机器学习多标的组合轮动 vs 全市场等权持有")
    axes[0].set_ylabel("净值(初始=1)"); axes[0].legend(fontsize=10)
    axes[0].grid(alpha=0.3)
    axes[1].fill_between(dts, dd * 100, 0, color="#27ae60", alpha=0.4)
    axes[1].set_ylabel("轮动策略回撤 %")
    axes[1].annotate(f"最大回撤 {ms*100:.1f}%",
                     xy=(dts[np.argmin(dd)], ms*100),
                     xytext=(0.4, 0.3), textcoords="axes fraction",
                     arrowprops=dict(arrowstyle="->"), fontsize=10)
    axes[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "bonus_rotation.png"), dpi=130)
    plt.close()
    print("附加题完成 -> figures/bonus_rotation.png")


if __name__ == "__main__":
    main()
