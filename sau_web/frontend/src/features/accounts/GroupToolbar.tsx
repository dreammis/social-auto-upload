import { memo, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  CheckSquare,
  CircleDot,
  LayoutGrid,
  List,
  Loader2,
  Search,
  Square,
  Trash,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { toneDotStyle, type Tone } from '@/lib/tone'
import { useAccountsDispatch, useAccountsState } from './AccountsProvider'

/** All four shape axes (value / label / icon / tone) are present on every
 *  item so iterating `VALIDITY_OPTIONS` doesn't fall into a discriminated
 *  union with missing properties (TS2339 in render). 'all' has `tone = null`
 *  and renders no decoration — it's the "no filter" baseline. The `tone`
 *  field is `Tone | null` (renamed from `dotClass: string | null`) so the
 *  filter decoration pulls colour from `@/lib/tone.ts` rather than from
 *  the deleted `.status-dot-{valid,invalid}` CSS rules. */
const VALIDITY_OPTIONS: ReadonlyArray<{
  value: 'all' | 'valid' | 'invalid'
  label: string
  icon: typeof CircleDot | null
  tone: Tone | null
}> = [
  { value: 'all', label: '全部', icon: null, tone: null },
  { value: 'valid', label: '有效', icon: CircleDot, tone: 'success' },
  { value: 'invalid', label: '失效', icon: null, tone: 'error' },
] as const

/**
 * Toolbar at the top of the accounts page: search input + validity filter
 * (paired as "filter controls"), batch-delete bar (only when something is
 * selected), select-all + view toggle + reorder-in-flight chip.
 *
 * Search state is intentionally LOCAL with a 120ms debounce — typing must
 * not churn the dispatch context identity (which memoized children depend
 * on to skip re-renders).
 */
function GroupToolbarImpl() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  // ── local search state with debounce ──
  const [localSearch, setLocalSearch] = useState(state.searchQuery)
  useEffect(() => {
    const handle = setTimeout(() => {
      if (localSearch !== state.searchQuery) {
        dispatch.setSearchQuery(localSearch)
      }
    }, 120)
    return () => clearTimeout(handle)
  }, [localSearch, state.searchQuery, dispatch])

  // ── keep local in sync if dispatch changes from outside (clear button etc.) ──
  useEffect(() => {
    setLocalSearch(state.searchQuery)
  }, [state.searchQuery])

  const allSelected =
    state.selectedIds.size === state.filteredGroups.length &&
    state.filteredGroups.length > 0

  /** Decorative dot/decoration rendering right after each segmented button
   *  label. Centralised here to keep the segmented map below readable. */
  const renderValidityIcon = (opt: (typeof VALIDITY_OPTIONS)[number]) => {
    if (opt.icon) {
      const Icon = opt.icon
      // lucide-react icons propagate the `style` prop down to the SVG where
      // `toneDotStyle(tone)` paints the canonical --status-{tone}-fg
      // background + 40% halo (replaces the deleted `.status-dot-{valid,
      // invalid}` CSS rules previously applied via `className`).
      return <Icon className="h-3 w-3 mr-1" style={toneDotStyle(opt.tone)} />
    }
    if (opt.tone) {
      return <span className="mr-1.5 h-1.5 w-1.5 rounded-full" style={toneDotStyle(opt.tone)} />
    }
    return null
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Search with keyword hint */}
      <div className="relative flex-1 min-w-[200px] max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
        <Input
          placeholder="搜索分组名称、平台..."
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          className="pl-9 pr-16"
          data-search-input
        />
        {!localSearch && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
            <kbd className="kbd-hint">/</kbd>
          </div>
        )}
        {localSearch && (
          <button
            type="button"
            onClick={() => {
              setLocalSearch('')
              dispatch.handleClearSearch()
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Validity filter — visually paired with search input (both are
          "filter controls"); replaces the magic 已/失效 search-keyword branch. */}
      <div className="flex items-center bg-muted/50 rounded-lg p-0.5 border border-border/50">
        {VALIDITY_OPTIONS.map((opt) => {
          const active = state.validityFilter === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => dispatch.setValidityFilter(opt.value)}
              className={cn(
                'flex items-center justify-center h-7 px-2.5 rounded-md text-[11px] font-medium transition-all duration-200',
                active
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground/60 hover:text-muted-foreground',
              )}
              aria-pressed={active}
              aria-label={`筛选：${opt.label}`}
            >
              {renderValidityIcon(opt)}
              {opt.label}
            </button>
          )
        })}
      </div>

      {/* Batch actions (only when something is selected) */}
      {state.selectedIds.size > 0 && (
        <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-2">
          <span className="text-sm text-muted-foreground">
            已选择 {state.selectedIds.size} 项
          </span>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => dispatch.setBatchDeleteOpen(true)}
          >
            <Trash className="h-4 w-4 mr-1" />
            批量删除
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => dispatch.setSelectedIds(new Set())}
          >
            取消选择
          </Button>
        </div>
      )}

      {/* Select-all + view toggle + reorder-in-flight chip */}
      <div className="flex items-center gap-1.5">
        <Button
          variant={allSelected ? 'secondary' : 'ghost'}
          size="sm"
          onClick={dispatch.handleSelectAll}
          className="text-muted-foreground h-8"
        >
          {allSelected ? (
            <CheckSquare className="h-4 w-4 mr-1" />
          ) : (
            <Square className="h-4 w-4 mr-1" />
          )}
          全选
        </Button>

        {/* Segmented view toggle */}
        <div className="flex items-center bg-muted/50 rounded-lg p-0.5 border border-border/50">
          <button
            type="button"
            onClick={() => dispatch.setViewMode('grid')}
            className={cn(
              'flex items-center justify-center h-7 w-7 rounded-md transition-all duration-200',
              state.viewMode === 'grid'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground/50 hover:text-muted-foreground',
            )}
            aria-label="Grid view"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => dispatch.setViewMode('list')}
            className={cn(
              'flex items-center justify-center h-7 w-7 rounded-md transition-all duration-200',
              state.viewMode === 'list'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground/50 hover:text-muted-foreground',
            )}
            aria-label="List view"
          >
            <List className="h-3.5 w-3.5" />
          </button>
        </div>

        {state.isReorderInFlight && (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-foreground/[0.04] animate-in fade-in slide-in-from-left-2 duration-200"
          >
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground whitespace-nowrap">
              保存顺序中…
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export const GroupToolbar = memo(GroupToolbarImpl)
