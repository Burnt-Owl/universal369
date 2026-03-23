import { useState } from 'react'

export default function SettingsPanel() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('oa_api_key') || '')
  const [saved, setSaved] = useState(false)
  const [showKey, setShowKey] = useState(false)

  const saveKey = () => {
    localStorage.setItem('oa_api_key', apiKey.trim())
    setSaved(true)
    window.dispatchEvent(new Event('oa_key_updated'))
    setTimeout(() => setSaved(false), 2500)
  }

  const clearKey = () => {
    localStorage.removeItem('oa_api_key')
    setApiKey('')
    window.dispatchEvent(new Event('oa_key_updated'))
  }

  const clearAllData = () => {
    if (window.confirm('This will delete all tasks, calendar events, chat history, and documents. Continue?')) {
      const key = localStorage.getItem('oa_api_key')
      localStorage.clear()
      if (key) localStorage.setItem('oa_api_key', key)
      window.location.reload()
    }
  }

  const hasKey = !!localStorage.getItem('oa_api_key')

  return (
    <>
      <div className="panel-header">
        <span>⚙️</span>
        <h1>Settings</h1>
      </div>

      <div className="panel-body">
        {/* API Key */}
        <div className="settings-section">
          <h2>Anthropic API Key</h2>
          <p>
            Your API key is stored only in this browser's local storage — it's never sent anywhere except directly to Anthropic's API when you use AI features.
            Get a key at <strong>console.anthropic.com</strong>.
          </p>

          <div className="api-key-field">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-..."
              autoComplete="off"
              spellCheck={false}
            />
            <button className="btn btn-ghost" onClick={() => setShowKey(v => !v)}>
              {showKey ? '🙈 Hide' : '👁 Show'}
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
            <button className="btn btn-primary" onClick={saveKey} disabled={!apiKey.trim()}>
              {saved ? '✓ Saved!' : 'Save Key'}
            </button>
            {hasKey && (
              <button className="btn btn-danger" onClick={clearKey}>Remove Key</button>
            )}
            <span className={`key-status ${hasKey ? 'set' : 'not-set'}`}>
              {hasKey ? '✓ Key is set' : '✗ No key set'}
            </span>
          </div>
        </div>

        {/* About */}
        <div className="settings-section">
          <h2>About</h2>
          <p>
            Office Assistant is an all-in-one productivity app powered by Claude AI. All your data (tasks, events, documents, chat history) is stored locally in your browser.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 13, color: 'var(--text-muted)' }}>
            <span>💬 AI Chat — Claude-powered assistant</span>
            <span>•</span>
            <span>✅ Tasks — priority to-do list</span>
            <span>•</span>
            <span>📅 Calendar — event tracking</span>
            <span>•</span>
            <span>📄 Documents — upload & summarize</span>
          </div>
        </div>

        {/* Danger zone */}
        <div className="settings-section" style={{ borderColor: 'var(--danger)' }}>
          <h2>Danger Zone</h2>
          <p>Clear all app data (tasks, events, chat history, documents). Your API key will be preserved.</p>
          <button className="btn btn-danger" onClick={clearAllData}>
            🗑 Clear All Data
          </button>
        </div>
      </div>
    </>
  )
}
