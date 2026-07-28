---
name: skill备份
description: 把 ~/.claude/skills 下用户自己的 skill 增量同步并推送到 GitHub 仓库 zhong1120342771/ai_skill。日维度检查有更新的 skill 文件就覆盖推送。触发词：skill备份、备份skill、同步skill到github、推送skill。
---

# skill备份

把本机 `~/.claude/skills` 下**用户自己的** skill（排除内置 lark-* 软链、`.bak` 备份、data/产物/缓存/密钥）
同步到 staging 仓 `~/ai_skill_sync` 并推送到 GitHub `https://github.com/zhong1120342771/ai_skill`。

## 何时触发
- 用户说「skill备份」「备份 skill」「同步 skill 到 github」「推送 skill」。
- 每日 cron 自动跳入（见下「定时」）。

## 怎么做（一步）
直接运行脚本，按输出播报：

```bash
bash ~/.claude/skills/skill备份/scripts/backup_skills.sh
```

脚本输出约定：
- `NO_CHANGES` —— 无 skill 变动，静默结束，不打扰用户、不推送。
- `PUSHED_OK <时间>` —— 有变动已提交并推送成功，向用户简报变更文件数即可。
- `PUSH_FAILED` —— 提交成功但推送失败（多半是 token 过期/被撤销）。提示用户到
  https://github.com/settings/tokens 重新生成含 `public_repo` 权限的 token，再运行
  `bash ~/.claude/skills/skill备份/scripts/update_token.sh <新token>` 更新本机凭证后重试。

## 覆盖逻辑
每次运行都**重建** staging 仓的 `skills/` 快照（先删后拷），再 `git add -A`，
因此 skill 的新增/修改/删除都会被如实覆盖到远端；采用增量 commit（保留历史、可回溯）。

## 认证
自动推送依赖 git credential store（`~/.git-credentials` 明文 token，仅本机可读，chmod 600）。
token 只需 `public_repo` 权限。token 过期或被撤销后自动推会失败，用 `scripts/update_token.sh` 换新。
**红线**：token 只进本机凭证库，绝不提交进仓库；脚本推送失败时会把日志里的 token 打码。

## 定时（macOS launchd，不依赖 Claude 会话）
每天 **20:07** 由系统级 launchd agent `com.zmt.skill-backup` 直接跑 `backup_skills.sh`，
和 Claude 会话完全解耦——只要 Mac 开着机就会执行；关机/睡眠错过的那次，唤醒后 launchd 会补跑一次。

> 为什么不用 Claude Code 的 cron：会话级 cron 是内存态，REPL 一关就失效；durable recurring cron 约 7 天自动过期。做长期每天例行不可靠，故迁到 launchd。

- plist 位置：`~/Library/LaunchAgents/com.zmt.skill-backup.plist`
- 运行日志：`~/.claude/skills/skill备份/backup.out.log`（stdout）、`backup.err.log`（stderr）

### 运维命令
```bash
# 看它在不在、上次退出码（第二列 0 = 正常）
launchctl list | grep skill-backup

# 看最近一次跑的输出（NO_CHANGES / PUSHED_OK / PUSH_FAILED）
tail -20 ~/.claude/skills/skill备份/backup.out.log

# 改完 plist 后重载（先卸再装）
launchctl unload ~/Library/LaunchAgents/com.zmt.skill-backup.plist
launchctl load  ~/Library/LaunchAgents/com.zmt.skill-backup.plist

# 不等到点，立刻手动触发一次验证
launchctl start com.zmt.skill-backup
```

### 换机器/重装后恢复
1. 确认 `backup_skills.sh` 里的 `REMOTE_URL` 指向 `zhong1120342771/ai_skill`。
2. 配好 `~/.git-credentials` 的 token（见「认证」；含 `public_repo` 权限）。
3. 把 `com.zmt.skill-backup.plist` 放到 `~/Library/LaunchAgents/`，注意 plist 里
   `HOME`、脚本路径、日志路径都写的是绝对路径 `/Users/zhongmengting/...`，换用户名要一并改。
4. `launchctl load ~/Library/LaunchAgents/com.zmt.skill-backup.plist`，再用上面的 `list` 确认已加载。
