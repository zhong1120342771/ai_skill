---
name: xinghe-data
description: >
  Connect to 58's Xinghe (星河) data platform to run SQL queries, execute existing SQL documents,
  poll for results, and export data (Excel download or pandas DataFrame for analysis).
  Use this skill whenever the user mentions 星河, Xinghe, data exploration (数据探查),
  running SQL on the data platform, fetching data from Hive/StarRocks, or exporting query results.
  Also trigger when the user references doc IDs, execute IDs, or wants to query internal 58 data tables.
---

# Xinghe Data Explorer (星河数据探查)

This skill lets you connect to 58's Xinghe data platform via its OpenAPI, run SQL queries or existing SQL documents, and retrieve results for export or analysis.

## Step 0: Credential Check (ALWAYS DO THIS FIRST)

Every time this skill is triggered, before doing anything else, run this check:

```bash
echo "USER=${XINGHE_CLIENT_USER:-MISSING}" "OA=${XINGHE_OA:-MISSING}"
```

### If all set → proceed to Step 1

### If any are MISSING → guide setup in chat

Each person must use their own Xinghe credentials — permissions differ between accounts, so mixing is forbidden. When credentials are missing, walk the user through setup right here in the chat:

1. **Explain briefly**: "You need to configure your own Xinghe API credentials before I can query data for you. I need three things from you — you only have to do this once."

2. **Ask for three values** (use AskUserQuestion or just ask in text):
   - OA account (你的OA账号, e.g. `zhangsan`)
   - Service account / 服务账号 (e.g. `xn_zhangsan`)
   - Secret / 调用密码

   If they don't have an API account yet, point them to the application page:
   `https://dp.58corp.com/api-manage/service-list`

3. **Save credentials** by running the bundled script — it persists credentials so all future sessions can use them:
   ```bash
   python <skill-path>/scripts/save_credentials.py "<client_user>" "<client_secret>" "<oa>"
   ```
   The script does three things automatically:
   - Verifies the credentials work (runs `SELECT 1` against the API)
   - **Windows**: uses `setx` to write permanent user-level environment variables (available to all new terminals and programs) + writes `.bashrc` for Git Bash
   - **macOS/Linux**: writes to `~/.zshrc` or `~/.bashrc`

4. **Apply to current session** — the script outputs an `EXPORT:` line. You MUST also run it so the current conversation can immediately use the credentials:
   ```bash
   export XINGHE_CLIENT_USER="<value>" XINGHE_CLIENT_SECRET="<value>" XINGHE_OA="<value>"
   ```
   Without this step, the current session still won't have the variables even though they're saved for future sessions.

5. **Confirm to user**: "配置完成! 已验证连接成功。这是一次性设置，以后新开对话也会自动使用你自己的 API，不需要再输入了。"

After this one-time setup, the credentials persist in the user's shell profile — future sessions pick them up automatically.

### Security rules

- **Never** display `CLIENT_SECRET`, `token`, or authentication headers in your output to the user.
- When running `save_credentials.py`, the secret appears in the command args but the output to the user should NOT echo it back.
- When showing API responses or errors, redact any credential-related fields.
- The `save_credentials.py` script verifies the connection before saving — if verification fails, tell the user to double-check their credentials.

## Core Workflow

```
Credential check → Understand request → Execute SQL → Poll for results → Export or Analyze
```

### Step 1: Understand the Request

The user may want to:
- **Run ad-hoc SQL**: They provide SQL or describe what data they need, and you write the SQL for them
- **Run an existing document**: They reference a Xinghe document ID (doc_id)
- **Check status**: They have an execute_id and want to know if it's done
- **Get results**: They want to download or analyze results from a completed execution

### Step 2: Execute

Use the bundled client at `scripts/xinghe_client.py`. Read it for the full API, but here's the typical flow:

```python
import sys
sys.path.insert(0, "<path-to-skill>/scripts")
from xinghe_client import XingheExplorer

client = XingheExplorer()

# Option A: Run ad-hoc SQL
execute_id = client.run_sql("SELECT * FROM some_table LIMIT 100")

# Option B: Run existing document
execute_id = client.run_doc_by_id(doc_id=12345)

# Option C: Edit a document's SQL then run it
client.edit_doc(doc_id=12345, sql="SELECT ...")
execute_id = client.run_doc_by_id(doc_id=12345)
```

