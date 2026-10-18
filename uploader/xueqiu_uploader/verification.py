"""核对雪球编辑器、预览与服务端文章的文字、图片位置和原生结构。"""
import json
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from patchright.async_api import async_playwright, expect
from conf import LOCAL_CHROME_PATH
from uploader.xueqiu_uploader.constants import XUEQIU_HOME_URL
from uploader.xueqiu_uploader.content import load_xueqiu_article
from uploader.xueqiu_uploader.session import load_xueqiu_identity, read_xueqiu_identity


async def check_xueqiu_article_content(body, document, image_sources=None):
    """按文字和图片交错顺序核对，不用图片数量冒充段间位置正确。"""
    await expect(body.locator("img")).to_have_count(len(document.images))
    if image_sources is not None:
        # 服务端可能保留数量但交换图片；按首次上传取得的绝对 URL 核对每个原稿位置。
        actual_sources = await body.locator("img").evaluate_all(
            "images => images.map(image => new URL(image.getAttribute('src'), 'https://mp.xueqiu.com/').href)")
        if actual_sources != image_sources:
            raise RuntimeError("雪球文章图片内容或顺序与本次上传不一致")
    actual = await body.evaluate("""(body, html) => {
        let sequence = '';
        function visit(node) {
            if (node.nodeType === Node.TEXT_NODE) { sequence += node.nodeValue; return; }
            if (node.nodeName === 'IMG') { sequence += '\\x00IMG\\x00'; return; }
            node.childNodes.forEach(visit);
        }
        visit(body);
        const source = document.createElement('template'); source.innerHTML = html;
        return {sequence, headings: body.querySelectorAll('h4').length,
            bold: body.querySelectorAll('b,strong').length, italic: body.querySelectorAll('i,em').length,
            links: [...body.querySelectorAll('a')].map(a => ({text: a.textContent, href: a.href})),
            expectedLinks: [...source.content.querySelectorAll('a')].map(a => ({text: a.textContent,
                href: new URL(a.getAttribute('href'), document.baseURI).href}))};
    }""", document.content_html)
    sequence = re.sub(r"[\s\u200b\ufeff]+", "", actual["sequence"])
    if sha256(sequence.encode()).hexdigest() != document.manifest["structure_sha256"]:
        raise RuntimeError("雪球文章文字或段间图片位置与原稿不一致")
    expected = {"headings": document.tags["h4"], "bold": document.tags["strong"], "italic": document.tags["em"]}
    for key, count in expected.items():
        if actual[key] != count:
            raise RuntimeError(f"雪球文章结构不一致: {key} 期望 {count}，实际 {actual[key]}")
    if actual["links"] != actual["expectedLinks"]:
        raise RuntimeError("雪球文章链接文字或目标与原稿不一致")


async def query_xueqiu_article(page, identity, content_id, title=None, visibility=None):
    """通过实测的已发布管理列表查询原 ID，只读核对，绝不重新发表。"""
    await page.goto(XUEQIU_HOME_URL, wait_until="domcontentloaded", timeout=45000)
    if (await read_xueqiu_identity(page))["uid"] != identity["uid"]:
        raise RuntimeError("雪球查询主体与绑定账号不一致")
    # 内容管理是首页实际侧栏入口；SPA 导航会附带平台所需的请求头，直接请求 JSON 并不等价。
    async with page.expect_response(lambda response: response.request.method == "GET"
                                    and urlsplit(response.url).path == "/xq/query/v1/search/long",
                                    timeout=30000) as listing:
        await page.get_by_role("link", name="内容管理", exact=True).click()
    response = await listing.value
    payload = await response.json()
    # 实测列表有 page/maxPage/list；后续页沿用该请求的认证头，不输出任何认证值。
    headers = await response.request.all_headers()
    query_url = urlsplit(response.url)
    params = parse_qs(query_url.query)
    seen_pages = set()
    while True:
        if not response.ok or not isinstance(payload.get("list"), list):
            raise RuntimeError(f"雪球原作品查询失败: HTTP {response.status}，未返回已发布列表")
        matches = [item for item in payload["list"] if str(item.get("id")) == str(content_id)]
        if len(matches) > 1:
            raise RuntimeError("雪球同一作品 ID 匹配多条记录")
        if matches:
            item = matches[0]
            if str(item.get("user_id")) != identity["uid"] or (title is not None and item.get("title") != title):
                raise RuntimeError("雪球原作品的主体或标题不一致")
            if visibility is not None and item.get("is_private") is not (visibility == "私人"):
                raise RuntimeError("雪球原作品的分享范围不一致")
            # 首屏接口先于列表绘制返回；截图前等待原作品标题可见，避免把骨架屏当作后台证据。
            if payload.get("page") == 1:
                await expect(page.get_by_text(item["title"], exact=True)).to_be_visible(timeout=30000)
            return item
        current, last = payload.get("page"), payload.get("maxPage")
        if not isinstance(current, int) or not isinstance(last, int) or current >= last:
            raise RuntimeError(f"已发布列表未找到原作品 {content_id}，请核查后台，勿直接重发")
        if current in seen_pages:
            raise RuntimeError("雪球查询重复返回同一页，已停止查询；请核查后台，勿重新发表")
        seen_pages.add(current)
        params["page"] = [str(current + 1)]
        url = urlunsplit(query_url._replace(query=urlencode(params, doseq=True)))
        response = await page.context.request.get(url, headers=headers, timeout=30000)
        payload = await response.json()


async def verify_xueqiu_result(account_file, result_file, headless=False):
    """从结果文件恢复原作品 ID，在绑定账号下只读查询提交结果。"""
    account_file = Path(account_file)
    result_file = Path(result_file)
    result = json.loads(result_file.read_text(encoding="utf-8"))
    identity = load_xueqiu_identity(account_file)
    content_id = result.get("content_id", "")
    if not re.fullmatch(r"[1-9][0-9]*", str(content_id)):
        raise ValueError("结果文件没有平台返回的作品 ID，请先在后台核查原作品，勿重新发表")
    if result.get("identity", {}).get("uid") != identity["uid"]:
        raise ValueError("结果文件与所选雪球账号不一致")
    # 当前结果保存原稿路径；查询必须使用未修改的原稿重查正文，不能清除原有内容错误后直接报成功。
    document = None
    if result.get("content_file"):
        document = load_xueqiu_article(Path(result["content_file"]))
        if document.manifest != result.get("manifest"):
            raise ValueError("原稿与发表时的内容不一致，请恢复原稿后查询，勿重新发表")
    elif result.get("error"):
        raise ValueError("旧结果缺少原稿路径且保留核对错误，请先在后台核查原作品，勿重新发表")
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=LOCAL_CHROME_PATH or None, channel="chrome", headless=headless)
        try:
            context = await browser.new_context(storage_state=str(account_file))
            page = await context.new_page()
            record = await query_xueqiu_article(page, identity, content_id, result.get("title"), result.get("visibility"))
            if document is not None:
                # 核对后台实际保存的正文，不改写编辑器，不触发发表动作。
                check_page = await context.new_page()
                await check_page.set_content(record.get("text") or "")
                await check_xueqiu_article_content(check_page.locator("body"), document, result.get("images"))
                await check_page.close()
            screenshot = result_file.with_suffix(".verified.png")
            await page.screenshot(path=str(screenshot), full_page=True)
            result.update(success=True, status="published", management_verified=True,
                          url=f"https://xueqiu.com/{identity['uid']}/{content_id}",
                          verified_screenshot=str(screenshot), is_private=record["is_private"])
            result.pop("error", None)
            result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        finally:
            await browser.close()
