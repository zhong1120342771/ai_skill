---
name: 飞书群bot问答机制
description: >-
  飞书群 @机器人 → 常驻 Claude Code 工人池智能问答服务(group_auto_reply.py)的架构/流程/运维/成本控制说明书。
  当用户问到「群里@机器人怎么回复的」「群bot/自动回复服务怎么工作/怎么排障/怎么重启」「长连接还是轮询」
  「群bot耗多少token/怎么省钱/自动清空上下文」「机器人怎么调用Claude Code执行任务」「加白名单群/改worker数」
  「群bot没反应/爆外语/反应慢」等问题时,或需要改动、部署、排查这个群问答服务时,必须使用本 skill。
  这是运维说明型 skill:先读它搞清机制和现状,再动手改代码或排障,避免凭旧记忆误判。
---

# 飞书群 bot 问答机制说明书

飞书白名单群里 @ 机器人 → 常驻 Claude Code 工人池生成回复 → 以 bot 身份回到原消息话题。
本 skill 是这套服务的权威说明:机制、生效前提、运维命令、成本控制、排障。

**改动或排障前先读本文,再读源码确认现状** —— 代码会演进,本文的行号/参数以源码为准。

## 核心事实(先记住这几条)

- **不是轮询,是长连接。** 服务用 `lark-cli event consume im.message.receive_v1 --as bot` 跟飞书维持一条 WebSocket 长连接,事件实时推下来,全程没有任何定时拉取。
- **@bot = 真执行,不是聊天。** 每个 worker 是一个全权限 Claude Code 进程(`--dangerously-skip-permissions`),能跑 Bash/SQL/调 skill/出图/写飞书。跟你终端里的 Claude Code 是同一个二进制、同一台机、同一套 skill 和凭证,只是独立进程。
- **成本全额自付。** 群里每句 @ 都真调 Claude API,烧的是同一个账号额度。
- **只白名单群、只真人 @、只 bot 身份应答** —— 三重过滤防刷屏和自回环。

## 关键文件与路径

| 用途 | 路径 |
|------|------|
| 主服务脚本 | `~/.claude/scripts/group_auto_reply.py` |
| 花费统计脚本 | `~/.claude/scripts/group_auto_reply_cost_report.py` |
| launchd 托管 | `~/Library/LaunchAgents/com.zmt.group-auto-reply.plist`（label `com.zmt.group-auto-reply`）|
| 运行日志 | `~/.claude/logs/group_auto_reply.run.log` |
| 事件留档 | `~/.claude/logs/group_auto_reply.ndjson` |
| 花费日志 | `~/.claude/logs/group_auto_reply.cost.ndjson` |
| 单实例锁 | `~/.claude/logs/group_auto_reply.lock` |

监听 App = `cli_aa8e16c998b89cc5`（lark-cli 登录的 bot「菜的飞书 CLI」）；Claude 真身 `/Users/zhongmengting/.local/bin/claude`。

## 消息处理链路

```
飞书群有人 @机器人
      ↓
① lark-cli event consume ——长连接把消息事件推给 group_auto_reply.py
      ↓
② handle_line() 过滤: 白名单群? 群聊? 真人(ou_开头)? @了bot? 非空正文?
      ↓
③ 口令判断: reset类→清空记忆; 「保留上下文」→撤销自动清空预约
      ↓
④ worth_llm() 轻量过滤: 招呼语/太短/纯表情 → 不叫大模型,回引导语
      ↓
⑤ worker_of(chat_id)=crc32(群id)%NUM_WORKERS → 该群固定绑一个 worker
      ↓
⑥ 即时 ACK「收到,处理中…」+ 把消息塞进该 worker 队列
      ↓
⑦ worker 常驻 claude 进程从 stdin 吃消息 → 全权限执行 → stdout 吐 result
      ↓
⑧ send_reply() 用 lark-cli 以 bot 身份回到群里那条消息(reply-in-thread,失败回退普通send)
```

## 生效前提(排障先逐条核对)

群里 @ 他能收到并回复,下面几条要**同时**成立:

1. **服务进程在跑** —— `pgrep -fl group_auto_reply.py` 有 PID；launchd `RunAtLoad+KeepAlive` 保证开机自启、挂了自动拉起。
2. **机器不休眠、网络在线** —— 长连接靠机器活着。合盖睡眠/断网则连接断,睡眠期间的 @ 消息会丢(醒来后退避重连恢复,但补不回丢失的)。
3. **机器人在那个群里** —— 飞书只推「机器人所在群」的事件。不在群里=收不到,与长连接无关。
4. **群在白名单** —— `ALLOWED_CHATS` 里有该 chat_id。
5. **消息 @ 了 bot + 发送人是真人** —— 不 @ 不理;非 `ou_` 开头(机器人)不理,防自回环。
6. **bot 身份 token 有效** —— `lark-cli auth status` 里 `bot: ready`。launchd 模式无 cron 那种 keychain 坑;App Secret 变了/被踢需重新 `lark-cli auth`。

