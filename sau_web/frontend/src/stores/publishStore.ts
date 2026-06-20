import { create } from 'zustand'

export type SubmitSuccessInfo = {
  count: number
  mode: '视频' | '图文'
  taskIds: string[]
}

interface PublishState {
  /** Task IDs from the most recent submit */
  lastTaskIds: string[]
  /** Success banner info (null = hidden) */
  submitSuccess: SubmitSuccessInfo | null

  setLastTaskIds: (ids: string[]) => void
  setSubmitSuccess: (info: SubmitSuccessInfo | null) => void
  clearSubmit: () => void
}

export const usePublishStore = create<PublishState>((set) => ({
  lastTaskIds: [],
  submitSuccess: null,

  setLastTaskIds: (ids) => set({ lastTaskIds: ids }),
  setSubmitSuccess: (info) => set({ submitSuccess: info }),
  clearSubmit: () => set({ lastTaskIds: [], submitSuccess: null }),
}))
