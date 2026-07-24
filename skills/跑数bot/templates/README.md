# 分析模板库

> 把高频、稳定的分析骨架预写成参数化 SQL 模板，跑数bot 优先匹配，匹配上**不让 LM 现写**——降低出错概率，提速 5-10 倍。

## 设计原则

1. **模板写"骨架"，不写"业务结论"**：参数化品类 ID / 时间窗 / 维度等易变值
2. **每个模板配业务描述**：复用 `_分析上下文协议/business-statement.md` 格式，让业务方能审
3. **模板需要被实战验证过才放进来**：必须是跑通过的 case 抽出来的，不能凭想象写
4. **业务规则变了改模板**：模板 = 单一事实来源，改一次全公司同步

## 触发逻辑（跑数bot Step 1 第 0 档）

```
用户提需求
  ↓
父 agent 拼 yaml
  ↓
跑数bot Step 1：
  第 0 档：先看 templates/ 有没有匹配的模板（按需求类型 + 关键词）✨ 新增
    ├── 有 → 套模板填参数，跳过 Step 2 探表
    └── 无 → 走原 3 档（用户给参考 → 本地搜 → 星河兜底）
```

匹配逻辑由 LM 判断——看用户需求关键词（"趋势" / "画像" / "来源" / "归因"）+ 模板的 `适用场景` 描述。

## 模板清单（每加一个更新此表）

### 订单 / 画像类

| 模板文件 | 适用场景 | 参数 | 实战验证 |
|---|---|---|---|
| `category_daily_trend.sql` | 任何品类的日订单 / GMV 趋势 | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` / `time_field` | 骑行近 2 个月趋势 ✅ |
| `category_order_source_drilldown.sql` | 任何品类按场景渠道拆订单来源（一级场景） | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` / `time_field` | 骑行 5/18 异动渠道归因 ✅ |
| `category_user_profile.sql` | 任何品类的下单用户画像（性别 × 新老客 × 兴趣分类） | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` | 骑行近 30 天画像 ✅ |

### 品类现状类

| 模板文件 | 适用场景 | 参数 | 实战验证 |
|---|---|---|---|
| `category_conversion_timing.sql` | 商详/收藏/加购次数分桶下的日均支付用户率（识别转化关键门槛） | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` | 骑行 3.5 个月 8 档分桶 ✅ |
| `category_cross_intersection.sql` | 目标品类新老客 × 是否历史下过其他品类订单四象限交叉 | `target_cate_type` / `order_full_table` / `start_dt` / `end_dt` | 骑行 × 兴趣其他 ✅ |

### 搜索链路类

| 模板文件 | 适用场景 | 参数 | 实战验证 |
|---|---|---|---|
| `search_before_pay_query.sql` | 支付前搜索词主表（query 级 PV / UV / 召回 / 意图分类） | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` / `result_table` | 骑行 3.5 个月 ✅ |
| `search_filter_usage.sql` | 搜索筛选（静态/品牌墙/快筛/抽屉/推荐）+ 5 类排序使用率拆解 | `query_scope_table` / `detail_table` / `cate_first_id` / `start_dt` / `end_dt` / `query_limit` | 骑行 top1000 ✅ |
| `search_funnel_with_love_cart.sql` | 支付前搜索全链路：PV → click → 收藏 → 加购 → pay（4 键关联） | `cate_first_id` / `start_dt` / `end_dt` / `snapshot_dt` / `detail_output_table` / `query_scope_table` / `query_limit` | 骑行 top1000 ✅ |

### 已降维（不做模板，方法论沉淀在别处）

以下场景**不做单独模板**，LM 按数据地图 + 方法论现写即可。若某天发现现写困难度显著提升，再考虑抽模板：

| 已降维场景 | 方法论位置 |
|---|---|
| 搜索 TopN 坑位点击率（Top6 / Top16 / 17+ 三段拆） | `空间盘点（机会预估）/references/riding-case-pattern.md` §范式 A |
| 任意指标 10 档分位分桶（`percentile_approx`） | 同上 §范式 B |
| Top N 品牌 × Top M 系列（`ROW_NUMBER OVER PARTITION`） | 同上 §范式 C |

## 模板文件格式

每个模板文件包含 3 部分：

```
1. 顶部注释块（YAML 格式）：模板元信息
   - name: 模板名称
   - scene: 适用场景描述（中文，让 LM 匹配用）
   - params: 必填/选填参数清单
   - validated: 实战验证记录
   - business_statement: 业务描述模板（让业务方审）

2. @lifecycle 注释（继承跑数bot 的生命周期机制）

3. SQL 主体（用 ${param_name} 占位参数）
```

## 怎么用（LM 视角）

```bash
# $SKILL_DIR = 跑数bot skill 根目录；模板库为其子目录 templates/
# 模板匹配上之后，先读模板：
cat $SKILL_DIR/templates/category_user_profile.sql

# 用 sed / python 替换参数，生成实际 SQL：
sed -e "s/\${cate_first_id}/105/g" \
    -e "s/\${start_dt}/2026-05-30/g" \
    -e "s/\${end_dt}/2026-06-28/g" \
    -e "s/\${snapshot_dt}/2026-06-28/g" \
    $SKILL_DIR/templates/category_user_profile.sql \
    > ~/claude-output/<topic>_query.sql

# 然后按跑数bot Step 3.5 给用户审（业务描述从模板顶部 yaml 抽取，跟参数化后的 SQL 一起贴）
```

## 怎么加新模板

1. 拿一次跑通的真实 case
2. 抽出 SQL 骨架，把易变值参数化（品类 ID、时间窗、维度等）
3. 顶部加 yaml 元信息（scene / params / business_statement）
4. 跑一遍参数化后的 SQL 验证还能 work
5. 加进上面的"模板清单"表
6. **不要预先想象**——没真实跑通过的"假设模板"不要放

## 关键边界

- ❌ **不要把业务结论塞模板**（如"骑行 = 105"——这是飞书 Hive 表导航的事）
- ❌ **不要预写过细的模板**（如"骑行用户画像_仅女性"——颗粒度太碎，参数化覆盖）
- ❌ **不要为了凑数加模板**——少而精，每个都得有实战验证
- ✅ **业务变了改模板**（如时间字段语义改了，改一处全公司同步）
- ✅ **模板覆盖不到的需求 → LM 现写**（保留灵活性）
