# PKU AI 量化工作坊

作者：张哲铭

北京大学 AI 量化交易工作坊系列任务代码与作业文档。

## 目录结构
| 目录 | 任务 | 说明 |
|------|------|------|
| [`TASK1/`](./TASK1) | 量化交易初体验：从零搭建数据引擎 | Tushare 数据获取、收盘价可视化、CSV 存储 |
| [`TASK2/`](./TASK2) | 数据炼金术：数据诊断与构造交易指标 | 数据诊断、RSI/MACD/布林带/KDJ 指标计算与可视化 |

## 研究标的
长江电力（600900.SH），沪市水电龙头，样本区间 2025-07-04 ~ 2026-07-03，共 242 个交易日。

## 环境依赖
```
tushare  pandas  numpy  matplotlib  python-docx  docx2pdf
```

## 数据来源
[Tushare Pro](https://www.tushare.pro/)

> 注：代码中的 Tushare token 已改为从环境变量 `TUSHARE_TOKEN` 读取，未硬编码。
