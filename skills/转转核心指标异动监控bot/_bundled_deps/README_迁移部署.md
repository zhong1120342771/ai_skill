# 转转核心指标异动监控bot skill —— 迁移部署说明

这份 skill 迁移到新电脑，光复制 `转转核心指标异动监控bot/` 目录不够——它运行时还依赖几样不在自己目录里的东西。为了让压缩包自包含，这些依赖已随包放进本目录 `_bundled_deps/`。

## 一、随包携带、跑脚本自动还原的依赖

`_bundled_deps/` 里按 `~/.claude` 的相对结构镜像了依赖：

| 依赖 | 包内位置 | 还原到 | 作用 |
|---|---|---|---|
| `xinghe-data` skill | `_bundled_deps/skills/xinghe-data/` | `~/.claude/skills/xinghe-data/` | **主取数通道**（星河 StarRocks/Hive）。取数子 agent 引用 `xinghe_client` |
| `humanizer` skill | `_bundled_deps/skills/humanizer/` | `~/.claude/skills/humanizer/` | 对外产出去 AI 味（全局强制规范） |
| `oneservice_cli.py` | `_bundled_deps/scripts/oneservice_cli.py` | `~/.claude/scripts/oneservice_cli.py` | **兜底取数通道**（星河不可用/权限不足时切它） |

> 为什么还原到规范位置：取数子 agent 与脚本里的路径是规范位（`~/.claude/skills/xinghe-data`、`~/.claude/scripts/oneservice_cli.py`），放回规范位才不用改任何引用。

### 还原步骤

解压后，在本目录执行：

```bash
cd <解压路径>/转转核心指标异动监控bot/_bundled_deps
bash install_deps.sh          # 已存在的目标会跳过
bash install_deps.sh --force  # 需要覆盖时
```

脚本幂等，重复跑安全。

## 二、包里带不了、目标机必须自己配的

### 1. 环境变量凭证（写进 ~/.zshrc，不进包）

```bash
# 星河（主取数通道）
export XINGHE_CLIENT_USER="..."
export XINGHE_CLIENT_SECRET="..."
export XINGHE_OA="..."
# One-Service（兜底取数通道）
export ONESERVICE_OA="..."
export ONESERVICE_ACCESS_KEY="..."
```

包里所有脚本都走这些环境变量读凭证，**没有任何明文密码**。星河凭证按人隔离（权限不同不可混用），首次可用 `~/.claude/skills/xinghe-data/scripts/save_credentials.py` 引导配置并验证连接。

### 2. lark-cli（外部二进制，建飞书文档 + P2P 推送）

本机版本 v1.0.43。目标机：

```bash
brew install lark-cli          # 或对应渠道
lark-cli auth login            # 授权 user + bot 两种身份
lark-cli auth status           # 确认 user / bot 都 ready
```

结论生成步用 lark-cli 建 docx + P2P 推送；v1.0.43 P2P 必须 `--user-id`、文本用 `--text` 内联（见 `scripts/feishu_publish.py`）。

### 3. Python 第三方库

```bash
pip3 install pandas numpy matplotlib requests
```

- `pandas`：analyze_dimension / detect_anomaly / qa_check / render_charts 都用
- `numpy`：detect_anomaly（MAD 异动）
- `matplotlib`：render_charts（出图，注意中文字体）
- `requests`：xinghe_client 唯一的第三方依赖

## 三、部署后自查清单

按顺序确认：

1. `~/.claude/skills/xinghe-data/scripts/xinghe_client.py` 存在，import 不报错。
2. `~/.claude/scripts/oneservice_cli.py` 存在且可执行。
3. `~/.claude/skills/humanizer/SKILL.md` 存在。
4. `lark-cli auth status` 显示 user + bot 都 ready。
5. 五个环境变量都 export 了（`echo "X=${XINGHE_CLIENT_USER:-MISSING}"` 之类不打印密钥）。
6. `python3 -c "import pandas, numpy, matplotlib, requests"` 不报错。
7. matplotlib 中文字体可用（`PingFang SC`/`Heiti SC`/`Arial Unicode MS`/`SimHei` 任一），否则出图乱码。

## 四、飞书推送范围（硬规则，别改）

当前只推钟梦婷一人 P2P（`ou_5e572adca6deef8ef21c3b18dfade573`），不推群。调整推送范围改 `LARK_CORE_RECEIVERS` 环境变量，别在脚本里写死。
