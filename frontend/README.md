# Kranti P1 - Frontend

This is the Next.js 15 frontend for the Kranti P1 Project Controls intelligence layer (SIH26122).

## Unified Dashboard
The UI has been consolidated into a single powerful dashboard located at `app/page.tsx` that provides:
1. **Interactive Gantt Chart**: A timeline view of the project schedule, auto-adjusting to the XER baseline dates.
2. **Review Queue**: A confidence-gated queue of incoming events parsed by the AI.
3. **Ingestion Feed**: A live feed of incoming field messages (WhatsApp, Site Diaries, etc).

## Getting Started

First, ensure the backend services are running.
Then, run the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to access the dashboard.
To select a project, start at [http://localhost:3000/navigator](http://localhost:3000/navigator).
