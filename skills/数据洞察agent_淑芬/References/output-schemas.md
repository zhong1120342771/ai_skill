# Output Schemas

> 流水线四步之间的契约。任何步骤的产物字段都必须按本文件定义,不允许 sub-agent 自行加字段或改字段名——下游脚本(Scripts/qa_check.py / Scripts/render_charts.py / Scripts/feishu_publish.py)按这里的 key 直接读。

如需新增字段,先在本文件加 schema,再改产生方与读取方,严禁先污染产物再补文档。

> **页面范围(2026-07-13 起默认四页)**:分析默认覆盖 G1001 首页 + G1002 奢品馆 + G1003 兴趣圈 + G1004 数码集,核心模块 11 个(2026-07-15 起 108 商卡feed流与 109 feed轮播图拆开;见 `section-to-module.json`)。`modules[]` 主块仍是 **primary_page(G1001 首页)** 的 11 模块(机会计算器/conv_aov 主排页读它,"首页为主");四页对比、page×module 矩阵、page×module×layer、增量拆解走新增的 **`pages[]` 块**(场馆页供结构参考)。参数化双模:`section-to-module.json` 的 `pages` 改成 `["G1001"]` 时退回单页,`pages[]` 只有一页、口径不变。

## 一、`analysis_reports/exploration_淑芬_${dt}.json` (Step 2 数据分析产出)

```jsonc
{
  "dt": "YYYY-MM-DD",
  "n_users": 9314,
  "user_layer_distribution": { "z0": 0.0952, "z1-z3": 0.7129, "z4-z5": 0.1918 },
  "user_source_distribution": { "新媒体召回": 5240, "自然留存": 3187, "新媒体新增": 445, "自然新增": 442 },
  "token_coverage": { "data2-2": 1.0, "data3-2": 1.0, "data4-2": 1.0 },

  "home_overall": { "exposure_uv": 8000, "exposure_pv": 60000, "click_uv": 7300, "click_pv": 4900, "uv_ctr": 0.9125 },

  "modules": [
    {
      "module": "搜索框",                 // 必须来自 References/section-to-module.json 的 core_modules
      "exposure_uv": 7749,
      "exposure_pv": 41237,               // 仍上报,用于"人均曝光 PV"等量级,但不再计算 PV-CTR
      "click_uv": 4001,
      "click_pv": 7002,                   // 仍上报,用于全量点击 PV 量级展示,但不再计算 PV-CTR
      "uv_ctr": 0.516196,                 // = click_uv / exposure_uv,**唯一 CTR 口径**(看到的人里有多少点了)
      "exposure_coverage": 0.831973,      // 该模块曝光 UV / n_users
      "exposure_pv_per_uv": 5.3216,
      "by_user_type":   { "z0": {...}, "z1-z3": {...}, "z4-z5": {...} },   // 子 dict 同上数值字段(只算 uv_ctr,不再有 pv_ctr)
      "by_user_source": { "新媒体召回": {...}, "自然留存": {...}, ... }
    }
    // 其余 7 个 core_modules
  ],

  "module_unmapped_summary": { "exposure_pv_pct": 0.04 },
  "chi_square_layer_vs_click": [
    { "module": "回收模块", "df": 2, "chi2": 63.02, "threshold_p05": 5.99, "significant": true }
  ],
  "high_exposure_low_uv_ctr_candidates": [
    { "module": "栏目区", "rank_exposure": 1, "uv_ctr": 0.0191, "uv_ctr_rank_from_bottom": 2 }
  ],
  "feed_depth": {
    "global": { "user_count_with_feed_exposure": 6776, "p50": 2, "p90": 27, "mean": 10.96, "max": 713 },
    "by_user_type": {
      "z0":    { "user_count": 726,  "p50": 3, "p90": 31, "mean": 13.69 },
      "z1-z3": { "user_count": 4730, "p50": 1, "p90": 29, "mean": 10.48 },
      "z4-z5": { "user_count": 1320, "p50": 1, "p90": 25, "mean": 11.29 }
    }
  },
  "stay_duration": { "p50_seconds": 23, "p90_seconds": 187, "n_users_with_duration": 4944 },
  "module_co_exposure_jaccard": [ { "a": "金刚位", "b": "栏目区", "jaccard": 0.71 } ],
  "anomaly_vs_d_minus_1": {
    "status": "ok",
    "details": [
      { "scope": "home_overall", "metric": "exposure_pv", "today": 426499, "prev": 443255, "delta_pct": -0.0378, "anomaly": false },
      { "scope": "搜索框",       "metric": "uv_ctr",      "today": 0.516196, "prev": 0.518071, "delta_pct": -0.0036, "anomaly": false }
    ]
  },
  "anomaly_vs_7d": { "status": "ok", "details": [ /* 同上结构 */ ] },
  "anomaly_vs_baseline": {                            // 去周期异动判定:28 天(4整周)整窗均值/标准差 + 同星期几双判据
    "status": "ok",                                   // ok / unavailable(基线软产物缺失或 status≠ok,退回 D-1 单基线)
    "window_days": 28,                                // 参考窗 = dt-28..dt-1;每星期几恰好 4 次,整窗均值无星期偏差
    "baseline_source": "module_daily_baseline_${dt}.csv",
    "dow_of_dt": 3,                                   // dt 是星期几(0=周一..6=周日),辅判据用它挑同星期几历史点
    "details": [
      {
        "scope": "回收模块",                          // home_overall 或 11 模块之一(primary_page)
        "metric": "uv_ctr",                           // uv_ctr / exposure_uv / click_uv / exposure_pv / click_pv
        "today": 0.0431,
        "window_mean": 0.0489,                        // 主判据:整窗(28天)均值
        "window_std": 0.0021,                         // 整窗标准差(样本标准差,ddof=1)
        "z_window": -2.76,                            // 主判据 z = (today-window_mean)/window_std
        "dow_mean": 0.0478,                           // 辅判据:历史同星期几(4个点)均值,扣周内周期
        "dow_std": 0.0015,                            // 同星期几标准差(点数少,std 可能不稳,<3 点时置 null)
        "z_dow": -3.13,                               // 辅判据 z(去周期);同星期几点数<2 时置 null
        "n_window_days": 28,                          // 实际参与整窗统计的历史天数(缺分区会 <28)
        "n_dow_days": 4,                              // 实际参与同星期几统计的历史天数
        "anomaly": true,                              // 铁律:仅当 |z_window|≥2 且 |z_dow|≥2(同号) 才 true;去周期后仍显著
        "direction": "down"                           // up / down / flat
      }
    ]
  },
  "ctr_data_quality_issues": [],
  "notable_findings": ["..."],
  "ranked_by_uv_ctr_desc": ["搜索框", "金刚位", ...],
  "ranked_by_exposure_desc": ["栏目区", ...],
  "module_subelement_rank": [                        // 子元素常驻排行:每个点击 UV≥100 的主要模块一块
    {
      "module": "金刚位", "section_id": "100",
      "subelements": [                               // 按 click_uv 降序 Top10,超出截断并补"其余合计"行
        {
          "sortName": "手机",                        // 区域内子元素中文名(同 section 内唯一);缺失/null/0 归"未命名"单列
          "tabName": null,                           // 多 tab 模块(如场馆tab)才填,否则 null
          "click_uv": 1907,                          // distinct token,抽样值,全量乘 ratio
          "exposure_uv": null,                       // 该模块曝光无坑位粒度时 null(报告标注),有则填
          "uv_ctr": null,                            // = click_uv/exposure_uv;exposure_uv 为 null 时置 null(只给点击 UV+占比)
          "click_uv_share": 0.51,                    // 该子元素点击 UV 占模块内占比(比例,不乘 ratio)
          "sample_warn": false                       // click_uv < 30 → true,报告标"子元素级样本不足,仅方向参考"
        }
        // ... 其余子元素
      ]
    }
    // ... 其余主要模块
  ]
}
```

