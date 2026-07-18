# -*- coding: utf-8 -*-
"""
TASK6 策略回测主程序 run_backtest.py
====================================
流程：
  1. 复用 TASK5 的特征工程，对每个标的重新在“测试集时间段”上，用 TASK5 里
     表现最好的若干算法（Top3，按 AUC）产出样本外上涨概率；
  2. 对每个 (标的×算法) 做参数网格搜索，寻找最优 (buy_th, sell_th, max_pos,
     stop_loss, take_profit)，目标函数=测试集夏普（可改）；
  3. 用最优参数回测，输出核心指标、季度收益、四张核心图；
  4. 对比不同算法（决策树/随机森林/GBDT/XGBoost 等）的策略效果；
  5. 汇总所有结果到 CSV。

四张核心图（每个标的-最优算法）：
  图A 价格走势 + 预测概率（双轴，标注买卖点）——回答“何时交易”
  图B 资产曲线：策略 vs 买入持有——回答“赚了多少”
  图C 回撤曲线（标注最大回撤）——回答“最大亏了多少”
  图D 持仓比例变化曲线——回答“仓位怎么变”
作者：张哲铭
"""
import os
import sys
import json
import warnings
import pickle
import itertools
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 复用 TASK5 的特征工程与模型定义
TASK5 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TASK5")
sys.path.insert(0, TASK5)
import features as F  # noqa
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import roc_auc_score

import strategy as ST

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
os.makedirs(FIG, exist_ok=True)

C_UP, C_DOWN, C_STRAT, C_BH = "#c0392b", "#27ae60", "#c0392b", "#7f8c8d"

# TASK6 用于对比的算法（可解释+集成，覆盖作业要求的决策树/随机森林等）
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False

RANDOM = 42


def candidate_models():
    m = {
        "Logistic回归": (LogisticRegression(max_iter=2000, class_weight="balanced"),
                       {"C": [0.1, 1.0]}),
        "决策树": (DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM),
                {"max_depth": [3, 4], "min_samples_leaf": [20, 50]}),
        "随机森林": (RandomForestClassifier(class_weight="balanced", random_state=RANDOM, n_jobs=-1),
                 {"n_estimators": [300], "max_depth": [4, 6], "min_samples_leaf": [20, 50]}),
        "GBDT": (GradientBoostingClassifier(random_state=RANDOM),
                 {"n_estimators": [200], "max_depth": [2, 3], "learning_rate": [0.05]}),
    }
    if HAS_XGB:
        m["XGBoost"] = (XGBClassifier(random_state=RANDOM, n_jobs=-1, eval_metric="logloss"),
                        {"n_estimators": [300], "max_depth": [3], "learning_rate": [0.05]})
    return m


def get_oos_proba(code, model, grid):
    """在 train+val 上网格搜索训练，产出测试集样本外概率与回测所需序列。"""
    feat = F.load_symbol(code)
    tr, va, te = F.time_split(feat)
    cols = F.get_feature_columns(feat.dropna())
    trva = pd.concat([tr, va]).reset_index(drop=True)
    scaler = StandardScaler().fit(trva[cols].values)
    Xtr = scaler.transform(trva[cols].values)
    Xte = scaler.transform(te[cols].values)
    tscv = TimeSeriesSplit(n_splits=4)
    if grid:
        gs = GridSearchCV(model, grid, cv=tscv, scoring="roc_auc", n_jobs=-1)
        gs.fit(Xtr, trva["y_cls"].values)
        est = gs.best_estimator_
    else:
        est = model.fit(Xtr, trva["y_cls"].values)
    proba = est.predict_proba(Xte)[:, 1]
    try:
        auc = roc_auc_score(te["y_cls"].values, proba)
    except Exception:
        auc = np.nan
    bt = ST.build_backtest_frame(te["date"].values, te["close"].values, proba)
    return bt, auc


# ---- 参数网格（缩小范围以控制计算量，符合作业“可先缩小范围”的建议）----
GRID = {
    "buy_th": [0.55, 0.60, 0.65],
    "sell_th": [0.45, 0.50],
    "max_pos": [0.8, 1.0],
    "stop_loss": [0.05, 0.08],
    "take_profit": [0.15, 0.25],
}


