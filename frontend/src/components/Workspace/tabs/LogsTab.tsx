import { useState, useMemo } from 'react'
import { Plus, Edit2, Trash2, Calendar, Check } from 'lucide-react'
import { useAppStore } from '@/store'
import { useLogs } from '@/hooks/useApi'
import { getStatusColor, formatRelativeTime } from '@/utils'
import type { DailyLog } from '@/types'

const LogsTab = () => {
  const { logs, updateLog, deleteLog, loading } = useLogs()
  const { setModal } = useAppStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [tagFilter, setTagFilter] = useState('all')
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())

  // Filter and search logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch = log.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          log.content?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesTag = tagFilter === 'all' || (log.tags && log.tags.includes(tagFilter))
      
      return matchesSearch && matchesTag
    })
  }, [logs, searchQuery, tagFilter])

  const handleAddLog = () => {
    setModal({
      isOpen: true,
      mode: 'add',
      item: {
        id: '',
        name: '',
        description: '',
        type: 'log',
        date: new Date(),
        content: '',
        lastModified: new Date(),
        mood: 'neutral',
        productivity: 5,
      } as DailyLog,
    })
  }

  const handleEditLog = (log: DailyLog) => {
    setModal({
      isOpen: true,
      mode: 'edit',
      item: log,
    })
  }

  const handleDeleteLog = async (logId: string) => {
    if (confirm('Are you sure you want to delete this log?')) {
      await deleteLog(logId)
    }
  }

  const handleSelectItem = (logId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(logId)) {
      newSelected.delete(logId)
    } else {
      newSelected.add(logId)
    }
    setSelectedItems(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedItems.size === filteredLogs.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(filteredLogs.map(log => log.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (confirm(`Are you sure you want to delete ${selectedItems.size} logs?`)) {
      await Promise.all(Array.from(selectedItems).map(id => deleteLog(id)))
      setSelectedItems(new Set())
    }
  }

  const totalLogs = logs.length

  return (
    <div className="items-list">
      <div className="items-header">
        <div className="items-count">
          {filteredLogs.length} logs
          {filteredLogs.length !== totalLogs && ` (${totalLogs} total)`}
        </div>
        <button className="add-button" onClick={handleAddLog}>
          <Plus size={16} />
          Add Log
        </button>
      </div>

      <div className="search-filters">
        <input
          type="text"
          placeholder="Search logs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        
        <select
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Tags</option>
          <option value="personal">Personal</option>
          <option value="work">Work</option>
        </select>
      </div>

      {selectedItems.size > 0 && (
        <div className="bulk-actions">
          <span className="bulk-actions-text">
            {selectedItems.size} selected
          </span>
          <button
            className="bulk-action-button danger"
            onClick={handleBulkDelete}
          >
            Delete Selected
          </button>
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner" />
          <span>Loading logs...</span>
        </div>
      )}

      {!loading && filteredLogs.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <Calendar size={32} />
          </div>
          <h3 className="empty-state-title">
            {logs.length === 0 ? 'No logs yet' : 'No logs match your filters'}
          </h3>
          <p className="empty-state-description">
            {logs.length === 0 
              ? 'Get started by creating your first daily log to track your activities and progress.'
              : 'Try adjusting your search or filter criteria to find the logs you\'re looking for.'
            }
          </p>
          {logs.length === 0 && (
            <button className="btn btn-primary" onClick={handleAddLog}>
              <Plus size={16} />
              Create Your First Log
            </button>
          )}
        </div>
      )}

      {!loading && filteredLogs.length > 0 && (
        <>
          <div className="list-header">
            <label className="select-all-checkbox">
              <input
                type="checkbox"
                checked={selectedItems.size === filteredLogs.length}
                onChange={handleSelectAll}
              />
              Select All
            </label>
          </div>

          {filteredLogs.map((log) => (
            <div
              key={log.id}
              className={`workspace-item ${selectedItems.has(log.id) ? 'selected' : ''}`}
              data-testid="log-item"
            >
              <div
                className={`item-checkbox ${selectedItems.has(log.id) ? 'checked' : ''}`}
                onClick={() => handleSelectItem(log.id)}
              >
                {selectedItems.has(log.id) && <Check size={12} />}
              </div>

              <div className="item-icon log">
                <Calendar size={20} />
              </div>

              <div className="item-content">
                <div className="item-title">{log.name}</div>
                {log.description && (
                  <div className="item-description">{log.description}</div>
                )}
                {log.content && (
                  <div className="item-content-preview">{log.content.substring(0, 100)}{log.content.length > 100 ? '...' : ''}</div>
                )}
                <div className="item-meta">
                  {log.mood && (
                    <span className={`item-mood ${log.mood}`}>
                      {log.mood}
                    </span>
                  )}
                  {log.productivity && (
                    <span className="item-productivity">
                      Productivity: {log.productivity}/10
                    </span>
                  )}
                  <span>Updated {formatRelativeTime(log.lastModified)}</span>
                  {log.tags && log.tags.length > 0 && (
                    <span className="item-tags">
                      {log.tags.map(tag => (
                        <span key={tag} className="tag">{tag}</span>
                      ))}
                    </span>
                  )}
                </div>
              </div>

              <div className="item-actions">
                <button
                  className="item-action-button"
                  onClick={() => handleEditLog(log)}
                  title="Edit log"
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="item-action-button danger"
                  onClick={() => handleDeleteLog(log.id)}
                  title="Delete log"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

export default LogsTab