**契约要点:**

- **`modules[]` 长度恒为 11**(2026-07-13 起新增品类tab/品牌墙;2026-07-15 起 109 feed轮播图从商卡feed流拆出),对应 primary_page(G1001 首页)的 11 核心模块;缺一个就是上游问题,QA 直接 hard 失败。单页模式(`pages=['G1001']`)下品类tab/品牌墙首页无曝光,允许这两个模块的 exposure_uv=0(不算缺失);feed轮播图(109)首页有曝光,不属此豁免。
- `by_user_type` 三档键名固定 `z0` / `z1-z3` / `z4-z5`(短横线,不是下划线)。
- 所有 ctr 字段都是 0.xxx 的小数,不是百分号字符串。
- **CTR 唯一口径 = `uv_ctr` = `click_uv / exposure_uv`**(看到模块的人里有多少点了)。**`pv_ctr` / 历史 `ctr` 字段已废弃**,Step 2 sub-agent 不再产出,下游脚本不再读;`exposure_pv` / `click_pv` 仍上报(用于"人均曝光 PV"、机会点 PV 体量等量级展示),但**不再计算 PV-CTR**,`home_overall` 同样只算 `uv_ctr`。
- 比例指标推广到全量时**保持不变**(同比例放大,本身不变);只有 `exposure_uv` / `exposure_pv` / `click_uv` / `click_pv` 这些绝对量乘 ratio。
- **`anomaly_vs_baseline`(去周期异动判定,主判据)**:数据源是取数侧软产物 `data_storage/淑芬/module_daily_baseline/module_daily_baseline_${dt}.csv`(近 28 天日度基线,每天在当天范围内 1/339 哈希桶去重独立算,**绝不跨天去重**)。判定规则:
  - **各天单独算 → 对日序列求统计量**:参考分布 = dt-28..dt-1 这 28 天(4 整周)的日值序列;`window_mean`/`window_std` 是整窗均值/样本标准差,`z_window=(today-window_mean)/window_std` 是主判据。
  - **去周内周期(硬要求)**:电商有周一~周日周期,`z_window` 会把"正常的周末低点"误判成异动。故必配辅判据 `z_dow`——只用历史**同星期几**(如 dt 是周三就取过去 4 个周三)的均值/标准差算 z,把周内周期扣掉。28 天整周窗保证每个星期几恰好 4 个点。
  - **`anomaly=true` 铁律**:仅当 `|z_window| ≥ 2` **且** `|z_dow| ≥ 2` **且两者同号**才置 true——即"对整体分布显著、去掉周期后仍显著、方向一致",三条全中才算真异动。任一不满足 → `anomaly=false`,记为"落在正常波动/周期内"。
  - **样本护栏**:`window_std` 或 `dow_std` 为 0(历史全等,罕见)→ 对应 z 置 null 并在 `notable_findings` 标注;同星期几历史点 < 2 → `z_dow=null`,此时**不得**仅凭 `z_window` 判 true(标"去周期基准不足,降级观察")。缺分区致 `n_window_days < 28` 时照常算但报告标注窗口不完整。
  - **基线不可用退回**:基线 CSV 缺失或其 meta `status != ok` → 本块 `status="unavailable"`,Step2 退回旧的 `anomaly_vs_d_minus_1` 单基线判异动,报告显式标注"历史窗不可用,异动判定仅基于 D-1,置信度降低"。
  - `anomaly_vs_d_minus_1` / `anomaly_vs_7d` 保留(向后兼容/交叉参考),但**主判据以 `anomaly_vs_baseline` 为准**;三者结论冲突时以去周期的 baseline 为主,并在 `notable_findings` 记录分歧。
