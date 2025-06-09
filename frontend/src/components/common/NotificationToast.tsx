import React, { useEffect } from 'react'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'

export type NotificationType = 'success' | 'error' | 'info'

interface NotificationToastProps {
  id: string
  message: string
  type: NotificationType
  onClose: (id: string) => void
  duration?: number
}

export const NotificationToast: React.FC<NotificationToastProps> = ({
  id,
  message,
  type,
  onClose,
  duration = 5000
}) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(id)
      }, duration)
      
      return () => clearTimeout(timer)
    }
  }, [id, duration, onClose])

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} />
      case 'error':
        return <AlertCircle size={20} />
      case 'info':
        return <Info size={20} />
    }
  }

  const getClassName = () => {
    const base = 'notification-toast'
    switch (type) {
      case 'success':
        return `${base} toast-success`
      case 'error':
        return `${base} toast-error`
      case 'info':
        return `${base} toast-info`
    }
  }

  return (
    <div className={getClassName()} role="alert" aria-live="polite">
      <div className="toast-icon">
        {getIcon()}
      </div>
      <div className="toast-message">
        {message}
      </div>
      <button
        className="toast-close"
        onClick={() => onClose(id)}
        aria-label="Close notification"
      >
        <X size={16} />
      </button>
    </div>
  )
}

export default NotificationToast