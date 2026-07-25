# -*- coding: utf-8 -*-
"""生成 TASK8 网页版综合报告 index.html（自包含，图片 base64 内嵌）。"""
import os
import base64
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
AI = os.path.dirname(BASE)
FIG = os.path.join(BASE, "figures")
OUT = os.path.join(BASE, "index.html")


def img64(name):
    p = os.path.join(FIG, name)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def P(x, d=1):
    try:
        return f"{float(x)*100:.{d}f}%"
    except Exception:
        return "-"


def F(x, d=2):
    try:
        return f"{float(x):.{d}f}"
    except Exception:
        return "-"


def tbl(headers, rows):
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def build():
    pan = pd.read_csv(os.path.join(BASE, "panorama_summary.csv"), encoding="utf-8-sig")
    etf_m = pd.read_csv(os.path.join(BASE, "etf_metrics.csv"), encoding="utf-8-sig")
    def em(k,c):
        return etf_m[etf_m["方案"]==k][c].iloc[0]
    pan_rows = [[r["策略类别"], r["代表配置"], F(r["夏普"]), P(r["最大回撤"])] for _, r in pan.iterrows()]

    task_rows = [
        ["任务一", "数据引擎搭建", "基础设施", "行情数据获取、K线与收盘价曲线"],
        ["任务二", "技术指标实现", "技术分析", "MACD/RSI/KDJ/BOLL 等指标计算与解读"],
        ["任务三", "双均线策略", "趋势跟随", "金叉死叉信号，8 标的×3 周期回测"],
        ["任务四", "海龟交易法则", "通道突破趋势", "唐奇安通道+ATR 头寸管理，双系统回测"],
        ["任务五", "机器学习算法", "监督学习", "分类+回归多算法建模、评估与对比"],
        ["任务六", "机器学习定制策略", "ML 择时", "概率仓位+双阈值+风控的可回测策略"],
        ["任务七", "实盘推演", "动量/风格轮动", "小市值、银行股轮动、ETF 轮动三策略"],
        ["任务八", "成果总结", "综合分析", "本报告"],
    ]
    pat_rows = [
        ["趋势跟随(双均线)", "任务三", "逻辑简单、大趋势中稳健", "震荡市反复被扫、参数敏感", "单边趋势明确的市场"],
        ["通道突破(海龟)", "任务四", "严格头寸/止损、纪律性强", "单边牛市易踏空、胜率偏低", "有大波段的品种"],
        ["机器学习择时", "任务五、六", "信息利用充分、可控风险", "日频信噪比低、易过拟合", "震荡下跌市控回撤"],
        ["动量/风格轮动", "任务七", "攻守兼备、分散风险", "拐点处动量崩溃、依赖标的池", "多资产、分化明显市场"],
    ]

    adv = [
        ("建议 1", "以动量/风格轮动类策略为核心。 回测证明其风险调整收益最优，应作为未来策略研发与资金配置的重点，而非把主要精力放在收益上限受限的单标的日频择时上。"),
        ("建议 2", "始终以风险调整指标评判策略、警惕“低仓位高夏普”的假象。 评估时应同时考察夏普比率、最大回撤与平均仓位/资金利用率，确保收益是在充分投资下取得的。"),
        ("建议 3", "构建低相关的多策略组合。 将攻守兼备的 ETF 轮动、进攻型小市值、防御型银行股轮动按风险预算组合，利用其在不同市场阶段的互补性平滑收益曲线。"),
        ("建议 4", "搭建“核心—卫星—风控”三层系统并引入总仓位择时。 以趋势/机器学习类大盘信号作为组合级“风险总闸”，在系统性下跌时统一降低敞口；各子策略保留独立止损，定期再平衡。"),
        ("建议 5", "坚持“预测—转化—风控”的机器学习落地范式并严防未来函数。 特征按发布日对齐、训练测试按时间切分、结果次日成交、计入成本，是一切结论可信的前提。"),
        ("建议 6", "把机器学习的应用从日频方向预测转向更高信噪比场景。 优先用于中长周期、横截面排序选股与因子合成，并采用“机器学习选股打分 + 规则策略风控执行”的人机结合模式。"),
    ]
    adv_html = "".join(f'<li><b>{t}：</b>{c}</li>' for t, c in adv)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>量化交易策略开发与实践 · 张哲铭TASK8</title>
