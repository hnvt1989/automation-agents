import React from 'react'
import { useNotifications } from '@/hooks/useNotifications'
import NotificationToast from './NotificationToast'

export const NotificationContainer: React.FC = () => {
  const { notifications, removeNotification } = useNotifications()

  if (notifications.length === 0) return null

  return (
    <div className="notification-container" role="region" aria-label="Notifications">
      {notifications.map((notification) => (
        <NotificationToast
          key={notification.id}
          id={notification.id}
          message={notification.message}
          type={notification.type}
          duration={notification.duration}
          onClose={removeNotification}
        />
      ))}
    </div>
  )
}

export default NotificationContainer