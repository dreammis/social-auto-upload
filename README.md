# SocialFlow AI

Hệ thống tự động hóa tạo & đăng tải video đa nền tảng tích hợp AI Content Generation.

## Tech Stack

- **Backend**: NestJS + TypeScript + PostgreSQL + Redis
- **Frontend**: Vue 3 + Vite + Pinia + TypeScript
- **AI Worker**: Python 3.11 + FastAPI
- **Upload Engine**: Python 3.11 + Playwright
- **Storage**: MinIO (S3-compatible)
- **Auth**: JWT + License Gate
- **Infrastructure**: Docker Compose → aaPanel VPS

## Architecture

```
socialflow-ai/
├── docker-compose.yml          # All services orchestration
├── .env.example                # Environment variables template
├── backend/                    # NestJS application
│   ├── src/
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── frontend/                   # Vue 3 application
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── ai-worker/                  # Python AI service
│   ├── main.py
│   ├── pyproject.toml
│   └── Dockerfile
└── upload-engine/              # Python upload service
    ├── main.py
    ├── pyproject.toml
    └── Dockerfile
```

## Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Quick Start

1. Clone & setup environment:
```bash
git clone <repo>
cd socialflow-ai
cp .env.example .env
```

2. Start all services:
```bash
docker compose up
```

3. Access services:
- Backend API: http://localhost:3000
- Frontend: http://localhost:5173
- MinIO Console: http://localhost:9001
- Redis: localhost:6379
- PostgreSQL: localhost:5432

## Phase Roadmap

- **Phase 0**: Project Skeleton ✓
- **Phase 1**: Auth + License Gate
- **Phase 2**: Account Manager
- **Phase 3**: Trend Engine
- **Phase 4**: Video Factory
- **Phase 5**: Upload Engine
- **Phase 6**: Page Warmer + Scheduler
- **Phase 7**: Analytics + Affiliate
- **Phase 8**: Multi-tenant + SaaS

## Health Checks

All services expose `/health` endpoints:

```bash
curl http://localhost:3000/health          # Backend
curl http://localhost:8001/health          # AI Worker
curl http://localhost:8002/health          # Upload Engine
```

## Development

### Backend
```bash
cd backend
npm install
npm run dev
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### AI Worker
```bash
cd ai-worker
pip install -r requirements.txt
python main.py
```

### Upload Engine
```bash
cd upload-engine
pip install -r requirements.txt
python main.py
```

## Testing

Run tests for each service:

```bash
docker compose exec backend npm run test
docker compose exec frontend npm run test
docker compose exec ai-worker pytest
docker compose exec upload-engine pytest
```

## Deployment

Production deployment via aaPanel:

1. Build images
2. Push to registry
3. Deploy via aaPanel dashboard

See [deployment docs](./docs/DEPLOYMENT.md) for details.

## License

Proprietary - SocialFlow AI
