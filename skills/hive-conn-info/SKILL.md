---
name: hive-conn-info
description: 提供 Hive / Spark 查询方式说明（脱敏版），用于团队查看 One-Service 的执行模式。
---

# Hive/Spark Query via One-Service

Use One-Service to run Hive/Spark SQL without direct database connections.

## 适用场景

- 仅当用户明确说 Hive 或 Spark 时使用 One-Service。
- 未说明时默认走 Doris。

## 查表约束

- 查任何表前，先确认该表是否存在 `dt` 字段或分区。
- 若表存在 `dt`，探查 SQL 默认限制为 `t-1`。
- 若表不存在 `dt`，才允许不加 `dt`，但必须加 `limit`。

## 1) 提交 SQL 任务

```bash
curl -s -X POST https://oneservice.zhuanspirit.com/sqlTask/submit \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'sql=select 1 as c' \
  --data-urlencode 'oaName58=你的OA账号' \
  --data-urlencode 'accessKey=你的accessKey'
```

## 2) 查询任务状态

```bash
curl -s https://oneservice.zhuanspirit.com/sqlTask/queryTaskProgress/{taskId}
```

## 3) 获取结果

```bash
curl -s "https://oneservice.zhuanspirit.com/sqlTask/downloadTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"
```

## 4) 获取下载链接（大结果集）

```bash
curl -s "https://oneservice.zhuanspirit.com/sqlTask/queryTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"
```

## 认证凭据（当前用户）

- oaName58: `zz_zhongmengting`
- accessKey: `GesOzutifIelszzDcXWjnpIOUVcCUYzubHDBNphKIvIEfBHSaM_zhongmengting`

所有 SQL 提交和结果下载均使用以上凭据，无需每次询问。

## Python 提交模板

优先使用 Python 提交（避开 shell 转义问题）：

```python
import urllib.request, urllib.parse, json

sql = """<SQL HERE>"""

data = {
    'sql': sql,
    'oaName58': 'zz_zhongmengting',
    'accessKey': 'GesOzutifIelszzDcXWjnpIOUVcCUYzubHDBNphKIvIEfBHSaM_zhongmengting'
}
encoded = urllib.parse.urlencode(data).encode('utf-8')
req = urllib.request.Request('https://oneservice.zhuanspirit.com/sqlTask/submit', data=encoded)
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read().decode('utf-8'))
# execute_id = result['respData']['data']['execute_id']
```

## Notes

- 若 accessKey 失效，引导用户访问 `https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey` 重新获取，再更新本文件凭据。
- `queryTaskProgress=success` 仅表示执行完成，不代表结果已可立即获取。
- 大结果集请走下载链接方式获取。
- 下载结果到 xlsx 时，优先使用 openpyxl，数值列保留数字类型不要转字符串。
