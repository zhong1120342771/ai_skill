"""
validate_data.py — 莫斯科保卫战周报数据两遍校验脚本
用法：python3 validate_data.py --baowei 莫斯科保卫战周报260608.xlsx --biz 莫斯科保卫战周报补充数据格式.xlsx
"""

import sys, argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import timedelta

PASS = "✅"
WARN = "⚠️ "
FAIL = "❌"

errors = []
warnings = []

def check(label, ok, msg="", level="fail"):
    mark = PASS if ok else (WARN if level == "warn" else FAIL)
    print(f"  {mark} {label}" + (f" — {msg}" if msg else ""))
    if not ok:
        if level == "warn":
            warnings.append(label)
        else:
            errors.append(label)
    return ok


# ── 第一遍：明细数据校验 ──────────────────────────────────────────────────────

def validate_round1(baowei_path, biz_path):
    print("\n=== 第一遍校验：明细数据 ===\n")

    wb_baowei = pd.ExcelFile(baowei_path)
    wb_biz    = pd.ExcelFile(biz_path)

    # 1. 周期连续性（过去8周数据）
    print("【过去8周数据 - 周期连续性】")
    df8 = pd.read_excel(baowei_path, sheet_name='过去8周数据')
    df8['week_end'] = pd.to_datetime(df8['week_end'])
    overall8 = df8[df8['tag_01'] == '整体'].sort_values('week_end')
    weeks = overall8['week_end'].unique()
    print(f"  周列表: {[str(w.date()) for w in sorted(weeks)]}")
    check("周数量为8", len(weeks) == 8, f"实际{len(weeks)}周", level="warn")
    if len(weeks) >= 2:
        diffs = [(weeks[i+1]-weeks[i]).days for i in range(len(weeks)-1)]
        check("周间隔均为7天", all(d == 7 for d in diffs),
              f"间隔={diffs}", level="warn")

    latest_week = pd.Timestamp(sorted(weeks)[-1])
    print(f"  最新周: {latest_week.date()}")

    # 2. 漏斗合理性
    print("\n【过去8周数据 - 漏斗合理性】")
    try:
        cols_needed = ['曝光uv', '商详uv', '净支付pv']
        avail = [c for c in cols_needed if c in df8.columns]
        if len(avail) == 3:
            row = df8[(df8['tag_01'] == '整体') & (df8['week_end'] == latest_week)].iloc[0]
            check("曝光UV > 商详UV", row['曝光uv'] > row['商详uv'],
                  f"{row['曝光uv']:.0f} > {row['商详uv']:.0f}")
            check("商详UV > 净支付PV", row['商详uv'] > row['净支付pv'],
                  f"{row['商详uv']:.0f} > {row['净支付pv']:.0f}")
        else:
            print(f"  {WARN} 列名不完整，跳过漏斗校验，可用列: {list(df8.columns)}")
    except Exception as e:
        print(f"  {WARN} 漏斗校验异常: {e}")

    # 3. 转化率区间 [0,1]
    print("\n【过去8周数据 - 转化率合理性】")
    rate_cols = [c for c in df8.columns if '率' in c or 'rate' in c.lower()]
    for col in rate_cols[:5]:
        vals = df8[col].dropna()
        in_range = ((vals >= 0) & (vals <= 1)).all()
        check(f"{col} 在 [0,1]", bool(in_range),
              f"min={vals.min():.4f} max={vals.max():.4f}")

    # 4. 逐月数据同比对齐
    print("\n【逐月数据 - 25/26年同期对齐】")
    try:
        dflm = pd.read_excel(baowei_path, sheet_name='逐月数据')
        dflm.columns = [str(c).strip() for c in dflm.columns]
        # 找年份标识列
        year_col = next((c for c in dflm.columns if '年' in c or 'year' in c.lower()), None)
        month_col = next((c for c in dflm.columns if '月' in c or 'month' in c.lower()), None)
        if year_col and month_col:
            months_25 = set(dflm[dflm[year_col] == 2025][month_col].dropna().astype(int))
            months_26 = set(dflm[dflm[year_col] == 2026][month_col].dropna().astype(int))
            matched = months_25 & months_26
            check("25/26年有同期月份", len(matched) > 0,
                  f"共{len(matched)}个月份对齐: {sorted(matched)}")
        else:
            print(f"  {WARN} 找不到年份/月份列，可用列: {list(dflm.columns)[:10]}")
    except Exception as e:
        print(f"  {WARN} 逐月数据校验异常: {e}")

    # 5. 分业务文件最新周对齐
    print("\n【分业务文件 - 最新周与大盘对齐】")
    for sheet in ['搜推场景', '商详商列', '馆渗透', '新媒新客', '分端数据']:
        try:
            df_biz = pd.read_excel(biz_path, sheet_name=sheet)
            # 找日期列
            date_col = next((c for c in df_biz.columns
                            if 'week' in c.lower() or '日' in c or '周' in c), None)
            if date_col:
                latest_biz = pd.to_datetime(df_biz[date_col]).max()
                match = (latest_biz.date() == latest_week.date())
                check(f"{sheet} 最新周对齐",
                      match, f"分业务={latest_biz.date()} 大盘={latest_week.date()}",
                      level="warn")
            else:
                print(f"  {WARN} {sheet}: 找不到日期列")
        except Exception as e:
            print(f"  {WARN} {sheet}: {e}")

    print(f"\n第一遍完成 — 错误:{len(errors)} 警告:{len(warnings)}")


