import { DragDropProvider } from '@dnd-kit/react'
import { SortableGroup } from './SortableGroup'
import { useAccountsDispatch, useAccountsState } from './AccountsProvider'

/**
 * Grid view of account groups. The DragDropProvider lives here — and ONLY
 * here — so that:
 *   1. The list view doesn't pay the cost of subscribing to drag-lifecycle
 *      updates that only the sortable items need.
 *   2. Sidebar / toolbar / dialogs can re-render freely without fighting
 *      dnd-kit's internal listeners.
 *
 * Drag-end dispatch (group vs auth discriminated by id prefix) is provided
 * by `useAccountsDispatch().handleDragEnd`, registered once in
 * `AccountsProvider`.
 */
export function GroupGridArea() {
  const state = useAccountsState()
  const dispatch = useAccountsDispatch()

  return (
    <DragDropProvider
      onDragStart={dispatch.handleDragStart}
      onDragEnd={dispatch.handleDragEnd}
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {state.filteredGroups.map((group, index) => (
          <SortableGroup key={group.id} group={group} index={index} />
        ))}
      </div>
    </DragDropProvider>
  )
}
