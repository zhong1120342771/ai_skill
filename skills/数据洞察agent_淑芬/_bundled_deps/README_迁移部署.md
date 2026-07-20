# 首页数据洞察（淑芬）skill —— 迁移部署说明

这份 skill 迁移到新电脑，光复制 `数据洞察agent_淑芬/` 目录不够。它运行时还依赖几样不在自己目录里的东西。为了让压缩包自包含，这些依赖已经随包放进了本目录 `_bundled_deps/`。

## 一、随包携带、跑脚本自动还原的依赖

`_bundled_deps/` 里按 `~/.claude` 的相对结构镜像了 3 个依赖：

| 依赖 | 包内位置 | 还原到 | 作用 |
|---|---|---|---|
| `xinghe-data` skill | `_bundled_deps/skills/xinghe-data/` | `~/.claude/skills/xinghe-data/` | 主取数通道（星河 StarRocks/Hive）。`run_step1.py`、`run_module_click_conv_aov.py` 硬引用 `xinghe_client` |
| `humanizer` skill | `_bundled_deps/skills/humanizer/` | `~/.claude/skills/humanizer/` | 对外产出去 AI 味（全局强制规范） |
| `oneservice_cli.py` | `_bundled_deps/scripts/oneservice_cli.py` | `~/.claude/scripts/oneservice_cli.py` | 兜底取数通道 + dau_query 执行 |

> 为什么还原到规范位置而不是就地引用：`run_step1.py` 等脚本里的路径是硬编码 `~/.claude/skills/xinghe-data`，只有放回规范位才不用改代码。

### 还原步骤

解压后，在本目录执行：

```bash
cd <解压路径>/数据洞察agent_淑芬/_bundled_deps
bash install_deps.sh          # 已存在的目标会跳过
bash install_deps.sh --force  # 需要覆盖时
```

脚本幂等，重复跑安全。

## 二、包里带不了、目标机必须自己配的

### 1. lark-cli（外部二进制，建飞书文档 + P2P 推送）

本机版本 v1.0.43，装在 `/opt/homebrew/bin/lark-cli`。目标机：

```bash
brew install lark-cli          # 或对应渠道
lark-cli auth login            # 授权 user + bot 两种身份
lark-cli auth status           # 确认 user / bot 都 ready
```

发送方应用「菜的飞书cli」appId `cli_aa8e16c998b89cc5`，appSecret 由 `lark-cli config` 在本机管理，不写明文。

### 2. 环境变量凭证（写进 ~/.zshrc，不进包）

```bash
export XINGHE_CLIENT_USER="..."
export XINGHE_CLIENT_SECRET="..."
export XINGHE_OA="..."
export ONESERVICE_OA="..."
export ONESERVICE_ACCESS_KEY="..."
```

包里所有脚本都走这些环境变量读凭证，**没有任何明文密码**。

### 3. Python 第三方库

```bash
pip3 install requests   # xinghe_client 唯一的第三方依赖；其余脚本只用标准库
```

## 三、部署后自查清单

按顺序确认：

1. `~/.claude/skills/xinghe-data/scripts/xinghe_client.py` 存在，import 不报错。
2. `~/.claude/scripts/oneservice_cli.py` 存在且可执行。
3. `~/.claude/skills/humanizer/SKILL.md` 存在。
4. `lark-cli auth status` 显示 user + bot 都 ready。
5. 五个环境变量都 export 了。
6. `python3 -c "import requests"` 不报错。

## 四、data_storage/ 里的历史 CSV

包内 `data_storage/` 带了 06-29 那天的样本 CSV（曝光/点击/时长，约 108M）作为示例数据。这不是 skill 本体，是某次运行的产物。目标机重新跑流水线会按当天 dt 重新生成，旧文件可留作参考、也可删。

## 五、飞书推送范围（硬规则，别改）

当前只推钟梦婷一人 P2P（`ou_5e572adca6deef8ef21c3b18dfade573`），不推群、不推董亚坤。调整推送范围改 `LARK_INSIGHT_RECEIVERS` 环境变量，别在脚本里写死。
