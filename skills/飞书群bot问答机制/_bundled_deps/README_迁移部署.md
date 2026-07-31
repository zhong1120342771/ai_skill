# 飞书群bot问答机制 — 迁移部署说明

本 skill 是**运维说明型**:主体是 SKILL.md + references/troubleshooting.md(讲机制、排障)。
它描述的服务由三个外部文件组成,已随包打进 `_bundled_deps/`,解压后跑还原脚本即可落到规范位置。

## ① 随包自动还原的依赖(跑 install_deps.sh)

| 包内路径 | 还原到 |
|----------|--------|
| `_bundled_deps/.claude/scripts/group_auto_reply.py` | `~/.claude/scripts/group_auto_reply.py`(主服务) |
| `_bundled_deps/.claude/scripts/group_auto_reply_cost_report.py` | `~/.claude/scripts/group_auto_reply_cost_report.py`(花费统计) |
| `_bundled_deps/LaunchAgents/com.zmt.group-auto-reply.plist` | `~/Library/LaunchAgents/`(launchd 托管) |

```bash
bash _bundled_deps/install_deps.sh          # 幂等,已一致则跳过
bash _bundled_deps/install_deps.sh --force  # 强制覆盖
```

## ② 包里带不了、目标机自己配的东西

- **lark-cli 二进制**:`/opt/homebrew/bin/lark-cli`,自行安装并 `lark-cli auth` 登录 bot(App `cli_aa8e16c998b89cc5`)。
- **Claude Code CLI**:脚本里 `CLAUDE_BIN=/Users/zhongmengting/.local/bin/claude`,目标机需已装 claude 并按此路径(或手改脚本)。
- **Python3**:plist 用 `/usr/bin/python3`,标准库即可(subprocess/threading/fcntl…无第三方依赖)。
- **凭证**:本服务不读明文密码,靠 lark-cli 自身的登录态(keychain),不进包。

## ③ 硬编码路径警告(换机器/换用户名必看)

脚本和 plist 里写死了 `/Users/zhongmengting/...` 绝对路径。若目标机:
- 用户名同为 `zhongmengting` → 直接 install_deps.sh 即可。
- 用户名不同 → install_deps.sh 会提示,需手改两处:
  1. `group_auto_reply.py` 顶部 `CLAUDE_BIN`
  2. `com.zmt.group-auto-reply.plist` 里 `ProgramArguments`/`WorkingDirectory`/`Std*Path` 的绝对路径

## ④ 部署后自查清单

```bash
lark-cli auth status                 # bot: ready ?
pgrep -fl group_auto_reply.py        # 服务进程在跑?
launchctl list | grep group-auto-reply
tail ~/.claude/logs/group_auto_reply.run.log   # 有 "starting consumer" ?
```
再在白名单群里 @机器人 发一句测试,看是否回帖。

## 注意:白名单群与本机绑定

`group_auto_reply.py` 里 `ALLOWED_CHATS` 是钟梦婷环境的两个群 chat_id,换环境需改成目标机器人所在群的 chat_id,且机器人要先被拉进那些群。
