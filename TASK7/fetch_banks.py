# -*- coding: utf-8 -*-
"""补充：银行股轮动策略的标的池数据（主流上市银行，前复权日线）"""
import os, subprocess
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
SKILL = r"C:/Users/jamminzhang/.workbuddy/skills/westock-data/scripts/index.js"
NODE = r"C:/Users/jamminzhang/.workbuddy/binaries/node/versions/22.22.2/node.exe"

# 银行股轮动池：覆盖国有大行/股份行/城商行，兼顾高股息与成长
BANKS = {
    "sh601398": "工商银行", "sh601939": "建设银行", "sh601288": "农业银行",
    "sh601988": "中国银行", "sh600036": "招商银行", "sh600000": "浦发银行",
    "sh601166": "兴业银行", "sh600016": "民生银行", "sz000001": "平安银行",
    "sh601169": "北京银行", "sh600926": "杭州银行", "sh601818": "光大银行",
}


def fetch_one(code):
    cmd = [NODE, SKILL, "kline", code, "--period", "day", "--limit", "2000", "--fq", "qfq"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
    rows = []
    for l in r.stdout.splitlines():
        if not l.strip().startswith("|"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if not c or c[0] in ("date", "symbol", "---") or c[0].startswith("---"):
            continue
        rows.append(c)
    return rows


def parse(rows):
    recs = []
    for c in rows:
        if len(c) >= 6:
            try:
                recs.append((c[0], float(c[1]), float(c[3]), float(c[4]), float(c[2]), float(c[5])))
            except ValueError:
                continue
    df = pd.DataFrame(recs, columns=["date", "open", "high", "low", "close", "volume"])
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def main():
    summ = []
    for code, name in BANKS.items():
        df = parse(fetch_one(code))
        if len(df) == 0:
            print(f"[FAIL] {code} {name}"); continue
        df.to_csv(os.path.join(DATA, f"{code}.csv"), index=False, encoding="utf-8-sig")
        summ.append((code, name, len(df), df["date"].iloc[0], df["date"].iloc[-1]))
        print(f"[OK] {code} {name}: {len(df)} 行 {df['date'].iloc[0]}~{df['date'].iloc[-1]}")
    pd.DataFrame(summ, columns=["code", "name", "rows", "start", "end"]).to_csv(
        os.path.join(DATA, "_banks_summary.csv"), index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
