# EVA — Enhanced Virtual Assistant

**EVA** is an AI-powered academic assistant for students. It goes beyond a to-do list: talk to it in plain language and it plans your tasks, builds full learning roadmaps for technical subjects, schedules study sessions around your real free time, adapts when your plans change, and surfaces insights about how you actually work.

A Final Year Project — Department of Computer Science, School of Systems & Technology, University of Management & Technology, Lahore.

---

## Table of Contents

- [What EVA Does](#what-eva-does)
- [Architecture](#architecture)
- [NLP/AI Pipeline](#nlpai-pipeline)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [External Dependencies](#external-dependencies)
- [Testing](#testing)
- [Deployment](#deployment)
- [Limitations](#limitations)
- [Team](#team)

---

## What EVA Does

- **Conversational task & schedule management** — add, update, delete, and review tasks through natural language, with reminders, priorities, and Google Calendar sync.
- **AI-generated learning roadmaps** — say "I want to learn MongoDB" and EVA builds a full, ordered curriculum with real curated video resources, scheduled into your preferred study slots.
- **Sequential, adaptive progression** — roadmap sessions unlock one at a time; missed or overdue sessions are surfaced back to the user for an explicit decision (complete/reschedule) rather than being silently auto-completed.
- **Conflict-aware scheduling** — detects overlaps between tasks, quiet hours, and study sessions before they're created.
- **Behavioral insights** — aggregates completed-task history to identify a user's most productive hours/days and recommend the best time to study.
- **Collaboration** — shared/invite-based learning roadmaps between friends.
- **Cross-platform** — native mobile app (Flutter) and a web app (React), both backed by the same APIs.

## Architecture

EVA is a three-tier system:

```
Flutter (mobile) ─┐
                   ├─► Node.js/Express backend ─► Python AI/NLP server
React (web)     ───┘         │                         │
                              ▼                         ▼
                          MongoDB                  Redis (context)
```

- **Clients** (Flutter mobile app, React web app) talk to the backend over a REST API.
- **Backend** (`Eva_Backend_Server`) owns auth, tasks, roadmaps, notifications, settings, and persistence — and proxies natural-language chat messages to the AI server.
- **AI server** (`Eva_AI_Server`) owns the NLP pipeline: understanding what the user said, extracting the relevant details, and deciding what should happen.

## NLP/AI Pipeline

A user's chat message flows through several stages before anything happens:

1. **Input routing (CLF1)** — classifies the message into a top-level type: `command`, `help`, `general` (small talk), `out_of_scope`, `confirmation`, or `multiple_command`. This stage is Gemini-backed with a locally-trained transformer classifier as a fallback if Gemini is unavailable.
2. **Sub-intent classification (CLF2)** — for `command` messages, determines the specific action (add a task, reschedule, create a roadmap, delete, etc.).
3. **Entity extraction (NER)** — a custom-trained BERT-based token-classification model extracts structured entities (task title, date, time, priority, learning topic, duration). A deterministic regex/keyword fallback fills in any field the model misses, so the extraction is robust even where the model is uncertain.
4. **Deterministic business logic** — scheduling conflict checks, roadmap curriculum lookup, session lock-state computation, and behavioral-analytics aggregation all run as plain, testable code — not model inference — for correctness and predictability.
5. **Reply generation** — a natural-language response is generated (Gemini) using only the structured result of the steps above, never inventing outcomes the backend didn't actually perform.

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile app | Flutter (Dart) |
| Web app | React + Vite |
| Backend API | Node.js + Express, Mongoose |
| AI/NLP server | Python, FastAPI-style + Uvicorn |
| Custom ML models | PyTorch + Hugging Face Transformers (BERT-based intent & NER models) |
| LLM | Google Gemini API |
| Database | MongoDB (Atlas) |
| Context/session cache | Redis (Upstash) |
| Date/time NLP | Duckling |
| Testing | Jest (backend), Pytest (AI server) |
| Hosting | Render (backend + web), Hugging Face Spaces (AI server, Docker) |

## Repository Structure

```
Frontend/               Flutter mobile app
Web_Frontend/            React web app
Eva_Backend_Server/      Node.js/Express REST API
Eva_AI_Server/           Python NLP/AI server (models, pipeline, handlers)
Api's documentation/     Backend API reference docs
```

## Getting Started

### Prerequisites

- Flutter SDK
- Node.js + npm
- Python + pip
- MongoDB (local or Atlas)
- Redis (local or Upstash)
- Docker (optional, for containerized AI server runs)

### Backend

```bash
cd Eva_Backend_Server
npm install
cp .env.example .env   # fill in the required values, see below
npm run dev
```

### AI Server

```bash
cd Eva_AI_Server
pip install -r requirements.txt
cp .env.example .env   # fill in the required values, see below
uvicorn main:app --reload
```

### Web App

```bash
cd Web_Frontend
npm install
npm run dev
```

### Mobile App

```bash
cd Frontend
flutter pub get
flutter run
```

## Environment Variables

Each server has its own `.env` (never committed — see `.gitignore`). At minimum, both need a MongoDB connection string; the AI server additionally needs a Redis connection and API keys for the external services below.

## External Dependencies

EVA relies on the following third-party services and infrastructure:

- **Google Gemini API** — LLM used in the chat NLU pipeline
- **YouTube Data API** — curated video resources for roadmap topics
- **Google OAuth** — user sign-in
- **Google Calendar API** — task/schedule sync
- **Firebase Cloud Messaging** — push notifications
- **Brevo** — transactional email
- **Cloudinary** — profile picture storage
- **MongoDB Atlas** — primary database
- **Redis (Upstash)** — chat session/context storage
- **Duckling** — date/time parsing for scheduling
- **Render** — backend & web hosting
- **Hugging Face Spaces** — AI server hosting

## Testing

```bash
# Backend
cd Eva_Backend_Server && npm test

# AI server
cd Eva_AI_Server && pytest

# Web app
cd Web_Frontend && npm run lint
```

## Deployment

- **Backend** — deployed as a Render web service (`node app.js`).
- **Web app** — deployed as a Render static site (`npm run build`, SPA rewrite).
- **AI server** — containerized (Docker) and deployed to Hugging Face Spaces.
- **Database** — MongoDB Atlas. **Cache** — Redis on Upstash.

## Limitations

- **Custom NLP models are trained on a self-built dataset.** No existing public dataset covered this project's specific intent/entity schema for academic task-and-roadmap planning, so the team designed and generated the training data in-house. As with any custom, relatively small dataset, this means the models may generalize less well to phrasing patterns outside what was represented during data generation — an expected, known tradeoff of building for a genuinely novel task rather than a limitation of the modeling approach itself.
- Chat interface currently supports English only.
- Learning roadmaps are limited to a fixed, curated set of subjects — not arbitrary topics.
- No offline mode; core features require an active internet connection.
- No real-time simultaneous multi-user editing of shared roadmaps (collaboration is invite/visibility-based).
- Mobile app is currently distributed as a direct build, not yet published to app stores.

## Team

| Name | Role |
|---|---|
| **Hamid Shehzad** | Application design & system architecture, backend development, dataset creation & model training, testing (web & mobile), deployment |
| **Areej Fatima** | Mobile app design & development (Flutter) |
| **Muhammad Asim** | Web app design & development (React) |
| **Bareera Ayub** | Complete project documentation, dataset support |

**Supervisor:** Shahbaz Qadeer — Department of Computer Science, School of Systems & Technology, University of Management & Technology, Lahore.
