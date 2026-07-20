# -*- coding: utf-8 -*-
"""
星河数据探查 API 客户端

封装了数据探查的核心接口：
  - run_sql          直接运行 SQL
  - run_doc_by_id    按文档 ID 运行
  - edit_doc         编辑文档 SQL
  - get_progress     查询执行进度
  - get_result       获取执行结果
  - cancel_task      取消执行任务
  - wait_and_get_result  轮询等待并返回结果

认证方式：
  Header: client-user / ts / token（token = md5(client_secret + ts)）
  凭证通过环境变量配置，详见 xinghe_config.py
"""

import requests
import time
from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse

from xinghe_config import (
    API_BASE, OA, DEFAULT_SQL_ENGINE,
    EXPORT_TYPE, POLL_INTERVAL, MAX_WAIT_TIME,
    get_auth_headers,
)


class XingheAPIError(Exception):
    """星河 API 异常"""
    pass


class XingheExplorer:
    """星河数据探查客户端"""

    DOWNLOAD_HOST_REWRITES = {
        "xinghe-storage.58corp.com": "xinghe-store.58corp.com",
    }

    def __init__(self, oa: str = None, api_base: str = None):
        self.oa = oa or OA
        self.api_base = api_base or API_BASE
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.api_base}{endpoint}"
        headers = get_auth_headers()
        try:
            resp = self.session.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                raise XingheAPIError(
                    f"API 错误 (code={result.get('code')}): {result.get('msg', result)}"
                )
            return result.get("data", {})
        except requests.RequestException as e:
            raise XingheAPIError(f"请求失败: {e}")

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{self.api_base}{endpoint}"
        headers = get_auth_headers()
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                raise XingheAPIError(
                    f"API 错误 (code={result.get('code')}): {result.get('msg', result)}"
                )
            return result.get("data", {})
        except requests.RequestException as e:
            raise XingheAPIError(f"请求失败: {e}")

    @classmethod
    def normalize_download_url(cls, url: str) -> str:
        """将导出地址统一替换为可直接下载二进制文件的内网域名。"""
        if not url:
            return url
        parsed = urlparse(url)
        new_host = cls.DOWNLOAD_HOST_REWRITES.get(parsed.netloc)
        if not new_host:
            return url
        return urlunparse(parsed._replace(netloc=new_host))

    @classmethod
    def normalize_result_download_urls(cls, result: dict) -> dict:
        """标准化结果中的下载地址，避免拿到 HTML 登录页。"""
        normalized = dict(result)
        for key in ("filename_excel", "filename"):
            if normalized.get(key):
                normalized[key] = cls.normalize_download_url(normalized[key])
        return normalized

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run_sql(
        self,
        sql: str,
        sql_engine: int = DEFAULT_SQL_ENGINE,
        export_type: int = EXPORT_TYPE,
        biz_time: str = None,
    ) -> int:
        """
        运行 SQL 查询，返回 execute_id。

        参数:
            sql:        SQL 语句（最大 10 万字符，支持星河内置变量）
            sql_engine: 1=智能切换, 2=sparksql, 4=starrocks(默认), 5=hive
            export_type: 导出类型，默认 6=http 导出
            biz_time:   基准时间，如 "2024-06-03 15:16:44"
        """
        data = {
            "oa": self.oa,
            "content": sql,
            "sql_engine": sql_engine,
            "export_type": export_type,
        }
        if biz_time:
            data["biz_time"] = biz_time
        result = self._post("/team/doc/run", data)
        return result["execute_id"]

    def run_doc_by_id(self, doc_id: int, biz_time: str = None) -> int:
        """
        按文档 ID 运行 SQL 文档，返回 execute_id。

        参数:
            doc_id:   星河文档 ID
            biz_time: 基准时间
        """
        data = {"oa": self.oa, "doc_id": doc_id}
        if biz_time:
            data["biz_time"] = biz_time
        result = self._post("/team/doc/run-doc-by-id", data)
        return result["execute_id"]

    def edit_doc(self, doc_id: int, sql: str) -> bool:
        """
        编辑文档的 SQL 内容。

        参数:
            doc_id: 星河文档 ID
            sql:    新的 SQL 内容
        """
        return self._post("/team/doc/edit", {
            "oa": self.oa,
            "doc_id": doc_id,
            "sql": sql,
        })

    def get_progress(self, execute_ids: List[int]) -> List[Dict[str, Any]]:
        """
        批量查询执行进度（最多 20 个）。

        返回:
            [{execute_id, status, error_msg?}, ...]
            status: WAITING / RUNNING / SUCCESS / FAILED / KILLED
        """
        return self._post("/team/doc/histories/progresses", {
            "execute_ids": execute_ids,
        })

    def get_result(self, execute_id: int, limit: int = 50) -> dict:
        """
        获取执行结果。

        参数:
            execute_id: 执行 ID
            limit:      预览行数，默认 50，最大 50

        返回:
            {execute_id, sql, filename_excel, filename, previews, ...}
            其中下载地址会自动规范为 xinghe-store 内网域名。
        """
        result = self._get("/team/doc/histories/results", {
            "execute_id": execute_id,
            "oa": self.oa,
            "limit": limit,
        })
        return self.normalize_result_download_urls(result)

    def cancel_task(self, execute_id: int) -> bool:
        """取消执行任务。"""
        return self._post("/team/doc/kill", {
            "execute_id": execute_id,
            "oa": self.oa,
        })

    def wait_and_get_result(
        self,
        execute_id: int,
        poll_interval: int = POLL_INTERVAL,
        max_wait: int = MAX_WAIT_TIME,
    ) -> dict:
        """
        轮询等待执行完成并返回结果。

        参数:
            execute_id:    执行 ID
            poll_interval: 轮询间隔（秒），默认 2
            max_wait:      最大等待时间（秒），默认 300
        """
        start = time.time()
        while time.time() - start < max_wait:
            progresses = self.get_progress([execute_id])
            if not progresses:
                raise XingheAPIError("未获取到执行状态")

            status = progresses[0].get("status")

            if status == "SUCCESS":
                return self.get_result(execute_id)
            elif status == "FAILED":
                error_msg = progresses[0].get("error_msg", "未知错误")
                raise XingheAPIError(f"执行失败: {error_msg}")

            # 仍在运行，继续等待
            time.sleep(poll_interval)

        raise XingheAPIError(f"等待超时（{max_wait} 秒），execute_id={execute_id}")
