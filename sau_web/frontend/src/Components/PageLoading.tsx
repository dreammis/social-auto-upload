/**
 * Loading fallback displayed inside the page transition container
 * while lazy-loaded page components are being fetched.
 */
export function PageLoading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] gap-4">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-foreground" />
      <div className="text-sm text-muted-foreground">加载中...</div>
    </div>
  )
}
