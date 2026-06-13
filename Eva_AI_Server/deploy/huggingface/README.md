---
title: EVA AI Server
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# EVA AI Server

FastAPI service for **EVA** (Enhanced Virtual Assistant): intent classification, NER, chat `/process`, and learning/scheduling internal APIs.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | OpenAPI UI |
| POST | `/process` | Main chat pipeline |
| GET | `/analytics` | Productivity analytics |

## Required Space secrets

Set these under **Settings → Variables and secrets** (Repository secrets):

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `REDIS_URL` | **Easiest:** full Upstash TCP string, e.g. `rediss://default:PASSWORD@endless-hagfish-121522.upstash.io:6379` |
| `REDIS_HOST` | Or hostname only: `endless-hagfish-121522.upstash.io` (no `https://`) |
| `REDIS_PORT` | `6379` |
| `REDIS_PASSWORD` | Upstash TCP **password** (not REST token) |
| `REDIS_SSL` | `true` when using separate host/port/password fields |
| `GEMINI_API_KEY` | Google Gemini API key |
| `DUCKLING_URL` | Optional — defaults to `http://127.0.0.1:8000`. **Remove** if you set an external URL by mistake. |

Optional: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `YOUTUBE_API_KEY`.

## Models (required)

Space repos are limited to **1 GB**. Model weights (~1.3 GB) are stored in a separate **Model** repo:

1. Create https://huggingface.co/new → **Model** → `eva-models` → **Public**
2. From `deploy/huggingface`: `.\upload-models.ps1`
3. The Dockerfile downloads `hamidshehzad/eva-models` at build time

## Backend connection

Point your Node backend to this Space:

```env
AI_SERVER_URL=https://hamidshehzad-eva-ai-server.hf.space
AI_SERVER_TIMEOUT_MS=60000
```
