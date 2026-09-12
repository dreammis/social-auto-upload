# Browser initialization bundle

`stealth.min.js` is shared by `set_init_script()` and legacy callers that load
the file directly. The vendored bundle omits these hardware overrides:

- `navigator.hardwareConcurrency`: leave the browser's native getter intact.
- `webgl.vendor`: leave native WebGL 1 and WebGL 2 `getParameter()` intact,
  including the vendor and renderer returned by `WEBGL_debug_renderer_info`.

Do not replace these with values detected by Python or copied from another
browser context. The current browser may expose fewer logical processors,
use a software renderer, or restrict WebGL information. Its native values
should remain authoritative, including when an extension or context is
unavailable. Other initialization behavior is unchanged.

If regenerating the bundle with its upstream extractor, retain both exclusions:

```sh
cd utils
npx extract-stealth-evasions@2.7.3 \
  --exclude navigator.hardwareConcurrency \
  --exclude webgl.vendor
```

The existing generated code was retained except for these two modules to avoid
an unrelated dependency or bundle refresh. The extractor command above may
resolve newer transitive dependencies; review any additional generated changes.

Run the hardware regression tests from the repository root after configuring
`conf.py` and installing the project's Patchright Chromium:

```sh
SAU_BROWSER_TESTS=1 python -m unittest tests.test_stealth_hardware -v
```

The tests only visit local fixtures and cover direct bundle loading plus the
shared initializer in a top-level page and an iframe. They compare against the
same browser without the bundle and verify that the hardware getter and WebGL
methods were not replaced. Set `SAU_BROWSER_HEADLESS=1` only when running these
local tests on a machine without a display.
