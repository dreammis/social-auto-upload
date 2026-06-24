import { create } from 'zustand'

export interface HistoryEntry {
  id: string
  timestamp: number
  platform: string
  model: string
  prompt: string
  content: string
  parsed: {
    title: string
    desc: string
    tags: string
  }
}

interface AiHistoryState {
  entries: HistoryEntry[]
  addEntry: (entry: Omit<HistoryEntry, 'id' | 'timestamp'>) => void
  removeEntry: (id: string) => void
  clearHistory: () => void
}

const STORAGE_KEY = 'sau-ai-history'
const MAX_ENTRIES = 50

function loadEntries(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveEntries(entries: HistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)))
}

export const useAiHistoryStore = create<AiHistoryState>((set, get) => ({
  entries: loadEntries(),

  addEntry: (entry) => {
    const newEntry: HistoryEntry = {
      ...entry,
      id: crypto.randomUUID(),
      timestamp: Date.now(),
    }
    const updated = [newEntry, ...get().entries].slice(0, MAX_ENTRIES)
    saveEntries(updated)
    set({ entries: updated })
  },

  removeEntry: (id) => {
    const updated = get().entries.filter((e) => e.id !== id)
    saveEntries(updated)
    set({ entries: updated })
  },

  clearHistory: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ entries: [] })
  },
}))
