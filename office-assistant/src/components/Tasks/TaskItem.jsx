export default function TaskItem({ task, onToggle, onDelete }) {
  const due = task.due ? new Date(task.due + 'T00:00:00') : null
  const isOverdue = due && !task.done && due < new Date()

  return (
    <div className={`task-item ${task.done ? 'done' : ''}`}>
      <button
        className={`task-checkbox ${task.done ? 'checked' : ''}`}
        onClick={() => onToggle(task.id)}
        title={task.done ? 'Mark incomplete' : 'Mark complete'}
      >
        {task.done ? '✓' : ''}
      </button>

      <div className="task-content">
        <div className="task-title">{task.title}</div>
        <div className="task-meta">
          <span className={`badge badge-${task.priority}`}>{task.priority}</span>
          {due && (
            <span style={{ color: isOverdue ? 'var(--danger)' : 'var(--text-muted)' }}>
              {isOverdue ? '⚠️ ' : ''}
              {due.toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      <button
        className="task-delete"
        onClick={() => onDelete(task.id)}
        title="Delete task"
      >
        ×
      </button>
    </div>
  )
}
