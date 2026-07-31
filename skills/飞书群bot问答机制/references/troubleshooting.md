# 排障速查

改这套服务前务必读本文,避免重蹈历史覆辙。症状→根因→修复,均为已发生并验证的真实事故。

## 三大症:@没反应 / 反应慢 / 爆外语(2026-07-20 崩溃循环)

**症状**:群里 @ 机器人久久无响应、时有时无;偶尔回复变成日文/英文。

**根因**:`event consume` 出现崩溃循环 —— stdout 一起来就关(6 分钟内秒退重连 30+ 次),launchd `KeepAlive+ThrottleInterval=10` 每 10s 硬重拉,期间 @ 事件全丢。最可能触发 = **同一 bot app 双 consumer 抢飞书长连接**(常驻服务 + 会话里另起的 poll 重叠)。爆外语则是长活 worker 记忆漂移。

**四项修复(已在代码里,别删)**:
1. **单实例锁** `acquire_lock()`:flock `logs/group_auto_reply.lock`,抢不到直接 `exit(0)`,杜绝双开抢连接。
2. **进程内退避重连**:`main()` 里 `while True` 包住 consume,断了自己 sleep backoff(2→60s,连过 120s 归零)重连,不再靠 launchd 每 10s 硬重拉刷屏。
3. **语言强制**:`SYS_PROMPT`(spawn 注入)+ 每条消息前夹 `ZH_REMINDER`,双保险防外语漂移。
4. **单轮超时兜底** `TURN_TIMEOUT=600`(10min):超时回一句「处理超时」,保证 @ 永远有响应,不会静默吞消息。

**排障动作**:先 `pgrep -fl group_auto_reply.py` 看是不是多个实例;`tail logs/group_auto_reply.run.log` 看有没有高频 "consume disconnected" 或 "another instance holds the lock"。若发现自己在会话里另跑了 consume,先停掉。

## keychain not initialized(仅 cron,launchd 无此坑)

launchd 托管本服务时**没有** keychain 问题。但若哪天改用 cron 拉起、报 `keychain not initialized`:真因是 `master.key.file` 过期不匹配;`mv` 走旧文件重跑 keychain-downgrade 刷新即可。详见 memory `feedback-larkcli-cron-keychain-fix`。

## 上下文满 / 越聊越贵

单 worker 聊太久 → 上下文膨胀。三条应对:
- 手动:群里发「清空」重启该 worker。
- 自动:看门狗空闲 30min / 25 轮触发预约清空(带 5min 提醒可喊停),见 SKILL.md 成本控制。
- 缓存:cache_read 让重复历史打 1/10 折,所以没有想象中线性贵。

## 回复发不出去 / 发错地方

- `send_reply` 优先 `im +messages-reply --reply-in-thread`,失败回退 `im +messages-send --chat-id`。
- P2P 与群不同:群消息用 `--chat-id`;若要私推个人用 `--user-id`(见 memory `feedback-larkcli-p2p-send-quirks`)。
- 群内以 bot 身份发(`--as bot`),对应 App `cli_aa8e16c998b89cc5`。

## 加群后收不到 @

飞书只推「机器人所在群」的事件。新群必须先把机器人 `cli_aa8e16c998b89cc5` 拉进去,再往 `ALLOWED_CHATS` 加 chat_id 并重启。两步缺一收不到。

## 关键设计点(改代码别踩)

- `event consume` 的 stdin 用 `os.pipe()` 只开不写保活(不 EOF),否则 consume 会因 stdin 关闭而退出。
- 每 worker 串行处理(queue),同群消息按序;两群分属不同 worker 天然并行。
- worker 的 `meta_lock` 保护活跃度/轮数/预约态,别和 `_ask` 的长持锁 `self.lock` 混用(否则看门狗会被卡住)。
- 正常新消息撤销预约时,若轮数已超 `TURN_LIMIT` 要把 `turn_count` 归零,否则下个巡检周期又立刻重新提醒 → 每分钟刷屏。
