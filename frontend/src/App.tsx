import { useEffect } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useTasks, useDocuments, useNotes, useLogs, useMemos, useConfig } from '@/hooks/useApi'
import Chat from '@/components/Chat'
import Workspace from '@/components/Workspace'
import ErrorBoundary from '@/components/common/ErrorBoundary'
import ErrorNotifications from '@/components/common/ErrorNotifications'
import BackendStatus from '@/components/common/BackendStatus'

function App() {
  const { isConnected } = useWebSocket()
  const { fetchTasks } = useTasks()
  const { fetchDocuments } = useDocuments()
  const { fetchNotes } = useNotes()
  const { fetchLogs } = useLogs()
  const { fetchMemos } = useMemos()
  const { fetchConfig } = useConfig()

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // Try to load data, but don't fail if backend is unavailable
        await Promise.allSettled([
          fetchTasks(),
          fetchDocuments(),
          fetchNotes(),
          fetchLogs(),
          fetchMemos(),
          fetchConfig(),
        ])
      } catch (error) {
        console.warn('Some initial data failed to load:', error)
      }
    }

    loadInitialData()
  }, [fetchTasks, fetchDocuments, fetchNotes, fetchLogs, fetchMemos, fetchConfig])

  return (
    <ErrorBoundary>
      <div className="container">
        <Chat />
        <Workspace />
        <ErrorNotifications />
        
        {/* Backend and connection status */}
        <div
          style={{
            position: 'fixed',
            top: 16,
            right: 16,
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <BackendStatus />
          {!isConnected && (
            <div
              style={{
                background: '#dc3545',
                color: 'white',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '14px',
              }}
            >
              WebSocket disconnected - attempting to reconnect...
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}

export default App