import { useAppStore } from '@/store'
import { X } from 'lucide-react'

const ErrorNotifications = () => {
  const { errors, removeError, clearErrors } = useAppStore()

  if (errors.length === 0) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: '16px',
        right: '16px',
        zIndex: 1000,
        maxWidth: '400px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      {errors.length > 1 && (
        <button
          className="btn btn-sm btn-outline"
          onClick={clearErrors}
          style={{ alignSelf: 'flex-end' }}
        >
          Clear All
        </button>
      )}
      
      {errors.map((error) => (
        <div
          key={error.code}
          className="error-message"
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {error.code}
            </div>
            <div>{error.message}</div>
            <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.8 }}>
              {new Date(error.timestamp).toLocaleTimeString()}
            </div>
          </div>
          
          <button
            onClick={() => removeError(error.code)}
            style={{
              background: 'none',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Dismiss error"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default ErrorNotifications