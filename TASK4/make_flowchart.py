# -*- coding: utf-8 -*-
"""
TASK4 海龟交易策略完整流程图（对照用户提供的流程图重绘）
作者：张哲铭

链路：① 选择市场 → ② 计算ATR → ③ 计算单位头寸 → ④ 监控突破信号 → ⑤ 入场
     → 判断价格是否涨0.5ATR？
          是 → ⑥ 加仓（最多4单位）→ 回到"涨0.5ATR"循环
          否 → 价格跌破止损线？
                  是 → 止损离场
                  否 → 价格跌破N日最低？
                          是 → 止盈离场
                          否 → 循环判断
输出：figures/flowchart.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

sim_hei = r"C:\Windows\Fonts\simhei.ttf"
if os.path.exists(sim_hei):
    font_manager.fontManager.addfont(sim_hei)
    matplotlib.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 配色（延续 A 股审美：橙主色链路，红止损，绿止盈）
ORANGE = "#e67e22"
ORANGE_L = "#fdf2e9"
RED = "#c0392b"
RED_L = "#fdedec"
GREEN = "#1e8449"
GREEN_L = "#eafaf1"
BLUE = "#2874a6"
BLUE_L = "#ebf5fb"
GRAY = "#566573"
DARK = "#2c3e50"

fig, ax = plt.subplots(figsize=(13.2, 8.6), dpi=160)
ax.set_xlim(0, 132); ax.set_ylim(0, 86)
ax.axis("off")


def box(x, y, w, h, title, sub, fc, ec, num=None, tsize=12, ssize=9):
    """圆角流程框：标题 + 副说明。(x,y) 为中心。"""
    b = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle="round,pad=0.4,rounding_size=1.2",
                       linewidth=2, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(b)
    if num:
        ax.add_patch(plt.Circle((x - w/2 + 2.6, y + h/2 - 2.6), 1.7,
                                 color=ec, zorder=4))
        ax.text(x - w/2 + 2.6, y + h/2 - 2.6, str(num), ha="center",
                va="center", color="white", fontsize=9, fontweight="bold", zorder=5)
    ax.text(x + (1.6 if num else 0), y + (h/2 - 4.3 if sub else 0), title,
            ha="center", va="center", fontsize=tsize, fontweight="bold",
            color=DARK, zorder=3)
    if sub:
        ax.text(x, y - 3.2, sub, ha="center", va="center",
                fontsize=ssize, color=GRAY, zorder=3, linespacing=1.35)


def diamond(x, y, w, h, text, fc="#fff7e6", ec=ORANGE, tsize=10.5):
    """菱形判断框。"""
    pts = [(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=2,
                         edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=tsize,
            fontweight="bold", color=DARK, zorder=3, linespacing=1.3)


def arrow(x1, y1, x2, y2, color=ORANGE, label=None, lx=0, ly=0,
          lcolor=None, style="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle="-|>", mutation_scale=18,
                        linewidth=2, color=color, zorder=1,
                        connectionstyle="arc3,rad=0", linestyle=style)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2)/2 + lx, (y1 + y2)/2 + ly, label, ha="center",
                va="center", fontsize=10, fontweight="bold",
                color=lcolor or color,
                bbox=dict(boxstyle="round,pad=0.2", fc="white",
                          ec="none", alpha=0.9), zorder=4)


# 标题
ax.text(66, 82.5, "海龟交易策略完整流程", ha="center", fontsize=21,
        fontweight="bold", color=DARK)
ax.text(66, 78, "从市场选择到最终离场的完整决策链路（做多方向）",
        ha="center", fontsize=11.5, color=ORANGE)

# ===== 顶部主链路 ①~⑤ 横向 =====
Y = 68
box(13, Y, 20, 12, "选择市场", "从高流动性品种\n中选择交易标的",
    ORANGE_L, ORANGE, num=1)
box(38, Y, 20, 12, "计算 ATR", "计算 N 日 ATR\n（通常 N=20）",
    ORANGE_L, ORANGE, num=2)
box(63, Y, 20, 12, "计算单位头寸",
    "单位头寸 = 风险资本 /\n(N × ATR × 价值因子)", ORANGE_L, ORANGE, num=3)
box(88, Y, 20, 12, "监控突破信号",
    "价格突破 N 日最高价\n(做多)/最低价(做空)", ORANGE_L, ORANGE, num=4)
box(115, Y, 20, 12, "入场·建1单位",
    "突破确认后\n建立 1 个单位头寸", BLUE_L, BLUE, num=5, tsize=11)

arrow(23, Y, 28, Y)
arrow(48, Y, 53, Y)
arrow(73, Y, 78, Y)
arrow(98, Y, 105, Y)

# ===== 判断1：价格涨 0.5ATR？=====
D1Y = 50
arrow(115, Y - 6, 115, D1Y + 7)
diamond(115, D1Y, 22, 13, "价格涨\n0.5 ATR？")

# 右侧“否”→ 折回到 止损判断（右侧竖线）
# 是 → 向下 加仓
ADDY = 33
arrow(115, D1Y - 6.5, 115, ADDY + 6, label="是", ly=1, lcolor=GREEN)
box(115, ADDY, 20, 12, "加仓·最多4单位",
    "每涨 0.5 ATR 加\n1 单位，直至 4 单位", GREEN_L, GREEN, num=6, tsize=11)
# 加仓后回到“涨0.5ATR”循环（右侧折线向上）
arrow(125, ADDY, 129, ADDY, color=GREEN)
FancyArrowPatch
ax.plot([129, 129], [ADDY, D1Y], color=GREEN, lw=2, zorder=1)
arrow(129, D1Y, 126, D1Y, color=GREEN)

# 否 → 向左 到 止损判断
D2Y = D1Y
arrow(104, D1Y, 88, D1Y, label="否", ly=2, lcolor=ORANGE)
diamond(74, D2Y, 22, 13, "价格跌破\n止损线？", fc=RED_L, ec=RED)

# 止损判断：是 → 左 止损离场
box(30, D2Y, 22, 12, "止损离场",
    "以突破失败或\n止损线价格平仓", RED_L, RED)
arrow(63, D2Y, 41, D2Y, label="是", ly=2, lcolor=RED)

# 止损判断：否 → 下 到 止盈判断
D3Y = 30
arrow(74, D2Y - 6.5, 74, D3Y + 7, label="否", lx=3, lcolor=ORANGE)
diamond(74, D3Y, 22, 13, "价格跌破\nN 日最低？", fc=GREEN_L, ec=GREEN)

# 止盈判断：是 → 左 止盈离场
box(30, D3Y, 22, 12, "止盈离场",
    "价格跌破 N 日最低价\n平仓离场", GREEN_L, GREEN)
arrow(63, D3Y, 41, D3Y, label="是", ly=2, lcolor=GREEN)

# 止盈判断：否 → 循环回到 “价格涨0.5ATR？”（底部大回环）
LOOPY = 16
arrow(74, D3Y - 6.5, 74, LOOPY, color=BLUE)
ax.plot([74, 115], [LOOPY, LOOPY], color=BLUE, lw=2, zorder=1)
ax.text(94, LOOPY - 2.4, "否 → 继续持有，循环监控",
        ha="center", fontsize=9.5, color=BLUE, fontweight="bold")
arrow(115, LOOPY, 115, D1Y - 6.5, color=BLUE)

# 图例
lx, ly = 6, 8
for i, (c, t) in enumerate([(ORANGE, "主流程/指标"), (BLUE, "入场·持有循环"),
                            (GREEN, "加仓/止盈（正向）"), (RED, "止损（风控）")]):
    ax.add_patch(plt.Rectangle((lx + i*29, ly), 2.2, 2.2, color=c))
    ax.text(lx + i*29 + 3, ly + 1.1, t, va="center", fontsize=9.5, color=DARK)

fig.tight_layout()
fig.savefig(os.path.join(FIG, "flowchart.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("流程图已保存：figures/flowchart.png")
