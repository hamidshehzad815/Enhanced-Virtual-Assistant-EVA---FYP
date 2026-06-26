# Analytics Page — Build Checklist

Full API reference: [`ANALYTICS_DASHBOARD_API.md`](ANALYTICS_DASHBOARD_API.md)

## Backend — Done

Single API: `GET /api/analytics/dashboard?days=7|30|90`

| Section | Dashboard key |
|---------|---------------|
| Hero cards | `hero` |
| Behavioral (AI) | `behavioral` |
| Heatmap | `heatmap` |
| Tasks | `tasks` |
| Completion trend (3 weeks) | `completion_trend` |
| Best slots (top 3) | `best_slots` |

## Removed from backend

- Insights block
- Learning, top subjects, duration efficiency
- All other `/api/analytics/*` routes

## Phase 2 — Web UI (`Web/` folder)

Pending — consume `GET /api/analytics/dashboard` only.

## Demo data

```bash
cd Eva_Backend_Server
node scripts/seed-areej-behavioral-analytics.js --clean
```
