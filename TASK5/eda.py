# -*- coding: utf-8 -*-
"""
TASK5 探索性数据分析（EDA）与特征诊断 eda.py
==========================================
按作业要求，为每个标的输出：
  1. 目标变量分布：分类=下期涨跌次数分布(柱)；回归=下期涨跌幅度分布(直方)
  2. 所有特征(X)与目标(Y)的描述性统计（导出 CSV）
  3. 所有 X 对 Y 的相关性，按|相关系数|从大到小排序（导出 CSV + 图）
  4. 特征相关性矩阵热力图
  5. 与目标变量最相关的 Top15 特征（条形图）
  6. 关键特征按目标分组的箱线图
  7. 多重共线性诊断：VIF + 高相关特征对（>0.9），并说明处理方式
产物统一存入 figures/ 与 data/。
作者：张哲铭
"""
import os
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import features as F

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
os.makedirs(FIG, exist_ok=True)

# 涨=红 跌=绿（A股/中国习惯）
C_UP, C_DOWN = "#c0392b", "#27ae60"
C_MAIN, C_ACC = "#2c3e50", "#2980b9"


def variance_inflation(X):
    """计算 VIF（用线性回归 R^2 反推，避免额外依赖）。"""
    from sklearn.linear_model import LinearRegression
    vifs = {}
    cols = X.columns.tolist()
    Xv = X.values
    for i, col in enumerate(cols):
        y = Xv[:, i]
        Xo = np.delete(Xv, i, axis=1)
        try:
            r2 = LinearRegression().fit(Xo, y).score(Xo, y)
            vifs[col] = 1.0 / max(1e-6, (1.0 - r2))
        except Exception:
            vifs[col] = np.nan
    return pd.Series(vifs).sort_values(ascending=False)


