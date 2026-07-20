# Android Tool Layer

本文档用于 `user-chance` 的 Android 设备接入、转转 App 环境检查和 mobile-mcp 健康检查。只有在设备接入、工具升级、换设备、换 App 包或排查工具层问题时读取；普通体验报告不需要加载本文件。

## 设备模式

`user-chance` 支持两类 Android 设备：

| 模式 | 用途 | 注意 |
|---|---|---|
| 真机 | 正式体验实验、重要问题验证 | 体验真实性更高，适合作为机会点主证据 |
| 模拟器 | 轻量预检、流程调试、报告契约回归 | 成本低、可批量，但不能替代真实用户设备结论 |

如果少爷没有指定设备，先做可启用端判断，不要继承历史设备选择。可用脚本：

```bash
/Users/liangkun/.codex/skills/user-chance/scripts/resolve_android_endpoints.sh
```

端选择规则：

| 场景 | 处理 |
|---|---|
| 只有 1 个在线可启用端 | 直接使用，并说明端类型 |
| 没有在线端，但存在 1 个可启动 AVD | 自动启动该模拟器，等待开机完成后继续 |
| 多个可启用端 | 列出候选端，请少爷确认 |
| 只有模拟器，且本轮要输出正式体验问题/机会点 | 可以继续跑，但报告标注“模拟器证据”；高优结论建议真机复核 |
| 没有在线端，也没有可启动 AVD | 请少爷连接真机或接入云真机 |

可启用端判断只决定“在哪个端上跑”，不替代运行前状态快照。

注意：mobile-mcp 的设备列表来自当前在线设备。`mobile_list_available_devices` 返回空，只能说明当前没有被 ADB 识别的在线真机或正在运行的模拟器；不能说明本机没有可启动的 AVD。遇到 MCP 无设备时，按顺序检查：

1. `adb devices -l` 是否为空。
2. 是否有正在运行的模拟器进程。
3. 本机是否存在 AVD 配置，例如 `~/.android/avd/*.avd`。
4. 是否能找到 emulator 启动器；Homebrew 命令行工具常见路径是 `/opt/homebrew/share/android-commandlinetools/emulator/emulator`，不一定在 PATH 中。

如果存在 AVD 但未运行，应把它列为“可启动端”，并由 Agent 自动启动，而不是要求少爷手动启动，也不能直接判断工具层失败。

少爷已经明确指定模拟器、当前只有一个可启动 AVD，或系统按规则自动选择模拟器后，Agent 应自动启动，不要让少爷手动启动：

```bash
/Users/liangkun/.codex/skills/user-chance/scripts/start_android_avd.sh user_chance_api35
```

启动脚本会寻找 emulator 二进制、启动 AVD、等待 ADB 设备上线和系统开机完成，并输出可继续使用的 ADB serial。macOS 下默认使用 `launchctl` 托管模拟器进程，避免命令结束后模拟器被当前执行环境带走；其他环境回退到 `nohup`。

模拟器启动必须使用稳定驻留方式。脚本默认 `EMULATOR_HEADLESS=1` 以无窗口模式运行，并默认追加 `-idle-grpc-timeout 0`，降低无窗口模拟器空闲退出风险；如果少爷需要看到模拟器窗口，可设置 `EMULATOR_HEADLESS=0`。启动完成后必须持续观察 ADB 在线状态，默认稳定观察 `45` 秒；如果设备短暂上线后消失，视为工具层启动失败，不能进入体验实验。

## 接入验收与运行前快照

不要把已验收能力每轮重复当成新问题检查。工具层分两层：

| 层级 | 做什么 | 触发时机 |
|---|---|---|
| 接入验收 | 确认 ADB、App 安装、包名、版本、启动入口、mobile-mcp 截图/元素/点击能力 | 首次接入、换设备、换 App 包、工具升级、能力异常 |
| 运行前状态快照 | 确认设备在线、目标 App 前台或可启动、登录态、当前页面、起始弹窗、首张截图和 UI 树可保存 | 每轮正式实验前 |

接入验收是工具能力问题；运行前状态快照是本轮实验起点问题。

## 转转 App 基线

| 字段 | 当前基线 |
|---|---|
| App | 转转 |
| 包名 | `com.wuba.zhuanzhuan` |
| 已验证模拟器版本 | `12.9.0` |
| 已验证设备 | Android 模拟器 `user_chance_api35` / Android 15 / `emulator-5554` |
| 官方下载链路 | `https://m.zhuanzhuan.com/common/app_download/index.html?app=zz&isOpen=1&channelId=` |

