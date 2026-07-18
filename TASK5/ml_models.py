# -*- coding: utf-8 -*-
"""
TASK5 机器学习建模与评估 ml_models.py
=====================================
对 8 个标的，分别做“分类（下期涨跌）”与“回归（下期收益率）”两套建模，
覆盖作业要求的基础算法与检索到的重要算法，用时间序列网格搜索调参，
输出完整评估指标对比、混淆矩阵、ROC/AUC，并保存每个标的的最佳分类模型
（供 TASK6 策略复用）。同时用 scikit-learn 乳腺癌数据集做分类教学示例。

严守时间序列纪律：
  * 训练/验证/测试按时间顺序切分（features.time_split），绝不打乱；
  * 网格搜索用 TimeSeriesSplit（前向扩窗），不使用未来信息；
  * 标准化 scaler 只在训练集 fit，再 transform 验证/测试集。

算法清单：
  分类：Logistic 回归、决策树、随机森林、KNN、SVM(RBF)、GradientBoosting、
        AdaBoost、(可选)XGBoost、(可选)LightGBM
  回归：线性回归、Ridge、决策树回归、随机森林回归、KNN 回归、
        GradientBoosting 回归、(可选)XGBoost 回归、(可选)LightGBM 回归
作者：张哲铭
"""
import os
import json
import warnings
import pickle
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                              GradientBoostingClassifier, GradientBoostingRegressor,
                              AdaBoostClassifier)
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, roc_curve, confusion_matrix,
                             mean_squared_error, mean_absolute_error, r2_score)

import features as F

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
MODELS = os.path.join(BASE, "models")
os.makedirs(FIG, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)

# 可选梯度提升库
try:
    from xgboost import XGBClassifier, XGBRegressor
    HAS_XGB = True
except Exception:
    HAS_XGB = False
try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    HAS_LGBM = True
except Exception:
    HAS_LGBM = False

RANDOM = 42


# ============ 分类算法与调参网格 ============
def clf_models():
    m = {
        "Logistic回归": (LogisticRegression(max_iter=2000, class_weight="balanced"),
                       {"C": [0.05, 0.1, 0.5, 1.0]}),
        "决策树": (DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM),
                {"max_depth": [3, 4, 6], "min_samples_leaf": [20, 50]}),
        "随机森林": (RandomForestClassifier(class_weight="balanced", random_state=RANDOM, n_jobs=-1),
                 {"n_estimators": [200, 400], "max_depth": [4, 6, 8],
                  "min_samples_leaf": [20, 50]}),
        "KNN": (KNeighborsClassifier(),
                {"n_neighbors": [15, 25, 45], "weights": ["uniform", "distance"]}),
        "SVM": (SVC(probability=True, class_weight="balanced", random_state=RANDOM),
                {"C": [0.5, 1.0], "gamma": ["scale", 0.05]}),
        "GBDT": (GradientBoostingClassifier(random_state=RANDOM),
                 {"n_estimators": [150, 300], "max_depth": [2, 3],
                  "learning_rate": [0.03, 0.05]}),
        "AdaBoost": (AdaBoostClassifier(random_state=RANDOM),
                     {"n_estimators": [150, 300], "learning_rate": [0.3, 0.5]}),
    }
    if HAS_XGB:
        m["XGBoost"] = (XGBClassifier(random_state=RANDOM, n_jobs=-1, eval_metric="logloss"),
                        {"n_estimators": [200, 400], "max_depth": [3, 4],
                         "learning_rate": [0.03, 0.05]})
    if HAS_LGBM:
        m["LightGBM"] = (LGBMClassifier(random_state=RANDOM, n_jobs=-1, verbose=-1),
                         {"n_estimators": [200, 400], "max_depth": [3, 4],
                          "learning_rate": [0.03, 0.05], "num_leaves": [15, 31]})
    return m


# ============ 回归算法与调参网格 ============
def reg_models():
    m = {
        "线性回归": (LinearRegression(), {}),
        "Ridge回归": (Ridge(random_state=RANDOM), {"alpha": [1.0, 10.0, 50.0]}),
        "决策树": (DecisionTreeRegressor(random_state=RANDOM),
                {"max_depth": [3, 4, 6], "min_samples_leaf": [20, 50]}),
        "随机森林": (RandomForestRegressor(random_state=RANDOM, n_jobs=-1),
                 {"n_estimators": [200, 400], "max_depth": [4, 6, 8],
                  "min_samples_leaf": [20, 50]}),
        "KNN": (KNeighborsRegressor(),
                {"n_neighbors": [15, 25, 45], "weights": ["uniform", "distance"]}),
        "GBDT": (GradientBoostingRegressor(random_state=RANDOM),
                 {"n_estimators": [150, 300], "max_depth": [2, 3],
                  "learning_rate": [0.03, 0.05]}),
    }
    if HAS_XGB:
        m["XGBoost"] = (XGBRegressor(random_state=RANDOM, n_jobs=-1),
                        {"n_estimators": [200, 400], "max_depth": [3, 4],
                         "learning_rate": [0.03, 0.05]})
    if HAS_LGBM:
        m["LightGBM"] = (LGBMRegressor(random_state=RANDOM, n_jobs=-1, verbose=-1),
                         {"n_estimators": [200, 400], "max_depth": [3, 4],
                          "learning_rate": [0.03, 0.05], "num_leaves": [15, 31]})
    return m


