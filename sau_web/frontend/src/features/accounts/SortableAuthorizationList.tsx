import type { AccountGroup } from '@/api/client'
import { SortableAuthorizationItem } from './SortableAuthorizationItem'

interface SortableAuthorizationListProps {
  groupId: number
  authorizations: AccountGroup['authorizations']
}

// Render-only leaf under the page-root DragDropProvider (defined in
// `GroupGridArea` and wrapping `<GroupGridArea>` for the grid view only).
// Drag logic — including optimistic auth reordering — is handled in
// `AccountsProvider.handleDragEnd` where both group and auth dispatches
// share one root and discriminate by id prefix (`group:<id>` vs
// `auth:<gid>:<aid>`).
export function SortableAuthorizationList({
  groupId,
  authorizations,
}: SortableAuthorizationListProps) {
  return (
    <div className="space-y-2">
      {authorizations.map((auth, index) => (
        <SortableAuthorizationItem
          key={auth.id}
          auth={auth}
          index={index}
          groupId={groupId}
        />
      ))}
    </div>
  )
}
