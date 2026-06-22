---
name: phase3-trend-engine
description: Phase 3 Trend Engine complete — Python worker (FastAPI+APScheduler) + NestJS /trends/latest API + Vue 3 TrendsView with dark UI
metadata:
  type: project
---

Phase 3 Trend Engine fully built.

**Part 1 — Python Worker (ai-worker/):**
- FastAPI on :8001 with /health endpoint
- APScheduler BackgroundScheduler running trend crawl every 1min (test) or 2h (prod)
- SQLAlchemy model `Trend` (trends table: id, platform, keyword, volume, extracted_at)
- Mockup data: 17 keywords across TikTok/Facebook/YouTube with randomized volumes
- Connects to shared PostgreSQL (same DB as NestJS)

**Part 2 — NestJS Backend (backend/src/trends/):**
- Trend entity mapping to `trends` table
- GET /trends/latest — returns latest batch grouped by platform, top 10 per platform
- JwtAuthGuard — only authenticated users can access

**Part 3 — Vue 3 Frontend:**
- Trend store (Pinia) — fetchLatestTrends()
- Router: /app/trends route
- AppLayout: "🔥 Trends" sidebar menu item
- TrendsView.vue: Platform tabs + ranked cards with volume bars + HOT badge (≥800K)
- Dark glassmorphism theme consistent with all views

**Verification:**
- Backend tsc --noEmit: 0 errors
- Frontend Vite build: 104 modules, 0 errors
- Backend jest: 27/27 pass (0 regressions)

**Why:** Phase 3 DoD — AI Worker collects trend data → NestJS serves it → Vue 3 displays it with platform-grouped UI.
**How to apply:** Start ai-worker (python main.py), backend (npm run start:dev), frontend (npm run dev). Access /app/trends in browser.
