# -*- coding: utf-8 -*-
"""
TASK7 数据获取脚本
用 westock-data skill (腾讯自选股数据) 批量拉取指数/ETF 前复权日线，
每标的最多 2000 条（约 2018-2026，跨越多轮牛熊），保存为 CSV。
数据源无严格频率限制，可批量。
"""
import os
import subprocess
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
SKILL = r"C:/Users/jamminzhang/.workbuddy/skills/westock-data/scripts/index.js"
NODE = r"C:/Users/jamminzhang/.workbuddy/binaries/node/versions/22.22.2/node.exe"

# 指数（用于双均线择时、大盘基准、小市值风格代理）
INDEX = {
    "sh000300": "沪深300指数",
    "sh000905": "中证500指数",
    "sh000852": "中证1000指数",
    "sz399303": "国证2000指数",
    "sh000001": "上证指数",
}

# ETF 轮动池（宽基+行业+风格+跨境+商品）
ETF = {
    "sh510300": "沪深300ETF",
    "sh510500": "中证500ETF",
    "sh512100": "中证1000ETF",
    "sh588000": "科创50ETF",
    "sz159915": "创业板ETF",
    "sh512000": "券商ETF",
    "sh512010": "医药ETF",
    "sh512690": "酒ETF",
    "sh512800": "银行ETF",
    "sh518880": "黄金ETF",
    "sz159941": "纳指ETF",
    "sh515450": "红利低波ETF",
}

ALL = {**INDEX, **ETF}


def fetch_one(code):
    """拉单个标的 2000 条前复权日线"""
    cmd = [NODE, SKILL, "kline", code, "--period", "day", "--limit", "2000", "--fq", "qfq"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
    lines = [l for l in r.stdout.splitlines() if l.strip().startswith("|")]
    # 去掉表头与分隔行
    rows = []
    for l in lines:
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if not cells or cells[0] in ("date", "symbol", "---") or cells[0].startswith("---"):
            continue
        rows.append(cells)
    return rows


def parse(code, rows):
    """解析为 date,open,high,low,close,volume"""
    recs = []
    for c in rows:
        # 单标的格式: date open last high low volume amount exchange
        if len(c) >= 6:
            try:
                d = c[0]
                o = float(c[1]); close = float(c[2]); h = float(c[3]); lo = float(c[4]); v = float(c[5])
                recs.append((d, o, h, lo, close, v))
            except ValueError:
                continue
    df = pd.DataFrame(recs, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return df


def main():
    summary = []
    for code, name in ALL.items():
        rows = fetch_one(code)
        df = parse(code, rows)
        if len(df) == 0:
            print(f"[FAIL] {code} {name} 无数据")
            continue
        out = os.path.join(DATA, f"{code}.csv")
        df.to_csv(out, index=False, encoding="utf-8-sig")
        summary.append((code, name, len(df), df["date"].iloc[0], df["date"].iloc[-1]))
        print(f"[OK] {code} {name}: {len(df)} 行, {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    sdf = pd.DataFrame(summary, columns=["code", "name", "rows", "start", "end"])
    sdf.to_csv(os.path.join(DATA, "_data_summary.csv"), index=False, encoding="utf-8-sig")
    print("\n数据获取完成，汇总：")
    print(sdf.to_string(index=False))


if __name__ == "__main__":
    main()
