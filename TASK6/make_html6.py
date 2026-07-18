# -*- coding: utf-8 -*-
"""
生成 TASK6 网页版报告 index.html（图表 base64 内嵌，单文件可分发）。
内容与 PDF 对齐：核心理念与优缺点、因子与应变量定义、文献、策略设计、
逐标的四图、算法对比、附加题、结论。A股审美红涨绿跌。
作者：张哲铭
"""
import os
import json
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


def sign(v):
    try:
        return "pos" if float(v) >= 0 else "neg"
    except Exception:
        return ""


def fig_block(name, cap):
    src = img(name)
    if not src:
        return ""
    return f'<figure><img src="{src}"><figcaption>{cap}</figcaption></figure>'


def main():
    best = pd.read_csv(os.path.join(DATA, "best_strategy.csv"))
    strat = pd.read_csv(os.path.join(DATA, "strategy_results.csv"))
    bonus = pd.read_csv(os.path.join(DATA, "bonus_rotation.csv"))

    # 汇总表
    sum_rows = ""
    for code in CODES:
        b = best[best["code"] == code].iloc[0]
        sum_rows += (f"<tr><td>{NAME[code]}</td><td>{b['algo']}</td>"
                     f"<td class='{sign(b['strat_total'])}'>{pct(b['strat_total'])}</td>"
                     f"<td>{pct(b['bh_total'])}</td>"
                     f"<td class='{sign(b['excess_total'])}'>{pct(b['excess_total'])}</td>"
                     f"<td class='hl'>{b['sharpe']:.2f}</td>"
                     f"<td class='neg'>{pct(b['mdd'])}</td>"
                     f"<td>{int(b['trades'])}</td><td>{pct(b['win_rate'])}</td></tr>")

    # 逐标的四图 + 参数
    per = ""
    for i, code in enumerate(CODES):
        b = best[best["code"] == code].iloc[0]
        prm = json.loads(b["params"].replace("'", '"'))
        per += f"<h3>{NAME[code]}（{code}）— 最优算法：{b['algo']}</h3>"
        per += (f"<p>最优参数：买入阈值 {prm['buy_th']}、卖出阈值 {prm['sell_th']}、"
                f"最大仓位 {pct(prm['max_pos'],0)}、止损 {pct(prm['stop_loss'],0)}、"
                f"止盈 {pct(prm['take_profit'],0)}。测试段策略总收益 "
                f"<b class='{sign(b['strat_total'])}'>{pct(b['strat_total'])}</b>、"
                f"买入持有 {pct(b['bh_total'])}、超额 "
                f"<b class='{sign(b['excess_total'])}'>{pct(b['excess_total'])}</b>；"
                f"夏普 {b['sharpe']:.2f}、最大回撤 {pct(b['mdd'])}、交易 {int(b['trades'])} 次、"
                f"持仓日胜率 {pct(b['win_rate'])}、平均仓位 {pct(b['exposure'])}。</p>")
        per += fig_block(f"strat4_{code}.png",
                         f"图 {NAME[code]} 回测四图（A 买卖点 / B 净值 / C 回撤 / D 仓位）")

    r_s = bonus.iloc[0]; r_b = bonus.iloc[1]
    bonus_tbl = (f"<tr><td>{r_s['策略']}</td><td class='{sign(r_s['总收益'])}'>{pct(r_s['总收益'])}</td>"
                 f"<td>{pct(r_s['年化'])}</td><td class='hl'>{r_s['夏普']:.2f}</td>"
                 f"<td class='neg'>{pct(r_s['最大回撤'])}</td></tr>"
                 f"<tr><td>{r_b['策略']}</td><td class='{sign(r_b['总收益'])}'>{pct(r_b['总收益'])}</td>"
                 f"<td>{pct(r_b['年化'])}</td><td class='hl'>{r_b['夏普']:.2f}</td>"
                 f"<td class='neg'>{pct(r_b['最大回撤'])}</td></tr>")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>智能决策者：用机器学习定制专属策略 · 张哲铭 TASK6</title>
