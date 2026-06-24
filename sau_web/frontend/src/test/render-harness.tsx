import { Profiler, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

/**
 * Per-test query client. Defaults to disabled retries + minimal cache
 * TTL so tests don't accidentally cross-pollute between assertions.
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
        refetchOnWindowFocus: false,
      },
    },
  })
}

/**
 * Counter for React.Profiler onRender callbacks. Tests use this to
 * detect memo hits: re-rendering the same tree with shallow-equal
 * props must NOT trigger a fresh onRender for that subtree (React.memo
 * short-circuits before Profiler fires).
 */
export type ProfilerCounter = {
  /** Push of `phase` ('mount' | 'update' | 'nested-update') for each commit */
  phases: string[]
  reset: () => void
}

export function makeProfilerCounter(): ProfilerCounter {
  const phases: string[] = []
  return {
    phases,
    reset: () => {
      phases.length = 0
    },
  }
}

export function ProfilerWrap({
  id,
  counter,
  children,
}: {
  id: string
  counter?: ProfilerCounter
  children: ReactNode
}) {
  return (
    <Profiler
      id={id}
      onRender={(_id, _phase, _actualDuration, _baseDuration, _startTime, _commitTime) => {
        counter?.phases.push(_phase as string)
      }}
    >
      {children}
    </Profiler>
  )
}

/**
 * Standard harness used by every form/drawer test. Provides QueryClient;
 * tests wrap with <ProfilerWrap> themselves so they control the id.
 */
export function TestProviders({
  client,
  children,
}: {
  client: QueryClient
  children: ReactNode
}) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
