# -*- coding: utf-8 -*-
"""
TASK3 数据准备：将 westock-data 拉取的原始行情（Markdown 表格）解析为标准 CSV。
作者：张哲铭

原始字段：date | open | last(收盘) | high | low | volume | amount | exchange(换手率)
输出字段：date, open, high, low, close, volume（按日期升序），供回测脚本复用。
"""
import os
import re
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

# 标的代码 -> 中文名（用于图表标题）
UNIVERSE = {
    "sh600900": "长江电力",
    "hk00700": "腾讯控股",
    "sh518880": "黄金ETF",
    "sh515450": "红利低波50ETF",
    "sz159941": "纳指ETF",
    "sh588000": "科创50ETF",
    "sh510300": "沪深300ETF",
    "sh510500": "中证500ETF",
}


def parse_raw(code: str) -> pd.DataFrame:
    """解析单个标的的原始 Markdown 表格为 DataFrame。"""
    path = os.path.join(DATA, f"raw_{code}.md")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 只保留以日期开头的数据行：| 2026-07-07 | ...
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 6:
                continue
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", cells[0]):
                continue
            rows.append(cells[:8])

    df = pd.DataFrame(rows, columns=[
        "date", "open", "close", "high", "low", "volume", "amount", "turnover"
    ])
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    return df


def main():
    summary = []
    for code, name in UNIVERSE.items():
        df = parse_raw(code)
        out = os.path.join(DATA, f"{code}.csv")
        df.to_csv(out, index=False, encoding="utf-8-sig")
        summary.append((code, name, len(df),
                        df["date"].min().date(), df["date"].max().date()))
        print(f"[OK] {code} {name}: {len(df)} 行  "
              f"{df['date'].min().date()} ~ {df['date'].max().date()}")

    print("\n数据准备完成，共处理", len(summary), "个标的。")


if __name__ == "__main__":
    main()
