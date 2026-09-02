const DISABLED = Object.freeze({
  state: 'DISABLED',
  url: null,
  warningCode: null,
})

const IGNORED = Object.freeze({
  state: 'IGNORED',
  url: null,
  warningCode: 'INVALID_CONSOLE_URL',
})

const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '::1'])
const EXPLICIT_HTTP_URL = /^http:\/\/(\[[^\]]+\]|[^/:?#]+):(\d+)(\/[^?#]*)?$/i

export function parseConsoleNavigation(raw) {
  if (typeof raw !== 'string' || raw.trim() === '') {
    return { ...DISABLED }
  }

  const candidate = raw.trim()
  const match = EXPLICIT_HTTP_URL.exec(candidate)
  if (!match) {
    return { ...IGNORED }
  }

  const authorityHost = match[1]
  const hostname = authorityHost.startsWith('[')
    ? authorityHost.slice(1, -1).toLowerCase()
    : authorityHost.toLowerCase()
  const port = Number(match[2])
  const path = match[3] ?? ''

  let decodedPath
  try {
    decodedPath = decodeURIComponent(path)
  } catch {
    return { ...IGNORED }
  }

  if (
    !LOOPBACK_HOSTS.has(hostname)
    || !Number.isInteger(port)
    || port < 1
    || port > 65535
    || path.includes('\\')
    || decodedPath.includes('\\')
    || decodedPath.split('/').includes('..')
  ) {
    return { ...IGNORED }
  }

  const normalizedHost = hostname === '::1' ? '[::1]' : hostname
  return {
    state: 'ENABLED',
    url: `http://${normalizedHost}:${port}${path}`,
    warningCode: null,
  }
}
