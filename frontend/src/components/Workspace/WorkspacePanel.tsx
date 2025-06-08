import { useAppStore } from '@/store'
import TabNavigation from './TabNavigation'
import WorkspaceContent from './WorkspaceContent'
import './styles.css'

const WorkspacePanel = () => {
  const activeTab = useAppStore((state) => state.activeTab)
  const setActiveTab = useAppStore((state) => state.setActiveTab)

  return (
    <div className="workspace-panel">
      <div className="workspace-header">
        <div className="workspace-title">Workspace</div>
        <TabNavigation 
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>
      <div className="workspace-content">
        <WorkspaceContent activeTab={activeTab} />
      </div>
    </div>
  )
}

export default WorkspacePanel