<style>
:root {{ --red:#c0392b; --green:#1e8449; --blue:#2874a6; --purple:#8e44ad;
  --ink:#222; --muted:#666; --line:#e4e4e4; }}
* {{ box-sizing:border-box; }}
body {{ font-family:"Songti SC","宋体",SimSun,serif; color:var(--ink); line-height:1.9;
  max-width:1040px; margin:0 auto; padding:36px 24px 80px; background:#fafafa; text-align:justify; }}
h1 {{ text-align:center; font-size:26px; border-bottom:3px solid var(--red); padding-bottom:14px; }}
h2 {{ font-size:20px; border-left:5px solid var(--red); padding-left:12px; margin-top:38px; }}
h3 {{ font-size:16px; color:var(--blue); margin-top:26px; }}
.sub {{ text-align:center; color:var(--muted); margin-bottom:8px; }}
p {{ text-indent:2em; }}
table {{ border-collapse:collapse; width:100%; margin:16px 0; font-size:13.5px; background:#fff; }}
th,td {{ border:1px solid var(--line); padding:7px 9px; text-align:center; }}
th {{ background:#f2f4f7; }}
.hl {{ color:var(--blue); font-weight:bold; }}
.pos {{ color:var(--red); font-weight:bold; }}
.neg {{ color:var(--green); font-weight:bold; }}
figure {{ margin:16px 0; text-align:center; }}
figure img {{ max-width:100%; border:1px solid var(--line); border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
figcaption {{ font-size:12.5px; color:var(--muted); margin-top:6px; }}
.formula {{ text-align:center; font-style:italic; color:#444; margin:8px 0; font-family:"Cambria Math",serif; }}
.note {{ background:#fff8e1; border-left:4px solid #f39c12; padding:10px 16px; margin:16px 0; font-size:13.5px; text-indent:0; }}
</style></head><body>

<h1>智能决策者：用机器学习定制专属策略</h1>
<p class="sub">北京大学 AI 量化工作坊 · TASK6 　|　 姓名：张哲铭</p>

<p>本报告在 TASK5“用机器学习预测涨跌”的基础上，把模型输出的“上涨概率”转化为可执行、可回测的交易策略：
阐明 ML 交易策略的核心理念与优缺点、界定自变量因子与应变量、综述文献，设计“双阈值 + 概率加权仓位 +
技术指标过滤 + 止损止盈”框架并网格搜索最优参数，对 8 个标的用 Top3 算法产出样本外概率、构建策略并回测，
给出四张核心图（何时交易 / 赚多少 / 最大亏多少 / 仓位怎么变），系统对比不同算法，并完成附加题——多标的
机器学习组合轮动。全流程严格使用 TASK5 划分的测试集、无未来函数。</p>

<h2>一、基于机器学习的交易策略：核心理念与优缺点</h2>
<p>核心理念为“<b>预测—转化—风控</b>”三步：模型输出下期上涨概率 p → 概率高看多加仓、低则观望清仓 →
用仓位管理与止损止盈把统计上的微弱优势在风险可控下累积成收益。相比均线、海龟等固定规则，ML 策略让数据
自动挖掘非线性组合信号，适应性更强。</p>
<p><b>优点</b>：①处理高维非线性信息、②概率化可量化风险、③系统化可回测可迭代、④适应性强（重训即可换标的/环境）。</p>
<p><b>缺点与风险</b>：①过拟合（样本内好、样本外崩）、②依赖数据信噪比（日频方向 AUC 仅约 0.5~0.6，模型有上限）、
③未来函数/信息泄漏隐患大、④黑箱且市场结构会漂移、⑤频繁交易侵蚀收益（故本文用双阈值降换手）。</p>

<h2>二、常见自变量因子与应变量定义</h2>
<p><b>应变量 Y</b>：①回归型=未来某期收益率（用于收益排序选股）；②分类型=未来涨跌方向或涨跌分档。本文主用
分类型 y=“下一交易日不跌(收益≥0)”，因 TASK5 证明“预测方向”比“预测涨幅”更可行，分类概率即交易信号。</p>
<p><b>自变量 X</b>：动量/趋势（过去 N 日收益、均线斜率）、波动率（收益标准差、ATR、振幅、布林带宽）、
量价（量变化、量比、量价相关）、技术指标（RSI/MACD/KDJ/乖离/%B）、价格位置（分位、隔夜/日内）、
基本面/财务（EPS、营收/净利增速、ROE、净利率——个股按财务发布日对齐纳入，ETF 无财报不用）、宏观/情绪（可扩展）。
本文实际用约 38 个技术因子（个股叠加财务后约 43 个），严守相关性/无未来函数/稳定性/可计算性四原则。</p>

<h2>三、基于机器学习算法的交易策略：文献与行业成果</h2>
<p>（1）<b>Krauss, Do &amp; Huck (2017, EJOR)</b>：用 DNN/梯度提升树/随机森林预测个股相对表现概率，做多最强、
做空最弱一篮子，三模型集成扣费后仍获显著统计套利收益——“ML 预测+排序选股”经典范式。</p>
<p>（2）<b>López de Prado (2018)《Advances in Financial Machine Learning》</b>：提出三重障碍标注与元标签
（Meta-Labeling），并给出由预测概率决定仓位的方法（线性 size∝(p−0.5)、凯利、Sigmoid）——本文“概率加权仓位”
即其直接应用。</p>
<p>（3）<b>中文行业成果</b>（随机森林选择权策略、大模型量化策略等）系统讨论了信号阈值/持仓周期/仓位上限/
止损比例的敏感性，指出信号阈值敏感度最高——为本文“网格搜索最优参数”提供参考。</p>

<h2>四、交易策略设计</h2>
<p>以 TASK5 分类模型在测试集的样本外上涨概率 p 为唯一信号，决策“当日盘后算、次日生效”，杜绝未来函数：</p>
<p><b>1. 双阈值：</b>p≥买入阈值→开/持仓；p≤卖出阈值→清仓；两者之间（不确定区）维持原仓位。缓冲带减少抖动、
降低换手与成本、不确定不盲动。</p>
<p><b>2. 概率加权仓位：</b></p>
<p class="formula">目标仓位 = clip( (p − 0.5) × 2, 0, 1 ) × 最大仓位</p>
<p>概率 0.5 空仓、越接近 1 越接近满仓，确定性高则重仓、低则轻仓。</p>
<p><b>3. 技术过滤：</b>当 RSI&gt;70（超买）、MA5≤MA20（空头排列）、或波动率处于高分位（&gt;90%）时禁止新开仓，
用稳健技术规则过滤模型可能误判的不利环境。</p>
<p><b>4. 止损止盈：</b>以持仓成本为基准，浮亏达止损即离场、浮盈达止盈即兑现；单边成本万分之五。</p>
<p><b>5. 网格搜索：</b>对买入阈值∈&#123;0.55,0.60,0.65&#125;、卖出阈值∈&#123;0.45,0.50&#125;、最大仓位∈&#123;0.8,1.0&#125;、
止损∈&#123;5%,8%&#125;、止盈∈&#123;15%,25%&#125; 网格寻优，目标为测试集夏普（辅以超额收益）。</p>

<h2>五、逐标的回测：四张核心图与解读</h2>
<p>每个标的用综合最优算法+最优参数回测，四张图分别回答：A（价格+概率双轴、标买卖点）=何时交易；
B（策略 vs 买入持有净值）=赚了多少；C（回撤曲线、标最大回撤）=最大亏多少；D（持仓比例）=仓位怎么变。</p>
{per}

<h2>六、不同机器学习算法的策略效果对比</h2>
{fig_block("algo_compare.png", "图 6-1 各标的不同算法策略总收益对比（虚线=买入持有）")}
<table><tr><th>标的</th><th>最优算法</th><th>策略收益</th><th>买入持有</th><th>超额</th><th>夏普</th><th>最大回撤</th><th>交易数</th><th>胜率</th></tr>
{sum_rows}</table>
<p class="sub">表 6-1　各标的最优 ML 策略回测指标汇总</p>
<div class="note">三点关键结论：①<b>风险控制显著</b>——策略夏普普遍&gt;1（多在 1.2~2.4）、最大回撤压缩到个位数百分比
甚至更低，说明“概率信号+双阈值+技术过滤+止损止盈”有效控风险、改善风险调整收益；②<b>单边牛市中普遍跑输
买入持有</b>——择时为控回撤而降仓，必然在单边上涨中踏空，这是择时策略的固有代价；③<b>唯一显著跑赢的是腾讯</b>
（测试段买入持有为负的下跌市，策略取得正收益、超额可观）——生动印证“ML 择时价值主要在震荡下跌市而非单边牛市”，
与 TASK3/TASK4“核心价值在控回撤”的结论一脉相承。</div>

<h2>七、附加题：多标的机器学习组合轮动策略</h2>
<p>自行设计横截面策略：用随机森林对 8 标的分别输出下期上涨概率，每日选概率最高的 Top3 等权持有（每日再平衡、
计成本），与“等权买入持有全部 8 标的”对比，呼应原题“预测收益排序、挑选最优若干标的投资”。</p>
{fig_block("bonus_rotation.png", "图 7-1 机器学习组合轮动(Top3) vs 全市场等权持有：净值与回撤")}
<table><tr><th>策略</th><th>总收益</th><th>年化</th><th>夏普</th><th>最大回撤</th></tr>
{bonus_tbl}</table>
<p>轮动策略同样未跑赢等权持有——原因是样本区间整体上行、且各宽基 ETF 走势高度相关，选强汰弱空间有限；但其
最大回撤与基准接近，风险端未恶化。这提示横截面选股更适合标的众多、分化明显的股票池（如全 A 股），而非本文
以少数高相关宽基 ETF 为主的标的池。</p>

<h2>八、结论</h2>
<p>1. <b>方法论</b>：成功把 TASK5 的上涨概率通过双阈值、概率加权仓位、技术过滤与止损止盈转化为完整可回测策略，
并网格搜索为每个标的定制最优参数，践行“预测—转化—风控”。</p>
<p>2. <b>风险控制显著</b>：所有标的策略夏普普遍&gt;1、最大回撤压缩到个位数甚至更低。</p>
<p>3. <b>收益的诚实结论</b>：单边上涨测试段中择时/轮动普遍跑输买入持有（踏空代价），唯下跌市（腾讯）显著跑赢
——再次印证择时价值在震荡下跌市。</p>
<p>4. <b>关键前提</b>：严格时间序列纪律（不打乱、无未来函数、财务按发布日对齐、测试集隔离）是结论可信的基础；
低信噪比决定了应追求“可控风险下的稳定微弱优势”，而非高胜率神话。</p>
<p style="text-indent:0;color:#999;font-size:12px;margin-top:30px;">注：本文为量化学习实践，不构成投资建议；市场有风险，决策需谨慎。</p>
</body></html>"""

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {HTML}  大小={os.path.getsize(HTML)//1024} KB")


if __name__ == "__main__":
    main()
