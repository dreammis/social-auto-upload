import { create } from 'zustand'

interface AiState {
  selectedModel: string
  modelTags: string[]
  isGenerating: boolean
  queuePosition: number
  error: string | null

  setSelectedModel: (model: string) => void
  setModelTags: (tags: string[]) => void
  setIsGenerating: (val: boolean) => void
  setQueuePosition: (pos: number) => void
  setError: (err: string | null) => void
  reset: () => void
}

const DEFAULT_MODEL = 'google/gemma-4-26b-a4b-it:free'

export const useAiStore = create<AiState>((set) => ({
  selectedModel: DEFAULT_MODEL,
  modelTags: ['text'],
  isGenerating: false,
  queuePosition: 0,
  error: null,

  setSelectedModel: (model) => set({ selectedModel: model }),
  setModelTags: (tags) => set({ modelTags: tags }),
  setIsGenerating: (val) => set({ isGenerating: val }),
  setQueuePosition: (pos) => set({ queuePosition: pos }),
  setError: (err) => set({ error: err }),
  reset: () => set({ isGenerating: false, queuePosition: 0, error: null }),
}))
