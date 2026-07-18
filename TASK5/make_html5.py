# -*- coding: utf-8 -*-
"""
生成 TASK5 网页版报告 index.html（图表 base64 内嵌，单文件可分发）。
内容与 PDF 对齐：算法解释、评价指标、文献、数据与特征工程、EDA、
建模与评估、乳腺癌对照、结论。A股审美红涨绿跌。
作者：张哲铭
"""
import os
import base64
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
DATA = os.path.join(BASE, "data")
HTML = os.path.join(BASE, "index.html")

NAME = {
    "sh600900": "长江电力", "hk00700": "腾讯控股", "sh518880": "黄金ETF",
    "sh515450": "红利低波50ETF", "sz159941": "纳指ETF", "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF", "sh510500": "中证500ETF",
}
CODES = list(NAME.keys())


def img(name):
    p = os.path.join(FIG, name)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def pct(x, d=1):
    try:
        return f"{float(x)*100:.{d}f}%"
    except Exception:
        return "-"


def fig_block(name, cap):
    src = img(name)
    if not src:
        return ""
    return f'<figure><img src="{src}"><figcaption>{cap}</figcaption></figure>'


def main():
    clf = pd.read_csv(os.path.join(DATA, "clf_metrics.csv"))
    reg = pd.read_csv(os.path.join(DATA, "reg_metrics.csv"))
    cancer = pd.read_csv(os.path.join(DATA, "cancer_metrics.csv"))
    eda = pd.read_csv(os.path.join(DATA, "eda_summary.csv"))

    # 分类模型平均指标表
    g = clf.groupby("model")[["accuracy", "precision", "recall", "f1", "auc"]].mean().sort_values("auc", ascending=False)
    clf_rows = ""
    for m, r in g.iterrows():
        clf_rows += (f"<tr><td>{m}</td><td>{pct(r['accuracy'])}</td><td>{pct(r['precision'])}</td>"
                     f"<td>{pct(r['recall'])}</td><td>{pct(r['f1'])}</td>"
                     f"<td class='hl'>{r['auc']:.3f}</td></tr>")

    gr = reg.groupby("model")[["rmse", "mae", "r2", "dir_acc"]].mean().sort_values("dir_acc", ascending=False)
    reg_rows = ""
    for m, r in gr.iterrows():
        reg_rows += (f"<tr><td>{m}</td><td>{r['rmse']:.4f}</td><td>{r['mae']:.4f}</td>"
                     f"<td>{r['r2']:.4f}</td><td class='hl'>{pct(r['dir_acc'])}</td></tr>")

    # 逐标的最优
    best_rows = ""
    for code in CODES:
        sub = clf[clf["code"] == code].sort_values("auc", ascending=False)
        if len(sub) == 0:
            continue
        b = sub.iloc[0]
        best_rows += (f"<tr><td>{NAME[code]}</td><td>{b['model']}</td><td class='hl'>{b['auc']:.3f}</td>"
                      f"<td>{pct(b['accuracy'])}</td><td>{pct(b['precision'])}</td>"
                      f"<td>{pct(b['recall'])}</td><td>{pct(b['f1'])}</td></tr>")

    # 划分表
    split_rows = ""
    for _, r in eda.iterrows():
        n = int(r["n"])
        split_rows += (f"<tr><td>{NAME.get(r['code'], r['code'])}</td><td>{n}</td>"
                       f"<td>{int(n*0.6)}</td><td>{int(n*0.2)}</td><td>{n-int(n*0.6)-int(n*0.2)}</td>"
                       f"<td>{int(r['n_feat'])}</td><td>{pct(r['up_ratio'])}</td></tr>")

    cancer_rows = ""
    for _, r in cancer.iterrows():
        cancer_rows += (f"<tr><td>{r['model']}</td><td>{pct(r['accuracy'])}</td><td>{pct(r['precision'])}</td>"
                        f"<td>{pct(r['recall'])}</td><td>{pct(r['f1'])}</td><td class='hl'>{r['auc']:.3f}</td></tr>")

    # 各标的 EDA + ROC 图廊
    gallery = ""
    for code in CODES:
        gallery += f"<h4>{NAME[code]}（{code}）</h4><div class='grid'>"
        gallery += fig_block(f"eda_target_{code}.png", f"图 目标变量分布")
        gallery += fig_block(f"eda_topcorr_{code}.png", f"图 Top15 相关特征")
        gallery += fig_block(f"eda_corrmat_{code}.png", f"图 特征相关性矩阵")
        gallery += fig_block(f"eda_box_{code}.png", f"图 关键特征分组箱线图")
        gallery += fig_block(f"roc_{code}.png", f"图 各分类模型 ROC 曲线")
        gallery += fig_block(f"cm_{code}.png", f"图 最优模型混淆矩阵")
        gallery += "</div>"

    best_clf_model = g.index[0]
    best_clf_auc = g.iloc[0]["auc"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 交易引擎：机器学习算法与场景应用 · 张哲铭 TASK5</title>
<style>
:root {{ --red:#c0392b; --green:#1e8449; --blue:#2874a6; --purple:#8e44ad;
  --ink:#222; --muted:#666; --line:#e4e4e4; }}
* {{ box-sizing:border-box; }}
body {{ font-family:"Songti SC","宋体",SimSun,serif; color:var(--ink); line-height:1.9;
  max-width:1040px; margin:0 auto; padding:36px 24px 80px; background:#fafafa; text-align:justify; }}
h1 {{ text-align:center; font-size:26px; border-bottom:3px solid var(--red); padding-bottom:14px; }}
h2 {{ font-size:20px; border-left:5px solid var(--red); padding-left:12px; margin-top:38px; }}
h3 {{ font-size:16px; color:var(--blue); margin-top:26px; }}
h4 {{ font-size:15px; color:var(--purple); margin-top:22px; }}
.sub {{ text-align:center; color:var(--muted); margin-bottom:8px; }}
p {{ text-indent:2em; }}
table {{ border-collapse:collapse; width:100%; margin:16px 0; font-size:13.5px; background:#fff; }}
th,td {{ border:1px solid var(--line); padding:7px 9px; text-align:center; }}
th {{ background:#f2f4f7; }}
.hl {{ color:var(--red); font-weight:bold; }}
figure {{ margin:16px 0; text-align:center; }}
figure img {{ max-width:100%; border:1px solid var(--line); border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
figcaption {{ font-size:12.5px; color:var(--muted); margin-top:6px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.grid figure {{ margin:6px 0; }}
.formula {{ text-align:center; font-style:italic; color:#444; margin:8px 0; font-family:"Cambria Math",serif; }}
.note {{ background:#fff8e1; border-left:4px solid #f39c12; padding:10px 16px; margin:16px 0; font-size:13.5px; text-indent:0; }}
code {{ background:#f0f0f0; padding:1px 5px; border-radius:3px; }}
@media(max-width:720px){{ .grid{{grid-template-columns:1fr;}} }}
</style></head><body>

<h1>AI 交易引擎：机器学习算法与场景应用</h1>
<p class="sub">北京大学 AI 量化工作坊 · TASK5 　|　 姓名：张哲铭</p>

<p>本报告系统学习分类型机器学习算法及其在量化交易中的应用：讲清逻辑回归、决策树、随机森林、KNN 等基础算法与
SVM、GBDT/XGBoost/LightGBM 等文献验证的重要算法，解释混淆矩阵/准确率/精确率/召回率/F1/ROC/AUC 等评价指标，
综述量化领域机器学习的重要成果，并在 8 个代表性标的近八年前复权日线上做完整的 Python 实证——时间序列划分、
无未来函数的特征工程、网格搜索调优、分类与回归两套评估指标对比，配合乳腺癌数据集作高信噪比对照，为 TASK6
的策略构建奠定基础。</p>

<h2>一、分类型机器学习算法解释</h2>
<h3>1. 逻辑回归</h3>
<p>对特征线性加权后经 Sigmoid 映射为 (0,1) 概率，以 0.5 为默认阈值判类。优点：简单、快、可解释性强、天然输出概率；
缺点：只能刻画线性关系、对共线性敏感，需正则化。</p>
<h3>2. 决策树</h3>
<p>按“最大不纯度下降”递归二分特征空间。优点：可解释、天然处理非线性与交互、对量纲/共线性不敏感；缺点：单树高方差、
易过拟合，需剪枝控深度。</p>
<h3>3. 随机森林</h3>
<p>决策树的 Bagging 集成，样本与特征双重随机、多树投票，大幅降低方差。优点：精度高且稳健、抗过拟合、给出特征重要性、
对共线性/噪声不敏感；缺点：可解释性弱于单树、体积大。Gu-Kelly-Xiu(2020) 证实树模型显著优于线性方法。</p>
<h3>4. K 近邻（KNN）</h3>
<p>惰性学习，预测时按最近 K 个样本投票。优点：直观、能刻画任意局部边界；缺点：预测慢、对尺度极敏感、高维“维度灾难”。</p>
<h3>5. 支持向量机（SVM）</h3>
<p>寻找最大间隔超平面，核函数（RBF）处理非线性。优点：中小样本/高维/非线性表现好、泛化强；缺点：大样本与概率估计慢、
调参敏感、可解释性差。</p>
<h3>6. 梯度提升树（GBDT / XGBoost / LightGBM）</h3>
<p>Boosting 思想，串行拟合残差逐步纠错。XGBoost 加二阶梯度与正则更稳更快，LightGBM 用直方图与叶子优先生长进一步提速。
优点：精度通常最高、自动捕捉交互、内置正则；缺点：串行慢、超参多、更易过拟合噪声。Krauss et al.(2017) 证实其在统计
套利中的价值。</p>

<h2>二、机器学习模型评价指标解释</h2>
<h3>1. 混淆矩阵</h3>
<p>按“真实×预测”交叉汇总为 TP/TN/FP/FN 四格，是所有分类指标的基础。FP=误报，FN=漏报。</p>
<table><tr><th></th><th>预测：涨(1)</th><th>预测：不涨(0)</th></tr>
<tr><td>实际：涨(1)</td><td>TP 真正例</td><td>FN 假负例(漏报)</td></tr>
<tr><td>实际：不涨(0)</td><td>FP 假正例(误报)</td><td>TN 真负例</td></tr></table>
<h3>2. 准确率 / 精确率 / 召回率 / F1</h3>
<p class="formula">Accuracy=(TP+TN)/总数　Precision=TP/(TP+FP)　Recall=TP/(TP+FN)　F1=2·P·R/(P+R)</p>
<p>准确率在类别不平衡时会失真；精确率=出手命中率、召回率=机会捕获率，二者此消彼长；F1 为二者调和平均，是不平衡下
的综合指标。交易中往往更看重精确率（宁缺毋滥），这一取舍将在 TASK6 双阈值策略中利用。</p>
<h3>3. ROC 曲线与 AUC</h3>
<p>ROC 以 FPR 为横轴、TPR(召回率) 为纵轴，遍历所有阈值描点，越靠左上越好。AUC=曲线下面积，含义为“随机取一正一负样本、
模型给正样本打分更高的概率”，0.5=随机、1=完美，不依赖阈值且对不平衡不敏感，是本文比较模型的首选指标。金融日频预测
AUC 通常仅略高于 0.5。</p>

<h2>三、重要文献与行业成果综述</h2>
<p>（1）<b>Gu, Kelly &amp; Xiu (2020)</b>《Empirical Asset Pricing via Machine Learning》(Review of Financial Studies
33(5):2223-2273)：在约 3 万只美股、900 变量上做算法赛马，发现树模型与神经网络显著优于线性方法，优势源于非线性交互，
主导信号为动量/流动性/波动率，神经网络多空组合样本外夏普&gt;1.8。</p>
<p>（2）<b>Krauss, Do &amp; Huck (2017)</b>《Deep neural networks, gradient-boosted trees, random forests: Statistical
arbitrage on the S&amp;P 500》(EJOR)：三类模型的集成在标普 500 上扣费后仍获显著统计套利收益。</p>
<p>（3）<b>系统综述</b>(IJFS 2023, 11(3):94 等)：标准 ML 流水线为“加载→预处理/特征选择→划分→训练→评估→调优”，
回归用 RMSE/MAE/R²、分类用 Accuracy/Precision/Recall/F1(+ROC/AUC)，常用 RF/XGBoost/SVM/LSTM，集成/混合最佳。</p>
<p>（4）<b>中文行业成果</b>：逻辑回归为易解释基线；SVM 擅长小样本/非线性/转折识别；随机森林在高维金融数据/特征交互
上表现最佳；XGBoost/LightGBM 在因子挖掘与选股中应用最广。与英文文献互为印证。</p>
<div class="note">结论：本文算法谱系（逻辑回归/决策树/随机森林/KNN + SVM/GBDT/AdaBoost/XGBoost/LightGBM）
既覆盖教学要求，又贴合行业前沿。</div>

<h2>四、数据、特征工程与时间序列划分</h2>
<p>沿用工作坊统一数据：8 标的前复权日线（约 2018–2026、多数近 2000 日），覆盖个股与宽基/主题 ETF，风格互补。对个股
（长江电力、腾讯）额外补充季度财务因子（EPS/营收/净利/ROE 等），按财务<b>发布日</b>前向对齐到日频，杜绝未来函数；
ETF 无财报，仅用量价技术因子。</p>
<p>共构造技术因子约 38 个（个股叠加财务后约 43 个）：动量、均线偏离、波动率、量价、经典指标(RSI/MACD/KDJ/BOLL)、
价格位置六大类。工程四纪律：<b>相关性</b>（选与短期收益有经济学关联的因子）、<b>无未来函数</b>（滚动窗口只用历史、
标签定义在未来、财务按发布日对齐）、<b>稳定性</b>（无量纲比率/对数收益/标准化乖离）、<b>可计算性</b>（仅由 OHLCV+财报可复现）。</p>
<p><b>标签</b>：分类 y_cls=下期收益≥0 记 1（不跌），回归 y_reg=下期收益率。用“≥0”是因纳指/红利低波等 ETF 有大量平盘日
（占比达 40%），避免标签失衡。<b>划分</b>：按时间顺序切 60% 训练/20% 验证/20% 测试，绝不打乱；网格搜索用 TimeSeriesSplit
前向扩窗；标准化只在训练集 fit；测试集全程隔离。</p>
<table><tr><th>标的</th><th>有效样本</th><th>训练</th><th>验证</th><th>测试</th><th>特征数</th><th>上涨占比</th></tr>
{split_rows}</table>
<p class="sub">表 4-1　各标的样本量、时间序列划分与类别分布</p>

<h2>五、探索性数据分析与特征诊断</h2>
<p>建模前对每个标的做完整 EDA：目标分布、特征-目标相关性排序、特征相关性矩阵、多重共线性诊断、关键特征分组箱线图。
关键发现：短期收益<b>信噪比极低</b>（单特征|相关系数|普遍&lt;0.2），且存在<b>严重多重共线性</b>（每标的 15–22 对 |r|&gt;0.9，
KDJ/MACD/均线成组共线）。处理方式：主力用树集成（对共线性不敏感）、线性模型加 L2 正则、解释时对成组特征合并解读。
下方图廊给出全部 8 标的的诊断图。</p>
<div style="background:#fff;padding:14px;border:1px solid var(--line);border-radius:8px;">{gallery}</div>

<h2>六、模型构建、网格调优与评估</h2>
<h3>1. 分类模型评估指标对比（8 标的平均，按 AUC 降序）</h3>
<table><tr><th>分类算法</th><th>准确率</th><th>精确率</th><th>召回率</th><th>F1</th><th>AUC(均)</th></tr>
{clf_rows}</table>
<p>各模型平均 AUC 集中在 0.5 略偏上，相对最好的是 <b>{best_clf_model}</b>（均 AUC≈{best_clf_auc:.3f}）。这诚实反映了金融日频
方向预测的极高难度，但微弱而稳定的 edge 经仓位与风控放大仍可能转化为策略收益——这是 TASK6 要检验的。</p>
{fig_block("model_compare.png", "图 6-1 分类模型平均 AUC/F1（左）与回归模型平均方向命中率（右）")}
<h3>2. 回归模型评估指标对比（按方向命中率降序）</h3>
<table><tr><th>回归算法</th><th>RMSE(均)</th><th>MAE(均)</th><th>R²(均)</th><th>方向命中(均)</th></tr>
{reg_rows}</table>
<p>回归 R² 普遍接近 0 甚至微负（对收益率数值几乎无解释力），但方向命中率稳定在 50% 附近略高。说明“预测涨幅”几乎不可能、
“预测方向”尚存微弱可用信息——这正是 TASK6 用“分类概率+阈值”而非“回归数值”驱动策略的根本原因。</p>
<h3>3. 各标的最优分类模型</h3>
<table><tr><th>标的</th><th>最优模型</th><th>AUC</th><th>准确率</th><th>精确率</th><th>召回率</th><th>F1</th></tr>
{best_rows}</table>
<p>不同标的最优算法各异（KNN/LightGBM/Logistic/决策树/SVM/XGBoost），说明没有“万能模型”，需因标的而异。</p>

<h2>七、乳腺癌数据集分类示例（高信噪比对照）</h2>
<p>用 sklearn 威斯康星乳腺癌数据集（569 样本、30 特征、二分类）做标准分类流水线，作为高信噪比对照：</p>
<table><tr><th>算法</th><th>准确率</th><th>精确率</th><th>召回率</th><th>F1</th><th>AUC</th></tr>
{cancer_rows}</table>
{fig_block("cancer_demo.png", "图 7-1 乳腺癌：随机森林混淆矩阵（左）与各模型 ROC 曲线（右）")}
<div class="note">乳腺癌 AUC 高达 0.94–0.998，而同样算法用于股票日频涨跌 AUC 仅略高于 0.5。这一反差说明：机器学习并非
“点石成金”，<b>模型上限首先由数据本身的可预测性决定</b>。金融市场的高效率与强噪声，要求在策略层用严格风控与仓位管理把
“微弱 edge”转化为“稳健收益”。</div>

<h2>八、结论与对 TASK6 的衔接</h2>
<p>1. <b>算法</b>：树集成（随机森林、GBDT/XGBoost/LightGBM）综合最稳，与文献一致；基础算法作基线，可解释但预测力有限。</p>
<p>2. <b>数据</b>：日频方向预测信噪比极低（AUC 0.5–0.61、回归 R²≈0），单特征相关性&lt;0.2、多重共线性严重，宜以树模型为主、
以 AUC/F1 为主评估。</p>
<p>3. <b>工程</b>：严格时间序列划分、无未来函数特征工程、财务因子按发布日对齐，是结果可信的前提。</p>
<p>4. <b>衔接 TASK6</b>：采用分类模型输出的“上涨概率”，配合双阈值、概率加权仓位、技术过滤与止损止盈，把微弱 edge 转化为
可回测的交易策略，并系统对比不同算法与参数。</p>
<p style="text-indent:0;color:#999;font-size:12px;margin-top:30px;">注：本文为量化学习实践，不构成投资建议；市场有风险，决策需谨慎。</p>
</body></html>"""

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {HTML}  大小={os.path.getsize(HTML)//1024} KB")


if __name__ == "__main__":
    main()
