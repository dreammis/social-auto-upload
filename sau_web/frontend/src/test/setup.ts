import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom/happy-dom DOM cleanup between tests
afterEach(() => {
  cleanup()
})

// Silenced globally — Radix primitives occasionally emit an
// "act()" warning under happy-dom. Real component tests still
// get their own act() wrapping via @testing-library/react.
const originalError = console.error
vi.spyOn(console, 'error').mockImplementation((...args) => {
  const first = typeof args[0] === 'string' ? args[0] : ''
  if (first.includes('not wrapped in act(')) return
  if (first.includes('inside a test was not wrapped in act')) return
  originalError(...args)
})
