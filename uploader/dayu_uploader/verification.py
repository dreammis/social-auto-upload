"""只读确认原作品已提交发表；显式要求时再等待公开并核验内容。"""
from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime
from hashlib import sha256
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

from patchright.async_api import Browser, BrowserContext, Locator, expect
from uploader.dayu_uploader.constants import DAYU_CONTENT_PUBLIC, DAYU_CONTENT_REVIEWING, DAYU_CONTENT_SCHEDULED, DAYU_TIMEZONE
from utils.log import dayu_logger


async def check_dayu_article_content(body: Locator, manifest: dict) -> None:
    """编辑器和公开正文共用内容检查，图文顺序或支持的格式有变化即报错。"""
    await expect(body.locator("img")).to_have_count(manifest["image_count"])
    text = re.sub(r"[\s\u200b\ufeff]+", "", await body.inner_text())
    if sha256(text.encode()).hexdigest() != manifest["text_sha256"]:
        raise RuntimeError("文章正文与输入文件文字不一致")
    sequence = await body.evaluate("""body => {
        let value = '';
        function visit(node) {
            if (node.nodeType === Node.TEXT_NODE) { value += node.nodeValue; return; }
            if (node.nodeName === 'IMG') { value += '\\x00IMG\\x00'; return; }
            if (node.nodeName === 'HR') { value += '\\x00HR\\x00'; return; }
            node.childNodes.forEach(visit);
        }
        visit(body); return value;
    }""")
    sequence = re.sub(r"[\s\u200b\ufeff]+", "", sequence)
    if sha256(sequence.encode()).hexdigest() != manifest["structure_sha256"]:
        raise RuntimeError("文章的文字、图片或分隔线顺序与输入文件不一致")
    for tag, count in manifest["formats"].items():
        await expect(body.locator(tag)).to_have_count(count)
    if manifest.get("dayu_style"):
        # 兼容排版使用服务器实测保留的 font/table 属性；检查实际计算颜色，避免属性存在却被覆盖。
        actual = await body.evaluate("""body => ({
            text_colors: [...body.querySelectorAll('font[color]')].map(font => ({
                text: font.textContent.replace(/[\\s\\u200b\\ufeff]+/g, ''), color: getComputedStyle(font).color,
            })),
            background_colors: [...body.querySelectorAll('table[bgcolor]')].map(table => getComputedStyle(table).backgroundColor),
        })""")
        if actual != manifest["dayu_style"]:
            raise RuntimeError("大鱼号预览或公开正文未保留预期的主题文字颜色、背景色")