<style>
:root{{--red:#c0392b;--green:#27ae60;--blue:#2c6fbf;--ink:#222;--muted:#666;--line:#e2e2e2;--bg:#f7f7f9;--card:#fff;}}
*{{box-sizing:border-box;}}
body{{font-family:"宋体","SimSun","Microsoft YaHei",serif;color:var(--ink);background:var(--bg);line-height:1.5;margin:0;font-size:15px;}}
.wrap{{max-width:900px;margin:0 auto;padding:40px 48px;background:var(--card);box-shadow:0 2px 20px rgba(0,0,0,.06);}}
.cover{{text-align:center;padding:80px 0 60px;border-bottom:3px double var(--red);margin-bottom:32px;}}
.cover h1{{font-size:32px;margin:0 0 10px;}}
.cover .sub{{font-size:18px;font-weight:bold;margin-bottom:50px;}}
.cover .meta{{font-size:15px;color:var(--muted);line-height:2.1;}}
h2{{font-size:20px;border-left:5px solid var(--red);padding-left:12px;margin:30px 0 12px;}}
h3{{font-size:16px;color:var(--blue);margin:18px 0 8px;}}
p{{text-align:justify;text-indent:2em;margin:8px 0;}}
p.noind{{text-indent:0;}}
figure{{margin:18px 0;text-align:center;}}
figure img{{max-width:100%;border:1px solid var(--line);border-radius:6px;}}
figcaption{{font-size:13px;font-weight:bold;color:var(--muted);margin-top:8px;}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;}}
th,td{{border:1px solid var(--line);padding:6px 8px;text-align:center;line-height:1.35;}}
th{{background:#f0f3f8;font-weight:bold;}}
tbody tr:nth-child(even){{background:#fafbfc;}}
.tabcap{{text-align:center;font-size:13px;font-weight:bold;color:var(--muted);margin:-4px 0 16px;}}
.abstract{{background:#fbf5f4;border:1px solid #f0d9d6;border-radius:8px;padding:16px 20px;margin:18px 0;}}
.toc{{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:20px 28px;margin:20px 0;}}
.toc h2{{border:0;padding:0;text-align:center;margin:0 0 12px;}}
.toc ul{{list-style:none;padding:0;margin:0;}}
.toc li{{display:flex;justify-content:space-between;border-bottom:1px dotted #ccc;padding:5px 0;font-size:14px;}}
.toc li.lv1{{padding-left:2em;color:var(--muted);font-size:13px;}}
.toc li b{{font-weight:bold;}}
ul.adv{{padding-left:1.5em;}} ul.adv li{{margin:8px 0;text-align:justify;}}
.pos{{color:var(--red);font-weight:bold;}} .neg{{color:var(--green);font-weight:bold;}}
.note{{color:var(--muted);font-size:13px;border-top:1px dashed var(--line);padding-top:12px;margin-top:24px;}}
</style></head><body><div class="wrap">

<div class="cover">
<h1>量化交易策略开发与实践</h1>
<p class="sub">——北京大学 AI 量化工作坊学习成果综合报告</p>
<div class="meta">
作　者：张哲铭<br>所属项目：北京大学 AI 量化工作坊<br>
报告主题：八项任务的策略开发、机器学习应用与实盘推演总结<br>完成日期：2026 年 7 月</div>
</div>

<div class="toc">
<h2>目　录</h2>
<ul>
<li><b>摘要</b><span>1</span></li>
<li><b>一、量化交易核心概念</b><span>2</span></li>
<li class="lv1"><span>1.1 什么是量化交易</span><span>2</span></li>
<li class="lv1"><span>1.2 量化交易的核心价值</span><span>2</span></li>
<li><b>二、量化交易策略综合分析</b><span>3</span></li>
<li class="lv1"><span>2.1 八项任务与策略全景</span><span>3</span></li>
<li class="lv1"><span>2.2 各类策略的优缺点与适用场景</span><span>4</span></li>
<li class="lv1"><span>2.3 跨策略风险调整绩效对比</span><span>5</span></li>
<li class="lv1"><span>2.4 重点策略深度剖析：ETF 双重动量轮动</span><span>5</span></li>
<li class="lv1"><span>2.5 策略间的关联性与互补性</span><span>8</span></li>
<li class="lv1"><span>2.6 多策略量化交易系统的构建思路</span><span>8</span></li>
<li><b>三、机器学习在量化交易中的应用总结</b><span>9</span></li>
<li class="lv1"><span>3.1 数据预处理与特征工程</span><span>9</span></li>
<li class="lv1"><span>3.2 模型选择、训练与评估优化</span><span>9</span></li>
<li class="lv1"><span>3.3 机器学习的优势、局限与未来趋势</span><span>10</span></li>
<li><b>四、结论与展望</b><span>11</span></li>
<li><b>附录：改进建议</b><span>12</span></li>
</ul></div>

<h2>摘要</h2>
<div class="abstract"><p class="noind">本报告系统总结了本人在北京大学 AI 量化工作坊八项任务中的学习成果与实践经验。研究目的是打通
“数据—指标—策略—机器学习—实盘—总结”的量化交易完整链条，并回答核心问题：在真实 A 股市场（2018–2026 年、跨越多轮牛熊）中，
哪一类策略能以可控风险获得稳健超额收益。方法上依次搭建数据引擎、实现技术指标，回测双均线、海龟等趋势跟随策略，
构建基于机器学习的预测与择时策略，并在聚宽平台与本地对小市值、银行股轮动、ETF 双重动量轮动三策略完成设计、优化与跨牛熊对比；
全流程统一采用“信号次日成交、计单边万5成本、无未来函数”的严谨口径。主要成果是：以夏普比率与最大回撤为跨标的可比标准，
<span class="pos">ETF 双重动量轮动以夏普 1.13、最大回撤 −21.3% 居各类策略之首</span>，且通过“调仓降频”实现了收益、夏普、回撤、成本的四重改善；
银行股轮动与小市值策略加入风控后分别成为“低回撤防御”与“稳健进攻”代表。结论是：量化交易的核心竞争力不在预测的“准”，而在风险管理的“稳”；
机器学习在日频低信噪比场景下绝对收益贡献有限，其价值更多体现在震荡下跌市的择时与控回撤。报告最后就多策略组合、因子升级、执行优化提出改进建议（见附录）。</p></div>

<h2>一、量化交易核心概念</h2>
<h3>1.1 什么是量化交易</h3>
<p>量化交易是指借助数学模型、统计方法与计算机程序，将交易理念转化为明确、可执行、可回测的规则，并据此系统性做出买卖决策的交易方式。
它与传统手工交易的根本区别在于“纪律化”与“可验证”：交易规则事先用代码固化，决策由数据与模型驱动，而非临场情绪与主观判断。
一套完整量化系统通常包含数据引擎、因子与信号、策略逻辑、回测框架与风控执行五个环节——恰好对应本工作坊八项任务的递进主线：
任务一搭建数据引擎、任务二实现技术指标、任务三四实现并回测经典策略、任务五六引入机器学习、任务七完成平台实盘推演、任务八进行综合总结。</p>
<h3>1.2 量化交易的核心价值</h3>
<p>综合八项任务的实践，本人将量化交易的核心价值归纳为四点：其一是<b>纪律性</b>——把规则写进程序，克服贪婪与恐惧；
其二是<b>可回测与可验证</b>——任何想法都能用夏普比率、最大回撤等客观指标量化检验；其三是<b>系统性与规模化</b>——一套程序可同时监控大量标的、
执行复杂的多因子与轮动逻辑；其四是<b>风险的可度量与可控制</b>——把“亏多少”变成可事先设定的参数。这四点中体会最深的是最后一点：
贯穿八项任务的最重要结论是，量化的核心竞争力不是把涨跌“预测得多准”，而是把风险“管理得多稳”。</p>

<h2>二、量化交易策略综合分析</h2>
<h3>2.1 八项任务与策略全景</h3>
<p>八项任务由浅入深覆盖了量化交易主要策略范式。先以表 1 概览各任务核心内容与策略类别，再逐类展开。</p>
{tbl(["任务","主题","策略/方法类别","核心产出"], task_rows)}
<p class="tabcap">表 1　八项任务与策略全景一览</p>
<h3>2.2 各类策略的优缺点与适用场景</h3>
<p>基于回测实证，本人将所涉策略归为四大范式，其优缺点与适用场景对比见表 2。</p>
{tbl(["策略范式","代表任务","优点","缺点","适用场景"], pat_rows)}
<p class="tabcap">表 2　四大策略范式的优缺点与适用场景对比</p>
<p>从表 2 可见，趋势跟随与通道突破属于“单标的择时”，共同短板是单边上涨中因降仓而踏空，价值主要在控回撤。机器学习择时在日频方向预测上
信噪比极低（受试者工作特征曲线下面积仅约 0.5–0.6），策略常以极低仓位运行、绝对收益有限，但下跌市能有效规避损失。相比之下，
动量与风格轮动通过在多标的间“选强汰弱”，在合理风险下取得了最好的风险调整收益，是本工作坊综合表现最优的一类。据此提出<b>改进建议 1</b>（见附录）。</p>
<h3>2.3 跨策略风险调整绩效对比</h3>
<p>由于各任务标的与区间不同，直接比较绝对收益不公平。本报告改用夏普比率与最大回撤两个跨标的可比的风险调整指标横向对比，结果如图 1 与表 3。</p>
<figure><img src="{img64('panorama.png')}"><figcaption>图 1　各类策略的风险调整绩效对比（A 夏普比率；B 最大回撤）</figcaption></figure>
{tbl(["策略类别","代表配置","夏普比率","最大回撤"], pan_rows)}
<p class="tabcap">表 3　各类策略代表性配置的夏普比率与最大回撤</p>
<p>解读需一处关键说明：机器学习择时夏普名义最高（约 1.70）、回撤极小（约 −2.3%），但这是因其平均仓位极低、大量时间空仓，波动与回撤自然被压小，
代价是绝对收益也非常微薄——属于“看起来很稳、实则赚得很少”。真正在充分投资下取得高夏普的是 <span class="pos">ETF 双重动量轮动（夏普 1.13、回撤 −21.3%）</span>，含金量最高。
银行股轮动（夏普 0.54、回撤仅 −20.5%）以最小回撤成为“防御担当”；小市值（夏普 0.40）经风控后回撤压至 −22.6%、各阶段均正。作为对照，被动买入持有沪深300 夏普仅 0.27、
回撤高达 <span class="neg">−45.6%</span>，全面弱于主动策略。可见优秀的策略设计确实创造价值，据此提出<b>改进建议 2</b>（见附录）。</p>
<h3>2.4 重点策略深度剖析：ETF 双重动量轮动</h3>
<p>鉴于 ETF 双重动量轮动是本工作坊综合表现最优的策略，本节对其做多维度图表化剖析。图 2 为资产曲线对比，改进版 v1.1（双周调仓）以
总收益 <span class="pos">{P(em("v1.1双周","总收益"))}</span>、年化 {P(em("v1.1双周","年化"))} 显著跑赢 v1.0（周度）、等权持有与沪深300。</p>
<figure><img src="{img64('etf_A_equity.png')}"><figcaption>图 2　ETF 轮动策略资产曲线对比（策略 vs 基准）</figcaption></figure>
<p>图 3 的回撤曲线显示，v1.1 最大回撤仅 <span class="pos">{P(em("v1.1双周","最大回撤"))}</span>，明显浅于 v1.0 与等权持有，风险控制更优。</p>
<figure><img src="{img64('etf_B_drawdown.png')}"><figcaption>图 3　ETF 轮动策略回撤曲线（风险特征）</figcaption></figure>
<p>图 4 的月度收益热力图（红涨绿跌）展示收益的时间分布：正收益月份（红）明显多于负收益月份（绿），收益来源在时间上较分散、并非依赖个别月份。</p>
<figure><img src="{img64('etf_C_monthly_heatmap.png')}"><figcaption>图 4　ETF 轮动 v1.1 月度收益热力图（时间分布）</figcaption></figure>
<p>图 5 的日收益分布直方图显示，v1.1 收益分布相对沪深300 更向右偏移（日均为正）、尖峰特征明显，在控制单日波动的同时积累正向收益。</p>
<figure><img src="{img64('etf_D_return_hist.png')}"><figcaption>图 5　ETF 轮动 v1.1 日收益分布直方图（收益特征）</figcaption></figure>
<p>图 6 的滚动 1 年夏普比率考察稳定性：v1.1 滚动夏普多数时间位于零轴以上、频繁高于 1，稳定性优于等权持有，说明超额并非来自某段行情的偶然。</p>
<figure><img src="{img64('etf_E_rolling_sharpe.png')}"><figcaption>图 6　ETF 轮动 v1.1 滚动 1 年夏普比率（稳定性）</figcaption></figure>
<p>图 7 的月度持仓轮动图直观呈现“信号验证”：策略在宽基、行业与黄金等大类间动态切换——下跌与震荡期黄金（避险）权重上升，上涨期向创业板、券商等高弹性板块倾斜，轮动逻辑符合预期。</p>
<figure><img src="{img64('etf_F_holdings.png')}"><figcaption>图 7　ETF 轮动 v1.1 月度持仓轮动图（选中标的与权重，信号验证）</figcaption></figure>
<h3>2.5 策略间的关联性与互补性</h3>
<p>各类策略并非孤立，而在“进攻—均衡—防御”谱系上相互补位，这正是构建组合的基础。任务七三策略构成天然互补三角，其跨牛熊表现对比如图 8。</p>
<figure><img src="{img64('task7_compare.png')}"><figcaption>图 8　三类主力策略的跨牛熊表现对比（净值、回撤、分阶段收益与风险-收益散点）</figcaption></figure>
<p>由图 8 可见：ETF 轮动攻守兼备、牛市与反弹中弹性最强；小市值进攻性强、需风控约束；银行股轮动依托高股息低波、回撤最小，在成长风格失效时提供保护。
它们在不同阶段此消彼长——2024Q4 以来成长反弹中 ETF 轮动大幅领先而银行股轮动落后；但 2022–2024 熊市里银行股轮动逆势为正、成为压舱石。
趋势跟随与机器学习择时类则可作为“风险开关”，在系统性下跌中降低敞口。这种低相关、能互补的特性是组合成更稳健系统的前提，据此提出<b>改进建议 3</b>。</p>
<h3>2.6 多策略量化交易系统的构建思路</h3>
<p>综合上述分析，本人提出分层的多策略系统思路：第一层“<b>核心配置层</b>”以攻守兼备的 ETF 双重动量轮动为主力；第二层“<b>卫星增强层</b>”配以进攻型小市值与
防御型银行股轮动，通过风格分散平滑收益；第三层“<b>风险控制层</b>”用趋势/机器学习类大盘择时作为“总闸”，系统性风险来临时统一降仓。三层按风险预算分配资金、
定期再平衡，各子策略独立止损。这一“核心—卫星—风控”框架把单一策略的脆弱性分散到有机整体，是本人未来实盘的核心蓝图，落地要点见<b>改进建议 3、4</b>。</p>

<h2>三、机器学习在量化交易中的应用总结</h2>
<p>任务五与六系统实践了机器学习应用，本章按“数据预处理—特征工程—模型选择训练—评估优化”流程总结要点与教训。</p>
<h3>3.1 数据预处理与特征工程</h3>
<p>数据预处理的核心是“干净、对齐、无未来函数”，三条关键经验：其一，价格必须用前复权，否则除权除息造成跳空、污染收益；
其二，财务等低频数据必须按“信息发布日”而非“报告期”对齐到日频（任务五对个股财务因子即按发布日前向对齐），否则用到未公开信息、回测虚高；
其三，训练集与测试集必须严格按时间切分、绝不打乱。特征工程方面，任务五构造约 38 个技术因子，涵盖动量/趋势、波动率、量价、经典技术指标与价格位置等，
个股再叠加财务因子，均遵循“有经济含义、无未来函数、稳定可计算”的原则。</p>
<h3>3.2 模型选择、训练与评估优化</h3>
<p>任务五对比了逻辑回归、决策树、随机森林、支持向量机、梯度提升树及 XGBoost、LightGBM 等十余种算法，用时间序列交叉验证网格调参，以准确率、精确率、
召回率、受试者工作特征曲线下面积等评估分类，以均方根误差、方向命中率等评估回归。核心发现有二：一是<b>树集成类模型综合最优</b>，与国际权威研究一致；
二是<b>日频方向预测信噪比极低</b>，最优模型曲线下面积仅约 0.5–0.6、回归拟合优度近零，从根本上限制收益上限。任务六进一步把“上涨概率”通过“双阈值降换手、
概率加权仓位、技术过滤、止损止盈”转化为可回测策略并逐标的寻优。这一“预测—转化—风控”流程是机器学习落地的关键，据此提出<b>改进建议 5</b>（见附录）。</p>
<h3>3.3 机器学习的优势、局限与未来趋势</h3>
<p>机器学习优势在于处理高维非线性信息、以连续概率支持精细仓位管理；局限则突出：过拟合风险高、依赖数据信噪比、存在未来函数隐患、可解释性差且面临结构漂移。
故任务六中机器学习策略绝对收益普遍不高、多在单边牛市跑输买入持有，唯有在下跌市显著跑赢——印证“机器学习择时价值主要在震荡下跌市控回撤，而非单边牛市增强收益”。
展望未来趋势：转向更长周期与截面排序（信噪比更高）、引入另类数据、用深度学习做因子合成、以及“机器学习选股打分 + 规则策略风控执行”的人机结合。基于低信噪比现实，提出<b>改进建议 6</b>。</p>

<h2>四、结论与展望</h2>
<p>回顾八项任务，本人在三层面收获颇丰。<b>认知层面</b>：建立了对量化交易完整链条的系统理解，深刻体会“风险管理的稳比预测的准更重要”。
<b>技术层面</b>：掌握了从数据引擎、技术指标、经典策略回测，到机器学习建模、策略优化与平台实盘推演的全套技能，养成“次日成交、计成本、无未来函数”的严谨习惯。
<b>实践层面</b>：通过跨牛熊亲手回测与对比，积累了“适度降频可同时改善收益与风险”“冗余择时反而侵蚀超额收益”“高相关板块控系统性风险比板块内选股更重要”等反直觉却极具价值的结论。</p>
<p>展望未来，进一步探索方向有三：一是落地附录所列多策略组合系统、用真实资金做小规模实盘验证；二是升级因子体系，引入基本面景气度、资金流与另类数据，
尝试深度学习因子合成；三是完善执行与风控细节，包括交易与冲击成本精细建模、动态风险预算与组合再平衡。量化交易是一条“持续迭代、敬畏市场”的长路，
本次工作坊为本人打下坚实的方法论与实践基础。</p>

<h2>附录：改进建议</h2>
<p class="noind">以下改进建议根据正文分析与推断得出，逐项编号，正文相应位置已按编号引用。</p>
<ul class="adv">{adv_html}</ul>

<p class="note">注：本报告为量化学习实践总结，所用为历史数据回测，不构成任何投资建议；市场有风险，决策需谨慎。　|　作者：张哲铭 · 北京大学 AI 量化工作坊 TASK8</p>

</div></body></html>"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    return OUT


if __name__ == "__main__":
    build()