- **`module_subelement_rank` 是常驻子元素排行**(Step 2 无条件产出,不依赖异动):对**每个点击 UV≥100 的主要模块**按 `section_name_zh × sortName`(多 tab 模块叠 `tabName`)聚合,子元素按 `click_uv` 降序取 Top10。`sortName` 缺失/`null`/`0` 归入"未命名"不丢弃;子元素 `click_uv<30` 置 `sample_warn=true`。UV-CTR 仍只用 UV 口径(`exposure_uv` 无坑位粒度时 `uv_ctr` 置 null,只给点击 UV 与占比)。**此块可为空数组**(某天所有模块点击 UV 都<100 时),QA 不因它 hard 失败——它是常驻明细展示,不是硬闸口。下游洞察报告「2.3 内部坑位/子元素拆解」直接读它填表。
- **`pages[]` 是四页对比块**(2026-07-13 起,默认四页;单页模式下只有 G1001 一条):承载逐页整体对比、page×module 矩阵、page×module×layer 三维、增量拆解。schema 见下「§一·补:`pages[]` 四页对比块」。`modules[]` 仍是 primary_page(G1001)的 11 模块主块(向后兼容,机会计算器/conv_aov 读它);`pages[]` 是场馆页对比的增量信息,不替代 `modules[]`。

### §一·补:`pages[]` 四页对比块(exploration JSON 内)

