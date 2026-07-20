#!/usr/bin/env python3
"""
618消电趋势图生成脚本
用法: python gen_618_chart.py <date> <data_json_path> <output_png_path>
  date: 图表截至日期，格式 2026-06-15
  data_json_path: JSON 文件路径，结构见下方
  output_png_path: 输出 PNG 路径

JSON 数据格式:
{
  "2025": {
    "06-01": {"dau":..., "pay_pv":..., "exp_rate":..., "detail_reach_rate":..., "order_rate":..., "pay_rate":..., "conv_rate":...},
    ...
  },
  "2026": {
    "06-01": {...},
    ...
  }
}
"""
import sys, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

for fp in ['/System/Library/Fonts/STHeiti Medium.ttc', '/System/Library/Fonts/PingFang.ttc',
           '/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf']:
    try: fm.fontManager.addfont(fp)
    except: pass
plt.rcParams['font.family'] = ['STHeiti', 'PingFang SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def main():
    if len(sys.argv) < 4:
        print("Usage: python gen_618_chart.py <date> <data_json> <output_png>")
        sys.exit(1)

    date_str = sys.argv[1]   # e.g. 2026-06-15
    data_path = sys.argv[2]
    out_path = sys.argv[3]

    with open(data_path) as f:
        all_data = json.load(f)

    data_2025 = all_data.get("2025", {})
    data_2026 = all_data.get("2026", {})
    meta = all_data.get("meta", {})  # latest_day, prev_day, yoy_date_day, yoy_week_day

    latest_day = meta.get("latest_day")   # e.g. "06-15"
    prev_day   = meta.get("prev_day")     # e.g. "06-14"
    yoy_date_day = meta.get("yoy_date_day")  # e.g. "06-15" (2025同日期)
    yoy_week_day = meta.get("yoy_week_day")  # e.g. "06-16" (2025同星期)

    # 动态计算 x 轴范围：以 t-1 为终点向前滚动 WINDOW_DAYS 天，跨月连续
    # 6 月大促期天然覆盖在窗口内；跨月后不再无限拉长，聚焦近期趋势
    from datetime import date as _date, timedelta as _td
    _y = 2026
    _lm, _ld = int(latest_day.split('-')[0]), int(latest_day.split('-')[1])
    _end = _date(_y, _lm, _ld)
    WINDOW_DAYS = 30
    _start = max(_date(_y, 6, 1), _end - _td(days=WINDOW_DAYS - 1))
    all_days = []
    _d = _start
    while _d <= _end:
        all_days.append(_d.strftime('%m-%d'))
        _d += _td(days=1)
    max_day_num = len(all_days)
    metrics = [
        ('pay_pv',           '单量（支付PV）',   '万单', '#E74C3C'),
        ('dau',              'DAU',             '万人', '#3498DB'),
        ('conv_rate',        'DAU净支付PV转化率','%',    '#9B59B6'),
        ('exp_rate',         '曝光渗透率',       '%',    '#E67E22'),
        ('detail_reach_rate','商详到达率',       '%',    '#1ABC9C'),
        ('order_rate',       '下单率',          '%',    '#2ECC71'),
        ('pay_rate',         '支付率',          '%',    '#F39C12'),
    ]

    latest_x = all_days.index(latest_day) + 1
    cur  = data_2026[latest_day]
    prev = data_2026.get(prev_day, {})
    yd   = data_2025.get(yoy_date_day, {})
    yw   = data_2025.get(yoy_week_day, {})

    fig, axes = plt.subplots(3, 3, figsize=(18, 13))
    fig.patch.set_facecolor('#FAFAFA')

    for idx, (key, title, unit, color) in enumerate(metrics):
        row, col = divmod(idx, 3)
        ax = axes[row][col]
        ax.set_facecolor('white')

        x25 = [all_days.index(d)+1 for d in sorted(data_2025.keys()) if d in all_days]
        x26 = [all_days.index(d)+1 for d in sorted(data_2026.keys()) if d in all_days]
        y25 = [data_2025[d][key] for d in sorted(data_2025.keys()) if d in all_days]
        y26 = [data_2026[d][key] for d in sorted(data_2026.keys()) if d in all_days]

        if key in ('dau','pay_pv'):
            y25 = [v/10000 for v in y25]
            y26 = [v/10000 for v in y26]

        ax.plot(x25, y25, color='#AAAAAA', linestyle='--', linewidth=1.5, alpha=0.7, label='2025', zorder=2)
        ax.plot(x26, y26, color=color, linestyle='-', linewidth=2.2, marker='o', markersize=4, label='2026', zorder=3)

        v = cur[key]
        p = prev.get(key); vd_val = yd.get(key); vw_val = yw.get(key)
        mom_str = f'环{"↑" if (v-p)/p>0 else "↓"}{abs((v-p)/p*100):.1f}%' if p else ''
        yoy_d_str = f'日同{"↑" if (v-vd_val)/vd_val>0 else "↓"}{abs((v-vd_val)/vd_val*100):.1f}%' if vd_val else ''
        yoy_w_str = f'周同{"↑" if (v-vw_val)/vw_val>0 else "↓"}{abs((v-vw_val)/vw_val*100):.1f}%' if vw_val else ''

        vdisp = v/10000 if key in ('dau','pay_pv') else v
        fmt = f'{vdisp:.1f}{unit}' if key in ('dau','pay_pv') else (f'{v:.3f}%' if key=='conv_rate' else f'{v:.2f}%')
        ann = f'{fmt}\n{mom_str} {yoy_d_str}\n{yoy_w_str}'

        y_latest = v/10000 if key in ('dau','pay_pv') else v
        ymin, ymax = min(y26), max(y26)
        offset = (ymax - ymin) * 0.12
        yt = y_latest + offset if y_latest < ymax - offset else y_latest - offset * 1.5

        ax.annotate(ann, xy=(latest_x, y_latest), xytext=(latest_x-4.5, yt),
                    fontsize=7, color=color,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.85),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1))

        ax.set_title(title, fontsize=10, fontweight='bold', color='#333333')
        ax.set_xticks(range(1, max_day_num + 1))
        ax.set_xticklabels([f'{int(d[:2])}/{int(d[3:])}' for d in all_days], fontsize=6, rotation=45)
        ax.tick_params(axis='y', labelsize=7)
        ax.legend(fontsize=7, loc='upper left')
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[2][1].set_visible(False)
    axes[2][2].set_visible(False)

    fig.suptitle(f'消电数据监控 | 2025 vs 2026 趋势对比（截至 {date_str}）',
                 fontsize=14, fontweight='bold', color='#222222', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == '__main__':
    main()
