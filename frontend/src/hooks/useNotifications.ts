import { create } from 'zustand'
import { NotificationType } from '@/components/common/NotificationToast'

interface Notification {
  id: string
  message: string
  type: NotificationType
  duration?: number
}

interface NotificationStore {
  notifications: Notification[]
  addNotification: (message: string, type: NotificationType, duration?: number) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

export const useNotifications = create<NotificationStore>((set) => ({
  notifications: [],
  
  addNotification: (message, type, duration = 5000) => {
    const id = crypto.randomUUID()
    set((state) => ({
      notifications: [...state.notifications, { id, message, type, duration }]
    }))
  },
  
  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter(n => n.id !== id)
    }))
  },
  
  clearNotifications: () => {
    set({ notifications: [] })
  }
}))

// Convenience hooks
export const useSuccess = () => {
  const { addNotification } = useNotifications()
  return (message: string, duration?: number) => 
    addNotification(message, 'success', duration)
}

export const useError = () => {
  const { addNotification } = useNotifications()
  return (message: string, duration?: number) => 
    addNotification(message, 'error', duration)
}

export const useInfo = () => {
  const { addNotification } = useNotifications()
  return (message: string, duration?: number) => 
    addNotification(message, 'info', duration)
}