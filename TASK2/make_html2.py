# -*- coding: utf-8 -*-
"""生成 TASK2 交互式 HTML 展示页 index.html（自包含）。"""
import os, pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
imgs = {n: open(os.path.join(BASE, f"_{n}.txt")).read().strip()
        for n in ["rsi", "macd", "boll", "kdj"]}

df = pd.read_csv(os.path.join(BASE, "600900_with_indicators.csv"))
desc = pd.read_csv(os.path.join(BASE, "describe_stats.csv"), index_col=0)

sig = {
    "rsi_under": int((df["rsi"] < 30).sum()),
    "boll_up": int((df["close"] >= df["boll_up"]).sum()),
    "boll_low": int((df["close"] <= df["boll_low"]).sum()),
    "kdj_over": int((df["kdj_k"] > 80).sum()),
    "kdj_under": int((df["kdj_k"] < 20).sum()),
}

cap_map = {"open": "开盘价", "high": "最高价", "low": "最低价", "close": "收盘价",
           "vol": "成交量", "amount": "成交额", "pct_chg": "涨跌幅(%)"}
desc_rows = ""
for idx, row in desc.iterrows():
    def fmt(v): return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3f}"
    desc_rows += f"""<tr><td class="bold">{cap_map.get(idx, idx)}</td>
      <td>{fmt(row['mean'])}</td><td>{fmt(row['std'])}</td><td>{fmt(row['min'])}</td>
      <td>{fmt(row['50%'])}</td><td>{fmt(row['max'])}</td></tr>"""


def card(num, cn_title, en, img_key, points_html, interp):
    return f"""
  <div class="card">
    <h2><span class="num">{num}</span>{cn_title} <span class="en">{en}</span></h2>
    {points_html}
    <div class="fig"><img src="data:image/png;base64,{imgs[img_key]}"></div>
    <div class="cap">图 {num-1}　{cn_title}指标可视化</div>
    <p class="interp"><b>解读：</b>{interp}</p>
  </div>"""


