# Management UI Frontend

React frontend for the local-ai-packaged management interface.

## Features

- Dashboard with system overview and service status
- Service management with group filtering
- Interactive dependency visualization (React Flow)
- Real-time log viewer with WebSocket streaming
- Configuration editor with validation
- Setup wizard for first-time configuration
- Dark theme UI

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Zustand (state management)
- React Router
- React Flow (dependency graph)
- Lucide React (icons)

## Installation

```bash
npm install
```

## Development

```bash
# Start dev server (hot reload)
npm run dev

# The frontend expects the backend at http://localhost:8000
# Configure proxy in vite.config.ts if needed
```

## Building

```bash
# Type check and build
npm run build

# Preview production build
npm run preview
```

## Linting

```bash
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client functions
│   │   ├── auth.ts       # Authentication API
│   │   ├── client.ts     # Axios instance
│   │   ├── config.ts     # Configuration API
│   │   ├── services.ts   # Services API
│   │   └── websocket.ts  # WebSocket utilities
│   ├── components/
│   │   ├── common/       # Shared UI components
│   │   ├── config/       # Configuration components
│   │   ├── layout/       # Layout components
│   │   ├── logs/         # Log viewer components
│   │   ├── services/     # Service management components
│   │   └── setup/        # Setup wizard components
│   ├── hooks/            # Custom React hooks
│   ├── pages/            # Page components
│   ├── store/            # Zustand stores
│   ├── types/            # TypeScript types
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Dashboard | System overview, quick stats |
| `/services` | Services | Service list with controls |
| `/dependencies` | Dependencies | Interactive dependency graph |
| `/config` | Configuration | .env editor with validation |
| `/logs` | Logs | Real-time log streaming |
| `/setup-wizard` | SetupWizard | Guided first-time setup |
| `/login` | Login | Authentication |
| `/setup` | Setup | Initial admin account creation |

## Environment Variables

Create a `.env` file for local development:

```env
VITE_API_URL=http://localhost:8000/api
```
