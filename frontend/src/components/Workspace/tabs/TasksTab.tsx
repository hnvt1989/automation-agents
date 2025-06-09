import { useState, useMemo, useEffect } from 'react'
import { Plus, Edit2, Trash2, Check } from 'lucide-react'
import { useAppStore } from '@/store'
import { useTasks } from '@/hooks/useApi'
import { getStatusColor, formatRelativeTime } from '@/utils'
import type { Task } from '@/types'

const TasksTab = () => {
  const { tasks, fetchTasks, updateTask, deleteTask, loading } = useTasks()
  const { setModal } = useAppStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [completionStateFilter, setCompletionStateFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [sortBy, setSortBy] = useState('lastModified')
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())

  // Fetch tasks on mount
  useEffect(() => {
    fetchTasks()
  }, [])

  // Filter and search tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks.filter((task) => {
      const matchesSearch = task.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          task.description?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus = statusFilter === 'all' || task.status === statusFilter
      
      // Completion state filter logic
      let matchesCompletionState = true
      if (completionStateFilter === 'active') {
        matchesCompletionState = task.status === 'todo' || task.status === 'in_progress'
      } else if (completionStateFilter === 'done') {
        matchesCompletionState = task.status === 'completed' || task.status === 'cancelled'
      }
      
      const matchesPriority = priorityFilter === 'all' || task.priority === priorityFilter
      const matchesType = typeFilter === 'all' || (task.tags && task.tags.includes(typeFilter))
      
      return matchesSearch && matchesStatus && matchesCompletionState && matchesPriority && matchesType
    })

    // Sort tasks
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'priority-desc':
          const priorityOrder = { high: 3, medium: 2, low: 1 }
          return priorityOrder[b.priority] - priorityOrder[a.priority]
        case 'priority-asc':
          const priorityOrderAsc = { high: 3, medium: 2, low: 1 }
          return priorityOrderAsc[a.priority] - priorityOrderAsc[b.priority]
        case 'name':
          return a.name.localeCompare(b.name)
        case 'lastModified':
        default:
          return new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime()
      }
    })

    return filtered
  }, [tasks, searchQuery, statusFilter, completionStateFilter, priorityFilter, typeFilter, sortBy])

  const handleAddTask = () => {
    setModal({
      isOpen: true,
      mode: 'add',
      contentType: 'task',
    })
  }

  const handleEditTask = (task: Task) => {
    setModal({
      isOpen: true,
      mode: 'edit',
      item: task,
      contentType: 'task',
    })
  }

  const handleDeleteTask = async (taskId: string) => {
    // Find the task in the current tasks array
    const taskToDelete = tasks.find(t => t.id === taskId)
    console.log('=== FRONTEND DELETE DEBUG ===')
    console.log('Task to delete:', taskToDelete)
    console.log('Task ID:', taskId)
    console.log('Task ID type:', typeof taskId)
    console.log('Task ID JSON:', JSON.stringify(taskId))
    console.log('Current tasks in frontend:', tasks.map(t => ({ id: t.id, name: t.name })))
    console.log('Stack trace:')
    console.trace()
    
    if (confirm(`Are you sure you want to delete this task?\n\nTask: ${taskToDelete?.name || 'Unknown'}\nID: ${taskId}`)) {
      console.log('About to call deleteTask with ID:', taskId)
      await deleteTask(taskId)
      // Refresh tasks after deletion to ensure sync
      await fetchTasks()
    }
  }

  const handleToggleComplete = async (task: Task) => {
    const newStatus = task.status === 'completed' ? 'todo' : 'completed'
    await updateTask(task.id, { status: newStatus })
  }

  const handleSelectItem = (taskId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId)
    } else {
      newSelected.add(taskId)
    }
    setSelectedItems(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedItems.size === filteredTasks.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(filteredTasks.map(task => task.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (confirm(`Are you sure you want to delete ${selectedItems.size} tasks?`)) {
      await Promise.all(Array.from(selectedItems).map(id => deleteTask(id)))
      setSelectedItems(new Set())
    }
  }

  const completedTasks = tasks.filter(task => task.status === 'completed').length
  const totalTasks = tasks.length

  return (
    <div className="items-list">
      <div className="items-header">
        <div className="items-count">
          {totalTasks} tasks ({completedTasks} completed)
        </div>
        <button className="add-button" onClick={handleAddTask}>
          <Plus size={16} />
          Add Task
        </button>
      </div>

      <div className="search-filters">
        <input
          type="text"
          placeholder="Search tasks..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        
        <select
          value={completionStateFilter}
          onChange={(e) => setCompletionStateFilter(e.target.value)}
          className="filter-select"
          data-testid="completion-state-filter"
        >
          <option value="all">All Tasks</option>
          <option value="active">Active</option>
          <option value="done">Done</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Status</option>
          <option value="todo">To Do</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Priority</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Types</option>
          <option value="personal">Personal</option>
          <option value="work">Work</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="filter-select"
        >
          <option value="lastModified">Last Modified</option>
          <option value="name">Name</option>
          <option value="priority-desc">Priority (High to Low)</option>
          <option value="priority-asc">Priority (Low to High)</option>
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
          <span>Loading tasks...</span>
        </div>
      )}

      {!loading && filteredTasks.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <Check size={32} />
          </div>
          <h3 className="empty-state-title">
            {tasks.length === 0 ? 'No tasks yet' : 'No tasks match your filters'}
          </h3>
          <p className="empty-state-description">
            {tasks.length === 0 
              ? 'Get started by creating your first task to track your work and stay organized.'
              : 'Try adjusting your search or filter criteria to find the tasks you\'re looking for.'
            }
          </p>
          {tasks.length === 0 && (
            <button className="btn btn-primary" onClick={handleAddTask}>
              <Plus size={16} />
              Create Your First Task
            </button>
          )}
        </div>
      )}

      {!loading && filteredTasks.length > 0 && (
        <>
          <div className="list-header">
            <label className="select-all-checkbox">
              <input
                type="checkbox"
                checked={selectedItems.size === filteredTasks.length}
                onChange={handleSelectAll}
              />
              Select All
            </label>
          </div>

          {filteredTasks.map((task) => (
            <div
              key={task.id}
              className={`workspace-item ${selectedItems.has(task.id) ? 'selected' : ''}`}
              data-testid="task-item"
            >
              <div
                className={`item-checkbox ${selectedItems.has(task.id) ? 'checked' : ''}`}
                onClick={() => handleSelectItem(task.id)}
              >
                {selectedItems.has(task.id) && <Check size={12} />}
              </div>

              <div className="item-icon task">
                <Check size={20} />
              </div>

              <div className="item-content">
                <div className="item-title">{task.name}</div>
                {task.description && (
                  <div className="item-description">{task.description}</div>
                )}
                {task.todo && (
                  <div className="item-description" style={{ marginTop: '8px', fontStyle: 'italic' }}>
                    TODO: {task.todo.substring(0, 100)}{task.todo.length > 100 ? '...' : ''}
                  </div>
                )}
                <div className="item-meta">
                  <span className={`item-status ${getStatusColor(task.status)}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                  <span className={`item-priority ${getStatusColor(task.priority)}`}>
                    {task.priority}
                  </span>
                  <span>Updated {formatRelativeTime(task.lastModified)}</span>
                  {task.dueDate && (
                    <span>Due {formatRelativeTime(task.dueDate)}</span>
                  )}
                </div>
              </div>

              <div className="item-actions">
                <button
                  className="item-action-button"
                  onClick={() => handleToggleComplete(task)}
                  title={task.status === 'completed' ? 'Mark incomplete' : 'Mark complete'}
                >
                  <Check size={16} />
                </button>
                <button
                  className="item-action-button"
                  onClick={() => handleEditTask(task)}
                  title="Edit task"
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="item-action-button danger"
                  onClick={() => handleDeleteTask(task.id)}
                  title="Delete task"
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

export default TasksTab