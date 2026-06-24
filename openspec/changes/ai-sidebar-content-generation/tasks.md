## 1. Backend API Setup (Web API)

- [x] 1.1 Add OpenRoute API configuration to `web_runner.py` (environment variable `OPENROUTE_API_KEY`, `AI_MODELS` dict)
- [x] 1.2 Implement `POST /api/ai/generate` endpoint with request queue and rate limiting using `threading.Semaphore`
- [x] 1.3 Implement `GET /api/ai/models` endpoint to return available model list
- [x] 1.4 Add error handling for missing API key, rate limit exceeded, and OpenRoute API errors

## 2. Frontend API Client (Frontend)

- [x] 2.1 Add `generateAiContent()` function to `src/api/client.ts`
- [x] 2.2 Add `fetchAiModels()` function to `src/api/client.ts`
- [x] 2.3 Create `src/hooks/useAiGeneration.ts` TanStack Query mutation hook

## 3. AI Store (Frontend)

- [x] 3.1 Create `src/stores/useAiStore.ts` Zustand store (selectedModel, isGenerating, queuePosition, error)

## 4. AI Sidebar Component (Frontend)

- [x] 4.1 Create `src/components/AiSidebar/AiSidebar.tsx` component with model selector and generate button
- [x] 4.2 Create `src/components/AiSidebar/ModelSelector.tsx` dropdown component using Ant Design Select
- [x] 4.3 Create `src/components/AiSidebar/GenerateButton.tsx` with loading/queue states
- [x] 4.4 Style sidebar with 320px width, responsive drawer for < 1200px viewport

## 5. PublishPage Integration (Frontend)

- [x] 5.1 Refactor PublishPage layout to two-column (form + sidebar)
- [x] 5.2 Add sidebar toggle button for responsive mode
- [x] 5.3 Implement form field auto-fill from AI generation result (title, desc, tags)
- [x] 5.4 Implement "重新生成" (re-generate) functionality to overwrite fields

## 6. Error Handling & UX (Frontend)

- [x] 6.1 Add toast notifications for generation success, error, and queue status
- [x] 6.2 Add graceful degradation when AI service is unavailable
- [x] 6.3 Add estimated wait time display when request is queued
