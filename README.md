**中文** | **[English](#english)**

> **🧭 收徒 · 我靠这套路子吃饭，你也可以**
>
> 从「发现一个痛点」→「写个几百行的小工具」→「挂上资源位」→「有人付钱」，全流程我在这篇里讲透了。
> 想学这门手艺的，点这里：**[👉 收徒说明（知乎）](https://zhuanlan.zhihu.com/p/54351262)**

# 知乎 Morning Call · 本地播放器

**一个按钮，点开就播。** 不用装 App，不用翻知乎的播客页，不用每天早上找那个藏在二级菜单里的音频。

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Deps](https://img.shields.io/badge/dependencies-0-brightgreen)
![Local](https://img.shields.io/badge/runs%20on-127.0.0.1%3A8787-6f42c1)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 为什么做这个

知乎的 Morning Call 一天一期，只在 App 里能听。

想在电脑上听？打开网页版 `/podcast/morning-call/`，**404**。用 curl 抓一下，直接被 302 踢到登录页。它不是「藏起来了」，是压根没给网页版留入口。

但它的数据其实是开放的 —— `api.zhihu.com` 上那个接口，不带 cookie 就能拿到当天标题、封面、10 条热点，还有一个音频地址。问题只有一个：**那个地址是跨域的**，浏览器直接播会被拦。

所以就写了这个东西：本机跑一个小服务，替浏览器把该干的活干了。

```
浏览器  ──▶  127.0.0.1:8787  ──▶  api.zhihu.com     （元数据 + m3u8）
                              ──▶  知乎音频 CDN     （分片）
```

浏览器全程只跟 `127.0.0.1` 说话，跨域这回事就不存在了。

## 三步用起来

1. 装 Python 3.9+（**只用标准库，不需要 pip install**）
2. 双击 `start.cmd` —— 会自动打开 <http://127.0.0.1:8787/>
3. 点那个大按钮

Linux / macOS 一样能跑：

```bash
python3 server.py
```

`vendor/hls.min.js` 已经塞进仓库了，断网也能用。

## 界面上有什么

| 元素 | 说明 |
| --- | --- |
| 封面 + 标题 + 日期 | 当天节目的元数据，接口变了它自己会跟着变 |
| 76px 播放按钮 | 进度条、当前时间、总时长 |
| 音频直链输入框 | **已自动填好**当天的 m3u8；也可以手动粘别的地址 |
| 今日 10 条热点 | 点标题直接跳知乎对应问题 |
| 🔊 开声按钮 | 浏览器拦了自动播放的声音时，点一下就有 |
| 登录态输入框 | 可选。填 `z_c0` 用于未发布 / 需要登录的情况 |

## 三个我踩过的坑（都修了）

**1. 未发布时接口给的是占位地址**
`play_url.primary` 在节目上线前是 `.../player/0.m3u8`，请求它固定返回：

```json
{"error":{"code":20100,"message":"content not found: mcContentID=0"}}
```

带不带 cookie、换什么 UA 都一样 —— 因为服务端根本没内容可给。页面现在会**每 60 秒自动重试**，等到发布那一刻自动接上，你不用刷新。

**2. 跨域**
hls.js 直接 `loadSource('https://api.zhihu.com/...')` 会抛 `manifestLoadError`。
改成同源代理：m3u8 走 `/hls?u=`，分片走 `/seg?u=`，服务端在中间把 URI 全部改写一遍。

**3. 自动播放被浏览器拦**
现在打开就是**静音自动播**（否则连播都不让播）。
点页面任意处或右下角 `🔊 点击开声` 就有声音。
想以后直接带声：`chrome://settings/content/sound` 把 `127.0.0.1` 加进允许列表。

## 接口一览

| 路由 | 作用 |
| --- | --- |
| `GET /` | 播放页 |
| `GET /api/ep` | 当天节目元数据（标题 / 封面 / 10 条热点） |
| `GET /api/media` | 解析出可用的 m3u8（带兜底 id，结果缓存到 `media_cache.json`） |
| `GET /hls?u=` | 代理 m3u8，并把分片地址改写成 `/seg?u=` |
| `GET /seg?u=` | 代理音频分片（二进制透传） |
| `GET /api/probe?u=` | 探测任意音频地址：状态码 / Content-Type / 大小 / 前 16 字节 |
| `GET /api/diag` | 一次性体检：接口通不通、拿到什么地址、音频能不能取 |
| `GET /api/cookie?v=` | 保存知乎登录态 `z_c0` |

全部响应带 `Cache-Control: no-store` —— 改完代码刷新就生效，不用清缓存。

## 已知限制

- **只在本机跑**。没有做公网部署，也不打算做：它代理的是你的登录态。
- **节目没发布就没有声音**，这不是 bug，是知乎服务端就返回 404。等，或者填登录态。
- 音频版权是知乎的。自己听没问题，别拿去做二次分发。

## 作者

作者：[**知乎老哥**](https://www.zhihu.com/people/svip3) —— 点开在新窗口打开

## License

MIT

<a id=english></a>

# Morning Call Player

> Zhihu's daily podcast, in a local page with one big button. Click, it plays. Zero dependencies.

Zhihu publishes a daily audio show called Morning Call. The web player needs a login and the page itself is client-rendered, so a plain HTTP client gets a 404 or a redirect to the sign-in page. The JSON endpoint, however, is open — it returns the title, cover, ten hot topics and a play URL.

This project wraps that endpoint in a tiny Python server plus a single HTML page, so you can listen without opening Zhihu at all.

## How it works

    browser  →  127.0.0.1:8787  →  /api/ep   →  api.zhihu.com JSON
                                →  /api/media → resolves the real m3u8
                                →  /hls?u=   → proxies the playlist, rewrites segments
                                →  /seg?u=   → proxies the audio segments

Everything runs on loopback. No third-party service, no database, no build step.

## Run it

1. Install Python 3.9+ (standard library only — nothing to pip install).
2. Double-click `start.cmd`.
3. The browser opens `http://127.0.0.1:8787/` and starts playing.

Stop it by closing the console window. Set `MORNING_NO_BROWSER=1` to skip auto-opening the browser.

## Interface

| Element | Meaning |
|---|---|
| Big round button | Play / pause |
| Title and cover | Today's episode, pulled live from the API |
| Ten hot topics | Click any of them to open the matching Zhihu question |
| Audio URL box | Paste a direct `.m3u8` or `.mp3` if you grabbed one from the app |
| Login cookie box | Optional `z_c0~ value, for endpoints that require a session |
| Footer | Build timestamp, so you can tell which version you are running |

## Routes

| Route | Purpose |
|---|---|
| `/` | the page itself, served with `no-store` |
| `/api/ep` | proxy for the episode JSON |
| `/api/media` | resolve the latest real playlist URL |
| `/api/probe` | probe any URL, returns status, content type, size |
| `/hls?u=` | fetch the playlist and rewrite segment URIs to `/seg?u=` |
| `/seg?u=` | binary proxy for audio segments |
| `/api/cookie` | store or clear the optional login cookie |
| `/api/diag` | one-shot diagnostics: API status, title, media status |

## Three things that bit me

1. The API sometimes returns `player/0.m3u8`, which is a placeholder: requesting it gives HTTP 500 with `content not found: mcContentID=0`. No header or cookie fixes that — the episode simply is not published yet. The page retries every 60 seconds until a real ID appears.
2. hls.js cannot load the playlist cross-origin: you get `manifestLoadError`. Solved with a same-origin proxy — the page never talks to api.zhihu.com directly.
3. Autoplay is blocked unless the page has user interaction. It starts muted, plays, then unmutes on the first click; there is also a permanent speaker button.

## Known limitations

- Local only, no account, no history.
- If the episode has not been published, there is nothing to play — the page says so instead of hanging.
- Audio belongs to Zhihu; this is a personal listening tool, do not redistribute the files.

## Author

[知乎老哥](https://www.zhihu.com/people/svip3) — MIT licensed.

> **🧭 收徒 · 我靠这套路子吃饭，你也可以**
>
> 从「发现一个痛点」→「写个几百行的小工具」→「挂上资源位」→「有人付钱」，全流程我在这篇里讲透了。
> 想学这门手艺的，点这里：**[👉 收徒说明（知乎）](https://zhuanlan.zhihu.com/p/54351262)**