async def wait_dayu_publication(context: BrowserContext, content_id: str | None = None,
                                origin_id: str | None = None, title: str | None = None,
                                timeout: int = 60, public: bool = False,
                                schedule: str | None = None) -> dict:
    """默认确认原作品已提交；只有显式公开核验才等待公开，始终不重发。"""
    if not content_id and not origin_id:
        raise ValueError("核验必须提供 content_id 或 origin_id（预览时保存的草稿 ID）")
    deadline = time.monotonic() + timeout
    record = None
    last_status = None
    while time.monotonic() < deadline:
        page_number = 1
        total_pages = 1
        record = None
        while page_number <= total_pages and time.monotonic() < deadline:
            # 来自真实“全部”页的请求参数。不能依赖发表后跳转的 shortvideo 筛选。
            response = await context.request.get(
                "https://mp.dayu.com/dashboard/getNewContentList",
                params={"_rid": uuid4().hex, "currentView": "all", "source": "all",
                        "page": page_number, "currentTab": "all", "_": int(time.time() * 1000)},
                timeout=max(1, min(30000, int((deadline - time.monotonic()) * 1000))),
            )
            if not response.ok:
                raise RuntimeError(f"查询大鱼号作品失败: HTTP {response.status}")
            payload = await response.json()
            data_list = payload.get("dataList")
            if not isinstance(data_list, dict) or not isinstance(data_list.get("data"), list):
                raise RuntimeError("作品查询未返回 dataList.data；可能登录失效或平台接口变化")
            total_pages = int(data_list["totalPage"])
            matches = [item for item in data_list["data"]
                       if (not content_id or str(item.get("content_id")) == content_id)
                       and (not origin_id or item.get("origin_id") == origin_id)]
            if len(matches) > 1:
                raise RuntimeError("同一作品 ID 匹配多条记录，拒绝判定成功")
            if matches:
                record = matches[0]
                break
            page_number += 1
        if record:
            if title is not None and record.get("title") != title:
                raise RuntimeError("作品 ID 对应的标题与本次提交不一致")
            current_status = {"status": record.get("status"), "audit_status": record.get("audit_status")}
            if current_status != last_status:
                dayu_logger.info(f"大鱼号作品查询: content_id={record.get('content_id')}，{current_status}")
            last_status = current_status
            # 审核中的原作品已提交成功；公开核验是调用者额外选择的检查范围。
            if schedule or record.get("status") == DAYU_CONTENT_SCHEDULED:
                epoch = record.get("_app_extra", {}).get("time_for_release")
                if isinstance(epoch, bool) or not isinstance(epoch, (int, float)) or epoch <= 0:
                    raise RuntimeError("原作品缺少已保存的定时安排，拒绝确认成功")
                actual = datetime.fromtimestamp(epoch / 1000, DAYU_TIMEZONE)
                if schedule and actual != datetime.fromisoformat(schedule):
                    raise RuntimeError(f"原作品定时时间不一致: 预期={schedule}，实际={actual.isoformat()}")
            accepted = (DAYU_CONTENT_PUBLIC,) if public else (DAYU_CONTENT_PUBLIC, DAYU_CONTENT_REVIEWING, DAYU_CONTENT_SCHEDULED)
            if record.get("status") in accepted:
                break
        await asyncio.sleep(min(5, max(0, deadline - time.monotonic())))
    else:
        target = "公开访问" if public else "提交发表确认"
        raise TimeoutError(f"等待大鱼号{target}超时；最后状态={last_status}，请核查原作品，勿重新上传")

    return record


async def verify_dayu_video(context: BrowserContext, browser: Browser, identity: dict,
                            content_id: str | None = None, origin_id: str | None = None,
                            title: str | None = None, timeout: int = 60, public: bool = False,
                            schedule: str | None = None) -> dict:
    """确认原视频已提交；public=True 时额外验证匿名标题、作者及播放。"""
    record = await wait_dayu_publication(context, content_id, origin_id, title, timeout, public, schedule)
    result = {"success": True, "status": "published" if record["status"] == DAYU_CONTENT_PUBLIC else "submitted", "type": "video",
              "content_id": str(record["content_id"]), "origin_id": record["origin_id"],
              "title": record["title"], "identity": identity, "platform_status": record["status"]}
    if schedule or record["status"] == DAYU_CONTENT_SCHEDULED:
        result.update(schedule=datetime.fromtimestamp(record["_app_extra"]["time_for_release"] / 1000, DAYU_TIMEZONE).isoformat(),
                      schedule_verified=True)
        if record["status"] != DAYU_CONTENT_PUBLIC:
            result["status"] = "scheduled"
    if not public:
        return result
    public_url = record.get("ucUrl", "")
    parsed = urlsplit(public_url)
    query = parse_qs(parsed.query)
    if (parsed.scheme != "https" or parsed.hostname != "mparticle.uc.cn"
            or parsed.path != "/video.html"
            or query.get("wm_id") != [identity["wmid"]]
            or query.get("wm_aid") != [record["origin_id"]]):
        raise RuntimeError("作品公开地址的域名、主体或 origin_id 不匹配")

    # 新建不带 storage_state 的上下文，避免登录后的预览权限掩盖公开播放失败。
    public_context = await browser.new_context()
    try:
        public_page = await public_context.new_page()
        await public_page.goto(public_url, wait_until="domcontentloaded", timeout=45000)
        # 只使用组件含义前缀，排除构建生成的 class 哈希后缀与推荐卡片中的同名作者。
        await expect(public_page.locator('[class^="pc-videoContent-"]')).to_have_text(record["title"], timeout=30000)
        await expect(public_page.locator('[class^="pc-userInfoContainer-"] > span')).to_have_text(identity["name"])
        video = public_page.locator("video")
        await expect(video).to_have_count(1)
        await video.evaluate("async v => { v.muted = true; await v.play(); }")
        await public_page.wait_for_function(
            """() => { const v = document.querySelector('video');
                return v && !v.error && v.readyState >= 2 && v.duration > 0 && v.currentTime > 0.1; }""",
            timeout=30000,
        )
        playback = await video.evaluate("v => ({duration: v.duration, current_time: v.currentTime, ready_state: v.readyState})")
    finally:
        await public_context.close()
    result.update(status="published", audit_status=record.get("audit_status"),
                  audit_remark=record.get("_app_extra", {}).get("audit_remark", ""),
                  public_url=public_url, public_playback=playback)
    return result


