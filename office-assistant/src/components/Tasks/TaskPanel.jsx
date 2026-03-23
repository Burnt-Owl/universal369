import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage.js'
import TaskItem from './TaskItem.jsx'

const PRIORITIES = ['low', 'medium', 'high']
const FILTERS = ['all', 'pending', 'done', 'high', 'medium', 'low']

export default function TaskPanel() {
  const [tasks, setTasks] = useLocalStorage('oa_tasks', [])
  const [filter, setFilter] = useState('all')
  const [form, setForm] = useState({ title: '', priority: 'medium', due: '' })

  const addTask = (e) => {
    e.preventDefault()
    if (!form.title.trim()) return
    setTasks(prev => [
      { id: Date.now(), title: form.title.trim(), priority: form.priority, due: form.due, done: false, createdAt: new Date().toISOString() },
      ...prev,
    ])
    setForm({ title: '', priority: 'medium', due: '' })
  }

  const toggleDone = (id) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t))
  }

  const deleteTask = (id) => {
    setTasks(prev => prev.filter(t => t.id !== id))
  }

  const filtered = tasks.filter(t => {
    if (filter === 'all') return true
    if (filter === 'pending') return !t.done
    if (filter === 'done') return t.done
    return t.priority === filter
  })

  const pendingCount = tasks.filter(t => !t.done).length

  return (
    <>
      <div className="panel-header">
        <span>✅</span>
        <h1>Tasks</h1>
        {pendingCount > 0 && (
          <span className="subtitle">— {pendingCount} pending</span>
        )}
      </div>

      <div className="panel-body">
        {/* Add task form */}
        <form className="task-form" onSubmit={addTask}>
          <div className="form-row">
            <div className="field">
              <label>Task title</label>
              <input
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="What needs to be done?"
                autoFocus
              />
            </div>
          </div>
          <div className="form-row cols-3">
            <div className="field">
              <label>Priority</label>
              <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                {PRIORITIES.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Due date</label>
              <input
                type="date"
                value={form.due}
                onChange={e => setForm(f => ({ ...f, due: e.target.value }))}
              />
            </div>
            <div className="field" style={{ justifyContent: 'flex-end' }}>
              <label>&nbsp;</label>
              <button type="submit" className="btn btn-primary" disabled={!form.title.trim()}>
                + Add Task
              </button>
            </div>
          </div>
        </form>

        {/* Filters */}
        <div className="task-filters">
          {FILTERS.map(f => (
            <button
              key={f}
              className={`filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Task list */}
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✅</div>
            <p>{tasks.length === 0 ? 'No tasks yet — add one above.' : 'No tasks match this filter.'}</p>
          </div>
        ) : (
          filtered.map(task => (
            <TaskItem
              key={task.id}
              task={task}
              onToggle={toggleDone}
              onDelete={deleteTask}
            />
          ))
        )}
      </div>
    </>
  )
}
