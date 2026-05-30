# AgentBreaker Dashboard

Real-time ops console for AgentBreaker budget enforcement engine.

## Features

- **War Room**: Live session table with real-time burn rate, budget spend ratio, and status
- **Session Drill-Down**: Detailed view with burn timeline, tool call trace, and velocity gauge
- **Alerts Feed**: Real-time breach notifications with filtering and acknowledgement
- **Manual Controls**: Kill sessions, adjust budgets, acknowledge alerts

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** for fast builds and development
- **Tailwind CSS** for styling (ops console aesthetic)
- **Recharts** for real-time visualizations
- **WebSocket** for live updates

## Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint and format
npm run lint
npm run format
```

## Architecture

- **Pages**: WarRoom, SessionDetail, AlertsFeed
- **Hooks**: useWebSocket (bidirectional WebSocket client)
- **Components**: Reusable UI components
- **Store**: Zustand for state management (future)

## Design Language

- **Dark ops console aesthetic**: #050508 base, #00FF88 healthy (green), #FF3D00 critical (red), #FFD600 warning (yellow)
- **Typography**: IBM Plex Mono for numeric data, Archivo Black for headers
- **Layout**: Dense, information-maximalist, no padding, no rounded corners

## Docker

```bash
# Build image
docker build -t agentbreaker-dashboard .

# Run container
docker run -p 3000:80 agentbreaker-dashboard
```

The dashboard proxies `/api` and `/ws` requests to the FastAPI control plane (api:8000 in docker-compose).
