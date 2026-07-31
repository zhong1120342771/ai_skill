#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群 @ 消息 → 常驻 Claude 工人池 智能回复服务
- 监听 App: cli_aa8e16c998b89cc5（lark-cli 当前登录 bot）
- N 个常驻 worker: 各是一个 `claude -p --input-format stream-json` 长活进程，进程内天然多轮记忆
- 群固定绑定 worker: worker_id = crc(chat_id) % N → 同群永远同一个工人，记忆连续
- 白名单群 / 剥 @ 前缀 / 只处理真人 / reset 口令 / 即时 ACK / launchd 常驻
"""
import subprocess, json, threading, queue, time, os, sys, zlib, signal, fcntl

# ---- 配置 ----
ALLOWED_CHATS = [
    "oc_f9d6d274f793f89b92c455b5691b0a00",
    "oc_cef7aa7e0c0b3cfd74912be497f4f926",
]
BOT_MENTION   = "@cai的飞书 CLI"
CLAUDE_BIN    = "/Users/zhongmengting/.local/bin/claude"
LARK_BIN      = "lark-cli"
NUM_WORKERS   = 2                    # 工人数（候补窗口 1、2）
WORKDIR       = os.path.expanduser("~/.claude")
LOGDIR        = os.path.join(WORKDIR, "logs")
RUNLOG        = os.path.join(LOGDIR, "group_auto_reply.run.log")
NDJSON        = os.path.join(LOGDIR, "group_auto_reply.ndjson")
COSTLOG       = os.path.join(LOGDIR, "group_auto_reply.cost.ndjson")  # 每轮 token/花费,一行一条JSON,便于统计
LOCKFILE      = os.path.join(LOGDIR, "group_auto_reply.lock")  # 单实例锁,防双开抢飞书长连接
TURN_TIMEOUT  = 600                  # 单轮上限 10min,超时兜底回一句,保证 @ 永远有响应
RESET_WORDS   = {"reset","清空","清除","清空记忆","清空上下文","新开","新会话",
                 "重新开始","重置","忘记","forget","clear","newchat","newsession"}
KEEP_WORDS    = {"保留上下文","保留","保留记忆","别清","不要清空","不清","keep","keepcontext"}

# 自动清空(省钱):空闲太久 / 单 worker 聊太多轮 → 先发提醒,宽限期内可喊停,否则清。
IDLE_LIMIT    = 1800   # 空闲 30min 触发预约清空
TURN_LIMIT    = 25     # 单 worker 累计 25 轮触发预约清空
WARN_GRACE    = 300    # 预约后宽限 5min,期间可 @机器人回复「保留上下文」取消
WATCH_INTERVAL= 60     # 看门狗巡检周期

# worker 常驻 system prompt: 强制中文 + 双 skill 取数路由
SYS_PROMPT = (
    "你是转转数据分析群助手。铁律:\n"
    "1. 永远用简体中文回复,任何情况下都不要用日文/英文/其他语言,除非用户在本条消息里明确要求换语言。\n"
    "2. 群里的数据取数问题按下面规则选 skill(哪个取数快用哪个):\n"
    "   - DAU、单量、订单量、GMV、支付PV/净支付、大盘核心指标等『量级/取数』类问题 → 优先用 skill『转转核心指标异动监控bot』"
    "(走全局预聚合表 hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di,秒级最快)。\n"
    "   - 涉及前端点击、曝光、留存、转化漏斗、栏目/模块表现等问题 → 用 skill『数据洞察agent_淑芬』。\n"
    "   - 两个都能做时选取数更快的(一般是前者)。\n"
    "3. 回复简洁直接:先给结论/数字,再补一句口径说明。大盘量级类默认先给整体,再给拆三端(APP/小程序/找靓机)。"
)
# 每条消息再夹一句中文提醒,防长活 worker 记忆漂移到外语
ZH_REMINDER = "[务必用简体中文回复]\n"

os.makedirs(LOGDIR, exist_ok=True)
os.chdir(WORKDIR)

_loglock = threading.Lock()
def log(msg):
    with _loglock:
        with open(RUNLOG, "a") as f:
            f.write(f"{time.strftime('%F %T')} {msg}\n")

def log_cost(rec):
    """把一轮的 token/花费写成一行 JSON,供事后统计(见 cost_report.py)。"""
    rec["ts"] = time.strftime("%F %T")
    with _loglock:
        with open(COSTLOG, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def is_allowed(chat_id): return chat_id in ALLOWED_CHATS
def worker_of(chat_id):  return zlib.crc32(chat_id.encode()) % NUM_WORKERS
def is_reset(text):      return text.strip().lower().replace(" ", "") in RESET_WORDS
def is_keep(text):       return text.strip().lower().replace(" ", "") in KEEP_WORDS

# 轻量过滤: 白名单+@+真人已在 handle_line 挡过,这里再挡"不值得叫大模型"的闲聊,省算力。
# 纯招呼/太短/纯标点表情 → 不叫 worker,回一句引导语即可。
_GREETINGS = {"在吗","在么","在不在","你好","您好","hi","hello","嗨","哈喽","在","hey",
              "早","早上好","下午好","晚上好","谢谢","感谢","好的","收到","ok","okk","👍","🙏"}
def worth_llm(text):
    t = text.strip().lower().replace(" ", "")
    if len(t) < 4:          return False   # 太短(如"?"、"a")
    if t in _GREETINGS:     return False   # 纯招呼语
    if not any(c.isalnum() for c in t):    return False  # 纯标点/表情
    return True

def send_reply(message_id, chat_id, text):
    # 优先 reply-in-thread；失败回退普通 send 到该群
    r = subprocess.run([LARK_BIN,"im","+messages-reply","--message-id",message_id,
                        "--text",text,"--reply-in-thread","--as","bot"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run([LARK_BIN,"im","+messages-send","--chat-id",chat_id,
                        "--text",text,"--as","bot"], capture_output=True, text=True)


class Worker:
    """一个常驻 claude stream-json 进程。串行处理分给它的群消息（同群记忆连续）。"""
    def __init__(self, wid):
        self.wid = wid
        self.q = queue.Queue()
        self.proc = None
        self.lock = threading.Lock()
        self._last_cost = 0.0   # 上轮 total_cost_usd(进程级累计),用于算本轮增量
        # 自动清空相关元数据(meta_lock 保护,别和 _ask 的长持锁混用)
        self.meta_lock = threading.Lock()
        self.last_activity = time.time()
        self.turn_count = 0
        self.pending_since = 0.0      # >0 表示已发预约清空提醒,值为提醒时刻
        self.chats = set()            # 该 worker 服务过的群(reset 影响这些群,提醒发给它们)
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _spawn(self):
        self.proc = subprocess.Popen(
            [CLAUDE_BIN,"-p","--input-format","stream-json",
             "--output-format","stream-json","--dangerously-skip-permissions","--verbose",
             "--append-system-prompt",SYS_PROMPT],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        self._last_cost = 0.0   # 新进程,累计花费归零
        with self.meta_lock:
            self.turn_count = 0
            self.pending_since = 0.0
            self.last_activity = time.time()
        log(f"worker{self.wid} spawned pid={self.proc.pid}")

    def _alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _ask(self, text):
        """喂一条消息，读到本轮 result 返回 (文本, meta)。进程若死则重启。
        meta 带本轮 token 用量与花费,供 _run_loop 记账;失败/超时返回 (None, None)。"""
        if not self._alive():
            self._spawn()
        msg = {"type":"user","message":{"role":"user",
               "content":[{"type":"text","text":text}]}}
        try:
            self.proc.stdin.write(json.dumps(msg)+"\n"); self.proc.stdin.flush()
        except Exception as e:
            log(f"worker{self.wid} stdin broken ({e}); respawn")
            self._spawn()
            self.proc.stdin.write(json.dumps(msg)+"\n"); self.proc.stdin.flush()
        end = time.time() + TURN_TIMEOUT
        while time.time() < end:
            line = self.proc.stdout.readline()
            if not line:
                return None, None  # 进程 EOF/崩溃
            try: obj = json.loads(line)
            except: continue
            if obj.get("type") == "result":
                u = obj.get("usage") or {}
                meta = {
                    "input_tokens": u.get("input_tokens", 0),
                    "output_tokens": u.get("output_tokens", 0),
                    "cache_creation_input_tokens": u.get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": u.get("cache_read_input_tokens", 0),
                    "cost_usd": obj.get("total_cost_usd", 0),
                    "num_turns": obj.get("num_turns", 0),
                    "duration_ms": obj.get("duration_ms", 0),
                }
                return obj.get("result",""), meta
        return None, None  # 超时

    def reset(self):
        """清该 worker 记忆 = 重启进程（工人只服务固定的群集合，重启即清）。"""
        with self.lock:
            if self._alive():
                try: self.proc.stdin.close()
                except: pass
                try: self.proc.wait(timeout=10)
                except: self.proc.kill()
            self.proc = None
        with self.meta_lock:
            self.turn_count = 0
            self.pending_since = 0.0
            self.last_activity = time.time()
        log(f"worker{self.wid} reset (respawn on next msg)")

    def cancel_pending(self):
        """用户喊停「保留上下文」→ 撤销预约清空,活跃时间刷新,重新计时。"""
        with self.meta_lock:
            was = self.pending_since > 0
            self.pending_since = 0.0
            self.last_activity = time.time()
            self.turn_count = 0   # 保留记忆但轮数清零,避免立刻又触发
        return was

    def submit(self, job): self.q.put(job)

    def _run_loop(self):
        while True:
            job = self.q.get()
            msg_id, chat_id, prompt = job
            with self.lock:
                reply, meta = self._ask(ZH_REMINDER + prompt)
            if not reply:
                log(f"worker{self.wid} failed msg_id={msg_id} chat={chat_id}")
                reply = "抱歉，这条处理超时或出错了，换个说法再试试。"
            send_reply(msg_id, chat_id, reply)
            log(f"worker{self.wid} replied msg_id={msg_id} chat={chat_id} len={len(reply)}")
            with self.meta_lock:
                self.last_activity = time.time()
                # 若正处于预约态且是轮数超限触发的,新消息=用户还在用→轮数归零重新数,避免每分钟重复提醒
                if self.pending_since > 0 and self.turn_count >= TURN_LIMIT:
                    self.turn_count = 0
                self.turn_count += 1
                self.pending_since = 0.0   # 有新活动→撤销任何在途的预约清空
                self.chats.add(chat_id)
            if meta:
                # total_cost_usd 是进程级累计,减上轮得本轮增量成本
                turn_cost = round(max(0.0, meta["cost_usd"] - self._last_cost), 6)
                self._last_cost = meta["cost_usd"]
                log_cost({
                    "worker": self.wid, "chat_id": chat_id, "msg_id": msg_id,
                    "turn_cost_usd": turn_cost,
                    "proc_cum_cost_usd": round(meta["cost_usd"], 6),
                    "input_tokens": meta["input_tokens"],
                    "output_tokens": meta["output_tokens"],
                    "cache_read_input_tokens": meta["cache_read_input_tokens"],
                    "cache_creation_input_tokens": meta["cache_creation_input_tokens"],
                    "num_turns": meta["num_turns"],
                    "duration_ms": meta["duration_ms"],
                    "prompt_head": prompt[:60],
                })
                log(f"worker{self.wid} cost turn=${turn_cost} cum=${round(meta['cost_usd'],4)} "
                    f"in={meta['input_tokens']} out={meta['output_tokens']} "
                    f"cache_read={meta['cache_read_input_tokens']}")


def acquire_lock():
    """单实例锁:抢不到说明已有健康实例在跑,直接干净退出(不再和它抢飞书长连接)。"""
    f = open(LOCKFILE, "w")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("another instance holds the lock — exit cleanly (no double consumer)")
        sys.exit(0)
    f.write(str(os.getpid())); f.flush()
    return f  # 需保持句柄存活 → 进程退出前不释放


def handle_line(line, workers):
    line = line.strip()
    if not line: return
    try: ev = json.loads(line)
    except: return
    if ev.get("type") != "im.message.receive_v1": return

    chat_id  = ev.get("chat_id","")
    chat_type= ev.get("chat_type","")
    sender   = ev.get("sender_id","")
    content  = ev.get("content","")
    msg_id   = ev.get("message_id","")

    if not is_allowed(chat_id): return
    if chat_type != "group": return
    if not sender.startswith("ou_"): return   # 只真人；防自回环
    if not msg_id: return

    with open(NDJSON, "a") as f: f.write(line+"\n")

    # 剥 @ 前缀
    prompt = content
    for pre in (BOT_MENTION+" ", BOT_MENTION):
        if prompt.startswith(pre): prompt = prompt[len(pre):]
    prompt = prompt.strip()
    if not prompt: return

    log(f"recv msg_id={msg_id} chat={chat_id} sender={sender} prompt={prompt[:100]}")

    wid = worker_of(chat_id)
    if is_reset(prompt):
        workers[wid].reset()
        send_reply(msg_id, chat_id, "已清空本群对话记忆，下一条重新开始。")
        log(f"reset chat={chat_id} worker={wid}")
        return

    # 「保留上下文」= 撤销在途的自动清空预约
    if is_keep(prompt):
        was = workers[wid].cancel_pending()
        send_reply(msg_id, chat_id,
                   "好的，已保留本群上下文，重新计时。" if was else "当前没有待清空的预约，上下文保持不变。")
        log(f"keep(cancel pending) chat={chat_id} worker={wid} was_pending={was}")
        return

    # 轻量过滤: 招呼语/太短不值得叫大模型,回引导语,省算力
    if not worth_llm(prompt):
        send_reply(msg_id, chat_id, "在的，直接把要查的数据问题发我，比如「昨天APP的DAU多少」。")
        log(f"skip(not worth_llm) chat={chat_id} prompt={prompt[:50]}")
        return

    send_reply(msg_id, chat_id, "收到，处理中…")
    workers[wid].submit((msg_id, chat_id, prompt))


def send_group(chat_id, text):
    """主动给群发消息(无 message_id,不走 reply)。看门狗提醒用。"""
    subprocess.run([LARK_BIN,"im","+messages-send","--chat-id",chat_id,
                    "--text",text,"--as","bot"], capture_output=True, text=True)


def watchdog(workers):
    """看门狗:空闲超限 / 轮数超限 → 先发提醒(预约),宽限期到仍无人活动/喊停则清空。"""
    warn = (f"这个会话已{{reason}}，为省资源将在 5 分钟后自动清空上下文。"
            f"若还要接着聊、需要保留上下文，请 @机器人 回复「保留上下文」。")
    while True:
        time.sleep(WATCH_INTERVAL)
        now = time.time()
        for w in workers:
            with w.meta_lock:
                alive = w.proc is not None and w.proc.poll() is None
                idle = now - w.last_activity
                turns = w.turn_count
                pending = w.pending_since
                chats = list(w.chats)
            if not alive or not chats:
                continue  # 没起进程/没服务过群,无上下文可清
            # 阶段二:已预约,看宽限期是否到点
            if pending > 0:
                if now - pending >= WARN_GRACE:
                    w.reset()
                    for c in chats:
                        send_group(c, "已自动清空本群上下文（长时间无人继续）。下一条重新开始。")
                    log(f"watchdog auto-reset worker{w.wid} chats={chats}")
                continue
            # 阶段一:未预约,判断是否该触发
            reason = None
            if idle >= IDLE_LIMIT:
                reason = f"已闲置 {int(idle//60)} 分钟"
            elif turns >= TURN_LIMIT:
                reason = f"已连续对话 {turns} 轮"
            if reason:
                with w.meta_lock:
                    w.pending_since = now
                for c in chats:
                    send_group(c, warn.format(reason=reason))
                log(f"watchdog warn worker{w.wid} reason={reason} chats={chats}")


def main():
    _lock = acquire_lock()  # noqa: F841 (保活)
    workers = [Worker(i) for i in range(NUM_WORKERS)]
    threading.Thread(target=watchdog, args=(workers,), daemon=True).start()
    log(f"starting consumer; workers={NUM_WORKERS}; allowed={ALLOWED_CHATS}")

    # 进程内带退避重连:consume 断了就自己重连,不再靠 launchd 每 10s 硬重拉(那会引发抢连接刷屏)
    backoff = 2
    while True:
        # os.pipe 只开不写 → consume 的 stdin 永不 EOF
        r_fd, w_fd = os.pipe()
        started = time.time()
        consume = subprocess.Popen(
            [LARK_BIN,"event","consume","im.message.receive_v1","--as","bot"],
            stdin=r_fd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        os.close(r_fd)

        for line in consume.stdout:
            handle_line(line, workers)

        # 走到这里 = consume stdout 关闭(长连接断)。清理后退避重连。
        try: os.close(w_fd)
        except OSError: pass
        try: consume.wait(timeout=5)
        except Exception: consume.kill()

        ran = time.time() - started
        if ran > 120:            # 连过一段时间才断 → 视为正常抖动,退避归零
            backoff = 2
        log(f"consume disconnected after {ran:.0f}s — reconnect in {backoff}s")
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: (log("SIGTERM, bye"), sys.exit(0)))
    main()