```jsonc
{
  // ... 前述 dt / n_users / modules[] / anomaly_* / module_subelement_rank 等主块照旧 ...
  "pages": [
    {
      "page_id": "G1001",
      "page_name": "首页",
      "is_home": true,
      "overall": {
        "exposure_uv": 9379,               // 该页整体曝光 UV(去重,抽样值)
        "click_uv_full": 8630,             // 全口径点击 UV(含离场型;§3 增量/触达用)
        "click_uv_onpage": 6571,           // 剔离场型后点击 UV(§1 页面级 CTR 分子用)
        "uv_ctr_onpage": 0.7006,           // = click_uv_onpage / exposure_uv,页面级有效 CTR(唯一对外口径)
        "uv_ctr_full": 0.9201,             // 全口径 CTR(仅审计对照,不对外当页面效率)
        "visit_pv": 38258,                 // 访问 PV(抽样值)
        "duration_mean_seconds": 124,      // 人均停留时长(仅有正时长记录的用户,见 duration_coverage)
        "duration_coverage": {             // 时长覆盖率(分母口径,报告必须标注)
          "visit_uv": 8908, "with_pos_duration_uv": 3376,
          "no_duration_uv": 5532, "no_duration_pct": 0.621
        },
        "offpage_strip": {                 // 该页剔了哪些离场型、剔了多少
          "venue_tab_106_stripped": false, "venue_tab_106_click_uv": 385,
          "bottom_nav_500_stripped": true, "bottom_nav_500_click_uv": 7009
        }
      },
      "modules": [                         // 该页 × 11 模块;字段同主块 modules[] 单条(uv_ctr/exposure_uv/click_uv/by_user_type/exposure_capped)
        { "module": "搜索框", "exposure_uv": 7749, "click_uv": 4001, "uv_ctr": 0.5233, "exposure_capped": null, "by_user_type": {"z0":{...},"z1-z3":{...},"z4-z5":{...}} }
        // ... 其余模块;该页无曝光的模块整条省略(不像主块必须凑满11个)
      ],
      "module_layer": [                    // page×module×layer 三维(§4);场馆页分层样本小,仅方向参考
        { "module": "金刚位", "layer": "z0", "exposure_uv": 305, "click_uv": 119, "uv_ctr": 0.3902, "capped": false }
        // ... module × {z0,z1-z3,z4-z5}
      ],
      "layer_exposure_uv": { "z0": 872, "z1-z3": 6669, "z4-z5": 1838 }  // 该页各层整体曝光 UV(热力图 x 轴人数标注 + 场馆tab cap 分母)
    }
    // ... G1002/G1003/G1004
  ],
  "incremental": {                         // §3 增量拆解:三张添加页 vs G1001(全口径点击)
    "home": { "exposure_uv": 9379, "click_uv_full": 8630 },   // G1001 全口径(必须用原始点击,不能复用 §1 剔后值——踩过坑)
    "union_4pages": { "exposure_uv": 9382, "click_uv_full": 8667 },  // 四页合并去重
    "net_new": { "exposure_uv": 3, "exposure_uv_pct": 0.0003, "click_uv": 37, "click_uv_pct": 0.0043 },  // 净增(union − home)
    "per_module_increment": [              // 各模块三页增量(页级口径,同一用户可跨页重复计)
      { "module": "场馆tab", "incr_exposure_uv": 1129, "incr_click_uv": 233 }
    ]
  }
}
```

**`pages[]` 契约要点:**

- **离场型 strip 只作用于 `overall.uv_ctr_onpage`**(页面级对外 CTR 口径),配置见 `section-to-module.json` 的 `page_ctr_offpage_strip`:106 场馆tab 在 G1002/3/4 剔、G1001 不剔;500 底部导航四页统一剔(实际只 G1001 有)。剔按 UV 去重(只点了离场型、没点任何页内模块的用户从分子移除)。`click_uv_full` 保留全口径,`§2 modules[]`/`§3 incremental`/`§4 module_layer` 一律用全口径点击。
- **`incremental.home` 必须用 G1001 原始全口径点击 UV 重算**,不能复用 `overall.click_uv_onpage`(剔后值)——历史踩过坑:首页 §3 曝光/点击从全口径错成剔后值,量级失真。
- `page×module×layer`(`module_layer`)场馆页每格样本很小(如 G1003 各层 14/59/26 人),`uv_ctr` 仅方向参考,不做 χ² 显著性。
- 场馆tab cap 在 `pages[].modules[]` 内逐页判定(分母换该页 `overall.exposure_uv` 或对应层 `layer_exposure_uv`),规则同主块 `exposure_capped`。
- **`duration_coverage`**:仅 24.5%~37.9% 访问用户有有效正时长(其余 eventduration 缺失、非负值),`duration_mean_seconds` 只代表有记录的那部分人,报告必须标覆盖率、说明仅组间相对比较。
- 单页模式(`pages=['G1001']`)下 `pages[]` 只有 G1001 一条、`incremental` 各字段 net_new=0,报告退回单页叙事。
- **场馆tab(section_id=106)曝光埋点 cap 规则**:Step 2 sub-agent 在写 `modules[]` 前必须检查 `venue_tab.exposure_uv / home_overall.exposure_uv`;若 < 0.90,触发 cap——`exposure_uv` 改写为 `home_overall.exposure_uv`,`uv_ctr` 用新分母重算,新增字段 `exposure_capped`(见下示例)记录原始值与触发原因。`exposure_pv` / `click_pv` 不变(仍记录场馆tab 自己的原始 PV);PV-CTR 已废弃故无需置 null。同样规则递归应用到 `by_user_type` 的三个分层(各分层的 `exposure_uv` 改记为 `home_overall.by_user_type[layer].exposure_uv`)。

