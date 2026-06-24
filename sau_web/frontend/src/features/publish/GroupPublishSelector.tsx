import { memo, useCallback, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/index'
import { PlatformIcon } from '@/components/ui/platform-icon'
import { cn } from '@/lib/utils'
import { Layers, CheckCircle2, Users, ChevronRight, Sparkles } from 'lucide-react'
import type { AccountGroup } from '@/api/client'
import { PLATFORMS, NOTE_PLATFORMS } from '@/api/client'

export type PlatformAccountMapping = {
  platform: string
  cookieFile: string
  authId: number
}

export type GroupSelection = {
  groupId: number
  groupName: string
  platforms: string[]
  mappings: PlatformAccountMapping[]
}

type GroupPublishSelectorProps = {
  groups: AccountGroup[]
  mode: 'video' | 'note'
  value: GroupSelection | null
  onChange: (selection: GroupSelection | null) => void
}

/** Platforms that support note uploads. */
const NOTE_PLATFORM_SET = new Set(NOTE_PLATFORMS.map((p) => p.value))

/** Muted brand-tint border-left classes. */
const PLATFORM_BORDER: Record<string, string> = {
  douyin: 'border-l-neutral-800 dark:border-l-neutral-300',
  kuaishou: 'border-l-[#FF4906]/70',
  xiaohongshu: 'border-l-[#FE2C55]/70',
  tencent: 'border-l-[#07C160]/70',
  bilibili: 'border-l-[#00A1D6]/70',
  tiktok: 'border-l-neutral-800 dark:border-l-neutral-300',
  baijiahao: 'border-l-[#D7000F]/70',
}

export const GroupPublishSelector = memo(function GroupPublishSelector({
  groups,
  mode,
  value,
  onChange,
}: GroupPublishSelectorProps) {
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(
    value?.groupId ?? null,
  )

  const selectedGroup = useMemo(
    () => groups.find((g) => g.id === selectedGroupId) ?? null,
    [groups, selectedGroupId],
  )

  const availableAuths = useMemo(() => {
    if (!selectedGroup) return []
    return selectedGroup.authorizations.filter((a) =>
      mode === 'note' ? NOTE_PLATFORM_SET.has(a.platform) : true,
    )
  }, [selectedGroup, mode])

  const platformLabelMap = useMemo(
    () => Object.fromEntries(PLATFORMS.map((p) => [p.value, p.label])),
    [],
  )

  const checkedPlatforms = useMemo(
    () => new Set(value?.platforms ?? []),
    [value?.platforms],
  )

  const allChecked =
    availableAuths.length > 0 &&
    availableAuths.every((a) => checkedPlatforms.has(a.platform))

  // ── handlers ──────────────────────────────────────────────────────────

  const handleGroupChange = useCallback(
    (groupIdStr: string) => {
      const gid = Number(groupIdStr)
      setSelectedGroupId(gid)
      const group = groups.find((g) => g.id === gid)
      if (!group) {
        onChange(null)
        return
      }
      const auths = group.authorizations.filter((a) =>
        mode === 'note' ? NOTE_PLATFORM_SET.has(a.platform) : true,
      )
      const platforms = auths.map((a) => a.platform)
      const mappings: PlatformAccountMapping[] = auths.map((a) => ({
        platform: a.platform,
        cookieFile: a.cookie_file,
        authId: a.id,
      }))
      onChange({ groupId: group.id, groupName: group.name, platforms, mappings })
    },
    [groups, mode, onChange],
  )

  const handleTogglePlatform = useCallback(
    (platform: string) => {
      if (!selectedGroup) return
      const next = new Set(checkedPlatforms)
      if (next.has(platform)) next.delete(platform)
      else next.add(platform)

      const auths = availableAuths.filter((a) => next.has(a.platform))
      const mappings: PlatformAccountMapping[] = auths.map((a) => ({
        platform: a.platform,
        cookieFile: a.cookie_file,
        authId: a.id,
      }))
      onChange({
        groupId: selectedGroup.id,
        groupName: selectedGroup.name,
        platforms: Array.from(next),
        mappings,
      })
    },
    [selectedGroup, checkedPlatforms, availableAuths, onChange],
  )

  const handleToggleAll = useCallback(() => {
    if (!selectedGroup) return
    if (allChecked) {
      onChange({
        groupId: selectedGroup.id,
        groupName: selectedGroup.name,
        platforms: [],
        mappings: [],
      })
    } else {
      const platforms = availableAuths.map((a) => a.platform)
      const mappings: PlatformAccountMapping[] = availableAuths.map((a) => ({
        platform: a.platform,
        cookieFile: a.cookie_file,
        authId: a.id,
      }))
      onChange({ groupId: selectedGroup.id, groupName: selectedGroup.name, platforms, mappings })
    }
  }, [selectedGroup, allChecked, availableAuths, onChange])

  const groupsWithAuths = useMemo(
    () => groups.filter((g) => g.authorizations.length > 0),
    [groups],
  )

  const checkedCount = value?.platforms.length ?? 0
  const totalCount = availableAuths.length

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="card-refined">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-muted">
              <Layers className="h-4 w-4 text-muted-foreground" />
            </div>
            <span>选择发布账号组</span>
            {value && checkedCount > 0 && (
              <span className="ml-auto inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                <Sparkles className="h-3 w-3" />
                {checkedCount}/{totalCount} 平台
              </span>
            )}
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Group selector */}
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">账号分组</Label>
            <Select
              value={selectedGroupId != null ? String(selectedGroupId) : ''}
              onValueChange={handleGroupChange}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="选择一个账号分组…" />
              </SelectTrigger>
              <SelectContent>
                {groupsWithAuths.length === 0 ? (
                  <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                    暂无可用分组，请先在账号管理中创建
                  </div>
                ) : (
                  groupsWithAuths.map((group) => {
                    const pValues = group.authorizations.map((a) => a.platform)
                    return (
                      <SelectItem key={group.id} value={String(group.id)}>
                        <span className="flex items-center gap-2">
                          <Users className="h-3.5 w-3.5 text-muted-foreground/60" />
                          <span className="font-medium">{group.name}</span>
                          <span className="flex items-center gap-0.5 ml-1">
                            {pValues.slice(0, 4).map((p) => (
                              <PlatformIcon key={p} platform={p} className="h-3 w-3" />
                            ))}
                            {pValues.length > 4 && (
                              <span className="text-[10px] text-muted-foreground">+{pValues.length - 4}</span>
                            )}
                          </span>
                          <span className="text-muted-foreground text-[11px]">
                            ({group.authorizations.length})
                          </span>
                        </span>
                      </SelectItem>
                    )
                  })
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Platform list */}
          <AnimatePresence mode="wait">
            {selectedGroup && availableAuths.length > 0 && (
              <motion.div
                key={selectedGroupId}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-3 overflow-hidden"
              >
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-muted-foreground">
                    发布平台
                  </Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[11px] text-muted-foreground"
                    onClick={handleToggleAll}
                  >
                    {allChecked ? '取消全选' : '全选'}
                  </Button>
                </div>

                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {availableAuths.map((auth, idx) => {
                    const checked = checkedPlatforms.has(auth.platform)
                    const label = platformLabelMap[auth.platform] ?? auth.platform
                    const borderCls = PLATFORM_BORDER[auth.platform] ?? 'border-l-primary/50'

                    return (
                      <motion.div
                        key={auth.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: idx * 0.03 }}
                        className={cn(
                          'auth-row border-l-[3px] cursor-pointer select-none',
                          borderCls,
                          checked
                            ? 'bg-muted/60'
                            : 'hover:bg-muted/30',
                        )}
                        onClick={() => handleTogglePlatform(auth.platform)}
                      >
                        <div className="relative flex-shrink-0">
                          <Checkbox
                            checked={checked}
                            onCheckedChange={() => handleTogglePlatform(auth.platform)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>

                        <PlatformIcon platform={auth.platform} className="h-4 w-4 shrink-0" />

                        <div className="flex flex-col min-w-0 flex-1">
                          <span className="text-sm font-medium truncate">{label}</span>
                          <span className="text-[11px] text-muted-foreground/50 truncate font-mono">
                            {auth.cookie_file.split('/').pop()?.replace('.json', '') ?? ''}
                          </span>
                        </div>

                        {checked && (
                          <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
                        )}

                        {!auth.valid && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 shrink-0">
                            <span className="w-1 h-1 rounded-full bg-amber-500" />
                            失效
                          </span>
                        )}
                      </motion.div>
                    )
                  })}
                </div>

                {/* Summary */}
                {value && checkedCount > 0 && (
                  <div className="flex items-center gap-2.5 rounded-lg bg-muted/40 border border-border/50 px-3 py-2.5 text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span className="text-muted-foreground">将发布到</span>
                    <span className="font-semibold text-foreground">{checkedCount} 个平台</span>
                    <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
                    <div className="flex items-center gap-1 flex-wrap min-w-0">
                      {value.platforms.map((p) => (
                        <span
                          key={p}
                          className="inline-flex items-center gap-1 rounded bg-background border border-border/60 px-1.5 py-0.5 text-[11px] font-medium"
                        >
                          <PlatformIcon platform={p} className="h-3 w-3" />
                          {platformLabelMap[p] ?? p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {selectedGroup && availableAuths.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">
              该分组暂无{mode === 'note' ? '支持图文的' : ''}已授权平台
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
})
