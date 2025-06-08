// Frontend configuration using Vite environment variables
// Only variables prefixed with VITE_ are exposed to the client

interface AppConfig {
  api: {
    baseUrl: string
    timeout: number
  }
  websocket: {
    url: string
    reconnectAttempts: number
    reconnectDelay: number
  }
  app: {
    title: string
    version: string
  }
  development: {
    devMode: boolean
    enableDevtools: boolean
  }
}

const config: AppConfig = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || '',
    timeout: 10000,
  },
  websocket: {
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
    reconnectAttempts: 5,
    reconnectDelay: 1000,
  },
  app: {
    title: import.meta.env.VITE_APP_TITLE || 'Automation Agents',
    version: import.meta.env.VITE_APP_VERSION || '1.0.0',
  },
  development: {
    devMode: import.meta.env.VITE_DEV_MODE === 'true' || import.meta.env.DEV,
    enableDevtools: import.meta.env.VITE_ENABLE_DEVTOOLS === 'true' || import.meta.env.DEV,
  },
}

export default config

// Helper functions for common config access
export const getApiUrl = (endpoint: string = '') => {
  const baseUrl = config.api.baseUrl.endsWith('/') 
    ? config.api.baseUrl.slice(0, -1) 
    : config.api.baseUrl
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${baseUrl}${cleanEndpoint}`
}

export const getWebSocketUrl = () => {
  return config.websocket.url
}

export const isDevelopment = () => {
  return config.development.devMode
}

export const isDevtoolsEnabled = () => {
  return config.development.enableDevtools
}

// Environment validation (warn about missing variables in development)
if (isDevelopment()) {
  const requiredVars = [
    'VITE_API_BASE_URL',
    'VITE_WS_URL',
  ]
  
  const missingVars = requiredVars.filter(varName => !import.meta.env[varName])
  
  if (missingVars.length > 0) {
    console.warn('Missing environment variables:', missingVars)
    console.warn('Using default values. Create a .env file with VITE_ prefixed variables.')
  }
}

// Type definitions for Vite env
declare global {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string
    readonly VITE_WS_URL: string
    readonly VITE_APP_TITLE: string
    readonly VITE_APP_VERSION: string
    readonly VITE_DEV_MODE: string
    readonly VITE_ENABLE_DEVTOOLS: string
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv
  }
}