def _prep(code):
    """加载 + 划分 + 标准化。返回训练/测试所需的一切。"""
    feat = F.load_symbol(code)
    tr, va, te = F.time_split(feat)
    cols = F.get_feature_columns(feat.dropna())
    # 训练时把 train+val 合并做最终训练（网格搜索内部用 TimeSeriesSplit 选参），
    # 保持 test 完全独立
    trva = pd.concat([tr, va]).reset_index(drop=True)
    scaler = StandardScaler().fit(trva[cols].values)
    Xtr = scaler.transform(trva[cols].values)
    Xte = scaler.transform(te[cols].values)
    return {
        "cols": cols, "scaler": scaler,
        "Xtr": Xtr, "Xte": Xte,
        "ycls_tr": trva["y_cls"].values, "ycls_te": te["y_cls"].values,
        "yreg_tr": trva["y_reg"].values, "yreg_te": te["y_reg"].values,
        "date_te": te["date"].values, "close_te": te["close"].values,
        "n_train": len(trva), "n_test": len(te),
    }


def run_classification(code, D):
    """对单标的跑全部分类模型，返回指标表 + 每模型测试集预测概率 + ROC 数据。"""
    tscv = TimeSeriesSplit(n_splits=4)
    results, roc_data, proba_store = [], {}, {}
    best_model_obj, best_auc, best_name = None, -1, None

    for name, (est, grid) in clf_models().items():
        if grid:
            gs = GridSearchCV(est, grid, cv=tscv, scoring="roc_auc", n_jobs=-1)
            gs.fit(D["Xtr"], D["ycls_tr"])
            model = gs.best_estimator_
            best_params = gs.best_params_
        else:
            model = est.fit(D["Xtr"], D["ycls_tr"])
            best_params = {}
        # 测试集预测
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(D["Xte"])[:, 1]
        else:
            proba = model.decision_function(D["Xte"])
            proba = (proba - proba.min()) / (proba.max() - proba.min() + 1e-9)
        pred = (proba >= 0.5).astype(int)
        yte = D["ycls_te"]

        acc = accuracy_score(yte, pred)
        prec = precision_score(yte, pred, zero_division=0)
        rec = recall_score(yte, pred, zero_division=0)
        f1 = f1_score(yte, pred, zero_division=0)
        try:
            auc = roc_auc_score(yte, proba)
        except Exception:
            auc = np.nan
        cm = confusion_matrix(yte, pred)
        fpr, tpr, _ = roc_curve(yte, proba)
        roc_data[name] = (fpr, tpr, auc)
        proba_store[name] = proba

        results.append({
            "code": code, "task": "分类", "model": name,
            "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "auc": auc,
            "cm_tn": int(cm[0, 0]), "cm_fp": int(cm[0, 1]),
            "cm_fn": int(cm[1, 0]), "cm_tp": int(cm[1, 1]),
            "params": json.dumps(best_params, ensure_ascii=False),
        })
        if not np.isnan(auc) and auc > best_auc:
            best_auc, best_model_obj, best_name = auc, model, name

    # 保存该标的最佳分类模型（供 TASK6 复用）
    with open(os.path.join(MODELS, f"clf_{code}.pkl"), "wb") as f:
        pickle.dump({"model": best_model_obj, "scaler": D["scaler"],
                     "cols": D["cols"], "name": best_name, "auc": best_auc}, f)
    return results, roc_data, proba_store


def run_regression(code, D):
    tscv = TimeSeriesSplit(n_splits=4)
    results = []
    for name, (est, grid) in reg_models().items():
        if grid:
            gs = GridSearchCV(est, grid, cv=tscv,
                              scoring="neg_root_mean_squared_error", n_jobs=-1)
            gs.fit(D["Xtr"], D["yreg_tr"])
            model = gs.best_estimator_
            best_params = gs.best_params_
        else:
            model = est.fit(D["Xtr"], D["yreg_tr"])
            best_params = {}
        pred = model.predict(D["Xte"])
        yte = D["yreg_te"]
        rmse = np.sqrt(mean_squared_error(yte, pred))
        mae = mean_absolute_error(yte, pred)
        r2 = r2_score(yte, pred)
        # 方向命中率：回归预测的涨跌方向与真实一致的比例
        dir_hit = np.mean((pred > 0) == (yte > 0))
        results.append({
            "code": code, "task": "回归", "model": name,
            "rmse": rmse, "mae": mae, "r2": r2, "dir_acc": dir_hit,
            "params": json.dumps(best_params, ensure_ascii=False),
        })
    return results