async def verify_dayu_article(context: BrowserContext, browser: Browser, identity: dict,
                              content_id: str | None = None, origin_id: str | None = None,
                              title: str | None = None, timeout: int = 60,
                              manifest: dict | None = None, public: bool = False,
                              schedule: str | None = None) -> dict:
    """确认原文章已提交；public=True 时再匿名核对正文、图片位置及格式。"""
    record = await wait_dayu_publication(context, content_id, origin_id, title, timeout, public, schedule)
    result = {"success": True, "status": "published" if record["status"] == DAYU_CONTENT_PUBLIC else "submitted", "type": "article",
              "content_id": str(record["content_id"]), "origin_id": record["origin_id"],
              "title": record["title"], "identity": identity, "platform_status": record["status"]}
    if schedule or record["status"] == DAYU_CONTENT_SCHEDULED:
        result.update(schedule=datetime.fromtimestamp(record["_app_extra"]["time_for_release"] / 1000, DAYU_TIMEZONE).isoformat(),
                      schedule_verified=True)
        if record["status"] != DAYU_CONTENT_PUBLIC:
            result["status"] = "scheduled"
    if not public:
        return result
    if not re.fullmatch(r"[a-f0-9]{32}", record.get("origin_id", "")):
        raise RuntimeError("文章原稿 ID 不完整，无法打开公开文章")
    # 实际后台点击已发布图文标题产生此地址；图文列表不提供视频使用的 ucUrl 字段。
    public_url = "https://mparticle.uc.cn/article.html?" + urlencode({
        "uc_param_str": "frdnsnpfvecpntnwprdssskt", "wm_aid": record["origin_id"],
    })
    public_context = await browser.new_context()
    try:
        page = await public_context.new_page()
        await page.goto(public_url, wait_until="domcontentloaded", timeout=45000)
        # 公开正文组件前缀不包含构建哈希；限定文章容器，排除推荐区标题、作者及图片。
        article = page.locator('[class^="index-articleContainer-"]')
        await expect(article.locator(":scope > h1")).to_have_text(record["title"], timeout=30000)
        await expect(article.locator('[class^="article-userInfoName-"]')).to_have_text(identity["name"])
        body = article.locator('[class^="index-articleSummary-"]')
        await expect(body).to_have_count(1)
        await expect(body).not_to_be_empty()
        images = body.locator("img")
        if manifest:
            await expect(images).to_have_count(manifest["image_count"])
        for index in range(await images.count()):
            image = images.nth(index)
            await image.scroll_into_view_if_needed()
            await expect(image).to_have_attribute("src", re.compile(r"^https?://(?:image\.uc\.cn|mp\.dayu\.com)/"))
            await expect(image).to_have_js_property("complete", True, timeout=30000)
            if await image.evaluate("e => e.naturalWidth") <= 0:
                raise RuntimeError(f"公开文章第 {index + 1} 张图片无法加载")
        if manifest:
            await check_dayu_article_content(body, manifest)
        public_article = {"image_count": await images.count(), "content_checked": bool(manifest)}
    finally:
        await public_context.close()
    result.update(status="published", audit_status=record.get("audit_status"),
                  audit_remark=record.get("_app_extra", {}).get("audit_remark", ""),
                  public_url=public_url, public_article=public_article)
    return result