```jsonc
// 场馆tab 触发 cap 后的形态(必须包含 exposure_capped 字段,这样下游知道是修复值)
{
  "module": "场馆tab",
  "exposure_uv": 8514,        // 已替换为首页曝光 UV(uv_ctr 的分母)
  "exposure_pv": 1010,        // 保留场馆tab 自身原始埋点 PV(漏报,但不再用作 CTR 分母)
  "click_uv": 354,
  "click_pv": 523,            // 点击数据照常
  "uv_ctr": 0.041579,         // = click_uv / 8514,唯一 CTR 口径
  "exposure_capped": {
    "rule": "venue_tab_section_106",
    "raw_exposure_uv": 590,   // 原始埋点 UV,留作可追溯
    "raw_exposure_pv": 1010,  // 原始埋点 PV(漏报,与 exposure_pv 同值)
    "raw_uv_ctr": 0.6,        // 原始(误导性)UV-CTR,仅供审计
    "ratio_to_home": 0.0693,  // = 590 / 8514,触发阈值 < 0.90
    "reason": "曝光埋点漏报,场馆tab 是首页常驻 tab,曝光 UV 理应 ≈ 首页曝光 UV"
  }
}
```

## 二、`analysis_reports/quality_check_淑芬_${dt}.json` (Step 3 质量闸口产出)

```jsonc
{
  "dt": "YYYY-MM-DD",
  "passed": true,                         // = (hard_failures 为空)
  "hard_failures": [
    { "check": "11 个核心模块覆盖", "actual": 10, "threshold": 11, "detail": "缺失:回收模块" }
  ],
  "soft_failures": [
    { "check": "中文映射成功率", "actual": 0.93, "threshold": 0.95 }
  ],
  "warnings": [
    { "check": "金刚位CTR异常", "actual": 0.62, "details": "..." }
  ],
  "scores": { "completeness": 0.99, "validity": 1.0, "consistency": 0.96 },
  "row_counts": { "data1": 9314, "data2-2": 426499, "data3-2": 34165, "data4-2": 270710 },
  "user_layer_distribution": { "z0": 0.0952, "z1-z3": 0.7129, "z4-z5": 0.1918 },
  "user_source_distribution": { "新媒体召回": 5240, "自然留存": 3187, "新媒体新增": 445, "自然新增": 442 },
  "spot_recompute": [
    { "module": "金刚位", "ctr_from_csv": 0.0626, "ctr_from_exploration": 0.0626, "delta": 0.0 }
  ],
  "checks_passed": ["data1 行数", "token 互检", "..."],
  "notes": "可选自由文本,记录本次跑的特殊解释"
}
```

**契约要点:**

- `passed = (len(hard_failures) == 0)`。soft_failures / warnings 不影响 passed。
- 编排器读 `passed` 决定是否进入 Step 4;sub-agent 不能伪造 passed=true 来过闸。

## 三、`data_storage/dau_full_淑芬_${dt}.csv` (Step 1 附加产物 — 全量 DAU)

由 `Scripts/dau_query.sql` 经 oneservice_cli 执行后落盘,**Step 4 报告正文"全量推广量级"的分母**。两列固定:

```csv
dt,uv
2026-06-16,3111817
```

**契约要点:**

- `uv` 是当日转转 App 的 distinct token 数(去重后日活),不是 PV。
- Step 4 计算 `ratio = dau_full.uv / exploration.n_users` 作为推广倍率,UV/PV 类指标乘以 ratio 上推全量;**CTR / 覆盖率 / spread 类比例指标不变**(分子分母同比放大,本身保持)。
- 抽样总桶数为 339,健康抽样的 ratio 应在 [330, 350];超出该区间记为 warning(见 quality_check `warnings`),报告正文全量量级处必须显式说明 ratio(样本原始量与 ratio 明细放附录)。

## 四、`final_report/feishu_doc_淑芬_${dt}.json` (Step 5 飞书发布产出)

```jsonc
{
  "dt": "YYYY-MM-DD",
  "doc_url": "https://zhuanspirit.feishu.cn/docx/<token>",
  "doc_token": "<token>",
  "uploaded_at": "ISO 8601",
  "block_anchors": { "h1_conclusion": "doxcn...", "h1_body": "doxcn...", "h1_appendix": "doxcn...", "h2_opportunities": "doxcn...", "...": "..." },
  "image_blocks": {
    "module_ctr_rank_淑芬.png": { "block_id": "doxcn...", "file_token": "..." }
  },
  "im_push": [
    {
      "open_id":    "ou_...",
      "chat_id":    "oc_...",
      "message_id": "om_...",
      "pushed_at":  "ISO 8601",
      "status":     "ok"
    }
  ],
  "im_image_push": [
    {
      "open_id":    "ou_...",
      "message_id": "om_...",
      "pushed_at":  "ISO 8601",
      "status":     "ok"
    }
  ]
}
```

**契约要点:**

