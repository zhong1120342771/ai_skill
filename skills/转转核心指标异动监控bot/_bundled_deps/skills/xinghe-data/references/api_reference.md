# 星河数据探查 API Reference

## 目录

1. [全局说明](#全局说明)
2. [运行 SQL](#运行-sql)
3. [获取执行进度](#获取执行进度)
4. [查询执行结果](#查询执行结果)
5. [取消任务](#取消任务)
6. [按文档 ID 运行](#按文档-id-运行)
7. [编辑文档 SQL](#编辑文档-sql)

---

## 全局说明

**线上域名:** `https://58dp.58corp.com`
**测试域名:** `http://dp-dev-api.58dns.org`

**协议:** HTTP，支持 GET 和 POST（`Content-Type: application/json`）

### Header 认证参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `client-user` | 服务账号 | `xn_my_service` |
| `ts` | 毫秒级时间戳 | `1654598098000` |
| `token` | `md5(client_secret + ts)` | `a1b2c3d4...` |

### 通用响应格式

```json
{
  "status": "success",
  "msg": "",
  "code": 0,
  "data": {}
}
```

`code` 为 0 表示成功，其他均为失败。

---

## 运行 SQL

**POST** `/openapi/team/doc/run`

仅支持 Hive 服务器查询，不支持 MySQL。如需查询 MySQL，直接连接业务库。

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| oa | String | 是 | 执行人 OA |
| content | String | 是 | SQL 语句，最大 10 万字符，支持星河内置变量 |
| sql_engine | Int | 否 | 1=智能切换, 2=sparksql, 4=starrocks(默认), 5=hive |
| export_type | Int | 否 | 6=http 导出 |
| param | Object | 否 | 配合 http 导出使用 |
| biz_time | String | 否 | 基准时间，如 `"2024-06-03 15:16:44"` |

**响应:**

```json
{
  "status": "success",
  "code": 0,
  "data": {
    "execute_id": 999999
  }
}
```

---

## 获取执行进度

**POST** `/openapi/team/doc/histories/progresses`

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execute_ids | List[Long] | 是 | 执行 ID 列表，最多 20 个 |

**响应:**

```json
{
  "status": "success",
  "code": 0,
  "data": [
    {"execute_id": 88888, "status": "WAITING"},
    {"execute_id": 99999, "status": "SUCCESS"},
    {"execute_id": 77777, "status": "FAILED", "error_msg": "权限受限..."}
  ]
}
```

**状态枚举:** WAITING / RUNNING / SUCCESS / FAILED / KILLED

---

## 查询执行结果

**GET** `/openapi/team/doc/histories/results`

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execute_id | Long | 是 | 执行 ID |
| oa | String | 是 | 执行人 OA |
| limit | Int | 否 | 预览行数，默认 50，最大 50 |

**响应:**

```json
{
  "status": "success",
  "code": 0,
  "data": {
    "execute_id": 123321,
    "sql": "select 1;",
    "md5_excel": "8d2d06dd...",
    "filename_excel": "https://xinghe-storage.58corp.com/.../xxx.xlsx",
    "md5_txt": "32b4c4e5...",
    "filename": "https://xinghe-storage.58corp.com/.../xxx.txt",
    "previews": [
      [
        ["_c0"],
        ["1"]
      ]
    ]
  }
}
```

**Excel 下载地址说明:**
- API 响应里常见外网地址: `https://xinghe-storage.58corp.com/...`
- 实际下载时应优先使用内网地址: `https://xinghe-store.58corp.com/...`
- 经验上 `xinghe-storage.58corp.com` 即使后缀是 `.xlsx`，也可能返回 HTML 登录页/跳转页而不是真正的 Excel 二进制
- 因此客户端应在消费 `filename_excel` / `filename` 时先将域名替换为 `xinghe-store.58corp.com`

---

## 取消任务

**POST** `/openapi/team/doc/kill`

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| execute_id | Long | 是 | 执行 ID |
| oa | String | 是 | 执行人 OA |

---

## 按文档 ID 运行

**POST** `/openapi/team/doc/run-doc-by-id`

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| oa | String | 是 | 执行人 OA |
| doc_id | Long | 是 | 文档 ID |
| biz_time | String | 否 | 基准时间 |

**响应:**

```json
{
  "status": "success",
  "code": 0,
  "data": {
    "execute_id": 291439154
  }
}
```

---

## 编辑文档 SQL

**POST** `/openapi/team/doc/edit`

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| oa | String | 是 | 执行人 OA |
| doc_id | Long | 是 | 文档 ID |
| sql | String | 是 | 新的 SQL 内容 |
