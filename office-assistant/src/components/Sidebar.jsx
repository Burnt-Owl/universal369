const NAV = [
  { id: 'chat',      icon: '💬', label: 'AI Chat' },
  { id: 'tasks',     icon: '✅', label: 'Tasks' },
  { id: 'calendar',  icon: '📅', label: 'Calendar' },
  { id: 'documents', icon: '📄', label: 'Documents' },
]

const BOTTOM_NAV = [
  { id: 'settings', icon: '⚙️', label: 'Settings' },
]

export default function Sidebar({ active, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span>🏢</span> Office
      </div>

      <div className="sidebar-section">Workspace</div>

      {NAV.map(item => (
        <button
          key={item.id}
          className={`nav-item ${active === item.id ? 'active' : ''}`}
          onClick={() => onSelect(item.id)}
        >
          <span className="icon">{item.icon}</span>
          {item.label}
        </button>
      ))}

      <div className="sidebar-spacer" />

      {BOTTOM_NAV.map(item => (
        <button
          key={item.id}
          className={`nav-item ${active === item.id ? 'active' : ''}`}
          onClick={() => onSelect(item.id)}
        >
          <span className="icon">{item.icon}</span>
          {item.label}
        </button>
      ))}
    </aside>
  )
}
