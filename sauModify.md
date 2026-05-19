# SAU 源码修改记录

## 修改文件

`uploader/douyin_uploader/main.py`

## 修改内容

### 视频发布成功后打印 aweme_id

**位置**: 第 581 行，`douyin_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))` 之后

**目的**: SAU 的 `sau` 命令行进程成功时 stdout 不输出视频 ID，导致 douyin-api 无法获取抖音作品链接。本修改从发布成功后的页面 URL 中提取 `aweme_id` 并打印，供外部程序（douyin-api server.js）解析。

**代码变更**:

```python
# 修改前
douyin_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))

# 修改后
douyin_logger.success(_msg("🥳", "视频发布成功，小人开心收工"))
# 提取并打印 aweme_id（供外部程序解析）
url = page.url
import re
m = re.search(r'[?&]aweme_id=(\d+)', url)
if m:
    print(f"SAU_AWEME_ID:{m.group(1)}")
```

**输出格式**: `SAU_AWEME_ID:7523456789012345678`

**说明**:
- 发布成功后页面跳转到 `https://creator.douyin.com/creator-micro/content/manage?aweme_id={数字}&...`，URL 参数中包含 `aweme_id`
- 用正则 `[?&]aweme_id=(\d+)` 从 `page.url` 中提取
- 打印到 stdout，后被 douyin-api server.js 的 `proc.stdout.on('data')` 捕获

## douyin-api 侧对应修改

**文件**: `server.js`（`/admin/sau/submit` 路由，close 回调中）

**变更**: aweme_id 解析顺序增加 `SAU_AWEME_ID:` 前缀匹配

```javascript
// 1. 先尝试 SAU_AWEME_ID: 前缀
const sauMatch = stdout.match(/SAU_AWEME_ID:(\d+)/);
if (sauMatch) {
  awemeId = sauMatch[1];
} else {
  // 2. 再尝试 JSON 格式
  // 3. 最后尝试正则匹配
}
```

## 日期

2026-04-16
