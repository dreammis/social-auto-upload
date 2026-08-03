# WSL X11 + B站 Cookie 恢复指南

> 适用对象: WSL2 用户在 social-auto-upload 中遇到 `Missing X server` 或 B站 Cookie 文件丢失问题。
> 环境: WSL2 (Debian / Ubuntu / Kali)，SAU 使用 Playwright 自动化浏览器操作。

---

## TL;DR

在 WSL2 环境下运行 SAU 时，抖音等平台会因缺少 X11 显示服务器报错 `Missing X server or $DISPLAY`，只需安装 `xvfb` 并通过 `bin/sau-x11` 包装器启动即可；B站 Cookie 文件丢失时，用 `scripts/restore_bilibili_cookie.sh` 从 `.bak` 备份恢复，无需重新扫码登录。

---

## 1. 抖音 / 其他平台: Missing X server

### 症状

```
playwright._impl._errors.Error: Missing X server or $DISPLAY.
  at chromeozone_platform.cc(…): ozone_platform_x11.cc(…):Initialize
```

运行 `sau douyin check --account Pawly` 时报错，包含 `Missing X server or $DISPLAY` 和 `ozone_platform_x11.cc` 字样。

### 检测命令

```bash
# 检查 xvfb-run 是否已安装
which xvfb-run

# 检查是否有真实 X server socket（存在则不需要 xvfb）
ls /tmp/.X11-unix/

# 检查当前 DISPLAY 变量
echo $DISPLAY
```

- `which xvfb-run` 无输出 → 需要安装 xvfb
- `ls /tmp/.X11-unix/` 有 `X0`、`X1` 等 socket 且 `echo $DISPLAY` 有值 → 已有真实 X server，不需要 xvfb

### 修复步骤

**步骤 1: 安装 xvfb**（Debian / Ubuntu / Kali）

```bash
sudo apt update && sudo apt install xvfb
```

**步骤 2: 使用 `sau-x11` 包装器启动**

不要直接用 `sau douyin check`，改为：

```bash
bin/sau-x11 douyin check --account Pawly
```

`sau-x11` 会自动检测是否需要 xvfb（检查 `$DISPLAY` 和 `/tmp/.X11-unix/` socket），必要时用 `xvfb-run -a` 包装 `sau` 命令，对用户透明。

### 验证

```bash
xvfb-run -a -- /bin/echo "X server works"
# 输出: X server works
```

### 何时不需要 xvfb

当满足以下全部条件时，`$DISPLAY` 已设置且 X socket 存在，无需 xvfb：

```bash
# 条件：DISPLAY 有值 且 对应 socket 存在
[ -n "$DISPLAY" ] && ls /tmp/.X11-unix/X${DISPLAY#*:} 2>/dev/null | grep -q .
# 输出为空（条件不满足）→ 需要 xvfb
```

常见于：已启动 VcXsrv / X410 并设置 `DISPLAY=172.19.224.1:0.0` 的用户。

---

## 2. B站: Cookie .bak 恢复

### 症状

```bash
sau bilibili check --account Pawly
# exit code 1, 返回 invalid
```

同时：

```bash
ls cookies/bilibili_*.json*
# 输出只有: bilibili_Pawly.json.bak
#        或: bilibili_Pawly.json.bak.20260101_120000
# 缺少 bilibili_Pawly.json
```

### 检测命令

```bash
ls -la cookies/bilibili_Pawly.json* 2>/dev/null
```

正常状态应同时存在 `.json` 和 `.json.bak`，只有 `.bak` 说明主文件丢失。

### 修复步骤

**步骤 1: 预览恢复（不修改任何文件）**

```bash
scripts/restore_bilibili_cookie.sh --account Pawly --dry-run
```

**步骤 2: 正式恢复**

```bash
scripts/restore_bilibili_cookie.sh --account Pawly
```

脚本会从最新的 `.bak` 文件复制为 `.json`，自动备份当前（若有残存文件）。

**步骤 3: 验证**

```bash
sau bilibili check --account Pawly
```

### 仍无效时

```bash
# Cookie 文件损坏无法恢复，重新扫码登录
sau bilibili login --account Pawly
```

