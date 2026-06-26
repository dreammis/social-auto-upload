#!/bin/bash
# export_douyin_cookie.sh
# 导出已登录 Chrome 的抖音 cookie 到 douyin_{8位随机字符}.json
# 使用 curl 直接调用 Chrome DevTools HTTP API

set -e

# 解析参数
USERNAME=""
while [ $# -gt 0 ]; do
    case "$1" in
        --account)
            USERNAME="$2"
            shift 2
            ;;
        *)
            echo "用法: $0 --account <用户名>"
            exit 1
            ;;
    esac
done

if [ -z "$USERNAME" ]; then
    echo "未指定用户名，将使用随机文件名"
fi

DEBUG_PORT=9222

echo "=========================================="
echo "   抖音 Cookie 导出工具"
echo "=========================================="
echo ""

# 依赖: curl, python3, websocket-client

echo "检查 Chrome remote debugging..."
RESPONSE=$(curl -s "http://localhost:${DEBUG_PORT}/json" 2>/dev/null) || true

if ! echo "$RESPONSE" | grep -q "webSocketDebuggerUrl"; then
    echo "Chrome remote debugging 未运行"
    echo "请先启动 Chrome: chromium --remote-debugging-port=9222 ..."
    exit 1
fi

echo "Chrome remote debugging 已运行"
echo ""
echo "获取抖音 Cookie..."

USERNAME="$USERNAME" python3 << 'PYEOF'
import json
import os
import uuid
import sys

# Shell 把 USERNAME 作为环境变量传过来, Python 需要显式取
USERNAME = os.environ.get('USERNAME', '')

DEBUG_PORT = 9222
if USERNAME:
    COOKIE_FILE = f"cookies/douyin_{USERNAME}.json"
else:
    COOKIE_FILE = f"cookies/douyin_{uuid.uuid4().hex[:8]}.json"

def get_douyin_cookies():
    import urllib.request
    import websocket

    # 获取页面列表
    url = f"http://localhost:{DEBUG_PORT}/json"
    with urllib.request.urlopen(url, timeout=10) as response:
        pages = json.loads(response.read().decode())

    # 查找抖音创作者页面
    douyin_page = None
    for page in pages:
        page_url = page.get("url", "")
        if "creator.douyin.com" in page_url:
            douyin_page = page
            break

    if not douyin_page:
        print("未找到抖音创作者平台页面")
        print("请先在 Chrome 中打开并登录 https://creator.douyin.com")
        return False

    page_url = douyin_page["url"]
    ws_url = douyin_page.get("webSocketDebuggerUrl", "")

    print(f"找到页面: {page_url}")

    # 连接到目标页面的 WebSocket
    print(f"连接页面 WebSocket...")
    ws = websocket.create_connection(ws_url, timeout=30)

    # 获取所有 Cookie
    ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
    response = json.loads(ws.recv())

    cookies = response.get("result", {}).get("cookies", [])

    # 过滤抖音相关的 cookie
    douyin_cookies = [
        c for c in cookies
        if "douyin.com" in c.get("domain", "") or ".douyin.com" in c.get("domain", "")
    ]

    print(f"获取到 {len(douyin_cookies)} 个抖音 Cookie")

    if len(douyin_cookies) == 0:
        print("未获取到任何抖音 Cookie，可能未登录")
        return False

    # 获取 localStorage (origins)
    print(f"获取 localStorage...")
    local_storage_by_origin = {}

    # 获取页面 frame 树
    ws.send(json.dumps({"id": 2, "method": "Page.getResourceTree"}))
    resp = json.loads(ws.recv())
    frames = resp.get("result", {}).get("frameTree", {}).get("childFrames", [])
    all_frames = [resp.get("result", {}).get("frameTree", {})] + frames

    for frame in all_frames:
        frame_url = frame.get("url", "")
        frame_id = frame.get("id", "")
        if "douyin.com" in frame_url or "bytedance.com" in frame_url:
            # 执行 JavaScript 获取该 frame 的 localStorage
            script = """
            (function() {
                var result = [];
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    result.push([key, localStorage.getItem(key)]);
                }
                return result;
            })()
            """
            ws.send(json.dumps({
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {"expression": script, "contextId": frame.get("id")}
            }))
            resp = json.loads(ws.recv())
            result_eval = resp.get("result", {})
            if result_eval.get("result", {}).get("type") == "array":
                items = result_eval.get("result", {}).get("value", [])
                if items:
                    origin = frame_url.rsplit("/", 2)[0] + "//" + frame_url.split("/")[2]
                    local_storage_by_origin[origin] = items

    # 获取主文档的 localStorage
    script_main = """
    (function() {
        var result = [];
        try {
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                result.push([key, localStorage.getItem(key)]);
            }
        } catch(e) {}
        return result;
    })()
    """
    ws.send(json.dumps({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {"expression": script_main}
    }))
    resp = json.loads(ws.recv())
    result_eval = resp.get("result", {})
    if result_eval.get("result", {}).get("type") == "array":
        items = result_eval.get("result", {}).get("value", [])
        if items:
            origin = page_url.rsplit("/", 2)[0] + "//" + page_url.split("/")[2]
            local_storage_by_origin[origin] = items

    ws.close()

    # 构建 JSON
    result = {
        "cookies": [],
        "origins": []
    }

    for c in douyin_cookies:
        result["cookies"].append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": c.get("expires", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": c.get("sameSite", "Lax")
        })

    # 添加 origins
    for origin, items in local_storage_by_origin.items():
        origin_entry = {
            "origin": origin,
            "localStorage": [{"name": name, "value": value} for name, value in items]
        }
        result["origins"].append(origin_entry)

    # 保存
    os.makedirs("cookies", exist_ok=True)
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Cookie 已保存到: {COOKIE_FILE}")
    print("")

    # 打印关键 Cookie
    key_cookies = ["sessionid", "uid_tt", "ssid", "ttwid"]
    print("关键 Cookie:")
    for c in douyin_cookies:
        if c.get("name") in key_cookies:
            val = c.get("value", "")
            if len(val) > 30:
                val = val[:30] + "..."
            print(f"   {c.get('name')}: {val}")

    return True

if __name__ == "__main__":
    if not get_douyin_cookies():
        sys.exit(1)
PYEOF

echo ""
echo "=========================================="
echo "   完成！文件已导出为$COOKIE_FILE"
echo "=========================================="