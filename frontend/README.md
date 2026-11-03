# Frontend — AI Teacher Agent

Next.js 16 + React 19. Consumes the FastAPI backend at `NEXT_PUBLIC_API_URL`
(default `http://localhost:8000`).

```bash
npm install
npm run dev        # http://localhost:3000
npm run build
npm run start
```

## Routes

| Path                  | Purpose                              |
|-----------------------|--------------------------------------|
| `/`                   | session setup (student)              |
| `/project`            | live learning flow (5-phase wizard)  |
| `/student-dashboard`  | student's at-a-glance progress       |
| `/teacher-dashboard`  | project catalog + aggregate stats    |

## Layout

```
app/                UI routes (app router)
components/         Sidebar, TaskCard, ProgressAnimation, RoadmapProgress
lib/api.js          typed-ish REST client; everything routes through here
```

See `../README.md` at repo root for the end-to-end flow and backend setup.