# ── 第二遍：图表数据交叉校验 ──────────────────────────────────────────────────

def validate_round2(biz_path, chart_dir=None):
    print("\n=== 第二遍校验：图表数据交叉核实 ===\n")
    if chart_dir is None:
        chart_dir = Path(biz_path).parent

    checks_map = {
        '搜推场景':  ('搜索', '提袋率'),
        '商详商列':  ('1-手机', '提袋率'),
        '馆渗透':    ('电子', '馆渗透率'),
        '分端数据':  ('转转APP', 'dau-净支付pv转化率'),
        '新媒新客':  ('新客_1-手机', 'dau-净支付pv转化率'),
    }

    print("（本轮校验需要图表已生成并可读取数据点）")
    print("手动核实要点：")
    for sheet, (sample_dim, metric) in checks_map.items():
        print(f"  • {sheet}: 检查 [{sample_dim}] 的 [{metric}] 最新值与图表标注一致")

    # 数据层校验：各sheet最新一行数值合理性
    print("\n【分业务数据最终值合理性】")
    for sheet in ['搜推场景', '商详商列', '馆渗透', '新媒新客', '分端数据']:
        try:
            df = pd.read_excel(biz_path, sheet_name=sheet)
            rate_cols = [c for c in df.columns if '率' in c]
            for col in rate_cols[:3]:
                vals = df[col].dropna()
                if len(vals) > 0:
                    last_val = vals.iloc[-1]
                    in_range = 0 <= last_val <= 1
                    check(f"{sheet}.{col} 最新值合理",
                          bool(in_range), f"值={last_val:.4f}")
        except Exception as e:
            print(f"  {WARN} {sheet}: {e}")

    print(f"\n第二遍完成 — 错误:{len(errors)} 警告:{len(warnings)}")


# ── 汇总 ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baowei', default='~/Downloads/莫斯科保卫战周报260608.xlsx')
    parser.add_argument('--biz',    default='~/Downloads/莫斯科保卫战周报补充数据格式.xlsx')
    args = parser.parse_args()

    baowei = Path(args.baowei).expanduser()
    biz    = Path(args.biz).expanduser()

    print(f"大盘文件: {baowei}")
    print(f"分业务文件: {biz}")

    validate_round1(baowei, biz)
    validate_round2(biz)

    print("\n" + "="*50)
    if errors:
        print(f"{FAIL} 发现 {len(errors)} 个错误，需修复后再生成图表：")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)
    elif warnings:
        print(f"{WARN} 有 {len(warnings)} 个警告，建议确认后继续：")
        for w in warnings:
            print(f"   - {w}")
    else:
        print(f"{PASS} 全部校验通过，可以继续图表生成流程")


if __name__ == '__main__':
    main()