包名和版本必须以本轮设备实际返回为准。版本不同不是失败，但报告证据中必须记录版本号。

## APK 校验流程

当模拟器没有安装转转时，优先使用官方下载安装链路。安装前必须校验 APK：

1. 从官方转转下载页获取 APK。
2. 下载完成后拉取到本地证据目录。
3. 使用 `apkanalyzer manifest application-id <apk>` 校验包名。
4. 只有包名是 `com.wuba.zhuanzhuan` 时才可安装。
5. 安装后用 `pm list packages`、`dumpsys package`、`resolve-activity` 确认安装结果。

如果浏览器出现 "File might be harmful" 这类 APK 通用风险提示，必须向少爷说明来源、风险和控制方式，获得确认后再继续。

## 推荐脚本

环境检查：

```bash
/Users/liangkun/.codex/skills/user-chance/scripts/check_zhuanzhuan_android_env.sh emulator-5554
```

启动 App 并检查前台状态：

```bash
START_APP=1 /Users/liangkun/.codex/skills/user-chance/scripts/check_zhuanzhuan_android_env.sh emulator-5554
```

mobile-mcp 运行前快照：

```bash
node /Users/liangkun/.codex/skills/user-chance/scripts/mobile_mcp_healthcheck.mjs \
  --device emulator-5554 \
  --save-to /Users/liangkun/Documents/产品工作/user-chance-runs/<run_id>/preflight.png
```

`mobile_mcp_healthcheck.mjs` 必须严格失败：如果 mobile-mcp 设备列表没有目标设备、屏幕尺寸读取失败、截图文件没有生成、元素读取失败，均不能输出健康通过。

mobile-mcp 点击能力只在接入验收或受控页面中验证，不在每轮体验实验前随意点击：

```bash
node /Users/liangkun/.codex/skills/user-chance/scripts/mobile_mcp_healthcheck.mjs \
  --device emulator-5554 \
  --click 430,150
```

## 运行前状态快照要求

每轮正式实验前记录：

| 字段 | 说明 |
|---|---|
| `device_type` | `physical` 或 `emulator` |
| `device_id` | ADB serial，如 `emulator-5554` |
| `app_package` | 当前目标包名 |
| `app_version` | 当前设备安装版本 |
| `login_state` | 已登录 / 未登录 / 不确定 |
| `start_page` | 首页、搜索页、详情页、弹窗层等 |
| `blocking_layer` | 无 / 系统权限 / 运营活动 / 登录拦截 / 安全红线 / 不确定 |
| `first_screenshot` | 首张截图路径 |
| `first_ui_tree` | 首次 UI 树或元素快照路径 |

## 弹窗判断

弹窗不是默认红线。运行前或过程中遇到弹窗时，先判断它对本轮用户目标的意义。

| 类型 | 默认处理 |
|---|---|
| 系统权限 | 默认不授权，除非目标明确依赖 |
| 运营活动 | 结合角色和目标判断，可能关闭、领取、查看或忽略 |
| 普通权益/优惠 | 不是红线，按目标价值判断；查看说明、比较券后价、领取普通可放弃权益默认可尝试 |
| 登录拦截 | 若本轮要求已登录，提示登录态异常；若未登录任务可继续，则记录影响 |
| 支付/下单/实名/绑卡/客服 | 安全红线，停止或请求确认 |
| 高价值不可逆权益 / 付费会员 | 安全红线或请求确认 |

有些转转运营弹窗在 UI 树中只暴露为图片容器，不提供文字。遇到这类情况，不能仅依赖 UI 树；必须结合截图视觉内容判断，并在证据中标注“UI 树不可读，依据截图判断”。

## 工具失败与体验问题边界

工具层失败不能直接写成产品体验问题。

| 场景 | 结论口径 |
|---|---|
| ADB 找不到设备 | `tool_failure` |
| AVD 启动后没有稳定留在 ADB 列表 | `tool_failure`，优先检查 `launchctl` 托管、`-idle-grpc-timeout 0` 和本机资源，不写成产品体验问题 |
| App 未安装且无法取得官方包 | `tool_failure` 或接入未完成 |
| MCP 找不到目标设备或无法保存截图 | 证据链失败，不能继续正式实验 |
| UI 树读取不到文字但截图可见 | 可以继续，但证据需标注视觉判断 |
| 页面真实遮挡目标任务 | 可以作为体验点，但需截图支撑 |
