---
name: browser-profile-inspection
description: Use when 查本机浏览器登录的是哪个账号、哪个区、有几个配置（Chrome/Edge 只读取证）。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [chrome, edge, windows, account, forensics]
    related_skills: [cn-android-foreign-apps, windows-app-troubleshooting]
---

# 本机浏览器配置取证（Chrome / Edge）

## When to Use

问"我电脑登录的谷歌/微软账号是哪个""这号是哪个区的""我有几个浏览器配置""书签/历史/扩展在哪"，或要确认某账号是否还在登录态。

## 0. 先分清两个问题
- **账号是谁** → 本地文件直接读（§1），几十秒出结果。
- **账号属于哪个地区** → 本地根本没有这个字段（§3）。先把身份答出来，再说地区怎么确认，不要用网络痕迹硬猜。

## 1. 读登录账号（只读 JSON，不碰 cookie）
路径：`%LOCALAPPDATA%\Google\Chrome\User Data\`（Edge 换成 `Microsoft\Edge\User Data`）。

| 文件 | 键 | 内容 |
|---|---|---|
| `Local State` | `profile.info_cache.<配置目录>` | `gaia_id` / `gaia_name` / `gaia_given_name` / 头像文件 |
| `Preferences` | `account_info[]` | `email` / `full_name` / `gaia` / `locale` / `hd` |
| `Secure Preferences` | `google.services.last_signed_in_username` | 最后登录邮箱（兜底） |
| `Local State` | `variations_country` | **浏览器**地区，不是账号地区 |

直接跑 `scripts/browser_accounts.py`（纯 stdlib，Chrome/Edge/Brave/Chromium 全扫，按配置列邮箱/昵称/gaia/locale/最后登录）。

- 浏览器开着也能读：这些是 JSON，只读不锁。但 `History`、`Cookies`、`Web Data` 是 SQLite，**必须先 `cp` 到临时目录再打开**，否则锁库或读到空表。
- `Preferences` 可能被写到一半而 JSON 损坏 → `json.load` 抛错就换 `Secure Preferences` 兜底，别直接报"没登录"。
- 一个 `User Data` 下可能有 `Default` + `Profile 1..N`，每个配置是独立账号，全部列出再答。

## 2. 登录态到底在不在
- `Preferences → google.services.signin.REFRESH_TOKEN_RECEIVED` 有时间戳 = 有有效刷新令牌（真登录）。
- `Network/Cookies` 里 `.google.com` 出现 `SID` / `__Secure-1PSID` = 有会话 cookie。
- 只有 `ACCOUNT_CHOOSER` / `__Host-GAPS`、没有 SID = 只是"记住过这个号"，不算登录，别说成已登录。

## 3. "哪个地区"——本地无解，别绕路
**Google 账号没有"地区"字段**，`account_info` 里只有 `locale`（界面语言）。用户要的地区通常是下面之一：
- **Play 国家/地区** → `play.google.com/store/account`（决定应用、订阅、Google One 定价；通常一年只能改一次）
- **付款资料国家** → `payments.google.com` → 设置
- **YouTube Premium 区** → 跟随付款资料

不能当地区证据的三样：`accounts.google.com.hk`（大陆直连的香港域跳转）、`variations_country=cn`（浏览器地区）、`locale=zh-CN`（界面语言）。它们只说明人和网络在哪，跟账号归属无关。

答法：先给确定项（邮箱/昵称/gaia/最后登录时间，标明读自哪个文件），再说地区需登录后看，给出上面两条路径；末尾提议替他打开页面或问他买什么（Google One / Gemini / Play 应用），按用途盯对应页。

## 4. 坑（按代价排序）
- **别为了拿调试端口去“换路径启动默认配置”——会清空用户的 cookie。** 实测：Edge 157 直接用默认配置开 `--remote-debugging-port` 会拒绝（`DevTools remote debugging requires a non-default data directory`）；用目录联接（junction）指向同一份 User Data 骗过检查后端口虽通，但 cookie 解不开（v20 密钥绑原路径），浏览器按设计把解不开的 cookie **删除**：一次丢掉约 590/668 条 cookie，含 GitHub `user_session`，用户被迫重新登录几乎所有网站。看到“要用调试端口接管已登录浏览器”的念头，直接放弃这条路。
- **真正可行的接管方式：`computer_use` 驱动真实窗口。** 拉起 `msedge.exe <url>`（`powershell Start-Process`，不要 `cmd /c start`，会卡住前台命令）+ `capture(mode='som')` 拿元素、`click`/`key` 走 `delivery_mode='foreground'`（Chrome_WidgetWin_1 不吃后台按键）。密码框由浏览器自己自动填充，就能在不读明文密码的前提下完成登录。
- **复制 profile 到别的 `--user-data-dir` 再用 headless Chrome 打开 Google，必然撞登录墙。** 机制：cookie 已升级为 app-bound 加密（前缀 `v20`，密钥锁在浏览器 elevation service），叠加 DBSC 设备绑定会话，复制品既解不了 cookie 也过不了设备校验。别在这条路上耗时。
- **不要尝试绕过 app-bound 加密 / DBSC**（v20 解密、搬密钥、模拟设备）。这是浏览器的安全边界，不是查资料该做的事：读到明文元数据就停，剩下的让用户点一下。
- cookie 解密脚本碰到 `v20` 只会吐出垃圾字节，看到 `v20` 立刻收手，不要写一长串"尝试解密"的过程。
- 要第三方库时用 `uv run --with <pkg> python x.py`，别往用户全局 Python 里装包。
- 回答"哪个区"时别把账号资料全铺开（出生年、头像 URL、gaia 之类只给必要的），隐私信息点到为止。

## 5. 交付
短表格或列表，分两段：**本地已确认** / **需登录才能确认**。推测不许写成事实。
