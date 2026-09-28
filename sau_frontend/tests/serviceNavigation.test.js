import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { parseConsoleNavigation } from '../src/utils/serviceNavigation.js'

const validCases = [
  ['http://127.0.0.1:8848', 'http://127.0.0.1:8848'],
  ['http://localhost:1/console', 'http://localhost:1/console'],
  ['http://[::1]:65535/app/', 'http://[::1]:65535/app/'],
]

const invalidCases = [
  'https://127.0.0.1:8848',
  'file:///tmp/console',
  'http://example.com:8848',
  'http://127.0.0.1',
  'http://user@127.0.0.1:8848',
  'http://127.0.0.1:8848/?token=x',
  'http://127.0.0.1:8848/#fragment',
  'http://127.0.0.1:0',
  'http://127.0.0.1:65536',
  'http://127.0.0.1:8848/../secret',
]

test('accepts explicit loopback HTTP URLs', () => {
  for (const [raw, expected] of validCases) {
    assert.deepEqual(parseConsoleNavigation(raw), {
      state: 'ENABLED',
      url: expected,
      warningCode: null,
    })
  }
})

test('ignores invalid URLs without returning their values', () => {
  for (const raw of invalidCases) {
    const result = parseConsoleNavigation(raw)
    assert.deepEqual(result, {
      state: 'IGNORED',
      url: null,
      warningCode: 'INVALID_CONSOLE_URL',
    })
    assert.equal(JSON.stringify(result).includes(raw), false)
  }
})

test('treats a missing value as disabled', () => {
  assert.deepEqual(parseConsoleNavigation(undefined), {
    state: 'DISABLED',
    url: null,
    warningCode: null,
  })
})

test('App renders a current-tab legacy return link without API calls', async () => {
  const source = await readFile(new URL('../src/App.vue', import.meta.url), 'utf8')

  assert.match(source, /VITE_INDEPENDENT_MEDIA_CONSOLE_URL/)
  assert.match(source, /parseConsoleNavigation/)
  assert.match(source, /target="_self"/)
  assert.match(source, /旧版入口/)
  assert.doesNotMatch(source, /axios|fetch\(/)
})
