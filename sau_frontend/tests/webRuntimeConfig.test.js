import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveWebRuntimeConfig } from '../vite.config.js'


test('web runtime config defaults to loopback ports', () => {
  assert.deepEqual(resolveWebRuntimeConfig({}), {
    frontendPort: 5173,
    openBrowser: false,
    proxyTarget: 'http://127.0.0.1:5409',
  })
})

test('web runtime config accepts explicit loopback ports', () => {
  assert.deepEqual(resolveWebRuntimeConfig({
    VITE_PORT: '5174',
    VITE_API_PROXY_TARGET: 'http://localhost:5410',
    VITE_OPEN_BROWSER: 'true',
  }), {
    frontendPort: 5174,
    openBrowser: true,
    proxyTarget: 'http://localhost:5410',
  })
})

test('web runtime config rejects non-loopback proxy targets', () => {
  assert.throws(
    () => resolveWebRuntimeConfig({ VITE_API_PROXY_TARGET: 'http://192.0.2.10:5409' }),
    /loopback/,
  )
})
