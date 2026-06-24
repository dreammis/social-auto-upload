import { useTheme } from '../ThemeProvider'

interface PlatformIconProps {
  platform: string
  className?: string
}

import baijiahaoSvg from '@/assets/brands/baijiahao.svg'

import douyinDarkSvg from '@/assets/brands/douyin-dark.svg'
import kuaishouDarkSvg from '@/assets/brands/kuaishou-dark.svg'
import xiaohongshuDarkSvg from '@/assets/brands/xiaohongshu-dark.svg'
import tencentDarkSvg from '@/assets/brands/tencent-dark.svg'
import bilibiliDarkSvg from '@/assets/brands/bilibili-dark.svg'
import tiktokDarkSvg from '@/assets/brands/tiktok-dark.svg'
import baijiahaoDarkSvg from '@/assets/brands/baijiahao-dark.svg'

const ICON_MAP: Record<string, { light: string; dark: string }> = {
  douyin: { light: douyinDarkSvg, dark: douyinDarkSvg },
  kuaishou: { light: kuaishouDarkSvg, dark: kuaishouDarkSvg },
  xiaohongshu: { light: xiaohongshuDarkSvg, dark: xiaohongshuDarkSvg },
  tencent: { light: tencentDarkSvg, dark: tencentDarkSvg },
  bilibili: { light: bilibiliDarkSvg, dark: bilibiliDarkSvg },
  tiktok: { light: tiktokDarkSvg, dark: tiktokDarkSvg },
  baijiahao: { light: baijiahaoSvg, dark: baijiahaoDarkSvg },
}

export function PlatformIcon({ platform, className = "h-5 w-5" }: PlatformIconProps) {
  const { resolved } = useTheme()
  const icons = ICON_MAP[platform]
  if (!icons) return null

  const src = resolved === 'dark' ? icons.dark : icons.light

  return (
    <img
      src={src}
      alt={platform}
      className={className}
    />
  )
}

export const PLATFORM_COLORS: Record<string, string> = {
  douyin: 'bg-black',
  kuaishou: 'bg-[#FF4906]',
  xiaohongshu: 'bg-[#FE2C55]',
  tencent: 'bg-[#07C160]',
  bilibili: 'bg-[#00A1D6]',
  tiktok: 'bg-black',
  baijiahao: 'bg-[#D7000F]',
}
