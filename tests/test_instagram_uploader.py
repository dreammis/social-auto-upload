import sau_commands.instagram
"""Instagram 的业务响应、账号边界和实际 DOM/事件回归。"""
import asyncio
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from patchright.async_api import async_playwright

import sau_cli
from uploader.meta_uploader.insgraph_uploader.main import (
    InstagramUploader, _is_instagram_logged_out, instagram_created_media, instagram_response_payload,
    _dismiss_optional_prompt,
)
from uploader.meta_uploader.insgraph_uploader.posts import instagram_post_id, find_instagram_post


class InstagramContractTests(unittest.TestCase):
    def test_final_response_requires_matching_owner_caption_and_id(self):
        media = {'id': '123_42', 'pk': '123', 'code': 'ABC', 'user': {'pk': '42'}, 'caption': {'text': 'caption'}}
        payload = {'status': 'ok', 'media': media}
        self.assertEqual(instagram_created_media(payload, owner_id='42', caption='caption'), media)
        self.assertEqual(instagram_response_payload('for (;;);{"payload":{"did_delete":true}}')['payload']['did_delete'], True)
        for bad in ({'payload': {'statusCode': 202}}, {'status': 'ok'}, {'status': 'fail', 'media': media}):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                instagram_created_media(bad, owner_id='42', caption='caption')
        for owner, caption in [('99', 'caption'), ('42', 'another')]:
            with self.assertRaises(RuntimeError):
                instagram_created_media(payload, owner_id=owner, caption=caption)

    def test_real_url_shapes_and_external_url_rejection(self):
        for path in ('p/ABC', 'reel/ABC/', 'creator/p/ABC/', 'creator/reel/ABC/?hl=en'):
            self.assertEqual(instagram_post_id('https://www.instagram.com/' + path), 'ABC')
        for url in ('https://instagram.com.evil/p/ABC/', 'http://instagram.com/p/ABC/',
                    'https://instagram.com/creator/', 'https://bad@instagram.com/p/ABC/',
                    'https://instagram.com:8443/p/ABC/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                instagram_post_id(url)

    def test_caption_limit_and_mutually_exclusive_media(self):
        with self.assertRaises(ValueError):
            InstagramUploader('unused.json', title='x' * 2201, image_files=['image.png'])
        with self.assertRaises(ValueError):
            InstagramUploader('unused.json', title='title', image_files=['image.png'], video_file='video.mp4')

    def test_verify_and_delete_are_reachable_from_cli(self):
        for action in ('verify', 'delete'):
            args = sau_cli.build_parser().parse_args(['instagram', action, '--account', 'creator',
                '--post-url', 'https://www.instagram.com/p/ABC/', '--expected-text', 'caption'])
            operation = AsyncMock(return_value={'status': 'deleted' if action == 'delete' else 'published'})
            with patch('sau_commands.instagram.instagram_post_action', operation), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(asyncio.run(sau_cli.dispatch(args)), 0)
            self.assertEqual(operation.await_args.kwargs['delete'], action == 'delete')

    def test_cover_cli_reaches_uploader_and_invalid_cover_stops_before_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            video, cover = Path(folder)/'video.mp4', Path(folder)/'cover.PNG'
            video.touch()
            cover.touch()
            args = sau_cli.build_parser().parse_args(['instagram', 'upload-video', '--account', 'creator',
                '--file', str(video), '--thumbnail', str(cover), '--title', 'caption'])
            uploader = AsyncMock(return_value={'status': 'published'})
            with patch.object(InstagramUploader, 'upload', uploader), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(asyncio.run(sau_cli.dispatch(args)), 0)
            # 单独核对请求到构造函数的传递，避免只测 parser 丢失后续接线。
            request = sau_commands.instagram.InstagramUploadRequest('creator', 'caption', '', [], video_file=video, thumbnail=cover)
            with patch('sau_commands.instagram.InstagramUploader') as constructor:
                constructor.return_value.upload = AsyncMock(return_value={})
                asyncio.run(sau_commands.instagram.upload_instagram_content(request))
                self.assertEqual(constructor.call_args.kwargs['thumbnail'], cover)
            with self.assertRaisesRegex(ValueError, '仅用于视频'):
                InstagramUploader('unused', title='caption', image_files=[cover], thumbnail=cover)
            for invalid in (Path(folder)/'missing.png', Path(folder)/'cover.gif'):
                if invalid.suffix == '.gif':
                    invalid.touch()
                app = InstagramUploader('unused', title='caption', video_file=video, thumbnail=invalid)
                with patch('uploader.meta_uploader.insgraph_uploader.main._open_instagram_page', AsyncMock()) as launch:
                    with self.assertRaises((FileNotFoundError, ValueError)):
                        asyncio.run(app.upload())
                    launch.assert_not_called()


class InstagramBrowserRegressionTests(unittest.TestCase):
    def test_optional_prompts_present_absent_and_failed_dismissal(self):
        """按实际图标与按钮层级构造 DOM；覆盖延迟提示、缺席及点击未关闭的异常。"""
        async def scenario():
            async with async_playwright() as p:
                browser = await p.chromium.launch(channel='chrome', headless=True)
                page = await browser.new_page()
                try:
                    # 只保留真实页面的业务结构；不同语言按钮不参与生产定位。
                    html = '''<script>
                      function notification(){document.body.insertAdjacentHTML('beforeend',
                        `<div role="dialog" id="notifications">
                        <img src="/images/instagram/xig/ico/xxhdpi_launcher.png?test">
                        <div class="_a9-z"><button onclick="throw Error('wrong action')">Enable</button>
                        <button onclick="this.closest('[role=dialog]').remove()">後で</button></div></div>`);}
                      function create(){document.body.insertAdjacentHTML('beforeend',
                        `<div role="dialog"><input type="file" accept="image/jpeg,video/mp4" onchange="upload()"></div>`);}
                      function upload(){setTimeout(()=>{
                        document.querySelector('[role=dialog]').insertAdjacentHTML('beforeend',
                          '<div class="_ac76"><div role="button">Next</div></div>');
                        if(document.body.dataset.prompts==='true') document.body.insertAdjacentHTML('beforeend',
                          `<div role="dialog"><img src="/images/instagram/clips/reels_nux_icon.png?test">
                          <div class="_a9-z"><div><div><span><button onclick="throw Error('wrong action')">詳しく見る</button></span></div>
                          <div><button onclick="this.closest('[role=dialog]').remove()">OK</button></div></div></div></div>`);
                      },250);}
                      if(document.body.dataset.prompts==='true') setTimeout(notification,250);
                      </script>'''
                    for prompts in (True, False):
                        navigation = ''.join(
                            '<a class="_a6hd" href="#" ' + ('onclick="create()"' if i == 1 else '')
                            + '><span aria-selected="false">Navigation</span></a>' for i in range(4))
                        await page.set_content(f'<body data-prompts="{str(prompts).lower()}">{navigation}{html}</body>')
                        with tempfile.TemporaryDirectory() as folder:
                            video = Path(folder)/'video.mp4'
                            video.touch()
                            app = InstagramUploader('unused', title='caption', video_file=video)
                            await app._upload_files(page)
                        self.assertEqual(await page.get_by_role('dialog').count(), 1)
                        self.assertEqual(await page.locator('._ac76 [role=button]').count(), 1)
                    await page.set_content('<div role="dialog"><button>Unrelated dialog</button></div>')
                    known = page.get_by_role('dialog').filter(has=page.locator('img[src*="reels_nux_icon"]'))
                    self.assertFalse(await _dismiss_optional_prompt(known, known.get_by_role('button')))
                    self.assertEqual(await page.get_by_role('dialog').count(), 1)
                    # 已出现的已知提示若点击后未消失，必须保留异常，不能当作缺席吞掉。
                    await page.set_content('<div role="dialog"><button>Cannot close</button></div>')
                    page.set_default_timeout(300)
                    from patchright.async_api import TimeoutError as BrowserTimeoutError
                    with self.assertRaises(BrowserTimeoutError):
                        await _dismiss_optional_prompt(page.get_by_role('dialog'), page.get_by_role('button'))
                finally:
                    await browser.close()
        asyncio.run(scenario())

    def test_cover_waits_for_actual_preview_and_rejects_wrong_image(self):
        """真实 Chrome 中延迟替换预览，核对原图字节；错误预览必须停在编辑页。"""
        async def scenario():
            import base64
            import struct
            import zlib
            # 构造带正确 CRC 的 1×1 RGB PNG，避免依赖额外图像库或损坏的压缩样例。
            def chunk(kind, data):
                return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
            png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
                   + chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b''))
            async with async_playwright() as p:
                browser = await p.chromium.launch(channel='chrome', headless=True)
                page = await browser.new_page()
                try:
                    html = '''<input type="file" accept="image/jpeg,image/png" id="outside">
                      <div role="dialog"><div class="_ac76"><div role="heading">crop</div>
                      <button role="button" onclick="advance()">任意语言</button></div><section id="media"></section></div>
                      <script>let step=0;function advance(){step++;
                        const h=document.querySelector('[role=heading]');
                        if(step===1){h.textContent='edit'; document.querySelector('#media').innerHTML=
                          `<input type="file" accept="image/jpeg,image/png" onchange="coverChanged(this)">
                           <video></video><div style="background-image:url(old)"></div>`;
                        }else{h.textContent='compose';document.querySelector('#media').innerHTML+=
                          '<div contenteditable="true" role="textbox" data-lexical-editor="true"></div>';}}
                      function coverChanged(input){setTimeout(()=>{const blob=document.body.dataset.wrong ?
                        new Blob([Uint8Array.from(atob('PNG_BASE64'), c=>c.charCodeAt(0))],{type:'image/png'}) : input.files[0];
                        document.querySelector('video + div').style.backgroundImage=`url("${URL.createObjectURL(blob)}")`;
                      },250);}</script>'''
                    html = html.replace('PNG_BASE64', base64.b64encode(png).decode())
                    await page.route('https://www.instagram.com/**', lambda route: route.fulfill(body=html, content_type='text/html'))
                    with tempfile.TemporaryDirectory() as folder:
                        cover = Path(folder)/'cover.png'
                        cover.write_bytes(png)
                        app = InstagramUploader('unused', title='caption', video_file='video.mp4', thumbnail=cover)
                        await page.goto('https://www.instagram.com/')
                        await app._advance_media_editor(page)
                        self.assertEqual(await page.locator('[role=heading]').inner_text(), 'compose')
                        self.assertEqual(await page.locator('#outside').evaluate('e=>e.files.length'), 0)
                        await page.reload()
                        # 可解码但非指定文件的预览同样不能通过（本次改用不同有效 PNG 文件字节）。
                        cover.write_bytes(png + b'other image bytes')
                        await page.locator('body').evaluate("e=>e.dataset.wrong='true'")
                        with self.assertRaisesRegex(RuntimeError, '预览与指定图片不匹配'):
                            await app._advance_media_editor(page)
                        self.assertEqual(await page.locator('[role=heading]').inner_text(), 'edit')
                finally:
                    await browser.close()
        asyncio.run(scenario())

    def test_delayed_login_foreign_owner_and_async_reel_creation(self):
        """用真实 Chrome DOM 和网络事件验证：延迟页面不能误判、同配文不能跨作者、202 必须等正式作品。"""
        async def scenario():
            async with async_playwright() as p:
                browser = await p.chromium.launch(channel='chrome', headless=True)
                page = await browser.new_page()
                try:
                    await page.set_content('''<script>setTimeout(() => {
                        document.body.innerHTML = '<a href="/direct/inbox/?hl=ja">Inbox</a>';
                    }, 250)</script>''')
                    self.assertFalse(await _is_instagram_logged_out(page))
                    foreign = '''<meta property="og:url" content="https://www.instagram.com/p/ABC/">
                        <meta property="instapp:owner_user_id" content="99"><main>same caption</main>'''
                    await page.route('https://www.instagram.com/p/ABC/', lambda r: r.fulfill(body=foreign, content_type='text/html'))
                    with self.assertRaisesRegex(RuntimeError, '作者'):
                        await find_instagram_post(page, post_url='https://www.instagram.com/p/ABC/', expected_text='same caption', owner_id='42')
                    await page.unroute_all()
                    own = foreign.replace('content="99"', 'content="42"') + '<meta name="description" content="different caption"><meta property="al:ios:url" content="instagram://media?id=123">'
                    await page.route('https://www.instagram.com/p/ABC/', lambda r: r.fulfill(body=own, content_type='text/html'))
                    with self.assertRaisesRegex(RuntimeError, '配文元数据'):
                        await find_instagram_post(page, post_url='https://www.instagram.com/p/ABC/', expected_text='same caption', owner_id='42')
                    await page.unroute_all()
                    own = own.replace('different caption', 'same caption')
                    await page.route('https://www.instagram.com/p/ABC/', lambda r: r.fulfill(body=own, content_type='text/html'))
                    verified = await find_instagram_post(page, post_url='https://www.instagram.com/p/ABC/', expected_text='same caption', owner_id='42')
                    self.assertEqual(verified['content_id'], '123_42')
                    await page.unroute_all()
                    html = '''<div role="dialog"><div class="_ac76">
                        <div role="button" onclick="document.body.dataset.clicks=String(Number(document.body.dataset.clicks||0)+1); submitPost()">任意语言</div>
                        </div><div role="textbox" contenteditable="true" data-lexical-editor="true"></div></div>
                        <script>async function submitPost() {
                          await fetch('/api/v1/media/configure_to_clips/', {method:'POST'});
                          document.body.dataset.processing='true';
                          setTimeout(() => fetch('/api/v1/media/configure_to_clips/', {method:'POST'}), 350);
                        }</script>'''
                    calls = 0
                    async def route(request):
                        nonlocal calls
                        if '/configure_to_clips/' not in request.request.url:
                            await request.fulfill(body=html, content_type='text/html')
                            return
                        calls += 1
                        if calls == 1:
                            payload = {'payload': {'statusCode': 202}}
                        else:
                            payload = {'payload': {'media': {'id': '123_42', 'code': 'ABC', 'user': {'pk': '42'}, 'caption': {'text': 'caption'}}}}
                        await request.fulfill(body='for (;;);' + json.dumps(payload), content_type='application/json')
                    await page.route('https://www.instagram.com/**', route)
                    await page.goto('https://www.instagram.com/')
                    with tempfile.TemporaryDirectory() as folder:
                        target = Path(folder)/'result.json'
                        app = InstagramUploader('unused.json', title='caption', video_file='video.mp4', result_file=target)
                        task = asyncio.create_task(app._publish(page, {'user_id': '42', 'username': 'creator'}))
                        await page.locator('body[data-processing="true"]').wait_for()
                        self.assertFalse(task.done(), '202 后仍必须等待最终创建响应')
                        self.assertNotEqual(app.result['status'], 'published')
                        await task
                        self.assertEqual(app.result['status'], 'published')
                        self.assertEqual(app.result['content_id'], '123_42')
                        self.assertEqual(await page.locator('body').get_attribute('data-clicks'), '1')
                        self.assertEqual(calls, 2)
                finally:
                    await browser.close()
        asyncio.run(scenario())
