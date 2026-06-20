import { Tooltip } from 'antd'
import { DesktopOutlined, MoonOutlined, SunOutlined } from '@ant-design/icons'
import { useTheme } from './ThemeProvider'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const next = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'

  const icon = {
    light: <SunOutlined />,
    dark: <MoonOutlined />,
    system: <DesktopOutlined />,
  }[theme]

  const label = {
    light: '浅色模式',
    dark: '深色模式',
    system: '跟随系统',
  }[theme]

  return (
    <Tooltip title={`点击切换到${ { light: '深色', dark: '跟随系统', system: '浅色' }[theme] }`}>
      <span
        role="button"
        tabIndex={0}
        aria-label={label}
        onClick={() => setTheme(next)}
        onKeyDown={(e) => { if (e.key === 'Enter') setTheme(next) }}
        style={{
          cursor: 'pointer',
          fontSize: 18,
          lineHeight: 1,
          padding: '6px 8px',
          borderRadius: 6,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background-color 0.18s ease',
          userSelect: 'none',
        }}
        className="theme-toggle-btn"
      >
        {icon}
      </span>
    </Tooltip>
  )
}