- **报告固定三层结构 + 置顶核心汇总表**(`首页洞察_淑芬_${dt}.md` 及上传的 docx):文档最前面是**核心机会汇总总表**(表头 `模块 \| 机会 \| 策略 \| 优先级 \| 收益`,两轨道机会点合并按 P0→P1→P2),再接**第一层「结论」(机会点 → 对应策略建议 → 优先级 P0/P1/P2 位 → 优化后收益 点击UV/单量/GMV) → 第二层「正文」(分析框架图 → 整体 → 模块 → 分层 → 迁移/坑位下钻,全量量级) → 第三层「附录」(①抽样原始数据结果 ②抽样方式和样本质量 ③数据源描述)**。骨架见 `assets/report-template.md`。置顶总表与结论层「优先级」「优化后收益」均由 Step 4 留位、**Step 5 机会计算器回填后再调 `feishu_publish.py --skip-push` 建 docx**(所以上传的文档里已带完整优先级+置顶总表)。「优化后收益」的**单量/GMV 由 Step5 强制折算**(乘数来自 `module_click_conv_aov`,Step1 保证产出),提升型机会必带单量+GMV,乘数为兜底则标注非当日;`verifiable=false` 的 app机会点无法量化除外。绝不硬编。
- `im_push` 永远是数组,即便只有一个收件人。一个收件人失败不影响其他人,失败的那条 status 写 `"failed"` 并加 `error` 字段,**不能**整体打包失败。
- `im_image_push` 记录核心汇总表配图(`core_summary_table_淑芬_${dt}.png`)作为图片消息追加在文字末尾的推送回执。**配图是文字消息的补充,不是硬产物**:文字推送成功后才追加图片;渲染失败/图缺失时该条 status=`skipped`,**不影响** `im_push` 的成功判定与整体退出码。`--skip-push` 模式下本数组为空。
- 重试时复用 `doc_url` / `doc_token`,不重建文档。

## 五、`final_report/opportunity_priority_淑芬_${dt}.json` (Step 5 机会计算器产出)

```jsonc
{
  "dt": "YYYY-MM-DD",
  "ratio": 337.53,                    // dau_full.uv / n_users,全量推广倍率(健康 [330,350])
  "n_users": 10416,
  "dau_full_uv": 3515722,
  "uv_ctr_target": 0.0599,            // primary_page(G1001) 有曝光模块 UV-CTR 中位(剔除 capped venue_tab),机会对齐目标;首页无品类tab/品牌墙曝光,实际参与中位的仍是原 7 个非cap模块
  "uv_ctr_target_basis": "median_7_modules_excl_capped",  // 取值依据
  "uv_ctr_target_quartiles": { "p25": 0.0317, "p50": 0.0599, "p75": 0.1747 },  // 情景分析用
  "opportunities": [                  // 必须已按 priority(P0→P1→P2) 再按 priority_score 降序排好
    {
      "source": "data_flow",          // data_flow(常规SQL数据侧) / app_experience(真人App体验,来自 app_experience_opportunities)
      "module": "大促banner",          // 来自 References/section-to-module.json 的 core_modules;app_experience 且映射不到模块时可为 null
      "title": "高曝光低转化,UV-CTR 首页模块倒一",
      "priority": "P0",               // P0 / P1 / P2
      "priority_score": 135000.0,     // = importance_raw × 紧急度系数,同级内排序用
      "importance": "高",             // 高 / 中 / 低
      "importance_raw": 168750.0,     // = impact × confidence_coef
      "urgency": "高",                // 高 / 中 / 低
      "confidence": "MEDIUM",         // HIGH(0.8) / MEDIUM(0.5) / LOW(0.3)
      "confidence_coef": 0.5,
      "impact_incremental_click_uv_full": 135000,   // 增量点击 UV(全量/日,基准情形)主价值口径
      "impact_incremental_click_uv_full_range": { "pessimistic": 60000, "base": 135000, "optimistic": 310000 },
      "impact_incremental_orders_full": 3480,        // 增量订单数(全量/日)=增量点击UV × pv_conv_rate_diff;提升型机会强制填(乘数来自 module_click_conv_aov,Step1保证产出);verifiable=false 的 app机会点才 null
      "impact_gmv_full": 7952400,     // 增量GMV(元/日)=增量订单数 × clicked_aov_per_order(笔均);提升型机会强制填;verifiable=false 才 null
      "gmv_multipliers": {            // 单量/GMV 折算乘数来源(提升型机会必填;verifiable=false 的 app机会点整块 null)
        "pv_conv_rate_diff": 0.02578, "aov_per_order": 2285.0,
        "source": "module_click_conv_aov_${dt}.csv", "source_freshness": "fresh", // fresh=当日实测;fallback_from:YYYY-MM-DD=当日取数失败用该历史日兜底,报告须标注非当日
        "confidence_cap": "MEDIUM",
        "note": "单日相关含选择偏差,需A/B校准点击真实因果增量"
      },
      "formula": "exposure_uv 7442 × (target 0.0599 − actual 0.0063) × ratio 337.53",
      "components": [                 // 每个组成部分标来源
        { "name": "受影响用户(曝光UV)", "value": 7442, "source": "data-backed", "ref": "exploration.modules[].exposure_uv" },
        { "name": "提升幅度(pp)",       "value": 0.0536, "source": "data-backed", "ref": "uv_ctr_target − modules[].uv_ctr" },
        { "name": "全量倍率",           "value": 337.53, "source": "data-backed", "ref": "dau_full.uv / n_users" }
      ],
      "strategy": "核对 banner 是否非活动期空窗;区分营销展示位低 CTR 属预期 vs 素材/热区低效",
      "decision_logic": "增量量级大(重要度高) + 是倒一存在结构性低效(紧急度高,虽非恶化但量级压舱) → P0",
      "sensitivity": {
        "most_fragile_assumption": "目标 UV-CTR 取值(中位 vs 分位)",
        "break_even": "若 banner 属品牌展示型、低 CTR 为预期,则对齐中位的提升空间被高估",
        "scenario_consistent": true   // 三档情景结论是否一致
      },
      "triangulation": {              // 第 6 步四关核对,FAIL 要在 notes 说明
        "segment_first": "PASS", "internal": "PASS", "magnitude": "PASS", "denominator": "PASS"
      },
      "to_verify": "H7: 低 CTR 可能是展示型模块预期表现,需结合下游 GMV/转化定性,CTR 单指标不足",
      "quality_warn_affected": false  // true 时报告条目带 ⚠
    }
    // 其余机会,按 P0→P1→P2 + priority_score 降序
  ],
  "method_notes": "价值主口径=增量点击UV;目标=primary_page(G1001)有曝光模块中位(剔capped venue_tab);单量/GMV折算用 module_click_conv_aov 数据(pv_conv_rate_diff × 增量点击UV=增量订单,× 笔均客单价=增量GMV,置信度上限MEDIUM含选择偏差);三角校验全过",
  "report_backfilled": true,          // 是否已回填 首页洞察_淑芬_${dt}.md 结论层(优先级表 + 优化后收益表)
  "feishu_message_rewritten": true    // 是否已把 feishu_message 改写为「机会点+策略+优先级+优化后收益」四要素结论 + 文档链接
}
```

