import { GroupListItem } from './GroupListItem'
import { useAccountsState } from './AccountsProvider'

/**
 * List view of account groups — no DragDropProvider (groups in the list
 * view cannot be reordered; selection / actions still work via dispatch).
 */
export function GroupListArea() {
  const state = useAccountsState()

  return (
    <div className="space-y-2">
      {state.filteredGroups.map((group) => (
        <GroupListItem
          key={group.id}
          group={group}
          selected={state.selectedIds.has(group.id)}
        />
      ))}
    </div>
  )
}
