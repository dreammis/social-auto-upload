"""Real-browser regression tests for the vendored initialization script.

Run with SAU_BROWSER_TESTS=1 python -m unittest tests.test_stealth_hardware -v.
Requires the project's Patchright Chromium installation; only local pages are used.
"""
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "utils" / "stealth.min.js"
READ_HARDWARE = """() => {
    const graphics = kind => {
        const gl = document.createElement('canvas').getContext(kind);
        if (!gl) return null;
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        return ext ? {
            vendor: gl.getParameter(ext.UNMASKED_VENDOR_WEBGL),
            renderer: gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)
        } : null;
    };
    return {
        hardwareConcurrency: navigator.hardwareConcurrency,
        webgl: graphics('webgl'),
        webgl2: graphics('webgl2')
    };
}"""


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = b"<html><body>Local hardware fixture</body></html>"
        if self.path == "/":
            body = b'<html><body><iframe name="child" src="/child"></iframe></body></html>'
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@unittest.skipUnless(os.getenv("SAU_BROWSER_TESTS") == "1", "Opt in with SAU_BROWSER_TESTS=1")
class StealthHardwareTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from patchright.async_api import async_playwright

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/"
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            channel="chromium", headless=os.getenv("SAU_BROWSER_HEADLESS") == "1"
        )

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)

    async def test_bundle_leaves_native_hardware_functions_untouched(self):
        context = await self.browser.new_context()
        page = await context.new_page()
        await page.goto(self.url)
        before = await page.evaluate(READ_HARDWARE, isolated_context=False)
        await page.evaluate("""() => {
            window.originalHardwareFunctions = {
                cpu: Object.getOwnPropertyDescriptor(Navigator.prototype, 'hardwareConcurrency').get,
                gl: WebGLRenderingContext.prototype.getParameter,
                gl2: WebGL2RenderingContext.prototype.getParameter
            };
        }""", isolated_context=False)
        await page.add_script_tag(path=str(BUNDLE))
        unchanged = await page.evaluate("""() => ({
            cpu: originalHardwareFunctions.cpu === Object.getOwnPropertyDescriptor(Navigator.prototype, 'hardwareConcurrency').get,
            gl: originalHardwareFunctions.gl === WebGLRenderingContext.prototype.getParameter,
            gl2: originalHardwareFunctions.gl2 === WebGL2RenderingContext.prototype.getParameter
        })""", isolated_context=False)
        self.assertEqual(unchanged, {"cpu": True, "gl": True, "gl2": True})
        self.assertEqual(await page.evaluate(READ_HARDWARE, isolated_context=False), before)
        await context.close()

    async def test_common_initializer_preserves_hardware_in_page_and_frame(self):
        from utils.base_social_media import set_init_script

        observations = []
        for initialize in (False, True):
            context = await self.browser.new_context()
            if initialize:
                await set_init_script(context)
            page = await context.new_page()
            await page.goto(self.url)
            # Allow Patchright's deferred init-script delivery to settle.
            await page.wait_for_timeout(1000)
            child = page.frame(name="child")
            self.assertIsNotNone(child)
            observations.append({
                "page": await page.evaluate(READ_HARDWARE, isolated_context=False),
                "frame": await child.evaluate(READ_HARDWARE, isolated_context=False),
            })
            await context.close()
        self.assertEqual(observations[1], observations[0])


if __name__ == "__main__":
    unittest.main()