### 备份文件名格式

自动备份命名规则：

```
cookies/bilibili_Pawly.json.bak.YYYYMMDD_HHMMSS
```

每次运行 restore 脚本时，若检测到已有 `.json` 文件，会先创建带时间戳的备份，再复制 `.bak` 为新的 `.json`。

---

## 3. 完整工作流示例

```bash
# =====================
# 一次性 setup
# =====================

# 安装 xvfb（只需一次）
sudo apt update && sudo apt install xvfb

# =====================
# 日常使用
# =====================

# --- B站 Cookie 恢复 ---
# 预览
scripts/restore_bilibili_cookie.sh --account Pawly --dry-run
# 恢复
scripts/restore_bilibili_cookie.sh --account Pawly
# 验证 B站 Cookie
sau-x11 bilibili check --account Pawly

# --- 抖音检查 ---
sau-x11 douyin check --account Pawly

# --- 上传视频 ---
# 抖音
sau-x11 douyin upload-video \
  --account Pawly \
  --file ./video.mp4 \
  --title "视频标题" \
  --tags "tag1,tag2"

# B站
sau-x11 bilibili upload-video \
  --account Pawly \
  --file ./video.mp4 \
  --title "视频标题" \
  --desc "视频描述" \
  --tid 249 \
  --tags "tag1,tag2"
```

---

## 4. 相关脚本

| 脚本 | 路径 | 用途 |
|------|------|------|
| `sau-x11`（包装器） | `bin/sau-x11` | X11 检测 + xvfb-run 透明包装 |
| `restore_bilibili_cookie.sh` | `scripts/restore_bilibili_cookie.sh` | 从 `.bak` 恢复 B站 Cookie |

### sau-x11 工作原理

`bin/sau-x11` 是一个 shell 包装器：

1. 检测 `$DISPLAY` 是否设置 + `/tmp/.X11-unix/X${DISPLAY#*:}` socket 是否存在
2. 若两者都满足 → 直接执行 `sau "$@"`
3. 若不满足 → 用 `xvfb-run -a -- sau "$@"` 执行

对 SAU 源码无任何修改，纯透明包装。

### 相关文档

- [WSL-USER-GUIDE.md](./WSL-USER-GUIDE.md) — WSL2 完整踩坑指南（CDP 登录、Chrome IPv6 问题等）
- [install.md](./install.md) — 基础安装
- [CLI.md](./CLI.md) — 命令行参数全表

---

## 5. FAQ

**Q: `sau-x11` 会修改 SAU 源码吗？**

A: 不会。`sau-x11` 是独立的 shell 脚本，纯读取检测，不触碰 SAU 任何文件。

---

**Q: 为什么有头模式（headed）即使没有可见窗口也需要 X server？**

A: Chromium 的 Ozone/X11 平台代码在启动时就会尝试打开 X 连接，即使没有可见窗口。`--headless` 模式走的也不是纯无头路径，WSL2 缺少 X socket 所以直接报错。xvfb 提供虚拟帧缓冲（virtual framebuffer），骗过 Chromium 的检测。

---

**Q: 已有 VcXsrv / X410，可以不用 xvfb 吗？**

A: 可以。在 Windows 端启动 VcXsrv / X410（默认监听 `0.0.0.0:0`），然后在 WSL2 设置：

```bash
export DISPLAY=172.19.224.1:0.0
```

并禁用自动 xvfb 包装：

```bash
SAU_NO_XVFB=1 sau douyin check --account Pawly
```

---

**Q: Cookie 恢复脚本恢复失败了怎么办？**

A: 如果 `.bak` 文件也不可用或损坏，只能重新登录：

```bash
sau bilibili login --account Pawly
```

B站支持 QR 码登录，需要 headed 模式配合 X server（用 `sau-x11` 或有真实 X）。

---

**Q: 恢复脚本会覆盖我现有的 Cookie 吗？**

A: 不会。脚本检测到已存在 `.json` 文件时，先自动创建带时间戳的 `.bak.YYYYMMDD_HHMMSS` 备份，再复制源 `.bak` 为新的 `.json`。除非传入 `--force` 参数，否则不会直接覆盖。