#### SQL Engine Selection

| Value | Engine | When to use |
|-------|--------|-------------|
| 1 | Smart switch (智能切换) | Let Xinghe decide |
| 2 | SparkSQL | Large-scale batch queries |
| 4 | StarRocks (default) | Fast interactive queries |
| 5 | Hive | Traditional Hive queries |

If the user doesn't specify, use the default (StarRocks = 4). If the query involves very large datasets or the user mentions Hive tables, consider engine 5 or 2.

### Step 3: Wait for Results

```python
# Automatic polling — waits up to 5 minutes, checks every 2 seconds
result = client.wait_and_get_result(execute_id)
```

While polling, show the user periodic status updates ("waiting...", "still running...") so they know it hasn't stalled. If it fails, display the error message (check `error_msg` in the progress response — it often contains permission hints).

### Step 4: Handle Results

**Ask the user** what they want to do with the results — don't assume.

#### Export to Excel
```python
# The result contains a download URL for the Excel file
excel_url = result.get("filename_excel")
if excel_url:
    import urllib.request
    local_path = "<desired_path>/result.xlsx"
    urllib.request.urlretrieve(excel_url, local_path)
    print(f"Downloaded to {local_path}")
```

The client normalizes Xinghe download links to the internal host `xinghe-store.58corp.com` automatically. Prefer that host for real file downloads: `xinghe-storage.58corp.com` may return an HTML login/redirect page even when the URL ends with `.xlsx`.

#### Load into pandas for Analysis
```python
import pandas as pd

# From the preview data in the API response
previews = result.get("previews", [])
if previews:
    headers = previews[0][0]  # First row = column names
    rows = [row[0] if len(row) == 1 else row for row in previews[0][1:]]
    # Note: previews are limited to 50 rows. For full data, download the Excel.

# Or load from the downloaded Excel
df = pd.read_excel(local_path)
```

#### Preview Only
```python
# Show a quick preview from the API response
previews = result.get("previews", [])
if previews:
    for block in previews:
        headers = block[0]
        print(" | ".join(headers))
        print("-" * 40)
        for row in block[1:]:
            print(" | ".join(str(v) for v in row))
```

## Error Handling

Common errors and how to respond:

| Error Pattern | Meaning | What to Do |
|--------------|---------|------------|
| `权限受限` / permission denied | User lacks table access | Tell the user to apply for access via the link in the error message |
| `FAILED` status | SQL error or system issue | Show the `error_msg` to the user |
| Timeout (> 5 min) | Query is slow | Suggest the user check the SQL or try a different engine |
| Network error | Can't reach API | Check if the user is on the internal network |

## Learning & Preferences

This skill improves over time based on user feedback.

**When the user corrects your behavior** — for example, "don't show the raw JSON", "always save Excel to my Desktop", "use Hive for this type of query" — save this as a **feedback memory** so it applies to all future Xinghe interactions. Use a descriptive name like `feedback_xinghe_output_format.md` or `feedback_xinghe_engine_preference.md`.

**When you learn team-level patterns** — for example, everyone uses a certain table naming convention, or there's a standard way to handle date parameters — suggest updating this skill's instructions so the whole team benefits. Tell the user: "This seems like a team-wide pattern. Want me to add it to the Xinghe skill so everyone gets it automatically?"

**Before each Xinghe interaction**, check your memory for any saved Xinghe preferences and apply them.

## API Reference

For detailed API documentation (endpoints, parameters, response formats), read `references/api_reference.md`. You usually won't need it — the bundled client handles all the API details — but consult it if you need to understand edge cases or raw API behavior.

## Notes

- The API only supports Hive-based queries — it cannot query MySQL databases directly. If the user needs MySQL data, they should connect to the business database directly.
- SQL content supports Xinghe's built-in variables (内置变量).
- The `previews` field in results is limited to 50 rows. For full data, always use the Excel/TXT download.
- Execute IDs can be used across sessions — if the user has an execute_id from a previous run, you can check its status or fetch results.
