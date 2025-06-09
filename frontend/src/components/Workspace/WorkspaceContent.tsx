import { lazy, Suspense } from 'react'
import LoadingSpinner from '@/components/common/LoadingSpinner'

// Lazy load tab components for better performance
const TasksTab = lazy(() => import('./tabs/TasksTab'))
const DocumentsTab = lazy(() => import('./tabs/DocumentsTab'))
const NotesTab = lazy(() => import('./tabs/NotesTab'))
const LogsTab = lazy(() => import('./tabs/LogsTab'))

interface WorkspaceContentProps {
  activeTab: string
}

const WorkspaceContent = ({ activeTab }: WorkspaceContentProps) => {
  const renderTabContent = () => {
    switch (activeTab) {
      case 'tasks':
        return <TasksTab />
      case 'documents':
        return <DocumentsTab />
      case 'notes':
        return <NotesTab />
      case 'logs':
        return <LogsTab />
      default:
        return <TasksTab />
    }
  }

  return (
    <Suspense 
      fallback={
        <div className="loading-container">
          <LoadingSpinner />
          <span>Loading...</span>
        </div>
      }
    >
      {renderTabContent()}
    </Suspense>
  )
}

export default WorkspaceContent