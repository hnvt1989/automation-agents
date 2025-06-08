import { CheckSquare, FileText, StickyNote, Calendar, Settings } from 'lucide-react'
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
      label: 'Notes',
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
      id: 'configuration',
      label: 'Settings',
      icon: Settings,
      count: 0,
    },
  ]

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