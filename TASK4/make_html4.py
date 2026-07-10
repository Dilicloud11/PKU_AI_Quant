# -*- coding: utf-8 -*-
"""
生成 TASK4 网页版报告：index.html
内容与 PDF 一致，响应式排版，图片以 base64 内嵌（单文件可分发）。
A股审美：红涨绿跌。
作者：张哲铭
"""
import os
import base64
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
HTML = os.path.join(BASE, "index.html")

NAME = {
    "sh518880": "黄金ETF", "sz159941": "纳指ETF", "hk00700": "腾讯控股",
    "sh600900": "长江电力", "sh515450": "红利低波50ETF", "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF", "sh510500": "中证500ETF",
}


def pct(x, d=1):
    return f"{x*100:.{d}f}%"


def img(name):
    """把 figures/<name> 读为 base64 data URI。"""
    with open(os.path.join(FIG, name), "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def sign(v):
    return "pos" if v >= 0 else "neg"


def main():
    df = pd.read_csv(os.path.join(BASE, "backtest_results.csv"))
    scan = pd.read_csv(os.path.join(BASE, "param_scan_results.csv"))

    def get(code, s):
        return df[(df["code"] == code) & (df["system"] == s)].iloc[0]

    # 表1：论文标的
    t1 = ""
    for code in ["sh518880", "sz159941"]:
        for s in ["System1", "System2"]:
            r = get(code, s)
            t1 += (f"<tr><td>{NAME[code]}</td>"
                   f"<td>{s}({int(r['entry_n'])}/{int(r['exit_n'])})</td>"
                   f"<td>{pct(r['strat_annual'])}</td><td>{pct(r['bench_annual'])}</td>"
                   f"<td class='{sign(r['excess_annual'])}'>{pct(r['excess_annual'])}</td>"
                   f"<td>{r['sharpe']:.2f}</td>"
                   f"<td class='neg'>{pct(r['mdd'])}</td>"
                   f"<td class='neg'>{pct(r['bench_mdd'])}</td>"
                   f"<td>{pct(r['win_rate'],0)}</td><td>{r['pl_ratio']:.2f}</td></tr>")

    # 表2：8标的 System2
    t2 = ""
    sub = df[df["system"] == "System2"].sort_values("excess_annual", ascending=False)
    for _, r in sub.iterrows():
        t2 += (f"<tr><td>{r['name']}</td><td>{pct(r['strat_annual'])}</td>"
               f"<td>{pct(r['bench_annual'])}</td>"
               f"<td class='{sign(r['excess_annual'])}'>{pct(r['excess_annual'])}</td>"
               f"<td>{r['sharpe']:.2f}</td><td>{r['calmar']:.2f}</td>"
               f"<td class='neg'>{pct(r['mdd'])}</td><td class='neg'>{pct(r['bench_mdd'])}</td>"
               f"<td>{int(r['n_trades'])}</td><td>{pct(r['win_rate'],0)}</td></tr>")

    # 表3：黄金通道扫描
    t3 = ""
    for _, r in scan[scan["code"] == "sh518880"].iterrows():
        t3 += (f"<tr><td>{int(r['entry_n'])}/{int(r['exit_n'])}</td>"
               f"<td>{pct(r['strat_annual'])}</td><td>{r['sharpe']:.2f}</td>"
               f"<td class='neg'>{pct(r['mdd'])}</td><td>{int(r['n_trades'])}</td>"
               f"<td>{pct(r['win_rate'],0)}</td></tr>")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>复刻传奇：海龟交易法则实战演练 · 张哲铭 TASK4</title>
<style>
  :root {{ --red:#c0392b; --green:#1e8449; --blue:#2874a6; --orange:#e67e22;
    --ink:#222; --muted:#666; --line:#e4e4e4; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:"Songti SC","宋体",SimSun,serif; color:var(--ink);
    line-height:1.9; max-width:980px; margin:0 auto; padding:36px 24px 80px;
    background:#fafafa; text-align:justify; }}
  h1 {{ text-align:center; font-size:28px; margin:.2em 0 .1em; }}
  .sub {{ text-align:center; color:var(--muted); margin-bottom:1.6em; font-size:15px; }}
  h2 {{ font-size:21px; border-left:5px solid var(--orange); padding-left:12px;
    margin-top:1.8em; color:#1a1a1a; }}
  h3 {{ font-size:16px; color:#333; margin-top:1.2em; }}
  p {{ font-size:15.5px; text-indent:2em; margin:.5em 0; }}
  ul {{ font-size:15.5px; }}  li {{ margin:.35em 0; }}
  .lead {{ background:#fff; border:1px solid var(--line); border-left:4px solid var(--orange);
    padding:14px 20px; border-radius:8px; text-indent:0; }}
  .formula {{ text-align:center; font-style:italic; color:#111; background:#f4f0ea;
    padding:8px 12px; border-radius:6px; margin:.8em auto; font-size:15px; text-indent:0; }}
  figure {{ margin:1.4em 0; text-align:center; }}
  figure img {{ max-width:100%; border:1px solid var(--line); border-radius:8px;
    box-shadow:0 2px 10px rgba(0,0,0,.06); background:#fff; }}
  figcaption {{ font-size:13px; color:var(--muted); margin-top:.6em; font-weight:bold; }}
  table {{ border-collapse:collapse; width:100%; margin:1em 0; font-size:13px;
    background:#fff; }}
  th,td {{ border:1px solid var(--line); padding:7px 8px; text-align:center; }}
  th {{ background:#f3ede5; font-weight:bold; }}
  tr:nth-child(even) td {{ background:#fbfaf8; }}
  .pos {{ color:var(--red); font-weight:bold; }}
  .neg {{ color:var(--green); font-weight:bold; }}
  pre {{ background:#f6f6f6; border:1px solid var(--line); border-radius:8px;
    padding:14px 16px; overflow-x:auto; font-size:12.5px; line-height:1.55;
    font-family:Consolas,Monaco,monospace; color:#333; text-indent:0; }}
  .note {{ font-size:12.5px; color:#888; margin-top:2em; border-top:1px dashed var(--line);
    padding-top:1em; text-indent:0; }}
  .tag {{ display:inline-block; background:#fdf2e9; color:var(--orange);
    border:1px solid #f5cba7; border-radius:12px; padding:1px 10px; font-size:12px;
    margin:0 3px; }}
</style>
</head>
<body>

<h1>复刻传奇：海龟交易法则实战演练</h1>
<div class="sub">北京大学 AI 量化工作坊 · TASK4　|　姓名：张哲铭　|　
<span class="tag">趋势跟踪</span><span class="tag">唐奇安通道</span>
<span class="tag">ATR 头寸管理</span><span class="tag">8 标的 × 2 系统回测</span></div>

<p class="lead">本任务在前三次工作坊基础上，完整复刻华尔街传奇——海龟交易法则。全文阐明其核心思想与关键优势，
解释高低点通道、ATR 与止损条件三大基石，在回测前先设计策略全流程并绘制流程图，用 Python 手工实现该策略，
检索重要学术文献明确其适用标的，并对黄金 ETF、纳指 ETF、腾讯控股、沪深 300 等 8 个标的、两套海龟系统
（20/10 与 55/20）共 16 组参数做实证回测，用总收益、年化、超额收益、夏普、最大回撤、卡玛、胜率、盈亏比等
一整套指标全面评估，并做通道周期敏感性分析，总结海龟法则的适应场景与使用心得。</p>

<h2>一、海龟交易法则：核心思想与关键优势</h2>
<p>海龟交易法则源于 1983 年美国期货交易大师 Richard Dennis 与合伙人 William Eckhardt 的著名赌约：交易能力是
天赋还是可后天培养？丹尼斯从上千名报名者中挑选一批毫无经验的普通人（戏称“海龟”），用两周教会他们一套完全
机械化的交易系统。此后五年，海龟合计盈利超 1.75 亿美元、顶尖者年化约 80%。海龟法则由此成为金融史上最著名、
被最广泛研究与复现的系统化趋势跟踪策略。</p>
<h3>· 核心思想：机械化的趋势跟踪</h3>
<p>其哲学是“价格沿最小阻力方向运动”——市场一旦形成趋势往往延续。它不预测顶底，只在价格创出一段时间新高
（新趋势确立）时顺势入场、趋势逆转时离场，力求“截断亏损、让利润奔跑”，并把入场、加仓、止损、离场、头寸
规模全部量化为明确规则、要求 100% 机械执行。</p>
<h3>· 关键优势</h3>
<ul>
<li><b>完全机械化、可复制、可回测</b>：每步都有明确数值规则，杜绝情绪化交易，可严格量化检验。</li>
<li><b>以 ATR 为核心的风险管理</b>：用 ATR 动态度量各标的波动，波动大买得少、止损宽，波动小买得多、止损窄，
使每笔交易承担的账户风险大致相等（波动率平价）。</li>
<li><b>金字塔式分批加仓</b>：趋势确认后每涨 0.5 ATR 加 1 单位、最多 4 单位，让盈利头寸在大趋势中放大。</li>
<li><b>严格止损、控制回撤</b>：每单位 2 ATR 硬止损 + 多级持仓上限，在剧烈下跌中往往显著跑赢“死扛”的买入持有。</li>
<li><b>低胜率、高盈亏比的稳健结构</b>：靠少数大趋势盈利覆盖多次小额止损，只要严格执行就能长期为正。</li>
</ul>

<h2>二、核心概念解释：高低点通道、ATR 与止损条件</h2>
<h3>1. 高低点通道（唐奇安通道 Donchian Channel）</h3>
<p>取过去 N 日最高价为上轨、最低价为下轨。收盘价向上突破上轨即做多入场信号；跌破更短周期（N/2 日）下轨即
多头离场。海龟用两套周期：系统一（20 日入场/10 日离场）捕捉中短趋势，系统二（55 日入场/20 日离场）捕捉长期
大趋势。通道呈阶梯状、触发价格完全透明，天然适合机械执行。</p>
<div class="formula">上轨 = max(最近 N 日最高价)，下轨 = min(最近 N 日最低价)</div>
<h3>2. 平均真实波幅（ATR）</h3>
<p>ATR 度量价格平均单日波动，是海龟风险管理的标尺。先算真实波幅 TR（考虑跳空），再取 N 日 Wilder 平滑：</p>
<div class="formula">TR = max( 今高−今低, |今高−昨收|, |今低−昨收| )</div>
<div class="formula">ATR_t = [ ATR_(t−1)×(N−1) + TR_t ] / N，  单位头寸 = 风险资本 /(N × ATR × 价值因子)</div>
<p>含义：波动越大买得越少、越小买得越多，让不同标的每笔交易承担大致相等的风险。</p>
<h3>3. 止损条件与加仓规则</h3>
<p>三条硬规则：（1）<b>止损</b>——每单位入场价下方 2 ATR 处硬止损，把单笔最大亏损锁定在约 2%；
（2）<b>加仓</b>——每涨 0.5 ATR 加 1 单位、最多 4 单位，且每次加仓后止损线同步上移；
（3）<b>离场</b>——跌破离场通道（系统一 10 日 / 系统二 20 日最低）即趋势结束、全部平仓。三者构成
“亏损截断快、盈利放得开”的非对称收益结构。</p>

<h2>三、策略全流程设计（回测前的流程图）</h2>
<p>动手回测前，先把规则串成完整决策链路并绘制流程图（图 1），确保编程实现严格对应逻辑。</p>
<figure><img src="{img('flowchart.png')}" alt="流程图">
<figcaption>图 1　海龟交易策略完整流程图（做多方向）</figcaption></figure>
<p>如图 1，橙色主链路（①→⑤）完成开仓前准备：选定标的、计算 20 日 ATR、算单位头寸、监控突破，突破确认后建
第 1 单位（蓝色⑤）。此后进入循环：判断是否再涨 0.5 ATR（是则加仓，绿色⑥最多 4 单位），否则依次检查是否跌破
止损线（红色，止损离场）、是否跌破离场通道（绿色，止盈离场），都未触发则继续持有、循环监控。</p>

<h2>四、Python 编程实现</h2>
<p>回测引擎完全手工实现（turtle_strategy.py），核心为 ATR/通道计算、逐日状态机、净值与指标计算。考虑 A 股/ETF
现货难做空，本文只做多。为杜绝未来函数，通道取值用 shift(1) 排除当日、且信号次日生效，并计入单边万分之五成本。</p>
<pre>{'''# 1) ATR(Wilder) 与高低点通道
tr = pd.concat([high-low, (high-prev_close).abs(),
                (low-prev_close).abs()], axis=1).max(axis=1)
atr = wilder_smooth(tr, n=20)
dc_upper = high.rolling(entry_n).max().shift(1)   # 入场上轨(N日最高)
dc_exit  = low.rolling(exit_n).min().shift(1)     # 离场下轨(N/2日最低)

# 2) 逐日状态机(只做多)
if units == 0:                       # 空仓：监控突破
    if price > dc_upper[i]:          # 突破上轨 -> 入场1单位
        units=1; entry=price; stop=price-2*atr[i]
else:                                # 持仓：按优先级判定
    if price < stop:                 # (a) 跌破止损线 -> 止损离场
        close_trade("stop"); units=0
    elif price < dc_exit[i]:         # (b) 跌破离场通道 -> 止盈离场
        close_trade("exit"); units=0
    elif units&lt;4 and price&gt;=last_add+0.5*atr:   # (c) 涨0.5ATR -> 加仓
        units+=1; last_add=price; stop=price-2*atr

# 3) 仓位次日生效、扣成本、算净值
position  = (units/4).shift(1)
strat_ret = position*close.pct_change() - position.diff().abs()*0.0005
equity    = (1+strat_ret).cumprod()'''}</pre>
<figure><img src="{img('signal_hk00700.png')}" alt="腾讯信号图">
<figcaption>图 2　腾讯控股（00700）海龟策略交易信号与 ATR（入场20日/离场10日）</figcaption></figure>
<p>如图 2，红虚线为 20 日高点通道（入场上轨）、绿虚线为 10 日低点通道（离场下轨）；红三角=入场、橙十字=加仓、
紫叉=2 ATR 止损、绿倒三角=跌破下轨离场。下图 ATR 显示 2021—2022 腾讯剧烈波动时头寸自动缩小、止损放宽。</p>

<h2>五、文献综述：海龟/趋势跟踪在什么标的上更有效</h2>
<p><b>1. 通道突破的实证根基——BLL (1992, JF)</b>：用道指 1897—1986 年数据严格检验，发现区间突破/均线规则的
买入信号后收益显著更高、波动更小，为“简单突破规则含预测力”提供首个量化证据。</p>
<p><b>2. 主场是大宗商品——Miffre &amp; Rallis (2007, JBF)</b>：31 种商品期货 1979—2004 的趋势策略年均收益 9.38%，
而等权买入持有反而亏损；Moskowitz/Ooi/Pedersen (2012, JFE) 在 58 个跨资产品种证实“时间序列动量”普遍存在。
二者指向：趋势跟踪在黄金等商品、趋势鲜明资产上最有效。</p>
<p><b>3. 海龟规则的直接复现——Swart (2016, 开普敦大学)</b>：以海龟法则为蓝本，用唐奇安通道 + 20 日 ATR 完整
复现系统一/二及整合系统，指出既有文献主要在北美与亚洲的商品期货与股指期货上验证海龟，这两类高流动性、趋势性
资产是其被验证最充分、最有效的标的。</p>
<p><b>4. 有效性会衰减——自适应市场假说</b>：Bessembinder &amp; Chan (1998) 等发现规则预测力 1987 年后减弱，
Lo (2004) 提出“自适应市场假说”——规则一旦被广泛知晓、套利涌入，超额收益就被抢跑而衰减。这提醒：在高效率大盘
宽基指数上海龟越来越难跑赢买入持有。</p>
<p><b>5. 对本文标的选择的启示</b>：本文纳入文献直接指向的黄金 ETF（商品）与纳指 ETF（成长）作验证标的，
同时纳入沪深 300、中证 500 等宽基与长江电力、红利低波等低波动标的作对照。</p>

<h2>六、多标的、多参数实证回测</h2>
<p>对 8 标的分别运行系统一（20/10）与系统二（55/20）共 16 组，ATR 周期 20、止损 2 ATR、加仓 0.5 ATR 最多 4 单位，
每组与买入持有对比。<b>回测指标体系</b>：总收益、年化、超额收益（剥离标的β看策略α）、夏普、最大回撤 MDD、
卡玛（年化/|MDD|）、胜率、盈亏比、交易次数。</p>
<div class="formula">年化=(1+总收益)^(252/天数)−1；夏普=日超额收益均值/标准差×√252；MDD=min(净值/历史最高−1)</div>

<h3>1. 文献验证标的：黄金 ETF 与纳指 ETF</h3>
<table><thead><tr><th>标的</th><th>系统(入场/离场)</th><th>策略年化</th><th>基准年化</th>
<th>超额年化</th><th>夏普</th><th>策略回撤</th><th>基准回撤</th><th>胜率</th><th>盈亏比</th></tr></thead>
<tbody>{t1}</tbody></table>
<p style="text-align:center;font-size:13px;color:#666;">表 1　黄金 ETF 与纳指 ETF 海龟策略回测结果</p>
<p>结果既印证文献、也有一层修正：黄金 ETF 是海龟“理想画像”（系统二夏普 0.51、胜率 63%、盈亏比 3.73、回撤仅
16.7% vs 基准 30.5%），但 2018—2026 黄金单边长牛使买入持有年化高达 15.6%，海龟超额为负（−10.3%）。这揭示诚实
结论：在“一路上涨少深调”的长牛现货中，任何“突破进、破位出”的择时都会因反复止损跑输“一直满仓”。</p>
<figure><img src="{img('equity_sh518880.png')}" alt="黄金净值">
<figcaption>图 3　黄金 ETF 两套海龟系统净值 vs 买入持有</figcaption></figure>
<p>如图 3，黄金买入持有（灰虚线）2024—2025 加速上行，海龟因每轮小回调都离场而增长较缓；但策略净值更平滑、
回撤更浅，这正是趋势跟踪“用部分收益换回撤保护”的取舍。</p>

<h3>2. 全部标的横向对比（System2 · 55/20）</h3>
<table><thead><tr><th>标的</th><th>策略年化</th><th>基准年化</th><th>超额年化</th><th>夏普</th>
<th>卡玛</th><th>策略回撤</th><th>基准回撤</th><th>交易次数</th><th>胜率</th></tr></thead>
<tbody>{t2}</tbody></table>
<p style="text-align:center;font-size:13px;color:#666;">表 2　8 标的海龟策略（System2）指标全览（按超额年化排序）</p>
<figure><img src="{img('summary_excess.png')}" alt="超额收益">
<figcaption>图 4　各标的海龟策略（System2）超额年化收益对比</figcaption></figure>
<p>超额收益鲜明分化且与文献一致：腾讯控股（超额 <span class="pos">+4.9%</span>）、科创 50、沪深 300 等波动大、
有明显趋势与深调的标的跑赢或追平买入持有；黄金、纳指、长江电力、红利低波等“少回调”或“低波动无趋势”标的
则跑输。腾讯是最佳范例——2021—2022 经历腰斩级暴跌，海龟在下跌初期即离场规避，故超额转正、风控压倒性领先。</p>

<h3>3. 海龟真正的价值：控制回撤</h3>
<figure><img src="{img('risk_compare.png')}" alt="回撤对比">
<figcaption>图 5　海龟策略 vs 买入持有：最大回撤对比（System2，越低越好）</figcaption></figure>
<p>如图 5，高波动标的上海龟大幅削减回撤：腾讯 76.7%→21.0%、科创 50 59.9%→16.5%、沪深 300 44.7%→19.5%、
中证 500 40.7%→23.8%。即用“少赚一点”换“回撤浅一大截”。唯一例外是低波动长江电力——本无趋势可跟踪，择时
失误反增回撤，印证“低波动无趋势标的不适合海龟”。</p>
<figure><img src="{img('sharpe_compare.png')}" alt="夏普热力图" style="max-width:520px">
<figcaption>图 6　8 标的 × 2 系统 夏普比率热力图（红高绿低）</figcaption></figure>
<p>图 6 佐证：科创 50、腾讯、黄金大面积偏红（夏普 0.5—0.58 最高），最适合海龟；长江电力、红利低波偏绿（夏普
接近 0），风险调整后性价比差。</p>
<figure><img src="{img('return_risk.png')}" alt="收益回撤散点" style="max-width:680px">
<figcaption>图 7　海龟策略收益—回撤分布（红=跑赢基准 绿=跑输，●系统1 ■系统2）</figcaption></figure>
<p>图 7 中绝大多数点集中在左侧（回撤 15%—25%），说明 ATR 头寸管理把各标的回撤都压到相近的较低水平——无论
标的多凶，策略回撤都被控制在可控区间。</p>

<h2>七、参数调节与敏感性分析</h2>
<p>调节核心参数（标的、通道周期）观察收益变化。图 8 以黄金 ETF 为例，将入场周期从 10 日拉到 80 日（离场取一半）。</p>
<figure><img src="{img('param_scan.png')}" alt="参数扫描">
<figcaption>图 8　黄金 ETF 通道周期敏感性（周期越长交易越少、越稳）</figcaption></figure>
<table><thead><tr><th>入场/离场周期</th><th>年化收益</th><th>夏普</th><th>最大回撤</th><th>交易次数</th>
<th>胜率</th></tr></thead><tbody>{t3}</tbody></table>
<p style="text-align:center;font-size:13px;color:#666;">表 3　黄金 ETF 不同通道周期回测结果</p>
<p>黄金呈“周期越长越好”规律：入场 10→55 日，年化 2.9%→9.7%、夏普 0.33→0.82、交易 74→21 次，长周期过滤了
震荡假信号、只在大趋势出手，契合黄金慢牛特性；但 80 日后回撤反而扩大（反应太慢）。此规律不通用：纳指周期越长
越差（80 日年化 −1.1%，近年波动加剧），沪深 300 对周期不敏感。<b>没有万能周期，参数须与标的波动节奏匹配，
且“选对标的”比“调对参数”影响更大。</b></p>

<h2>八、海龟法则适应场景与使用心得</h2>
<ul>
<li><b>适应场景——趋势鲜明、波动较大、会有深度回调的标的</b>。在腾讯、科创 50 等高波动标的上最有价值（超额转正、
回撤腰斩）；在黄金、纳指等“慢牛少回调”上虽控回撤出色却难跑赢买入持有；在长江电力、红利低波等低波动无趋势
标的上基本失效。文献指向的商品/股指期货是海龟主场，正因趋势性强且可双向交易。</li>
<li><b>核心价值常是“控回撤”而非“多赚”</b>。它把腾讯回撤从 77% 压到 21%、科创 50 从 60% 压到 17%。用一点收益
换更浅回撤与更高夏普，是有意义的风险管理，也是趋势跟踪 CTA 在机构配置中的定位。</li>
<li><b>必须接受“低胜率、高盈亏比”并有纪律地止损</b>。趋势型标的盈亏比常 2—6 倍但胜率仅 30%—60%，盈利依赖少数
大趋势；不能因连续小亏放弃系统，否则恰好错过贡献全部收益的大行情。</li>
<li><b>参数须与标的波动匹配，且计入成本、规避未来函数</b>。趋势平稳用长周期、波动急促用短周期；短周期交易频繁，
务必计入成本（本文万分之五）、信号次日生效、通道排除当日，否则高估收益。</li>
<li><b>只做多是国内现货约束，也是超额偏低的重要原因</b>。海龟原版可双向做空、下跌趋势同样获利；本文受限只做多，
下跌时最多空仓规避。若在可做空的商品/股指期货上应用，海龟威力会更完整释放。</li>
</ul>
<p>总之，海龟法则用高低点通道捕捉趋势、用 ATR 统一风险度量、用金字塔加仓放大利润、用 2 ATR 止损截断亏损，把
一套完整交易纪律彻底量化。最重要的一课是——评价任何策略都要用超额收益把“标的的 β”与“策略的 α”分开，用夏普
和最大回撤把“收益”与“风险”一起看；海龟的价值未必写在收益率上，而常常藏在那条更平滑、回撤更浅的净值曲线里。</p>

<p class="note">数据来源：工作坊统一行情数据（前复权日线，2018—2026，8 标的约 2000 交易日）。
代码：turtle_strategy.py / metrics.py / run_backtest.py / make_flowchart.py。
参考文献：Brock, Lakonishok &amp; LeBaron (1992, JF)；Miffre &amp; Rallis (2007, JBF)；
Moskowitz, Ooi &amp; Pedersen (2012, JFE)；Swart (2016, UCT)；Faith《海龟交易法则》。
本文仅为量化学习实践，不构成投资建议，市场有风险，决策需谨慎。</p>

</body>
</html>"""

    with open(HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML 已生成：", HTML, f"({os.path.getsize(HTML)//1024} KB)")


if __name__ == "__main__":
    main()