def eda_one(code):
    feat = F.load_symbol(code).dropna().reset_index(drop=True)
    cols = F.get_feature_columns(feat)
    name = F.NAME[code]
    X = feat[cols]
    y_reg = feat["y_reg"]
    y_cls = feat["y_cls"]

    # ---------- 图1：目标变量分布（分类次数 + 回归幅度） ----------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    vc = y_cls.value_counts().sort_index()
    axes[0].bar(["下跌/平盘(0)", "上涨(1)"], [vc.get(0, 0), vc.get(1, 0)],
                color=[C_DOWN, C_UP], edgecolor="black", alpha=0.85)
    for i, v in enumerate([vc.get(0, 0), vc.get(1, 0)]):
        axes[0].text(i, v, str(int(v)), ha="center", va="bottom", fontsize=10)
    axes[0].set_title(f"{name} 下期涨跌次数分布（分类目标）")
    axes[0].set_ylabel("交易日数")

    axes[1].hist(y_reg * 100, bins=60, color=C_ACC, alpha=0.8, edgecolor="white")
    axes[1].axvline(0, color=C_UP, linestyle="--", linewidth=1.2)
    axes[1].set_title(f"{name} 下期收益率分布（回归目标）")
    axes[1].set_xlabel("下一交易日收益率 (%)")
    axes[1].set_ylabel("频数")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"eda_target_{code}.png"), dpi=130)
    plt.close()

    # ---------- 描述性统计（X + Y） ----------
    desc = X.describe().T
    desc["skew"] = X.skew()
    desc["kurt"] = X.kurt()
    desc.to_csv(os.path.join(DATA, f"desc_stats_{code}.csv"),
                encoding="utf-8-sig")

    # ---------- X 对 Y 相关性排序（对回归目标） ----------
    corr_reg = X.apply(lambda s: s.corr(y_reg)).sort_values(
        key=lambda s: s.abs(), ascending=False)
    corr_cls = X.apply(lambda s: s.corr(y_cls))
    corr_tbl = pd.DataFrame({"corr_with_yreg": corr_reg,
                             "corr_with_ycls": corr_cls.reindex(corr_reg.index)})
    corr_tbl.to_csv(os.path.join(DATA, f"corr_rank_{code}.csv"),
                    encoding="utf-8-sig")

    # ---------- 图2：Top15 相关特征条形图 ----------
    top = corr_reg.head(15)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    colors = [C_UP if v > 0 else C_DOWN for v in top.values]
    ax.barh(range(len(top)), top.values, color=colors, alpha=0.85,
            edgecolor="black")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top.index, fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title(f"{name} 与下期收益率相关性 Top15 特征")
    ax.set_xlabel("Pearson 相关系数")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"eda_topcorr_{code}.png"), dpi=130)
    plt.close()

    # ---------- 图3：特征相关性矩阵热力图（取 Top20 相关特征以便可读） ----------
    top_feats = corr_reg.head(20).index.tolist()
    cmat = X[top_feats].corr()
    fig, ax = plt.subplots(figsize=(9.5, 8))
    im = ax.imshow(cmat.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(top_feats)))
    ax.set_yticks(range(len(top_feats)))
    ax.set_xticklabels(top_feats, rotation=90, fontsize=7)
    ax.set_yticklabels(top_feats, fontsize=7)
    ax.set_title(f"{name} 特征相关性矩阵（Top20 相关特征）")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"eda_corrmat_{code}.png"), dpi=130)
    plt.close()

    # ---------- 图4：关键特征按目标分组箱线图 ----------
    key_feats = corr_reg.head(6).index.tolist()
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, ff in zip(axes.flat, key_feats):
        d0 = X.loc[y_cls == 0, ff].dropna()
        d1 = X.loc[y_cls == 1, ff].dropna()
        bp = ax.boxplot([d0, d1], labels=["跌/平", "涨"], patch_artist=True,
                        showfliers=False, widths=0.6)
        bp["boxes"][0].set_facecolor(C_DOWN)
        bp["boxes"][1].set_facecolor(C_UP)
        for b in bp["boxes"]:
            b.set_alpha(0.7)
        ax.set_title(ff, fontsize=10)
    fig.suptitle(f"{name} 关键特征按下期涨跌分组的箱线图", fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"eda_box_{code}.png"), dpi=130)
    plt.close()

    # ---------- 多重共线性：VIF + 高相关对 ----------
    vif = variance_inflation(X.fillna(0))
    vif.to_csv(os.path.join(DATA, f"vif_{code}.csv"), encoding="utf-8-sig",
               header=["VIF"])
    # 高相关特征对（|r|>0.9）
    full_corr = X.corr().abs()
    pairs = []
    cc = full_corr.columns.tolist()
    for i in range(len(cc)):
        for j in range(i + 1, len(cc)):
            r = full_corr.iloc[i, j]
            if r > 0.9:
                pairs.append((cc[i], cc[j], round(r, 3)))
    high_corr = pd.DataFrame(pairs, columns=["feat_a", "feat_b", "abs_corr"])
    high_corr.to_csv(os.path.join(DATA, f"highcorr_pairs_{code}.csv"),
                     index=False, encoding="utf-8-sig")

    return {
        "code": code, "name": name, "n": len(feat), "n_feat": len(cols),
        "up_ratio": float(y_cls.mean()),
        "ret_mean": float(y_reg.mean()), "ret_std": float(y_reg.std()),
        "top_feat": corr_reg.index[0], "top_corr": float(corr_reg.iloc[0]),
        "max_vif": float(vif.iloc[0]), "max_vif_feat": vif.index[0],
        "n_highcorr_pairs": len(pairs),
    }


def main():
    rows = []
    for code in F.CODES:
        print(f"[EDA] {code} {F.NAME[code]} ...")
        rows.append(eda_one(code))
    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(DATA, "eda_summary.csv"),
                   index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))
    print("EDA 完成，图表已存入 figures/")


if __name__ == "__main__":
    main()
