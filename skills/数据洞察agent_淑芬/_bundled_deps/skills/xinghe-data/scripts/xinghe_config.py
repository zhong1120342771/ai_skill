# -*- coding: utf-8 -*-
"""
星河数据探查 API 配置
凭证从环境变量读取，不要在代码中硬编码。

所需环境变量：
  XINGHE_CLIENT_USER   - 服务账号
  XINGHE_CLIENT_SECRET - 调用密码
  XINGHE_OA            - 执行人 OA
"""

import hashlib
import os
import time

# ============================================
# API 地址
# ============================================
# 线上: https://58dp.58corp.com/openapi
# 测试: http://dp-dev-api.58dns.org/openapi
API_BASE = os.getenv("XINGHE_API_BASE", "https://58dp.58corp.com/openapi")

# ============================================
# 认证参数（从环境变量读取，缺失则报错）
# ============================================
_REQUIRED_VARS = ["XINGHE_CLIENT_USER", "XINGHE_CLIENT_SECRET", "XINGHE_OA"]
_missing = [v for v in _REQUIRED_VARS if not os.environ.get(v)]
if _missing:
    raise EnvironmentError(
        f"\n星河 API 凭证未配置！缺少环境变量: {', '.join(_missing)}\n"
        f"\n"
        f"每个人必须配置自己的凭证，不可使用他人的。\n"
        f"请运行配置向导:  python scripts/setup.py\n"
        f"或手动设置:\n"
        f"  export XINGHE_CLIENT_USER=\"你的服务账号\"\n"
        f"  export XINGHE_CLIENT_SECRET=\"你的调用密码\"\n"
        f"  export XINGHE_OA=\"你的OA账号\"\n"
        f"\n"
        f"凭证申请地址: https://dp.58corp.com/api-manage/service-list\n"
    )

CLIENT_USER = os.environ["XINGHE_CLIENT_USER"]
CLIENT_SECRET = os.environ["XINGHE_CLIENT_SECRET"]
OA = os.environ["XINGHE_OA"]

# ============================================
# 默认配置
# ============================================
# SQL引擎: 1=智能切换, 2=sparksql, 4=starrocks, 5=hive
DEFAULT_SQL_ENGINE = 4

# 导出类型: 6=http导出
EXPORT_TYPE = 6

# 轮询间隔（秒）
POLL_INTERVAL = 2

# 最大等待时间（秒）
MAX_WAIT_TIME = 300


def get_auth_headers():
    """
    生成认证 Header。
    token = md5(client_secret + ts)
    """
    ts = str(int(time.time() * 1000))
    token = hashlib.md5((CLIENT_SECRET + ts).encode()).hexdigest()
    return {
        "client-user": CLIENT_USER,
        "ts": ts,
        "token": token,
        "Content-Type": "application/json",
    }
