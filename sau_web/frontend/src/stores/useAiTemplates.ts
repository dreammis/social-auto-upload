import { create } from 'zustand'

export interface PromptTemplate {
  id: string
  name: string
  content: string
  builtin: boolean
}

const BUILTIN_TEMPLATES: PromptTemplate[] = [
  { id: 'builtin-food', name: '美食探店', content: '这是一期美食探店内容，请生成吸引人的标题和描述，突出食物特色、环境氛围和性价比。', builtin: true },
  { id: 'builtin-product', name: '产品测评', content: '这是一期产品测评内容，请生成专业的标题和描述，包含产品亮点、使用体验和购买建议。', builtin: true },
  { id: 'builtin-travel', name: '旅行攻略', content: '这是一期旅行攻略内容，请生成有吸引力的标题和描述，包含景点推荐、实用tips和旅行感悟。', builtin: true },
  { id: 'builtin-lifestyle', name: '日常生活', content: '这是一期日常生活分享，请生成温馨亲切的标题和描述，展现生活美好瞬间。', builtin: true },
  { id: 'builtin-knowledge', name: '知识科普', content: '这是一期知识科普内容，请生成有深度的标题和描述，用通俗易懂的方式讲解专业知识。', builtin: true },
]

const STORAGE_KEY = 'sau-ai-templates'

function loadCustom(): PromptTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveCustom(templates: PromptTemplate[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(templates))
}

interface AiTemplatesState {
  templates: PromptTemplate[]
  addTemplate: (name: string, content: string) => void
  removeTemplate: (id: string) => void
}

export const useAiTemplatesStore = create<AiTemplatesState>((set, get) => ({
  templates: [...BUILTIN_TEMPLATES, ...loadCustom()],

  addTemplate: (name, content) => {
    const newTpl: PromptTemplate = {
      id: crypto.randomUUID(),
      name,
      content,
      builtin: false,
    }
    const updated = [...get().templates, newTpl]
    const custom = updated.filter((t) => !t.builtin)
    saveCustom(custom)
    set({ templates: updated })
  },

  removeTemplate: (id) => {
    const target = get().templates.find((t) => t.id === id)
    if (target?.builtin) return
    const updated = get().templates.filter((t) => t.id !== id)
    const custom = updated.filter((t) => !t.builtin)
    saveCustom(custom)
    set({ templates: updated })
  },
}))