## 架构:为什么是常驻工人池

不是每条消息新起一个 `claude -p`(冷启动慢、无记忆),而是预开 N 个常驻 Claude Code 进程当工人:

- `NUM_WORKERS=2`(可调):每个是 `claude -p --input-format stream-json --output-format stream-json --dangerously-skip-permissions --verbose --append-system-prompt <SYS_PROMPT>` 长活进程。
- **喂消息** = 往进程 stdin 写一行 `{"type":"user",...}` JSON;**读结果** = 从 stdout 读到 `type=="result"` 那行。进程不退出,内存即多轮记忆。
- **群固定绑 worker**:`worker_of=crc32(chat_id)%NUM_WORKERS`,同群永远同一 worker → 记忆连续。两个群分属不同 worker,天然并行、记忆互不串。
- 懒启动:首条消息到该 worker 才 spawn。空闲进程只是开着等,不调 API、不花钱。
- **群数超过 NUM_WORKERS 会共享 worker、记忆串** —— 加群时同步调大 NUM_WORKERS。

`SYS_PROMPT` 里写死两条铁律:①永远简体中文(防长活 worker 记忆漂移到外语);②群问答双 skill 路由(见下)。每条消息前还夹一句 `ZH_REMINDER="[务必用简体中文回复]\n"` 兜底。

## 群问答双 skill 路由(写在 SYS_PROMPT 里)

- DAU、单量、订单量、GMV、支付PV/净支付 等**量级/取数**类 → 优先 skill『转转核心指标异动监控bot』(全局预聚合表,秒级最快)。
- 前端点击、曝光、留存、转化漏斗、栏目/模块表现 → skill『数据洞察agent_淑芬』。
- 两个都能做时选取数更快的(一般前者)。大盘量级默认先给整体,再拆三端(APP/小程序/找靓机)。

## 口令(群里 @机器人 发)

| 口令 | 效果 |
|------|------|
| `reset` `清空` `清除` `重置` `新会话` `忘记` `clear` 等 | 立即重启该群 worker,清空上下文 |
| `保留上下文` `保留` `别清` `keep` 等 | 撤销在途的「自动清空预约」,重新计时 |

## 成本控制机制(2026-07-31 加)

多轮对话「越聊越贵」的根源:常驻进程靠把历史对话每轮重发维持记忆。但 **prompt 缓存(cache_read)让重复历史部分只按 1/10 价计**,所以不是线性变贵。三道控制:

**① token 花费日志** —— 每轮写 `logs/group_auto_reply.cost.ndjson`(本轮增量花费/进程累计/in-out token/缓存命中)。查账:
```bash
python3 ~/.claude/scripts/group_auto_reply_cost_report.py           # 全部+按天
python3 ~/.claude/scripts/group_auto_reply_cost_report.py --today   # 只看今天
python3 ~/.claude/scripts/group_auto_reply_cost_report.py --by-chat # 按群拆
```
注意:`total_cost_usd` 是**进程级累计**,减去 worker 的 `_last_cost` 才是本轮增量;进程 spawn/reset 时归零。

**② 轻量过滤 worth_llm** —— 招呼语(在吗/你好/谢谢…)、少于 4 字、纯标点表情 → 不叫大模型,回引导语,零 token。

**③ 自动清空上下文(带提醒可喊停)** —— 看门狗线程(`WATCH_INTERVAL=60s` 巡检)。单 worker 空闲 `IDLE_LIMIT=1800`(30min) 或连续 `TURN_LIMIT=25` 轮任一 → **先群发提醒**,宽限 `WARN_GRACE=300`(5min):期间有新提问自动撤销、或 @回复「保留上下文」撤销;无人理则 reset 并告知。参数都在脚本顶部,想改阈值改常量即可。

## 运维命令

```bash
# 看服务状态
pgrep -fl group_auto_reply.py
launchctl list | grep group-auto-reply

# 重启(改完代码让其生效;断连约1秒再重连,基本无感)
launchctl unload ~/Library/LaunchAgents/com.zmt.group-auto-reply.plist
launchctl load   ~/Library/LaunchAgents/com.zmt.group-auto-reply.plist

# 看日志
tail -f ~/.claude/logs/group_auto_reply.run.log

# 改代码后先语法自检
python3 -m py_compile ~/.claude/scripts/group_auto_reply.py

# 加白名单群: 编辑脚本 ALLOWED_CHATS 加一行 chat_id,先确认机器人已被拉进该群,再重启
# 加 worker: 改 NUM_WORKERS,群数超过它会共享 worker 记忆串,加群记得一起调大
```

## 排障速查

见 `references/troubleshooting.md` —— 涵盖「@没反应/反应慢/爆外语」三大症的历史根因与修复、双 consumer 抢连接、keychain、上下文满等。改这套服务前**务必**读它,别重蹈 2026-07-20 崩溃循环的覆辙。

## 相关记忆

本机制的实时状态记在 memory `group-auto-reply-service`(白名单群清单、当前架构、历次大修)。改动后同步更新那条 memory。