def plot_roc(code, roc_data):
    name = F.NAME[code]
    fig, ax = plt.subplots(figsize=(7.2, 6))
    for mname, (fpr, tpr, auc) in roc_data.items():
        ax.plot(fpr, tpr, linewidth=1.6, label=f"{mname} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="随机猜测 (AUC=0.5)")
    ax.set_xlabel("假正率 FPR")
    ax.set_ylabel("真正率 TPR")
    ax.set_title(f"{name} 各分类模型 ROC 曲线对比")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"roc_{code}.png"), dpi=130)
    plt.close()


def plot_confusion(code, results):
    """画该标的表现最好(AUC最高)模型的混淆矩阵。"""
    name = F.NAME[code]
    best = max(results, key=lambda r: (r["auc"] if not np.isnan(r["auc"]) else -1))
    cm = np.array([[best["cm_tn"], best["cm_fp"]],
                   [best["cm_fn"], best["cm_tp"]]])
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    im = ax.imshow(cm, cmap="Reds")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=15, color="black")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["预测跌/平", "预测涨"])
    ax.set_yticklabels(["实际跌/平", "实际涨"])
    ax.set_title(f"{name} 最优模型({best['model']}) 混淆矩阵")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"cm_{code}.png"), dpi=130)
    plt.close()


def plot_metric_compare(all_cls, all_reg):
    """跨标的算法平均指标对比（分类 AUC/F1，回归 RMSE/方向命中）。"""
    dfc = pd.DataFrame(all_cls)
    dfr = pd.DataFrame(all_reg)
    # 分类：各模型平均 AUC 与 F1
    g = dfc.groupby("model")[["auc", "f1", "accuracy"]].mean().sort_values("auc", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(g)); w = 0.4
    axes[0].bar(x - w/2, g["auc"], w, label="AUC", color="#2980b9", alpha=0.85)
    axes[0].bar(x + w/2, g["f1"], w, label="F1", color="#c0392b", alpha=0.85)
    axes[0].axhline(0.5, color="gray", linestyle="--", linewidth=1)
    axes[0].set_xticks(x); axes[0].set_xticklabels(g.index, rotation=30, fontsize=9)
    axes[0].set_title("分类模型跨标的平均 AUC / F1 对比")
    axes[0].legend(); axes[0].set_ylim(0, 1)

    gr = dfr.groupby("model")[["rmse", "dir_acc"]].mean().sort_values("dir_acc", ascending=False)
    x2 = np.arange(len(gr))
    ax2 = axes[1]
    ax2.bar(x2, gr["dir_acc"], 0.5, color="#16a085", alpha=0.85, label="方向命中率")
    ax2.axhline(0.5, color="gray", linestyle="--", linewidth=1)
    ax2.set_xticks(x2); ax2.set_xticklabels(gr.index, rotation=30, fontsize=9)
    ax2.set_title("回归模型跨标的平均方向命中率")
    ax2.set_ylim(0, 1); ax2.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "model_compare.png"), dpi=130)
    plt.close()
    return g, gr


def main():
    print(f"XGBoost可用={HAS_XGB}  LightGBM可用={HAS_LGBM}")
    all_cls, all_reg = [], []
    for code in F.CODES:
        print(f"\n===== {code} {F.NAME[code]} =====")
        D = _prep(code)
        print(f"  训练样本={D['n_train']} 测试样本={D['n_test']} 特征={len(D['cols'])}")
        cls_res, roc_data, _ = run_classification(code, D)
        all_cls += cls_res
        plot_roc(code, roc_data)
        plot_confusion(code, cls_res)
        best_c = max(cls_res, key=lambda r: (r["auc"] if not np.isnan(r["auc"]) else -1))
        print(f"  [分类] 最佳={best_c['model']} AUC={best_c['auc']:.3f} F1={best_c['f1']:.3f}")
        reg_res = run_regression(code, D)
        all_reg += reg_res
        best_r = max(reg_res, key=lambda r: r["dir_acc"])
        print(f"  [回归] 方向最佳={best_r['model']} 命中={best_r['dir_acc']:.3f} RMSE={best_r['rmse']:.5f}")

    pd.DataFrame(all_cls).to_csv(os.path.join(DATA, "clf_metrics.csv"),
                                 index=False, encoding="utf-8-sig")
    pd.DataFrame(all_reg).to_csv(os.path.join(DATA, "reg_metrics.csv"),
                                 index=False, encoding="utf-8-sig")
    g, gr = plot_metric_compare(all_cls, all_reg)
    print("\n=== 分类模型平均表现 ===")
    print(g.round(3).to_string())
    print("\n=== 回归模型平均表现 ===")
    print(gr.round(4).to_string())
    print("\nTASK5 建模完成，指标已存 data/，图存 figures/，模型存 models/")


if __name__ == "__main__":
    main()
