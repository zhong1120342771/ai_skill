# 申请 One-Service accessKey（只读辅助）

本 skill 调用 58 星河 One-Service HTTP API 跑 Hive/Spark SQL，需要个人凭证（OA 账号 + accessKey）。本文件用于：

1. 首次启动时 `check` 子命令探活失败 → Agent 据此走「准入流程」，主动用浏览器 skill 帮用户打开 zeye 申请页
2. 作为底层 API 的脱敏参考（排查或手工调用时用）

## Agent 准入流程（SKILL.md Step 0 配套）

Agent 收到 `check` 失败信号（`准入未通过` 或 `submit_source=PATH xinghe-submit fallback ... not found`）时，**不要**只把申请链接甩给用户，而是按以下顺序自助辅助：

1. **优先使用 `agent-browser`**（纯文本 snapshot，不读图，安全）：

   ```bash
   agent-browser open 'https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey'
   agent-browser snapshot -i        # 拿交互元素，引导用户在页面里点「申请/创建 AI accessKey」
   ```

   - 第一次打开通常会被 SSO 重定向到 `https://zzsso.zhuanspirit.com/user/login?...`，提示用户登录公司账号后再回到本页
   - 登录后用 `agent-browser snapshot -i` 引导用户点击"申请/创建 AI accessKey"按钮
   - **禁止 `agent-browser screenshot`**：会产出 PNG，本机 hook 会让会话崩溃

2. **`agent-browser` 不可用时**才退到「联网访问」skill；**禁止 `WebFetch`**（已被本机 PreToolUse hook 拦截）。

3. 用户拿到 accessKey 后，把 `OA_NAME` / `ACCESS_KEY` 写入 skill 目录下的 `.credentials.local`：

   ```
   OA_NAME=你的OA账号
   ACCESS_KEY=你的accessKey
   ```

   模板见 [`.credentials.local.example`](../.credentials.local.example)。

4. 写入完成后 **回到 Step 0 重跑 `check`，必须返回 `ok` 才能进 Step 1**。

## 申请 accessKey（直接给用户看的版本）

**特别说明：需提前在 zeye 平台申请一个 accessKey，访问以下链接获取（如果没访问权限，请联系业成）：**

https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey

拿到 accessKey 后，在 skill 目录下创建 `.credentials.local`（已被 `.gitignore` 忽略，不会随 skill 包分发）：

```
OA_NAME=你的OA账号
ACCESS_KEY=你的accessKey
```

模板见 [`.credentials.local.example`](../.credentials.local.example)。

## One-Service API（脱敏参考）

底层接口（`scripts/xinghe_submit.sh` 内部就是调这套）。凭证请用 `.credentials.local` 中的值替换占位符。

### 1) 提交 SQL 任务

```bash
curl -s -X POST https://oneservice.zhuanspirit.com/sqlTask/submit \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'sql=select 1 as c' \
  --data-urlencode 'oaName58=你的OA账号' \
  --data-urlencode 'accessKey=你的accessKey'
```

### 2) 查询任务状态

```bash
curl -s https://oneservice.zhuanspirit.com/sqlTask/queryTaskProgress/{taskId}
```

### 3) 获取结果（小结果集直接下载）

```bash
curl -s "https://oneservice.zhuanspirit.com/sqlTask/downloadTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"
```

### 4) 获取下载链接（大结果集）

```bash
curl -s "https://oneservice.zhuanspirit.com/sqlTask/queryTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"
```

## 注意

- `oaName58` 替换为自己的 OA 账号，`accessKey` 替换为自己的 accessKey。
- 不要把他人的真实 OA 账号或 accessKey 写进团队版 skill 或 `.credentials.local.example`。
- `queryTaskProgress=success` 仅表示执行完成，不代表结果已可立即获取。
- 大结果集走下载链接方式获取。
- 内网访问 oneservice 通常需要走 VPN/企业网卡/utun，`xinghe_submit.sh` 内置 `ifconfig` 探测 + `curl --interface` 选路；纯 curl 直连可能不通。
