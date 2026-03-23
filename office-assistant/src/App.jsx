import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import ChatPanel from './components/Chat/ChatPanel.jsx'
import TaskPanel from './components/Tasks/TaskPanel.jsx'
import CalendarPanel from './components/Calendar/CalendarPanel.jsx'
import DocumentPanel from './components/Documents/DocumentPanel.jsx'
import SettingsPanel from './components/Settings/SettingsPanel.jsx'

const PANELS = {
  chat: ChatPanel,
  tasks: TaskPanel,
  calendar: CalendarPanel,
  documents: DocumentPanel,
  settings: SettingsPanel,
}

export default function App() {
  const [activePanel, setActivePanel] = useState('chat')
  const Panel = PANELS[activePanel]

  return (
    <div className="app-layout">
      <Sidebar active={activePanel} onSelect={setActivePanel} />
      <div className="main-panel">
        <Panel />
      </div>
    </div>
  )
}
