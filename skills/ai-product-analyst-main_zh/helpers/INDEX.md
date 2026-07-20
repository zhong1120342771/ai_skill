# 辅助模块索引

基于 Cole Nussbaumer Knaflic 的 *Storytelling with Data* 方法论的可复用可视化工具：

| 文件 | 用途 |
|------|---------|
| `helpers/chart_helpers.py` | 核心：`swd_style()`、`highlight_bar()`、`highlight_line()`、`action_title()`、`annotate_point()`、`save_chart()`。进阶：`stacked_bar()`、`add_trendline()`、`add_event_span()`、`fill_between_lines()`、`big_number_layout()`、`retention_heatmap()`。分析类：`sensitivity_table()`、`funnel_waterfall()` |
| `helpers/tieout_helpers.py` | 数据源对账：`read_source_direct()`（仅用 pandas 的文件读取器）、`profile_dataframe()`（行数、空值、求和、去重计数、日期范围）、`compare_profiles()`（带容差的双路径对比）、`format_tieout_table()`、`overall_status()` |
| `helpers/analytics_chart_style.mplstyle` | Matplotlib 样式文件 —— 暖米白背景（#F7F6F2）、无上/右边框、无网格、无衬线字体、150 DPI |
| `helpers/chart_style_guide.md` | 完整 SWD 参考：配色、去杂检查清单、图表决策树、反模式、复核清单 |
| `helpers/sql_helpers.py` | SQL 合理性检查：`check_join_cardinality()`、`check_percentages_sum()`、`check_date_bounds()`、`check_no_duplicates()`、`warn_temporal_join()`。数据质量扩展：`check_temporal_coverage()`、`check_value_domain()`、`check_monotonic()` 及安全包装 |
| `helpers/stats_helpers.py` | 统计检验：`two_sample_proportion_test()`、`two_sample_mean_test()`、`mann_whitney_test()`、`confidence_interval()`、`chi_squared_test()`、`bootstrap_ci()`、`format_significance()`、`interpret_effect_size()` |
| `helpers/data_helpers.py` | 数据源访问：`detect_active_source()`、`check_connection()`、`get_local_connection()`、`read_table()`、`list_tables()`、`get_data_source_info()`。剖析：`get_connection_for_profiling()`、`schema_to_markdown()` |
| `helpers/error_helpers.py` | 友好的错误提示：`friendly_error()`、`safe_query()`、`check_empty_dataframe()`、`suggest_column()` |
| `helpers/file_helpers.py` | 原子写入、内容哈希、YAML 辅助：`atomic_write()`、`safe_read_yaml()`、`content_hash()`、`has_content_changed()` |
| `helpers/structural_validator.py` | 校验第 1 层的 schema/主键/完整性检查 |
| `helpers/logical_validator.py` | 校验第 2 层的聚合与趋势一致性检查 |
| `helpers/business_rules.py` | 校验第 3 层的合理性检查 |
| `helpers/simpsons_paradox.py` | 校验第 4 层的辛普森悖论检测 |
| `helpers/confidence_scoring.py` | 根据四层校验结果给出 A-F 置信度评分 |
| `helpers/business_validation.py` | 以知识为依据的指标规则和护栏指标配对 |
| `helpers/health_check.py` | 系统健康：安装状态、知识完整性、数据连通性、依赖导入 |
| `helpers/metric_validator.py` | 对照 schema 校验指标定义 |
| `helpers/entity_resolver.py` | 跨组织知识的实体消歧 |
| `helpers/miss_rate_logger.py` | 用 JSONL 记录知识缺口的未命中 |
| `helpers/business_context.py` | 加载组织业务背景：术语表、产品、指标、团队 |
| `helpers/archaeology_helpers.py` | 查询考古的写入侧：采集并检索 cookbook 条目 |
| `helpers/pipeline_state.py` | V1→V2 流水线状态迁移：`detect_schema_version()`、`migrate_v1_to_v2()` |
| `helpers/theme_loader.py` | 主题加载、缓存、深度合并：`load_theme()`、`get_color()`、`list_themes()` |
| `helpers/chart_palette.py` | 主题感知配色、WCAG 对比度：`apply_theme_colors()`、`palette_for_n()` |
| `helpers/context_loader.py` | 带 token 预算的分层内容加载：`load_tiered()`、`estimate_tokens()` |
| `helpers/schema_migration.py` | schema 迁移框架（在 V2 中处于惰性）：`migrate_if_needed()` |
| `helpers/examples/` | 4 组前后对比，展示柱状图、堆叠柱状图、折线图和多面板的改造 |
