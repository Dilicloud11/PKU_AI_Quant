# -*- coding: utf-8 -*-
"""生成交互式 HTML 展示页 index.html（自包含，内嵌图片与数据）。"""
import json, base64, os

BASE = os.path.dirname(os.path.abspath(__file__))
img_b64 = open(os.path.join(BASE, "_img_b64.txt")).read().strip()
sample = json.load(open(os.path.join(BASE, "_sample.json"), encoding="utf-8"))
chart = json.load(open(os.path.join(BASE, "_chart.json"), encoding="utf-8"))

# 统计量
import pandas as pd
df = pd.read_csv(os.path.join(BASE, "600900_daily.csv"))
stats = {
    "days": len(df),
    "start": df["close"].iloc[0], "end": df["close"].iloc[-1],
    "high": df["close"].max(), "low": df["close"].min(),
    "ret": (df["close"].iloc[-1]/df["close"].iloc[0]-1)*100,
    "mean": df["close"].mean(), "std": df["close"].std(),
    "up": int((df["pct_chg"]>0).sum()), "down": int((df["pct_chg"]<0).sum()),
}

rows = ""
for i, r in enumerate(sample):
    if i == 10:
        rows += '<tr class="sep"><td colspan="8">··· 中间省略 222 个交易日 ···</td></tr>'
    chg = r["pct_chg"]
    cls = "up" if chg > 0 else ("down" if chg < 0 else "")
    rows += f"""<tr>
      <td>{r['trade_date']}</td><td>{r['open']:.2f}</td><td>{r['high']:.2f}</td>
      <td>{r['low']:.2f}</td><td class="bold">{r['close']:.2f}</td>
      <td>{r['vol']:.0f}</td><td class="{cls}">{chg:+.2f}</td>
      <td class="{cls}">{chg:+.2f}%</td></tr>"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>张哲铭 · TASK1 量化交易数据引擎</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#f5f6f8;
         color:#1a1a1a; line-height:1.7; }}
  .hero {{ background:linear-gradient(135deg,#c0392b,#8e2b22); color:#fff;
          padding:48px 32px; text-align:center; }}
  .hero h1 {{ font-size:30px; font-weight:700; margin-bottom:10px; }}
  .hero p {{ font-size:15px; opacity:.92; }}
  .hero .tag {{ display:inline-block; margin-top:14px; background:rgba(255,255,255,.18);
              padding:5px 16px; border-radius:20px; font-size:13px; }}
  .wrap {{ max-width:960px; margin:-28px auto 40px; padding:0 20px; }}
  .card {{ background:#fff; border-radius:14px; padding:28px 30px; margin-bottom:22px;
          box-shadow:0 4px 20px rgba(0,0,0,.06); }}
  .card h2 {{ font-size:20px; color:#c0392b; border-left:4px solid #c0392b;
             padding-left:12px; margin-bottom:16px; }}
  .card h3 {{ font-size:16px; margin:16px 0 8px; color:#333; }}
  .card p {{ font-size:14.5px; color:#333; margin-bottom:10px; text-align:justify; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:8px 0; }}
  .stat {{ background:#faf5f4; border-radius:10px; padding:16px; text-align:center; }}
  .stat .v {{ font-size:22px; font-weight:700; color:#c0392b; }}
  .stat .v.green {{ color:#27ae60; }}
  .stat .l {{ font-size:12px; color:#888; margin-top:4px; }}
  ul {{ padding-left:22px; }}
  ul li {{ font-size:14.5px; margin-bottom:8px; text-align:justify; }}
  ul li b {{ color:#c0392b; }}
  .fig {{ text-align:center; margin:10px 0; }}
  .fig img {{ max-width:100%; border-radius:8px; border:1px solid #eee; }}
  .cap {{ font-size:13px; color:#666; text-align:center; margin-top:8px; font-weight:600; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; margin-top:10px; }}
  th,td {{ padding:7px 6px; text-align:center; border-bottom:1px solid #eee; }}
  th {{ background:#c0392b; color:#fff; font-weight:600; }}
  td.bold {{ font-weight:700; }}
  td.up {{ color:#c0392b; }} td.down {{ color:#27ae60; }}
  tr.sep td {{ background:#faf5f4; color:#999; font-size:12px; padding:5px; }}
  .chart-box {{ position:relative; height:360px; }}
  .code {{ background:#282c34; color:#abb2bf; border-radius:8px; padding:18px;
          font-family:Consolas,monospace; font-size:12.5px; overflow-x:auto;
          white-space:pre; line-height:1.5; }}
  .foot {{ text-align:center; color:#999; font-size:13px; padding:20px; }}
  .badge {{ display:inline-block; background:#eafaf1; color:#27ae60; padding:2px 10px;
           border-radius:12px; font-size:12px; margin-left:8px; }}
</style>
</head>
<body>
<div class="hero">
  <h1>量化交易初体验：从零搭建数据引擎</h1>
  <p>北京大学 AI 量化工作坊 · TASK1　｜　姓名：张哲铭</p>
  <span class="tag">研究标的：长江电力（600900.SH）· 沪市水电龙头</span>
</div>

<div class="wrap">

  <div class="card">
    <h2>数据引擎运行结果概览</h2>
    <div class="stats">
      <div class="stat"><div class="v">{stats['days']}</div><div class="l">交易日数</div></div>
      <div class="stat"><div class="v">{stats['start']:.2f}</div><div class="l">期初收盘（元）</div></div>
      <div class="stat"><div class="v">{stats['end']:.2f}</div><div class="l">期末收盘（元）</div></div>
      <div class="stat"><div class="v green">{stats['ret']:+.2f}%</div><div class="l">区间涨跌幅</div></div>
      <div class="stat"><div class="v">{stats['high']:.2f}</div><div class="l">期间最高</div></div>
      <div class="stat"><div class="v green">{stats['low']:.2f}</div><div class="l">期间最低</div></div>
      <div class="stat"><div class="v">{stats['up']}</div><div class="l">上涨天数</div></div>
      <div class="stat"><div class="v green">{stats['down']}</div><div class="l">下跌天数</div></div>
    </div>
  </div>

  <div class="card">
    <h2>一、量化交易相较传统手工交易的优势</h2>
    <ul>
      <li><b>纪律性强、克服人性弱点</b>——规则由程序严格执行，不受贪婪、恐惧等情绪干扰，避免追涨杀跌。</li>
      <li><b>系统性与可重复性</b>——策略以明确逻辑固化，任何人、任何时间运行都得到一致结果，便于复盘优化。</li>
      <li><b>处理海量数据、捕捉多维机会</b>——可同时跟踪成百上千只标的与多个因子，远超人脑信息处理能力。</li>
      <li><b>反应速度快、执行精准</b>——信号触发到下单可达毫秒级，避免手工下单的手误与延迟。</li>
      <li><b>可回测、可验证</b>——实盘前用历史数据检验收益、回撤、胜率，以数据而非主观感觉验证策略。</li>
      <li><b>严格的风险管理</b>——止损、仓位控制、风险敞口限制写入程序自动执行，风控贯穿全程。</li>
    </ul>
  </div>

  <div class="card">
    <h2>二、基本概念解释</h2>
    <h3>📊 K 线</h3>
    <p>又称蜡烛图，描述某时间周期内价格波动。每根 K 线含开盘价、收盘价、最高价、最低价四个价格，
    由实体和上下影线构成。收盘高于开盘为阳线（A股红色示涨），反之为阴线（绿色示跌），
    将多空力量对比浓缩于一图，是技术分析最基础的工具。</p>
    <h3>🏢 基本面</h3>
    <p>影响资产内在价值的基础性因素，回答“到底值多少钱”。含宏观（经济、利率、政策）、
    行业（景气度、竞争格局）、公司（营收、净利润、PE、PB、现金流）三个层面，
    着眼中长期价值，是价值投资的核心方法。</p>
    <h3>📈 技术面</h3>
    <p>通过历史价格与成交量研究市场行为、预测走势。以“价格反映一切、历史会重演、价格沿趋势运行”
    为假设，工具含 K 线形态、趋势线、支撑压力位及 MA、MACD、RSI、KDJ 等指标，偏重中短期择时。</p>
  </div>

  <div class="card">
    <h2>三、Tushare 数据引擎实现</h2>
    <h3>核心代码</h3>
    <div class="code">import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt

ts.set_token("你的Token")           # 设置身份凭证
pro = ts.pro_api()                  # 初始化接口

# 获取长江电力过去一年日线数据
df = pro.daily(ts_code="600900.SH",
               start_date="20250704", end_date="20260704")
df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
df = df.sort_values("trade_date")

# 绘制收盘价曲线 & 保存 CSV
plt.plot(df["trade_date"], df["close"], color="#c0392b")
plt.savefig("close_price.png")
df.to_csv("600900_daily.csv", index=False, encoding="utf-8-sig")</div>

    <h3>图 1　近一年每日收盘价走势图（静态）</h3>
    <div class="fig">
      <img src="data:image/png;base64,{img_b64}" alt="收盘价曲线">
    </div>
    <div class="cap">图 1　长江电力（600900.SH）近一年每日收盘价走势图</div>

    <h3>图 2　交互式收盘价曲线 <span class="badge">可悬停查看</span></h3>
    <div class="chart-box"><canvas id="priceChart"></canvas></div>
    <div class="cap">图 2　交互式收盘价曲线（鼠标悬停查看每日具体价格）</div>

    <p style="margin-top:16px;">程序共获取 2025-07-04 至 2026-07-03 期间 {stats['days']} 个交易日的有效数据。期初收盘
    {stats['start']:.2f} 元，期末 {stats['end']:.2f} 元，区间累计下跌约 {abs(stats['ret']):.2f}%；期间最高
    {stats['high']:.2f} 元、最低 {stats['low']:.2f} 元。收盘价均值约 {stats['mean']:.2f} 元、标准差约
    {stats['std']:.2f} 元，波动较低，呈现公用事业蓝筹股“稳健、低波动”的典型特征，与其稳定的水电主业和高分红属性相符。</p>

    <h3>数据表预览（CSV 首尾各 10 行，共 {stats['days']} 行）</h3>
    <table>
      <tr><th>交易日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th>
          <th>成交量(手)</th><th>涨跌额</th><th>涨跌幅</th></tr>
      {rows}
    </table>
  </div>

  <div class="foot">
    本页面为 TASK1 交互式成果展示 · 数据来源：Tushare Pro · 生成日期：2026-07-04
  </div>
</div>

<script>
const chartData = {json.dumps(chart, ensure_ascii=False)};
const ctx = document.getElementById('priceChart').getContext('2d');
new Chart(ctx, {{
  type:'line',
  data:{{
    labels: chartData.dates,
    datasets:[{{
      label:'收盘价（元）', data: chartData.close,
      borderColor:'#c0392b', backgroundColor:'rgba(192,57,43,.08)',
      borderWidth:1.6, pointRadius:0, pointHoverRadius:5, fill:true, tension:.1
    }}]
  }},
  options:{{
    responsive:true, maintainAspectRatio:false,
    interaction:{{intersect:false,mode:'index'}},
    plugins:{{legend:{{display:true}},
      tooltip:{{callbacks:{{label:c=>' 收盘价：'+c.parsed.y.toFixed(2)+' 元'}}}}}},
    scales:{{
      x:{{ticks:{{maxTicksLimit:12,color:'#888'}},grid:{{display:false}}}},
      y:{{ticks:{{color:'#888'}},grid:{{color:'#eee'}}}}
    }}
  }}
}});
</script>
</body>
</html>"""

open(os.path.join(BASE, "index.html"), "w", encoding="utf-8").write(html)
print("HTML 已生成: index.html  大小 %.1f KB" % (len(html.encode())/1024))
