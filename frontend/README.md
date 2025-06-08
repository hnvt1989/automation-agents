# Automation Agents Frontend

Modern React frontend for the Automation Agents application.

## Environment Configuration

The frontend uses Vite environment variables. Create a `.env` file in the frontend directory:

```bash
cp .env.example .env
```

### Environment Variables

All frontend environment variables must be prefixed with `VITE_` to be accessible in the browser:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Application Configuration
VITE_APP_TITLE=Automation Agents
VITE_APP_VERSION=1.0.0

# Development Configuration
VITE_DEV_MODE=true
VITE_ENABLE_DEVTOOLS=true
```

### Backend Integration

The frontend is designed to work with the backend API server. Make sure to:

1. **Start the backend first:**
   ```bash
   # In the root directory
   uvicorn src.api_server:app --reload
   # OR
   ./run.sh
   ```

2. **Then start the frontend:**
   ```bash
   # In the frontend directory
   npm run dev
   ```

### Configuration vs Backend local.env

| **Backend (local.env)** | **Frontend (.env)** | **Purpose** |
|------------------------|---------------------|-------------|
| `MODEL_CHOICE` | N/A | Server-side only |
| `LLM_API_KEY` | N/A | Server-side only |
| `OPENAI_API_KEY` | N/A | Server-side only |
| N/A | `VITE_API_BASE_URL` | Frontend API endpoint |
| N/A | `VITE_WS_URL` | Frontend WebSocket URL |

The backend's `local.env` contains sensitive API keys and server configuration that should never be exposed to the frontend. The frontend's `.env` only contains safe, public configuration.

## Development Commands

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run E2E tests
npm run test:e2e

# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run type-check
```

## Architecture

- **Vite + React 18 + TypeScript**
- **Zustand** for state management
- **React Router** for navigation
- **Tailwind CSS** for styling
- **Vitest + RTL** for testing
- **Playwright** for E2E testing

## API Integration

The frontend automatically connects to the backend API using the configured environment variables:

- **REST API**: `VITE_API_BASE_URL/api/*`
- **WebSocket**: `VITE_WS_URL`

All API calls are proxied through Vite during development for CORS handling.