**契约要点:**

- `opportunities[]` **必须已排序**:先 P0 后 P1 后 P2,同级按 `priority_score` 降序。读取方(报告/飞书摘要)直接顺序用,不再排。
- **Step 5 收口顺序(硬约束)**:排序 → 回填报告 md 结论层(`report_backfilled=true`)→ `feishu_publish.py --skip-push` 建含优先级的文档拿 doc_url → 改写 feishu_message 为四要素结论并替换 doc_url(`feishu_message_rewritten=true`)→ `--skip-doc` 推一条 P2P。**飞书文档由 Step 5 建,不是 Step 4**。
- 价值主口径恒为 `impact_incremental_click_uv_full`(增量点击 UV 全量/日)。**`module_click_conv_aov` 由 Step1 保证产出(重试+近14日兜底),所以提升型机会强制**追加填 `impact_incremental_orders_full`(增量订单)与 `impact_gmv_full`(增量GMV),乘数记入 `gmv_multipliers`(来源该 CSV,`source_freshness`=fresh 或 fallback_from:X,`confidence_cap`=MEDIUM 含选择偏差)。`source=app_experience` 且 `verifiable=false` 的机会点(首页SQL量化不到)三者均 `null`、`gmv_multipliers` 整块 null。
- 比例指标(UV-CTR/覆盖率)**不乘 ratio**;只有 UV/PV/点击次数类绝对量乘 ratio。
- `confidence` 与系数对应固定:HIGH=0.8 / MEDIUM=0.5 / LOW=0.3;assumption ≥2 个关键变量 → 强制 LOW。
- 高于 `uv_ctr_target` 的高位模块(搜索框/金刚位)不进"提升型机会",归 P2「维持监控」,`impact_incremental_click_uv_full` 记 0 或省略,`decision_logic` 写"高位基本盘,守住即可"。
- 受 `quality_check.warnings` 或埋点 cap 影响的机会(如场馆tab),`quality_warn_affected=true`,且动作应是"先修数据/埋点"而非直接业务提升。
- **`source` 区分两来源(修改4)**:`data_flow`=常规 SQL 数据侧机会点;`app_experience`=真人 App 体验机会点(来自 `app_experience_opportunities_淑芬_${dt}.json`)。报告结论层与飞书消息**按 source 分两并列轨道**呈现(轨道 A 数据洞察 / 轨道 B app体验),各自独立排 P0/P1/P2。`source=app_experience` 且 `verifiable=false`(映射不到首页模块)的机会点:`impact_*` 三项均 `null`、`module` 可为 null、`priority` 沿用 wiki 原级(不重新量化)、`decision_logic` 写"真人体验证据强度=X,SQL 无对应指标,收益待真人/埋点验证";`verifiable=true` 的走常规增量点击 UV/单量/GMV 公式,标 `source=app_experience`。

