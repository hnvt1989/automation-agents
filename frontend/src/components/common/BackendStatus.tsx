import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, Loader } from 'lucide-react'
import { apiClient } from '@/services/api'

interface BackendStatusProps {
  className?: string
}

const BackendStatus = ({ className = '' }: BackendStatusProps) => {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [lastCheck, setLastCheck] = useState<Date>(new Date())

  const checkBackendStatus = async () => {
    setStatus('checking')
    try {
      // Try a simple health check - test if backend is responding
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      
      await fetch('/tasks', { 
        method: 'GET',
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)
      setStatus('online')
    } catch (error) {
      console.warn('Backend health check failed:', error)
      setStatus('offline')
    }
    setLastCheck(new Date())
  }

  useEffect(() => {
    // Initial check
    checkBackendStatus()

    // Check every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000)

    return () => clearInterval(interval)
  }, [])

  const getStatusConfig = () => {
    switch (status) {
      case 'online':
        return {
          icon: CheckCircle,
          color: 'text-green-600 bg-green-50 border-green-200',
          message: 'Backend connected',
        }
      case 'offline':
        return {
          icon: AlertCircle,
          color: 'text-red-600 bg-red-50 border-red-200',
          message: 'Backend unavailable',
        }
      case 'checking':
        return {
          icon: Loader,
          color: 'text-blue-600 bg-blue-50 border-blue-200',
          message: 'Checking connection...',
        }
    }
  }

  const { icon: Icon, color, message } = getStatusConfig()

  if (status === 'online') {
    return null // Don't show when everything is working
  }

  return (
    <div className={`${className}`}>
      <div
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium
          ${color}
        `}
      >
        <Icon 
          size={16} 
          className={status === 'checking' ? 'animate-spin' : ''}
        />
        <span>{message}</span>
        {status === 'offline' && (
          <button
            onClick={checkBackendStatus}
            className="ml-2 px-2 py-1 text-xs bg-white rounded border hover:bg-gray-50"
          >
            Retry
          </button>
        )}
      </div>
      
      {status === 'offline' && (
        <div className="mt-2 text-xs text-gray-600">
          <p>To fix this issue:</p>
          <ol className="mt-1 ml-4 list-decimal">
            <li>Start the backend server: <code>uvicorn src.api_server:app --reload</code></li>
            <li>Or use the run script: <code>./run.sh</code></li>
          </ol>
        </div>
      )}
    </div>
  )
}

export default BackendStatus