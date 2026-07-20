# -*- coding: utf-8 -*-
"""一体化项目日报 — 全局常量配置"""
import os

# ---- 路径 ----
CLAUDE_HOME       = os.path.expanduser("~/.claude")
SKILL_DIR         = os.path.join(CLAUDE_HOME, "skills", "一体化项目日报数据bot")
SCRIPTS_SQL_DIR   = os.path.join(SKILL_DIR, "Scripts")

DATA_DIR          = os.path.join(CLAUDE_HOME, "data_storage")
REPORT_DIR        = os.path.join(CLAUDE_HOME, "analysis_reports")
FINAL_DIR         = os.path.join(CLAUDE_HOME, "final_report")
VIS_DIR_TPL       = os.path.join(CLAUDE_HOME, "visualizations", "{dt}")

for d in (DATA_DIR, REPORT_DIR, FINAL_DIR):
    os.makedirs(d, exist_ok=True)

# ---- 5 张前置表 ----
PRECONDITION_TABLES = [
    ("01_xianshang",  "hdp_zhuanzhuan_tmp_global.dws_yth_core_xianshang_layer01_zmt_v1_di"),
    ("02_yykj_xs",    "hdp_zhuanzhuan_dw_global.dws_yth_xs01_yykj_zmt_v1_di"),
    ("03_mdkh_xs",    "hdp_zhuanzhuan_dw_global.dws_yth_xs02_mdkh_zmt_v1_di"),
    ("04_tongshou",   "hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di"),
    ("05_xiaoshida",  "hdp_zhuanzhuan_dw_global.dws_yth_core_xsd_layer01_zmt_v1_di"),
]

# ---- 5 段取数 SQL & CSV ----
SQL_TASKS = [
    {"name": "xianshang", "sql": "01_xianshang_orders.sql"},
    {"name": "xiansuo",   "sql": "02_yiti_xiansuo.sql"},
    {"name": "tongshou",  "sql": "03_tongshou_dongxiao.sql"},
    {"name": "xiaoshida", "sql": "04_xiaoshida.sql"},
    {"name": "tongshou_yiti_city", "sql": "05_tongshou_dongxiao_by_yiti_city.sql"},
]

CSV_TPL = os.path.join(DATA_DIR, "yiti_{name}_{dt}.csv")
META_TPL = CSV_TPL + ".meta.json"

# ---- 中间产物文件名（带 yiti_ 命名空间，避免与其它 skill 同名互相覆盖）----
# 历史教训：多个 skill 共用 analysis_reports/ 时，曾出现裸 quality_check_${dt}.json
# 同日同跑互相覆盖（一体化读到淑芬的 page_name_zh 等无关 warning）。
# 当前 4 套 skill 已分别用 _yiti / _shufen / _dim / _seg 后缀隔离，本族用 _yiti。
METRICS_TPL         = os.path.join(REPORT_DIR, "metrics_yiti_{dt}.json")
METRICS_SUMMARY_TPL = os.path.join(REPORT_DIR, "metrics_yiti_{dt}.summary.md")
QC_TPL              = os.path.join(REPORT_DIR, "quality_check_yiti_{dt}.json")

# ---- 飞书 ----
# 默认收件人：一体化项目群（chat_id，oc_ 前缀）
# 也支持 ou_ 前缀（user open_id），脚本会按前缀自动切换 --chat-id / --user-id
DEFAULT_RECEIVERS = "oc_69bfbe82133fedc9592bc18c3307aa51"  # 一体化项目群

def get_receivers():
    """从环境变量读收件人列表，默认推一体化项目群。
    支持混合 oc_xxx（群）与 ou_xxx（用户 P2P）；多个用空格分隔。"""
    raw = os.environ.get("LARK_YITI_RECEIVERS", DEFAULT_RECEIVERS).strip()
    return [x for x in raw.split() if x]

# 待复核内容专推负责人（个人 P2P），不进群。默认钟梦婷 open_id。
# 历史决策（2026-06-25）：群消息只发干净结论，「数据待复核」单独私推负责人。
REVIEW_RECEIVER = "ou_5e572adca6deef8ef21c3b18dfade573"  # 钟梦婷

def get_review_receiver():
    return os.environ.get("LARK_YITI_REVIEW_RECEIVER", REVIEW_RECEIVER).strip()

# ---- 7 项北极星指标显示名 ----
METRIC_LABELS = {
    "tongcheng_orders":       "同城订单量",
    "tongcheng_share":        "同城订单占比",
    "offline_leads":          "线下线索量",
    "lead_conv_total":        "线索转化总量",
    "tongshou_orders":        "同售订单量",
    "tongshou_dongxiao_rate": "同售动销率",
    "xiaoshida_orders":       "小时达订单量",
}

# 指标格式化：rate=比率(%)，int=整数
METRIC_FMT = {
    "tongcheng_orders":       "int",
    "tongcheng_share":        "rate",
    "offline_leads":          "int",
    "lead_conv_total":        "int",
    "tongshou_orders":        "int",
    "tongshou_dongxiao_rate": "rate",
    "xiaoshida_orders":       "int",
}
