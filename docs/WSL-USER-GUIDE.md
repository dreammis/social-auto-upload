# WSL2 用户指南

> 适用对象: 在 WSL2 (Windows Subsystem for Linux) 环境下使用 social-auto-upload 的用户。
> 也适用于: 任何 Linux server / Linux 桌面环境 (无 GUI 或装了 patchright 但没装系统 Chrome)。

本文汇总 SAU 在类 Unix 环境下的踩坑与对应绕过方案,每节末尾给出"一句话总结"。

---

## 1. 抖音扫码登录 headless 模式被反爬墙识别

**症状**: `sau douyin login --account foo` 在 `--headless` 模式下反复报 `cookie 已失效`,
但实际 cookie 文件存在;或者扫码后页面跳转过快,被检测为 bot。

**原因**: 抖音创作者中心的反爬墙模块对无头浏览器 (headless) 检测敏感,经常将正常的扫码登录误判为 bot 失效。

**解决**: 默认走 headed 模式 (即默认 `--headed`,不传 `--headless`)。
如确实需要无头 (CI/CD / 服务器),显式设 `DOUYIN_COOKIE_AUTH_HEADLESS=true`:

```bash
# 推荐:headed 模式
sau douyin login --account myaccount --headed

# CI/CD 才用 headless
DOUYIN_COOKIE_AUTH_HEADLESS=true sau douyin login --account myaccount --headless
```

**一句话总结**: 抖音登录默认用 headed,只在 CI 里才开 headless。

---

## 2. Chrome 默认绑 IPv6 `::1:9222`,WSL2 无法访问

**症状**: `sau douyin login --cdp-url http://172.19.224.1:9222` 连不上 Windows 上的 Chrome DevTools。

**原因**: Chrome 111+ 移除了 `--remote-debugging-address` flag,只剩 `--remote-debugging-port`。
Chrome 默认绑 IPv6 `::1:9222` (dual-stack socket 在 Windows 优先 IPv6 loopback),而:
- WSL 的 IPv6 namespace 跟 Windows 不通 → `[::1]:9222` 失败
- WSL 自己的 IPv4 `127.0.0.1:9222` 是 WSL 的 loopback,不是 Windows 的 → 失败
- WSL 唯一能访问的 Windows IP 是 `172.19.224.1` (vEthernet (WSL) 适配器)

**解决**: 在 Windows 桌面跑一个 IPv4→IPv6 TCP proxy,转发 `0.0.0.0:9222` → `[::1]:9222`。

### 2.1. IPv4→IPv6 TCP proxy (Python)

把这个脚本保存到 `C:\Users\Admin\AppData\Local\Temp\chrome_cdp_proxy.py`:

```python
import asyncio

async def relay(reader, writer, label):
    try:
        while True:
            data = await reader.read(65536)
            if not data: break
            writer.write(data); await writer.drain()
    finally:
        writer.close()

async def handle(cr, cw):
    tr, tw = await asyncio.open_connection("::1", 9222)
    await asyncio.gather(relay(cr, tw, "c->t"), relay(tr, cw, "t->c"))

async def main():
    s = await asyncio.start_server(handle, "0.0.0.0", 9222, reuse_address=True)
    async with s: await s.serve_forever()

asyncio.run(main())
```

启动 (PowerShell,后台运行):
```powershell
Start-Process -FilePath 'C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe' `
  -ArgumentList '-u','C:\Users\Admin\AppData\Local\Temp\chrome_cdp_proxy.py' `
  -RedirectStandardOutput 'C:\Users\Admin\AppData\Local\Temp\cdp_proxy.log' `
  -WindowStyle Hidden
```

⚠️ **必须先删除 netsh portproxy**: `netsh interface portproxy delete v4tov4 listenport=9222` —
proxy 自己要 bind 9222 端口,不能跟 portproxy 抢。

### 2.2. 在桌面双击 .bat 启动 Chrome (有 UI)

Chrome 通过 WSL interop (`powershell.exe Start-Process chrome.exe`) 启动会跑到 Session 0,
**没有 UI 窗口**,无法扫码。**必须用户在桌面双击 .bat** 启动。

把下面保存为 `C:\Users\Admin\Desktop\SAU-Login-Chrome.bat`:

```bat
@echo off
taskkill /F /IM chrome.exe /T 2>nul
timeout /t 3 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-sau-login --remote-allow-origins=* "https://creator.douyin.com/"
exit
```

⚠️ **.bat 必须纯 ASCII**: UTF-8 中文 echo 在 cmd GBK 下变乱码当命令执行,会崩溃。
注释也写英文。

按需修改启动 URL:
- 抖音: `https://creator.douyin.com/`
- 快手: `https://cp.kuaishou.com/`
- B 站: `https://member.bilibili.com/`

### 2.3. WSL 端验证

```bash
# 确认 proxy 在听
curl -s http://172.19.224.1:9222/json/version | head

# 用 SAU 接 CDP
sau douyin login --account myaccount --headed --cdp-url http://172.19.224.1:9222
```

