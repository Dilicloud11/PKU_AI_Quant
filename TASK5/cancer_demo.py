# -*- coding: utf-8 -*-
"""
TASK5 乳腺癌二分类教学示例 cancer_demo.py
=======================================
用 scikit-learn 自带的威斯康星乳腺癌数据集（569 样本、30 特征、二分类：
恶性 0 / 良性 1），演示一条标准的分类机器学习流水线：
  加载数据 -> 训练/测试划分 -> 标准化 -> 训练多模型(逻辑回归/决策树/随机森林/KNN)
  -> 计算混淆矩阵/准确率/精确率/召回率/F1 -> 计算 AUC -> 画 ROC 曲线。
该示例与股票数据部分互为对照：癌症数据信噪比高、可分性强（AUC 常>0.98），
而股票数据信噪比极低（AUC 常在 0.5~0.6），直观说明“同样的算法，
数据可预测性决定了模型上限”。
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

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, roc_curve, confusion_matrix)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
os.makedirs(FIG, exist_ok=True)


def main():
    ds = load_breast_cancer()
    X, y = ds.data, ds.target   # y: 0=恶性 malignant, 1=良性 benign
    print(f"乳腺癌数据集：{X.shape[0]} 样本, {X.shape[1]} 特征, "
          f"正类(良性)占比={y.mean():.3f}")

    # 此处为独立同分布静态数据集，可随机划分（分层抽样保持类别比例）
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = scaler.transform(Xtr), scaler.transform(Xte)

    models = {
        "逻辑回归": LogisticRegression(max_iter=5000),
        "决策树": DecisionTreeClassifier(max_depth=4, random_state=42),
        "随机森林": RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
        "KNN": KNeighborsClassifier(n_neighbors=7),
    }

    rows, roc_data = [], {}
    for name, model in models.items():
        model.fit(Xtr_s, ytr)
        proba = model.predict_proba(Xte_s)[:, 1]
        pred = (proba >= 0.5).astype(int)
        acc = accuracy_score(yte, pred)
        prec = precision_score(yte, pred)
        rec = recall_score(yte, pred)
        f1 = f1_score(yte, pred)
        auc = roc_auc_score(yte, proba)
        cm = confusion_matrix(yte, pred)
        fpr, tpr, _ = roc_curve(yte, proba)
        roc_data[name] = (fpr, tpr, auc)
        rows.append({"model": name, "accuracy": acc, "precision": prec,
                     "recall": rec, "f1": f1, "auc": auc,
                     "cm_tn": cm[0, 0], "cm_fp": cm[0, 1],
                     "cm_fn": cm[1, 0], "cm_tp": cm[1, 1]})
        print(f"  {name:<8} Acc={acc:.3f} Prec={prec:.3f} Rec={rec:.3f} "
              f"F1={f1:.3f} AUC={auc:.3f}")

    metrics = pd.DataFrame(rows)
    metrics.to_csv(os.path.join(DATA, "cancer_metrics.csv"),
                   index=False, encoding="utf-8-sig")

    # ---- 图：随机森林混淆矩阵 + 全模型 ROC ----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    rf_row = metrics[metrics["model"] == "随机森林"].iloc[0]
    cm = np.array([[rf_row["cm_tn"], rf_row["cm_fp"]],
                   [rf_row["cm_fn"], rf_row["cm_tp"]]])
    im = axes[0].imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            axes[0].text(j, i, str(int(cm[i, j])), ha="center", va="center",
                         fontsize=16)
    axes[0].set_xticks([0, 1]); axes[0].set_yticks([0, 1])
    axes[0].set_xticklabels(["预测恶性", "预测良性"])
    axes[0].set_yticklabels(["实际恶性", "实际良性"])
    axes[0].set_title("随机森林 混淆矩阵（乳腺癌）")
    fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)

    for name, (fpr, tpr, auc) in roc_data.items():
        axes[1].plot(fpr, tpr, linewidth=1.8, label=f"{name} (AUC={auc:.3f})")
    axes[1].plot([0, 1], [0, 1], "k--", linewidth=1, label="随机 (0.5)")
    axes[1].set_xlabel("假正率 FPR"); axes[1].set_ylabel("真正率 TPR")
    axes[1].set_title("各模型 ROC 曲线（乳腺癌）")
    axes[1].legend(loc="lower right", fontsize=9); axes[1].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "cancer_demo.png"), dpi=140)
    plt.close()
    print("乳腺癌示例完成 -> figures/cancer_demo.png, data/cancer_metrics.csv")


if __name__ == "__main__":
    main()