html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>张哲铭 · TASK2 数据诊断与交易指标</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Microsoft YaHei","PingFang SC",sans-serif; background:#f5f6f8; color:#1a1a1a; line-height:1.75; }}
.hero {{ background:linear-gradient(135deg,#c0392b,#7d241c); color:#fff; padding:46px 32px; text-align:center; }}
.hero h1 {{ font-size:28px; margin-bottom:8px; }}
.hero p {{ font-size:14.5px; opacity:.92; }}
.hero .tag {{ display:inline-block; margin-top:12px; background:rgba(255,255,255,.18); padding:5px 16px; border-radius:20px; font-size:13px; }}
.wrap {{ max-width:980px; margin:-26px auto 40px; padding:0 20px; }}
.card {{ background:#fff; border-radius:14px; padding:26px 30px; margin-bottom:22px; box-shadow:0 4px 20px rgba(0,0,0,.06); }}
.card h2 {{ font-size:19px; color:#222; margin-bottom:14px; display:flex; align-items:center; gap:8px; }}
.card h2 .num {{ background:#c0392b; color:#fff; width:28px; height:28px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:15px; flex-shrink:0; }}
.card h2 .en {{ font-size:13px; color:#999; font-weight:400; }}
.card p {{ font-size:14.5px; color:#333; margin-bottom:10px; text-align:justify; }}
.card p.interp {{ background:#faf5f4; padding:12px 16px; border-radius:8px; border-left:3px solid #c0392b; margin-top:12px; }}
.formula {{ background:#f0f4f8; border-radius:8px; padding:12px 16px; text-align:center; font-family:"Cambria Math",serif; font-style:italic; color:#2c3e50; margin:8px 0; font-size:15px; }}
.stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:6px 0; }}
.stat {{ background:#faf5f4; border-radius:10px; padding:14px; text-align:center; }}
.stat .v {{ font-size:19px; font-weight:700; color:#c0392b; }}
.stat .l {{ font-size:12px; color:#888; margin-top:3px; }}
.fig {{ text-align:center; margin:10px 0; }}
.fig img {{ max-width:100%; border-radius:8px; border:1px solid #eee; }}
.cap {{ font-size:13px; color:#666; text-align:center; margin-top:6px; font-weight:600; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:10px; }}
th,td {{ padding:8px 6px; text-align:center; border-bottom:1px solid #eee; }}
th {{ background:#c0392b; color:#fff; }}
td.bold {{ font-weight:700; text-align:left; padding-left:14px; }}
.foot {{ text-align:center; color:#999; font-size:13px; padding:18px; }}
</style></head><body>
<div class="hero">
  <h1>数据炼金术：数据诊断与构造交易指标</h1>
  <p>北京大学 AI 量化工作坊 · TASK2　｜　姓名：张哲铭</p>
  <span class="tag">研究标的：长江电力（600900.SH）· 242 个交易日</span>
</div>
<div class="wrap">

  <div class="card">
    <h2><span class="num">1</span>数据基础诊断</h2>
    <p>对 TASK1 存储的日线数据进行完整性诊断：全部 <b>11 个字段 × 242 行均无缺失值</b>、
    无重复交易日，数据完整可用。核心字段描述性统计见表 1。</p>
    <div class="stats">
      <div class="stat"><div class="v">242</div><div class="l">样本交易日</div></div>
      <div class="stat"><div class="v">0</div><div class="l">缺失值</div></div>
      <div class="stat"><div class="v">27.56</div><div class="l">收盘价均值(元)</div></div>
      <div class="stat"><div class="v">0.92</div><div class="l">收盘价标准差</div></div>
      <div class="stat"><div class="v">30.61</div><div class="l">最高价(元)</div></div>
      <div class="stat"><div class="v">25.65</div><div class="l">最低价(元)</div></div>
    </div>
    <table>
      <tr><th>字段</th><th>均值</th><th>标准差</th><th>最小值</th><th>中位数</th><th>最大值</th></tr>
      {desc_rows}
    </table>
    <div class="cap" style="margin-top:8px;">表 1　核心字段描述性统计量</div>
  </div>

  {card(2, "RSI 相对强弱", "Relative Strength Index", "rsi",
    '''<p>通过比较一段时期涨跌力量强弱衡量多空相对强度，取值 0~100。</p>
       <div class="formula">RS = 平均涨幅 / 平均跌幅，  RSI = 100 − 100 / (1 + RS)</div>
       <p><b>作用：</b>RSI&gt;70 超买、&lt;30 超卖，50 为多空分界；价格与 RSI 背离预示反转。</p>''',
    f"样本期内 RSI 全程未破 70（最高 69.3），却有 <b>{sig['rsi_under']} 个交易日</b>跌破 30 超卖线，"
    "集中在 2026 年 1—2 月探底阶段，与该股创年内低点 25.65 元相互印证，超卖后价格随即企稳回升。")}

  {card(3, "MACD 指数平滑异同均线", "Moving Average Convergence Divergence", "macd",
    '''<p>基于快慢两条 EMA 的差离刻画趋势方向与动能，参数 (12,26,9)。</p>
       <div class="formula">DIF = EMA₁₂ − EMA₂₆，  DEA = EMA₉(DIF)，  柱 = 2×(DIF − DEA)</div>
       <p><b>作用：</b>DIF 上穿 DEA 为金叉(买入)、下穿为死叉(卖出)；红绿柱反映动能强弱变化。</p>''',
    "样本期约 7 次金叉、7 次死叉，金叉多现于阶段底部（2025-09、2026-03），死叉多现于阶段顶部，"
    "与波段起落吻合；10—12 月窄幅震荡出现较多假信号，提示无趋势市中需过滤噪音。")}

  {card(4, "布林带", "Bollinger Bands", "boll",
    '''<p>以均线为中枢、以标准差刻画波动区间，由中/上/下三轨组成，参数 (20,2)。</p>
       <div class="formula">中轨 = MA₂₀，  上/下轨 = 中轨 ± 2σ₂₀</div>
       <p><b>作用：</b>价格约 95% 时间在带内；触上轨偏强、触下轨偏弱；带宽收窄预示变盘。</p>''',
    f"收盘价绝大多数时间运行于通道内。触及/破上轨约 {sig['boll_up']} 次（阶段高点），"
    f"触及/破下轨约 {sig['boll_low']} 次（阶段低点）；2026-02 跌破下轨后快速收回，为典型超跌反弹。")}

  {card(5, "KDJ 随机指标（扩展）", "Stochastic Oscillator", "kdj",
    '''<p>综合动量、强弱与均线思想，对价格在近期高低区间中的位置更敏感，参数 (9,3,3)。</p>
       <div class="formula">RSV = (C − L₉)/(H₉ − L₉)×100，  K=SMA(RSV,3)，D=SMA(K,3)，J=3K−2D</div>
       <p><b>作用：</b>K、D&gt;80 超买、&lt;20 超卖；K 上穿 D 金叉、下穿死叉；J 最灵敏领先。</p>''',
    f"K 值有 {sig['kdj_over']} 日进入 80+ 超买区、{sig['kdj_under']} 日跌入 20- 超卖区，"
    "与震荡偏弱、底部停留久的走势相符；J 线波动最大、领先反映短期拐点，KDJ 在震荡市择时能力较强。")}

  <div class="foot">TASK2 交互式成果展示 · 数据来源：Tushare Pro · 生成日期：2026-07-04</div>
</div></body></html>"""

open(os.path.join(BASE, "index.html"), "w", encoding="utf-8").write(html)
print("HTML 已生成: index.html  %.1f KB" % (len(html.encode()) / 1024))
