#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 exploration_淑芬_2026-07-23.json 生成 summary.md 与 hypotheses.md。
口径严格按 agents/数据分析.md 与 References/output-schemas.md。"""
import json

DT = "2026-07-23"
OUT = "analysis_reports/"
d = json.load(open(f"{OUT}exploration_淑芬_{DT}.json", encoding="utf-8"))

mods = {m["module"]: m for m in d["modules"]}
median_ctr = d["_meta"]["median_uv_ctr_primary"]
ho = d["home_overall"]
nu = d["n_users"]
ld = d["user_layer_distribution"]
sd = d["user_source_distribution"]
stay = d["stay_duration"]
fd = d["feed_depth"]
cap = mods["场馆tab"].get("exposure_capped")
pages = {p["page_id"]: p for p in d["pages"]}
inc = d["incremental"]["net_new"]

# ranked with ctr values (exclude None / zero-exposure new modules)
mm = [m for m in d["modules"] if m["exposure_uv"] > 0 and m["uv_ctr"] is not None]
by_ctr_desc = sorted(mm, key=lambda m: -m["uv_ctr"])
by_exp_desc = sorted(mm, key=lambda m: -m["exposure_uv"])
chi = {c["module"]: c for c in d["chi_square_layer_vs_click"]}

def pct(x, nd=2):
    return "na" if x is None else f"{x*100:.{nd}f}%"

# ---------------- summary.md ----------------
S = []
S.append(f"# 首页数据洞察 · 数据分析摘要（{DT}）\n")
S.append("> 本摘要为流水线 Step2 产物，供下游质量检查/洞察结论生成 agent 直接消费。数值口径见 exploration JSON。\n")

S.append("## 一、高管摘要\n")
S.append(f"- 当日抽样 **{nu:,}** 名访问用户（1/339 哈希桶抽样），分层 z0={pct(ld['z0'])} / z1-z3={pct(ld['z1-z3'])} / z4-z5={pct(ld['z4-z5'])}；来源以新媒体召回（{sd['新媒体召回']:,}）+ 自然留存（{sd['自然留存']:,}）为主。")
S.append(f"- 首页（G1001）整体有效使用充分：曝光 UV **{ho['exposure_uv']:,}**，剔离场型点击后页面级 UV-CTR **{pct(ho['uv_ctr'])}**（看到首页的人里约七成在页内点了至少一次）。")
top3 = "、".join(f"{m['module']}({pct(m['uv_ctr'])})" for m in by_ctr_desc[:3])
bot3 = "、".join(f"{m['module']}({pct(m['uv_ctr'])})" for m in by_ctr_desc[-3:])
S.append(f"- 模块 UV-CTR 排行：高位 {top3}；低位 {bot3}。中位 UV-CTR = {pct(median_ctr)}（有曝光模块，剔 capped 场馆tab）。")
S.append(f"- 分层差异集中在**新用户 z0 转化反而更高**：金刚位（z0 {pct(mods['金刚位']['by_user_type']['z0']['uv_ctr'])} vs z4-z5 {pct(mods['金刚位']['by_user_type']['z4-z5']['uv_ctr'])}）、回收模块（z0 {pct(mods['回收模块']['by_user_type']['z0']['uv_ctr'])} vs z4-z5 {pct(mods['回收模块']['by_user_type']['z4-z5']['uv_ctr'])}）在 z0 上显著更高，卡方检验显著。")
S.append(f"- 四页对比：首页 G1001 曝光 UV {pages['G1001']['overall']['exposure_uv']:,} 占绝对主体；奢品馆/兴趣圈/数码集三页净增曝光 UV 仅 {inc['exposure_uv']}（{pct(inc['exposure_uv_pct'],2)}）、净增点击 UV {inc['click_uv']}，场馆页几乎不带来独立触达增量。\n")

S.append("## 二、方法论\n")
S.append("- 抽样：当日 1/339 哈希桶抽样用户名单（data1），事件表（data2/3/4）自带行内 user_type/user_source，分层/来源切分一律用事件表行内列——事件表 token 与 data1 哈希格式不同、无法 join，token_coverage 仅作数据质量说明。")
S.append("- CTR 唯一口径 = UV-CTR = 点击 UV / 曝光 UV（看到模块的人里多少点了），PV-CTR 已废弃。")
S.append("- 模块切分按 section-to-module.json 常量字典（11 核心模块 × 四页 G1001-G1004），未列入归「其他」。")
S.append("- 页面级 CTR 分子剔「离场型」点击：首页剔底部导航(500)，场馆页剔场馆tab(106)+底部导航。§2 模块矩阵/§3 增量/§4 分层用全口径。")
S.append(f"- 场馆tab(106) 曝光埋点漏报触发 cap：原始曝光 UV {cap['raw_exposure_uv']:,} / 首页曝光 UV = {cap['ratio_to_home']} < 0.90，分母改用首页曝光 UV 重算 CTR。")
S.append("- 异动判定：读近 28 天（4 整周）模块日度基线，主判据 z_window（整窗均值/标准差）+ 辅判据 z_dow（同星期几，扣周内周期），铁律 |z_window|≥2 且 |z_dow|≥2 且同号才算真异动。")
S.append("- 分层差异检验：每模块曝光×点击的 2×3 列联表卡方 + Cramér's V 效应量（大样本下 p 显著须配效应量判读）。\n")

S.append("## 三、关键洞察\n")
S.append(f"- **去周期异动（主判据）**：primary_page(G1001) home_overall + 11 模块 × 5 指标的双判据（z_window & z_dow 同号 ≥2）**均未触发**，当日全部落在近 28 天正常波动/周内周期内，无真实异动机会点。基线 status=ok。")
d1true = [x for x in d["anomaly_vs_d_minus_1"]["details"] if x["anomaly"]]
if d1true:
    txt = "、".join(f"{x['scope']}·{x['metric']}({pct(x['delta_pct'])})" for x in d1true)
    S.append(f"- **D-1 交叉参考（非主判据）**：与昨日单基线比有几处 |delta|≥30%：{txt}。这些在去周期基线下均未构成异动——品牌墙(301)为新增模块基数极小（曝光 UV 2）、栏目区/大促banner 属日波动大的低量模块，判为噪声，不下钻。")
S.append(f"- **最显著分层差异**：金刚位卡方 {chi['金刚位']['chi2']}（Cramér's V {chi['金刚位']['cramers_v']}）、回收模块卡方 {chi['回收模块']['chi2']}（V {chi['回收模块']['cramers_v']}）、商卡feed流卡方 {chi['商卡feed流']['chi2']}（V {chi['商卡feed流']['cramers_v']}）均显著；方向一致为 **z0 新用户在金刚位/回收模块转化更高，但在商卡feed流反而更低**（z0 {pct(mods['商卡feed流']['by_user_type']['z0']['uv_ctr'])} vs z1-z3 {pct(mods['商卡feed流']['by_user_type']['z1-z3']['uv_ctr'])}）。效应量均为小量级（V<0.08），业务意义方向性为主。")
S.append(f"- **高曝光低 CTR 候选**：{'、'.join(c['module'] for c in d['high_exposure_low_uv_ctr_candidates'])}（场馆tab 曝光量级第一但 CTR 仅 {pct(mods['场馆tab']['uv_ctr'])}，且受埋点 cap 影响，属先修数据而非直接业务提升）。大促banner UV-CTR {pct(mods['大促banner']['uv_ctr'])}、feed轮播图 {pct(mods['feed轮播图']['uv_ctr'])} 为倒数低位，需结合是否展示型/运营位预期判定。")
S.append(f"- **feed 流深度**：有 feed 曝光用户 {fd['global']['user_count_with_feed_exposure']:,}，人均曝光坑位 {fd['global']['mean']}（p50={fd['global']['p50']}、p90={fd['global']['p90']}），多数用户浅层浏览。")
S.append(f"- **停留时长**：首页人均停留 {pages['G1001']['overall']['duration_mean_seconds']}s（仅覆盖有正时长记录者），全站时长覆盖率仅 {pct(stay['coverage'])}——该均值只代表有记录的那部分人，仅供组间相对比较。\n")

S.append("## 四、局限性\n")
S.append(f"- **单日 + 抽样**：明细为当日 1/339 抽样，比例指标稳健、绝对量需乘 ratio 上推全量；因果推断仍需 A/B 或实验。")
S.append(f"- **场馆tab 埋点 cap**：曝光漏报（ratio {cap['ratio_to_home']}），其 CTR 为修复分母后的估计值，「低 CTR」首先是数据问题不是业务问题。")
S.append(f"- **时长覆盖率低**：仅 {pct(stay['coverage'])} 访问用户有有效正时长，时长结论不可当全体绝对停留。")
S.append(f"- **场馆页样本小**：G1002/3/4 曝光 UV 分别 {pages['G1002']['overall']['exposure_uv']}/{pages['G1003']['overall']['exposure_uv']}/{pages['G1004']['overall']['exposure_uv']}，分层三维仅方向参考。")
S.append(f"- **品类tab/品牌墙**：首页几乎无曝光（品类tab 曝光 UV 0、品牌墙 2），本页不作机会判断。")
S.append(f"- **unmapped 曝光占比 {pct(d['module_unmapped_summary']['exposure_pv_pct'])}**：首页有相当比例曝光行 section 未映射到 11 核心模块（含容器/浮层类与其他动态位），归「其他」不计入核心模块统计。\n")

S.append("## 五、建议（后续分析方向，非业务动作）\n")
S.append("- 大促banner / feed轮播图 的低 CTR 需结合「是否展示/运营位、活动是否空窗」定性，再判是否真机会点（见 hypotheses H7）。")
S.append("- 场馆tab 曝光埋点漏报建议交质量检查/埋点 Owner 复核，修复后再评估其真实 CTR。")
S.append("- z0 新用户在金刚位/回收模块转化更高、在 feed 流更低的分化，值得结合下游转化与承接路径进一步下钻。")
S.append("- 场馆页几乎无独立增量，是否值得维持四 tab 结构可结合更长周期趋势判断。\n")

open(f"{OUT}exploration_淑芬_{DT}.summary.md", "w", encoding="utf-8").write("\n".join(S))
print("wrote summary.md")

# ---------------- hypotheses.md ----------------
H = []
H.append(f"# 首页数据洞察 · 候选假设清单（{DT}）\n")
H.append("> 按业务关心 10 问组织，每条假设含类型/证据/反向/优先级。本 agent 只到「假设+证据」，不下因果结论、不给优化建议。\n")

def mod_line(name):
    m = mods[name]
    return f"曝光UV {m['exposure_uv']:,}、点击UV {m['click_uv']:,}、UV-CTR {pct(m['uv_ctr'])}、覆盖率 {pct(m['exposure_coverage'])}"

H.append("## Q1 首页整体有没有被有效使用？\n")
H.append("### H1：首页整体被有效使用，页面级有效 UV-CTR 处于健康高位\n")
H.append("- 类型：描述")
H.append(f"- 证据：首页曝光 UV {ho['exposure_uv']:,}，剔离场型点击后页面级 UV-CTR {pct(ho['uv_ctr'])}（全口径 {pct(pages['G1001']['overall']['uv_ctr_full'])}）。样本 n={nu:,}。")
H.append("- 反向：需与历史窗口页面级 CTR 比对确认是否处于常态区间；单日无法判趋势。")
H.append("- 优先级：低（现状描述，非机会点）\n")

H.append("## Q2 首页模块结构是否影响用户行为？\n")
H.append("### H2：模块 CTR 呈明显梯队，搜索框/金刚位为高转化承接主体\n")
H.append("- 类型：描述")
H.append(f"- 证据：UV-CTR 高位 搜索框 {pct(mods['搜索框']['uv_ctr'])}、金刚位 {pct(mods['金刚位']['uv_ctr'])}、商卡feed流 {pct(mods['商卡feed流']['uv_ctr'])}；低位 大促banner {pct(mods['大促banner']['uv_ctr'])}、feed轮播图 {pct(mods['feed轮播图']['uv_ctr'])}。中位 {pct(median_ctr)}。")
H.append("- 反向：CTR 高低受模块性质（搜索/导航 vs 展示/运营位）先天影响，不能仅凭 CTR 判优劣，需结合下游转化。")
H.append("- 优先级：中\n")

H.append("## Q3 用户实际看到了哪些首页内容？\n")
H.append("### H3：首屏常驻模块（搜索框/场馆tab/金刚位/回收/大促banner/feed）覆盖率高，运营型模块（新人条/栏目区）覆盖窄\n")
H.append("- 类型：描述")
H.append(f"- 证据：搜索框覆盖率 {pct(mods['搜索框']['exposure_coverage'])}、金刚位 {pct(mods['金刚位']['exposure_coverage'])}、回收模块 {pct(mods['回收模块']['exposure_coverage'])}；新人条 {pct(mods['新人条']['exposure_coverage'])}、栏目区 {pct(mods['栏目区']['exposure_coverage'])} 覆盖窄（新人条按人群定向属预期）。")
H.append("- 反向：覆盖率低可能是定向展示（新人条仅新人）而非触达不足，需区分「该不该看到」与「没看到」。")
H.append("- 优先级：低\n")

H.append("## Q4 用户在首页内产生了哪些行为？\n")
H.append("### H4：点击集中在搜索栏与金刚位手机类目，feed 流以商品卡点击为主\n")
H.append("- 类型：描述")
H.append("- 证据（子元素常驻排行）：搜索框内「搜索栏」占点击 91.6%；金刚位内「手机」占 54.5%、平板 14.0%、笔记本 11.3%；回收模块「手机数码上门回收」占 72.4%；商卡feed流「商品」占 97.6%。")
H.append("- 反向：子元素为点击侧口径，曝光侧无坑位粒度时无法算子元素真 CTR，占比高不等于效率高。")
H.append("- 优先级：低\n")

H.append("## Q5 不同用户分层在首页上的响应是否不同？\n")
H.append("### H5：z0 新用户在金刚位/回收模块转化显著更高，但在商卡feed流反而更低\n")
H.append("- 类型：相关（分层差异）")
H.append(f"- 证据：金刚位卡方 {chi['金刚位']['chi2']}（V {chi['金刚位']['cramers_v']}，显著），z0 {pct(mods['金刚位']['by_user_type']['z0']['uv_ctr'])} > z4-z5 {pct(mods['金刚位']['by_user_type']['z4-z5']['uv_ctr'])}；回收模块卡方 {chi['回收模块']['chi2']}（V {chi['回收模块']['cramers_v']}），z0 {pct(mods['回收模块']['by_user_type']['z0']['uv_ctr'])} > z4-z5 {pct(mods['回收模块']['by_user_type']['z4-z5']['uv_ctr'])}；商卡feed流卡方 {chi['商卡feed流']['chi2']}（V {chi['商卡feed流']['cramers_v']}），z0 {pct(mods['商卡feed流']['by_user_type']['z0']['uv_ctr'])} < z1-z3 {pct(mods['商卡feed流']['by_user_type']['z1-z3']['uv_ctr'])}。")
H.append("- 反向：效应量均为小量级（V<0.08），大样本下易显著；分层结构本身随当日新增用户涌入而漂移，需控制来源结构后复核。")
H.append("- 优先级：中\n")

H.append("## Q6 是否存在首页整体平稳但内部结构迁移？\n")
H.append("### H6：当日首页整体与各模块均落在去周期正常波动内，无结构迁移信号\n")
H.append("- 类型：描述")
H.append("- 证据：anomaly_vs_baseline 去周期双判据（z_window & z_dow）对 home_overall + 11 模块 × 5 指标全部未触发（0 真异动），status=ok。D-1 交叉参考的几处 |delta|≥30%（品牌墙/栏目区/大促banner）经去周期基线判为噪声，未构成迁移。")
H.append("- 反向：单日无法完整刻画结构迁移，需多日趋势；品牌墙为新增模块，基数小暂不判。")
H.append("- 优先级：低\n")

H.append("## Q7 是否存在高曝光但低价值的位置或内容？\n")
H.append("### H7：大促banner / feed轮播图 高曝光低 CTR，但可能属展示/运营位预期，待定性\n")
H.append("- 类型：相关（待验证）")
H.append(f"- 证据：大促banner 曝光 UV {mods['大促banner']['exposure_uv']:,} 但 UV-CTR 仅 {pct(mods['大促banner']['uv_ctr'])}（倒数低位）；feed轮播图曝光 UV {mods['feed轮播图']['exposure_uv']:,}、UV-CTR {pct(mods['feed轮播图']['uv_ctr'])}（109 运营位，CTR 结构性低于 108 商卡）。")
H.append("- 反向：低 CTR 可能是展示型/品牌位或非活动期空窗的预期表现——需核对当日 banner 是否有活动、feed轮播图是否运营位常态低点，并结合下游 GMV/转化才能判「低价值」，CTR 单指标不足以证伪。")
H.append("- 优先级：中（是否真机会点取决于定性核对）\n")

H.append("## Q8 是否存在某模块提升但挤压其他模块的情况？\n")
H.append("### H8：当日无模块间显著挤压，高曝光模块用户高度重叠（同屏共现）\n")
H.append("- 类型：描述")
top_jac = d["module_co_exposure_jaccard"][:3]
jtxt = "、".join(f"{j['a']}×{j['b']} Jaccard {j['jaccard']}" for j in top_jac)
H.append(f"- 证据：模块共现 Jaccard 前列为 {jtxt}，为正向共现（同屏一起曝光）而非此消彼长；去周期异动全未触发，无「一模块涨另一模块跌」的负相关迁移证据。")
H.append("- 反向：挤压需用户级路径与多日数据判定，单日共现矩阵只能证「无明显挤压」，不能证「一定没有」。")
H.append("- 优先级：低\n")

H.append("## Q9 当前数据是否足够支持机会判断？\n")
H.append("### H9：数据足以支持「现状描述 + 高曝光低 CTR 候选」判断，但不足以定因果\n")
H.append("- 类型：描述")
H.append(f"- 证据：11 模块 × 四页 × 三分层指标齐全，28 天基线支撑去周期异动判定；但时长覆盖率仅 {pct(stay['coverage'])}、场馆tab 曝光埋点漏报、明细为单日抽样，限制因果结论。")
H.append("- 反向：提升型机会的收益量化依赖 UV-CTR 目标假设，属观察数据外推，需实验校准。")
H.append("- 优先级：中\n")

H.append("## Q10 哪些结论必须等真实数据或实验验证？\n")
H.append("### H10：大促banner/feed轮播图「提升空间」与 z0 分层策略均需 A/B 验证\n")
H.append("- 类型：因果/预测（需实验）")
H.append("- 证据：低 CTR 模块「对齐中位 CTR」的增量、z0 定向优化的转化提升，均为观察数据外推。")
H.append("- 反向/实验设计：对目标模块做 A/B（对照=当前坑位/素材，实验=优化版），主指标 UV-CTR，MDE 设 ≥2pp、α=0.05、power=0.8 反算样本量，护栏指标首页整体 GMV 不降；控制节假日/大促节奏/并行实验等混淆。因果结论标「待验证」。")
H.append("- 优先级：中\n")

# app 体验验证小节（软产物 skipped_no_change）
H.append("## app体验机会点验证\n")
H.append("- 本期无 app 体验机会点产出（app_experience_opportunities status=skipped_no_change，wiki revision 未变），跳过体验侧假设检验。\n")

open(f"{OUT}hypotheses_淑芬_{DT}.md", "w", encoding="utf-8").write("\n".join(H))
print("wrote hypotheses.md")