**一句话总结**: Chrome 必须桌面启动 + Windows 跑 IPv4→IPv6 proxy + WSL 通过 `172.19.224.1:9222` 接。

---

## 3. 系统找不到 Chrome: `Chromium distribution 'chrome' is not found`

**症状**:
```
playwright._impl._errors.Error: Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome
```

**原因**: SAU 默认 `channel="chrome"`,Playwright 会去找系统装的 Google Chrome。
WSL2 Kali 通常没装,只有 patchright bundled 的 Chromium。

**解决 (v0.3.0+ 默认行为)**: SAU 已默认改用 `chromium` channel (patchright bundled),无需任何操作。

需要强制用系统 Chrome:
```bash
SAU_BROWSER_CHANNEL=chrome sau douyin login --account myaccount
```

需要 Edge:
```bash
SAU_BROWSER_CHANNEL=msedge sau douyin login --account myaccount
```

**一句话总结**: 默认用 bundled chromium,设 `SAU_BROWSER_CHANNEL=chrome` 切回系统 Chrome。

---

## 4. `--cdp-url` 让 WSL 用户用桌面 Chrome 扫码

**症状**: 想用 Windows 上已经登录好的 Chrome (有 UI) 扫码,但 SAU 默认会启动新的 headless Chromium。

**解决**: 所有 Playwright-based 平台 (`douyin`, `kuaishou`, `xiaohongshu`, `tencent`, `youtube`) 现在都支持 `--cdp-url`:

```bash
sau <platform> login --account myaccount --headed --cdp-url http://172.19.224.1:9222
```

前置条件: Chrome 必须在 Windows 桌面用 `.bat` 启动并带 `--remote-debugging-port=9222`
(参见 §2)。SAU 通过 `connect_over_cdp` 接到现有 Chrome,扫完码保存 cookie,**不会关掉你的 Chrome**。

⚠️ **不支持 `--cdp-url` 的平台**: `bilibili` (用 biliup CLI 而不是 Playwright)。

**一句话总结**: `--cdp-url` 把 SAU 接到桌面 Chrome,扫码后 Chrome 不会被关掉。

---

## 5. Chrome `--user-data-dir` 必须保留

**症状**: 每次跑 `sau douyin login` 都要重新扫码,之前登录态丢了。

**原因**: Chrome 不带 `--user-data-dir` 时,每次启动都新建临时 profile,cookie / login state 都不持久。

**解决**: `.bat` 启动 Chrome 时显式指定固定目录 (例子里用的是 `%TEMP%\chrome-sau-login`,
重启电脑后 `%TEMP%` 被清空,**Windows 桌面建议改成 `%USERPROFILE%\AppData\Local\chrome-sau-login`**):

```bat
@echo off
taskkill /F /IM chrome.exe /T 2>nul
timeout /t 3 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\AppData\Local\chrome-sau-login --remote-allow-origins=* "https://creator.douyin.com/"
exit
```

**一句话总结**: Chrome 启动必须带 `--user-data-dir=固定路径`,否则每次都得重新登录。

---

## 6. Windows .bat 不能含 UTF-8 中文

**症状**: 双击 .bat 立即弹出 cmd 窗口又关掉,或报"找不到命令"。

**原因**: Windows cmd 默认 GBK 编码,UTF-8 BOM 文件的中文 echo 会被解析为乱码命令并执行失败。

**解决**: `.bat` 文件保存为 ANSI / GBK / 纯 ASCII。注释也写英文。

**一句话总结**: `.bat` 文件**永远不要含中文**,包括注释。

---

## 7. 完整 WSL2 工作流示例 (抖音)

```bash
# 一次性 setup (Windows 桌面 PowerShell)
#   1. 把 §2.1 的 Python proxy 保存到 C:\Users\Admin\AppData\Local\Temp\chrome_cdp_proxy.py
#   2. 启动 proxy: Start-Process python.exe -ArgumentList '-u', 'C:\...\chrome_cdp_proxy.py' ...
#   3. 桌面双击 §2.2 的 .bat,Chrome 弹出并打开 https://creator.douyin.com/
#   4. (可选) 在 Chrome 里手动登录抖音,这样 cookie 就存到 user-data-dir

# WSL 端日常使用
source ~/.local/bin/proxy_switch.sh auto   # 网络命令前激活代理
sau douyin login --account myaccount --headed --cdp-url http://172.19.224.1:9222
sau douyin upload-video --account myaccount --file ./video.mp4 --title "标题" --tags "tag1,tag2"
```

---

## 8. 相关链接

- [install.md](./install.md) — 基础安装
- [CLI.md](./CLI.md) — 命令行参数全表
- [OpenClaw issue #108262](https://github.com/openclaw/openclaw/issues/108262) — agent fallback bug
  (与本指南无关,但常一起被踩到)