def grid_search_params(bt):
    """在参数网格上搜索最优参数，目标=夏普比率。返回最优参数与其指标。"""
    best, best_metrics, best_score = None, None, -1e9
    keys = list(GRID.keys())
    for combo in itertools.product(*[GRID[k] for k in keys]):
        params = dict(zip(keys, combo))
        if params["sell_th"] >= params["buy_th"]:
            continue
        _, m = ST.run_strategy(bt, **params)
        score = m["sharpe"] if not np.isnan(m["sharpe"]) else -1e9
        # 轻微偏好正超额，避免只追高夏普却跑输持有
        score += 0.5 * (m["excess_total"] if not np.isnan(m["excess_total"]) else 0)
        if score > best_score:
            best_score, best, best_metrics = score, params, m
    return best, best_metrics


def plot_four(code, algo, bt_df, mdd_val):
    """绘制四张核心图到一张 2x2 大图。"""
    name = F.NAME[code]
    d = bt_df["date"]
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))

    # 图A：价格 + 概率（双轴）+ 买卖点
    axA = axes[0, 0]
    axA.plot(d, bt_df["close"], color="#2c3e50", linewidth=1.2, label="收盘价")
    axA2 = axA.twinx()
    axA2.plot(d, bt_df["proba"], color="#8e44ad", linewidth=0.8, alpha=0.5,
              label="上涨概率")
    axA2.set_ylabel("模型上涨概率", color="#8e44ad")
    axA2.set_ylim(0, 1)
    # 买卖点：仓位从0变正=买入；从正变0=卖出
    pos = bt_df["pos"].values
    buys = (pos[1:] > 0) & (pos[:-1] == 0)
    sells = (pos[1:] == 0) & (pos[:-1] > 0)
    idx = np.arange(1, len(pos))
    axA.scatter(d.iloc[idx[buys]], bt_df["close"].iloc[idx[buys]],
                marker="^", color=C_UP, s=45, zorder=5, label="买入")
    axA.scatter(d.iloc[idx[sells]], bt_df["close"].iloc[idx[sells]],
                marker="v", color=C_DOWN, s=45, zorder=5, label="卖出")
    axA.set_title(f"A. {name} 价格走势与预测概率（标注买卖点）")
    axA.set_ylabel("价格"); axA.legend(loc="upper left", fontsize=8)

    # 图B：资产曲线 策略 vs 买入持有
    axB = axes[0, 1]
    axB.plot(d, bt_df["strat_equity"], color=C_STRAT, linewidth=1.6, label="ML策略")
    axB.plot(d, bt_df["bh_equity"], color=C_BH, linewidth=1.4,
             linestyle="--", label="买入持有")
    axB.set_title(f"B. {name} 资产净值曲线（策略 vs 买入持有）")
    axB.set_ylabel("净值(初始=1)"); axB.legend(loc="upper left", fontsize=9)
    axB.grid(alpha=0.3)

    # 图C：回撤曲线 + 最大回撤标注
    axC = axes[1, 0]
    axC.fill_between(d, bt_df["drawdown"] * 100, 0, color=C_DOWN, alpha=0.35)
    axC.plot(d, bt_df["drawdown"] * 100, color=C_DOWN, linewidth=1)
    mdd_i = bt_df["drawdown"].idxmin()
    axC.scatter(d.iloc[mdd_i], bt_df["drawdown"].iloc[mdd_i] * 100,
                color="black", zorder=5)
    axC.annotate(f"最大回撤 {mdd_val*100:.1f}%",
                 xy=(d.iloc[mdd_i], bt_df["drawdown"].iloc[mdd_i] * 100),
                 xytext=(0.4, 0.2), textcoords="axes fraction",
                 arrowprops=dict(arrowstyle="->", color="black"), fontsize=10)
    axC.set_title(f"C. {name} 策略回撤曲线")
    axC.set_ylabel("回撤 (%)"); axC.grid(alpha=0.3)

    # 图D：持仓比例变化
    axD = axes[1, 1]
    axD.fill_between(d, bt_df["pos"] * 100, 0, color="#2980b9", alpha=0.45)
    axD.plot(d, bt_df["pos"] * 100, color="#2980b9", linewidth=0.8)
    axD.set_title(f"D. {name} 持仓比例变化")
    axD.set_ylabel("仓位 (%)"); axD.set_ylim(0, 105); axD.grid(alpha=0.3)

    fig.suptitle(f"{name}（{code}）ML策略回测四图 · 最优算法：{algo}", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(os.path.join(FIG, f"strat4_{code}.png"), dpi=125)
    plt.close()


def plot_algo_compare(all_rows):
    """每标的不同算法策略的总收益/夏普对比。"""
    df = pd.DataFrame(all_rows)
    codes = df["code"].unique()
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    for ax, code in zip(axes.flat, codes):
        sub = df[df["code"] == code]
        x = np.arange(len(sub))
        ax.bar(x, sub["strat_total"] * 100, color="#c0392b", alpha=0.8)
        ax.axhline(sub["bh_total"].iloc[0] * 100, color="#7f8c8d",
                   linestyle="--", linewidth=1.2, label="买入持有")
        ax.set_xticks(x); ax.set_xticklabels(sub["algo"], rotation=40, fontsize=7)
        ax.set_title(f"{F.NAME[code]}", fontsize=10)
        ax.set_ylabel("总收益 %", fontsize=8)
        ax.legend(fontsize=7)
    fig.suptitle("各标的不同机器学习算法策略总收益对比（虚线=买入持有）", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(os.path.join(FIG, "algo_compare.png"), dpi=120)
    plt.close()


def main():
    # 读取 TASK5 分类指标，为每标的选 Top3 算法
    clf_metrics = pd.read_csv(os.path.join(TASK5, "data", "clf_metrics.csv"))
    cand = candidate_models()

    all_rows, best_per_code = [], {}
    quarterly_store = {}
    for code in F.CODES:
        name = F.NAME[code]
        # 该标的按 AUC 排序的算法，取候选集内的 Top3
        sub = clf_metrics[clf_metrics["code"] == code].sort_values("auc", ascending=False)
        top_algos = [a for a in sub["model"].tolist() if a in cand][:3]
        if not top_algos:
            top_algos = list(cand.keys())[:3]
        print(f"\n===== {code} {name} | Top算法: {top_algos} =====")

        code_best = None
        for algo in top_algos:
            model, grid = cand[algo]
            bt, auc = get_oos_proba(code, model, grid)
            best_params, m = grid_search_params(bt)
            bt_df, m2 = ST.run_strategy(bt, **best_params)
            row = {"code": code, "name": name, "algo": algo, "auc": auc,
                   **best_params, **m2}
            all_rows.append(row)
            print(f"  {algo:<10} AUC={auc:.3f} 策略总收益={m2['strat_total']*100:6.1f}% "
                  f"持有={m2['bh_total']*100:6.1f}% 夏普={m2['sharpe']:.2f} "
                  f"MDD={m2['mdd']*100:.1f}% 交易={m2['trades']}")
            # 选该标的综合最好的算法（夏普优先）做四图
            score = m2["sharpe"] + 0.5 * m2["excess_total"]
            if code_best is None or score > code_best[0]:
                code_best = (score, algo, bt_df, m2, best_params)

        # 该标的最优算法 -> 四图 + 季度收益
        _, algo, bt_df, m2, bp = code_best
        plot_four(code, algo, bt_df, m2["mdd"])
        q = ST.quarterly_returns(bt_df)
        q["code"] = code
        quarterly_store[code] = q
        best_per_code[code] = {"algo": algo, "params": bp, **m2}

    # 汇总保存
    pd.DataFrame(all_rows).to_csv(os.path.join(DATA, "strategy_results.csv"),
                                  index=False, encoding="utf-8-sig")
    bp_df = pd.DataFrame([{"code": k, "name": F.NAME[k], **v}
                          for k, v in best_per_code.items()])
    bp_df.to_csv(os.path.join(DATA, "best_strategy.csv"),
                 index=False, encoding="utf-8-sig")
    pd.concat(quarterly_store.values()).to_csv(
        os.path.join(DATA, "quarterly_returns.csv"),
        index=False, encoding="utf-8-sig")
    plot_algo_compare(all_rows)

    print("\n=== 各标的最优策略汇总 ===")
    show = bp_df[["name", "algo", "strat_total", "bh_total", "excess_total",
                  "sharpe", "mdd", "trades", "win_rate"]].copy()
    for c in ["strat_total", "bh_total", "excess_total", "mdd", "win_rate"]:
        show[c] = (show[c] * 100).round(1)
    show["sharpe"] = show["sharpe"].round(2)
    print(show.to_string(index=False))
    print("\nTASK6 回测完成，结果存 data/，图存 figures/")


if __name__ == "__main__":
    main()
