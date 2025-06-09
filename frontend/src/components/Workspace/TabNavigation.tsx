import { CheckSquare, FileText, StickyNote, Calendar, BookOpen } from 'lucide-react'
import { useAppStore } from '@/store'

interface TabNavigationProps {
  activeTab: string
  onTabChange: (tab: string) => void
}

const TabNavigation = ({ activeTab, onTabChange }: TabNavigationProps) => {
  const tasks = useAppStore((state) => state.tasks)
  const documents = useAppStore((state) => state.documents)
  const notes = useAppStore((state) => state.notes)
  const logs = useAppStore((state) => state.logs)
  const memos = useAppStore((state) => (state as any).memos || [])

  // Debug logging
  console.log('TabNavigation Debug:', {
    tasks: tasks?.length || 0,
    documents: documents?.length || 0,
    notes: notes?.length || 0,
    logs: logs?.length || 0,
    memos: memos?.length || 0,
    hasMemos: !!memos
  })

  const tabs = [
    {
      id: 'tasks',
      label: 'Tasks',
      icon: CheckSquare,
      count: tasks.length,
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: FileText,
      count: documents.length,
    },
    {
      id: 'notes',
      label: 'Meeting Notes',
      icon: StickyNote,
      count: notes.length,
    },
    {
      id: 'logs',
      label: 'Daily Logs',
      icon: Calendar,
      count: logs.length,
    },
    {
      id: 'memos',
      label: 'Memos',
      icon: BookOpen,
      count: memos?.length || 0,
    },
  ]

  console.log('TabNavigation tabs:', tabs)

  return (
    <div className="tabs">
      {tabs.map((tab) => {
        const Icon = tab.icon
        return (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
          >
            <Icon size={16} />
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span className="tab-badge">{tab.count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export default TabNavigation