#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_dimension.py — 核心底表分维度切分 + 漏斗链指标计算

输入：底表取数结果（csv/xlsx，列与 references/字段映射与指标口径.md 一致）
输出：tidy 长表 CSV（每行一个维度值×日期，拆出 端/来源/资产/三级场景/业务/品类 列 + 漏斗链派生指标）

口径要点（见 references/字段映射与指标口径.md）：
  - matched_dau_uv 是"分维度匹配"的 DAU 分母，pay_pv/matched_dau_uv（dau-净支付pv转化率）
    是【北极星】、可跨维度比大小（与旧表 uv_all 全局常数相反）。
  - matched_dau_uv 为 NULL 的行不能算任何 DAU 类比率，绝不当 0；本脚本用 where(denom>0) 使其自然为 NaN。

用法：
  python analyze_dimension.py --input raw.csv --out tidy.csv
  python analyze_dimension.py --input raw.csv --out tidy.csv --tag '3维度交叉-端_业务/品类_用户来源'
"""
import argparse, sys
import pandas as pd

# 四大维度枚举值（真源见 references/维度体系与样例数据.md；新增值同步这里）
TERMINALS = ['转转APP', '转转小程序', '找靓机']
SOURCES   = ['新媒体召回', '新媒体新增', '自然新增', '自然留存']
ASSETS    = ['z0', 'z1', 'z2', 'z3', 'z4', 'z5']
SCENE_MAIN = ['首页feeds', '首页金刚位', '首页栏目区', '馆', '大促三切分',
              '商详同款推荐', '搜索', '找靓机-不区分场景', '其他']
SCENE_02   = ['搜索', '首页', '奢品馆', '兴趣馆', '数码馆', '其他']
SCENE_03   = ['搜索', '首页feeds', '首页栏目区', '首页金刚位',
              '馆金刚位', '馆feed流', '馆栏目区', '其他']

NUM_COLS = ['exp_pv','exp_uv','detail_pv','detail_uv','order_pv','order_uv','pay_pv','matched_dau_uv']


def asset_band(z):
    if z == 'z0': return '新用户(z0)'
    if z in ('z1','z2','z3'): return '浅用户(z1-z3)'
    if z in ('z4','z5'): return '老用户(z4-z5)'
    return None


def _assign_goods(out, seg):
    """seg 形如 '业务消费电子' / '品类二奢包袋' / '业务_消费电子' / '品类_消费电子手机'。"""
    if not seg:
        return
    s = seg.replace('_', '')
    if s.startswith('业务'):
        out['goods_level'] = '业务'; out['cate'] = s[len('业务'):]
    elif s.startswith('品类'):
        out['goods_level'] = '品类'; out['cate_02'] = s[len('品类'):]
    elif s:
        out['goods_level'] = '其他'; out['cate_02'] = s


def parse_wd(tag, wd):
    """按 tag_01 决定的字段顺序，从 wd 反向/前向匹配枚举值切出各维度。"""
    out = {'duan': None, 'user_source': None, 'user_type': None, 'asset_band': None,
           'main_scene': None, 'scene_02': None, 'scene_03': None,
           'goods_level': None, 'cate': None, 'cate_02': None}
    if wd is None or (isinstance(wd, float)):
        return out
    if tag == '整体':
        out['goods_level'] = '整体'; return out

    # 单维度族：wd 本身就是一个维度值
    if tag == '单维度-拆分端':
        out['duan'] = wd; return out
    if tag == '单维度-拆分用户来源':
        out['user_source'] = wd; return out
    if tag == '单维度-拆分用户资产分层':
        out['user_type'] = wd; out['asset_band'] = asset_band(wd); return out
    if tag == '单维度-拆分场景':
        out['main_scene'] = wd; return out
    if tag == '单维度-拆分scene_02':
        out['scene_02'] = wd; return out
    if tag == '单维度-拆分scene_03':
        out['scene_03'] = wd; return out
    if tag == '单维度-拆分品类':
        _assign_goods(out, wd); return out

    parts = [p for p in str(wd).split('_') if p != '']

    # scene 组合族：wd 前缀为 <scene_02>_<main_scene>
    if 'scene组合' in tag:
        if parts and parts[0] in SCENE_02:
            out['scene_02'] = parts.pop(0)
        if parts and parts[0] in SCENE_MAIN:
            out['main_scene'] = parts.pop(0)

    # 端恒在剩余段首（scene组合族里端在场景之后）
    if parts and parts[0] in TERMINALS:
        out['duan'] = parts.pop(0)
    elif parts:
        # 无分隔符粘连（如 2维度交叉-端_用户来源 族 wd='转转APP新媒体召回'）：端作前缀粘在段首
        for t in sorted(TERMINALS, key=len, reverse=True):
            if parts[0].startswith(t):
                out['duan'] = t
                parts[0] = parts[0][len(t):]
                if parts[0] == '':
                    parts.pop(0)
                break

    # 从尾部反向吃掉 场景(main) / 来源 / 资产层
    def pop_tail(pool):
        if parts and parts[-1] in pool:
            return parts.pop()
        return None

    if '场景' in tag and out['main_scene'] is None:
        out['main_scene'] = pop_tail(SCENE_MAIN)
    if '用户来源' in tag:
        out['user_source'] = pop_tail(SOURCES)
    if '资产分层' in tag:
        z = pop_tail(ASSETS)
        out['user_type'] = z; out['asset_band'] = asset_band(z)

    # 剩下就是货段（业务X 或 品类XY），中文可能被 split 拆开，拼回再判
    _assign_goods(out, '_'.join(parts))
    return out


def load(path):
    if path.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(path, sheet_name=0)
    else:
        df = pd.read_csv(path)
    zh2en = {'口径':'tag_01','维度':'wd','曝光pv':'exp_pv','曝光uv':'exp_uv',
             '商详pv':'detail_pv','商详uv':'detail_uv','下单pv':'order_pv','订单pv':'order_pv',
             '下单uv':'order_uv','订单uv':'order_uv','净支付pv':'pay_pv',
             '活跃uv':'matched_dau_uv','dau':'matched_dau_uv','日期':'dt'}
    df = df.rename(columns={c: zh2en.get(c, c) for c in df.columns})
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--tag', default=None, help='只保留某个 tag_01 口径族')
    args = ap.parse_args()

    df = load(args.input)
    if 'dt' in df.columns:
        df['dt'] = df['dt'].astype(str).str.slice(0, 10)
    if args.tag:
        df = df[df['tag_01'] == args.tag].copy()
    if df.empty:
        print('[ERR] 过滤后无数据，检查 --tag 是否匹配', file=sys.stderr); sys.exit(1)

    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    dims = df.apply(lambda r: parse_wd(r['tag_01'], r.get('wd')), axis=1, result_type='expand')
    out = pd.concat([df.reset_index(drop=True), dims.reset_index(drop=True)], axis=1)

    def safe(a, b, nd):
        return (out[a] / out[b]).where(out[b] > 0).round(nd)

    # 北极星 + 漏斗四环节（matched_dau_uv 为 NULL/0 时自动 NaN，不填 0）
    out['dau_pay_rate']       = safe('pay_pv', 'matched_dau_uv', 6)   # 北极星
    out['exp_penetration']    = safe('exp_uv', 'matched_dau_uv', 5)   # 曝光渗透率
    out['detail_reach']       = safe('detail_uv', 'exp_uv', 4)        # 商详到达率
    out['order_rate']         = safe('order_uv', 'detail_uv', 4)      # 下单率
    out['pay_rate']           = safe('pay_pv', 'order_uv', 4)         # 支付率
    # 组合率
    out['detail_penetration'] = safe('detail_uv', 'matched_dau_uv', 5)  # 商详渗透率
    out['detail_pay_rate']    = safe('pay_pv', 'detail_uv', 5)          # 商详转化率
    out['bag_rate']           = safe('pay_pv', 'exp_uv', 5)             # 提袋率

    # 百分比展示列（×100）。原始小数列必须保留：
    #   质检的「北极星=漏斗四环节连乘」自洽校验用小数算，转百分比会破坏链乘。
    #   图表/报告/飞书正文一律读 *_pct 展示。
    #   ⚠️ 北极星 dau_pay_rate 保留【3 位小数】(X.XXX%，全局强制规则)，其余比率 2 位。
    RATE_COLS = ['dau_pay_rate','exp_penetration','detail_reach','order_rate','pay_rate',
                 'detail_penetration','detail_pay_rate','bag_rate']
    for c in RATE_COLS:
        if c in out.columns:
            nd = 3 if c == 'dau_pay_rate' else 2
            out[f'{c}_pct'] = (out[c] * 100).round(nd)

    out.to_csv(args.out, index=False, encoding='utf-8-sig')
    print(f'[OK] {len(out)} 行 → {args.out}')
    null_dau = int(out['matched_dau_uv'].isna().sum()) if 'matched_dau_uv' in out else -1
    print(f'     matched_dau_uv NULL 行数: {null_dau}')
    print('[口径] 北极星=dau_pay_rate(pay_pv/matched_dau_uv)，可跨维度比；'
          'NULL 分母行的 DAU 类比率为空，勿当 0。')


if __name__ == '__main__':
    main()
