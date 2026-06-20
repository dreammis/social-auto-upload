import { Spin } from 'antd'

/**
 * Loading fallback displayed inside the page transition container
 * while lazy-loaded page components are being fetched.
 */
export function PageLoading() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 300,
        gap: 16,
      }}
    >
      <Spin size="large" />
      <div style={{ fontSize: 13, color: '#999' }}>加载中...</div>
    </div>
  )
}