## 六、`analysis_reports/app_experience_opportunities_淑芬_${dt}.json` (Step 1.5 app体验机会点产出)

真人 App 体验机会点，来自飞书 wiki（按 user-chance 输出规范产出的聚合机会点报告）。本 agent **只搬运 wiki 已有结论**——优先级、证据强度、机会点标题原样照抄，不臆造、不升降级。

```jsonc
{
  "dt": "YYYY-MM-DD",
  "source_wiki": "CBpNwlvA5iMpMYkqr0zcE5xFnrf",       // 飞书 wiki token(数据源)
  "source_wiki_title": "转备用机路径对比聚合机会点报告", // 附件一级标题,原样(主题可能随天变)
  "revision_id": 18,                                   // 当前 wiki 版本号,revision 去重用
  "status": "ok",                                      // ok / skipped_no_change / unavailable
  "reason": null,                                      // status=unavailable 时填失败简述,否则 null
  "sample_caveat": [                                   // 全局样本 caveat,适用所有机会点,供下游降置信度
    "4 轮有效样本,方向性发现,不适合定量判断问题占比",
    "均为 Android 模拟器非真机,高优问题进需求前建议真机复核",
    "推荐流受同账号历史行为影响,相关性需降权"
  ],
  "role_insight": [                                    // 角色差异洞察,帮下游理解机会点面向哪档用户
    { "user_type": "价格敏感但不想翻车的新用户", "natural_path": "首页活动或电子城",
      "blocker": "被回收活动和风险标签打断", "product_hint": "活动入口区分买卖场景,低价候选解释风险" }
  ],
  "opportunities": [                                   // 顺序照 wiki 原表,不重排(排序是 Step5 的事)
    {
      "id": "app-01",                                  // app-01/02… 顺序编号,稳定可引用
      "title": "备用机/高性价比优先排序或频道",          // ← wiki「产品机会点」表 机会点列,原样
      "wiki_priority": "P1",                           // ← wiki 优先级列,原样(P0/P1/P2,当前 wiki 用 P1/P2)
      "evidence_strength": "高",                       // ← 从「高频体验问题」表按 round 回链,取最强(高>中高>中>低);回链不到="未标注"
      "evidence_refs": ["round-02", "round-03"],       // ← 证据列的 round-xx,split 成数组
      "problem": "低价不等于高性价比,用户需综合判断",    // ← 解决什么问题列,原样
      "suggestion": "综合价格/代际/成色/电池/保障给均衡推荐", // ← 建议方向列,原样
      "mapped_module": "商卡feed流",                   // 映射到 11 模块(section-to-module.json core_modules);映射不到=null
      "verifiable": true,                              // true=有 mapped_module,下游可 SQL 验证;false=保留定性
      "caveat": ""                                     // 该条专属备注(如多入口取主、映射不到原因),无则空串
    }
  ]
}
```

**契约要点:**

- **只搬运不臆造**:`title`/`wiki_priority`/`problem`/`suggestion` 全部原样照抄 wiki,不改写、不升降级、不新增 wiki 里没有的机会点。
- `evidence_strength` **只从「高频体验问题」表回链**,不自己评;回链不到记 `"未标注"`,下游按最保守处理。取值枚举:`高 / 中高 / 中 / 低 / 未标注`。
- `mapped_module` ∈ `section-to-module.json` 的 `core_modules`,或 `null`(映射不到)。`verifiable` 与之绑定:有 `mapped_module`→`true`,`null`→`false`。
- **软产物**:`status` 三值——`ok`(正常抽取)/`skipped_no_change`(revision 未变,`opportunities` 空数组)/`unavailable`(读取或解析失败,`opportunities` 空数组、`reason` 填因)。三种情况本 agent 均**退出码 0**,不阻断主流水线。
- `opportunities[]` **不排序**,照 wiki 原表顺序;排序/量化/定优先级是 Step5 的事。
- 本产物是 Step2(假设检验)、Step4(报告轨道 B)、Step5(合并排序)的**可选输入**——缺失或 `status≠ok` 时,下游 app体验轨道写占位句、不阻断。

