## 1. Backend: Platform-Aware Prompts (Web API)

- [x] 1.1 Add `PLATFORM_PROMPTS` dict to `web_runner.py` with per-platform system prompts (douyin, bilibili, xiaohongshu, kuaishou, tencent, tiktok, baijiahao)
- [x] 1.2 Update `POST /api/ai/generate` to accept `platform` parameter and use platform-specific system prompt

## 2. Backend: SSE Streaming (Web API)

- [x] 2.1 Implement `POST /api/ai/generate/stream` SSE endpoint that proxies OpenRoute streaming response
- [x] 2.2 Add `stream: true` flag to OpenRoute API call and handle chunked response
- [x] 2.3 Send `data`, `done`, and `error` SSE events

## 3. Frontend: API Client Updates

- [x] 3.1 Add `generateAiContentStream()` function to `src/api/client.ts` using fetch + ReadableStream
- [x] 3.2 Update `generateAiContent()` to accept `platform` parameter

## 4. Frontend: Platform-Aware Integration

- [x] 4.1 Pass current `mode` platform info from PublishPage to AiSidebar
- [x] 4.2 Update AiSidebar to send `platform` parameter in generate requests

## 5. Frontend: Streaming Response UI

- [x] 5.1 Add streaming text display area in AiSidebar with typing cursor effect
- [x] 5.2 Update GenerateButton to show streaming progress
- [x] 5.3 Parse streamed content and apply to form fields on completion

## 6. Frontend: Generation History

- [x] 6.1 Create `src/stores/useAiHistory.ts` with localStorage persistence (max 50 entries)
- [x] 6.2 Create `src/components/AiSidebar/HistoryPanel.tsx` component
- [x] 6.3 Add history tab to AiSidebar with apply/delete actions

## 7. Frontend: Prompt Templates

- [x] 7.1 Create `src/stores/useAiTemplates.ts` with localStorage persistence + built-in templates
- [x] 7.2 Create `src/components/AiSidebar/TemplateSelector.tsx` component
- [x] 7.3 Add template dropdown to AiSidebar with save/apply/delete actions

## 8. Frontend: Content Optimization

- [x] 8.1 Add optimize buttons (优化标题/优化描述/优化标签) to generated content display
- [x] 8.2 Implement optimize prompt construction and single-field update logic

## 9. Frontend: Queue Visibility

- [x] 9.1 Display queue position and estimated wait time in AiSidebar when request is queued
