import { useState, useRef, useEffect } from 'react'
import { useClaude } from '../../hooks/useClaude.js'
import { useLocalStorage } from '../../hooks/useLocalStorage.js'
import ChatMessage from './ChatMessage.jsx'

const SYSTEM = `You are a helpful, efficient office assistant. You help with tasks like:
- Drafting emails, memos, and reports
- Summarizing documents and meeting notes
- Answering questions and providing research
- Brainstorming ideas and solving problems
- Proofreading and editing text

Be concise, professional, and practical. Format your responses clearly.`

export default function ChatPanel() {
  const [messages, setMessages] = useLocalStorage('oa_chat_history', [])
  const [input, setInput] = useState('')
  const [streamingText, setStreamingText] = useState('')
  const { send, loading, error } = useClaude()
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text, id: Date.now() }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setStreamingText('')

    // Build messages for API (role + content only)
    const apiMessages = nextMessages.map(({ role, content }) => ({ role, content }))

    let accumulated = ''
    await send({
      messages: apiMessages,
      system: SYSTEM,
      onChunk: (_, full) => {
        accumulated = full
        setStreamingText(full)
      },
      onDone: (full) => {
        setStreamingText('')
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: full, id: Date.now() },
        ])
      },
    })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    if (window.confirm('Clear the entire conversation?')) {
      setMessages([])
    }
  }

  const noKey = !localStorage.getItem('oa_api_key')

  return (
    <div className="chat-layout">
      <div className="panel-header">
        <span>💬</span>
        <h1>AI Chat</h1>
        <span className="subtitle">— powered by Claude</span>
        <div className="panel-header-actions">
          {messages.length > 0 && (
            <button className="btn btn-ghost" onClick={clearChat}>Clear</button>
          )}
        </div>
      </div>

      {noKey && (
        <div style={{ padding: '0 28px', paddingTop: 14 }}>
          <div className="no-key-banner">
            ⚠️ No API key set — go to <strong style={{ margin: '0 3px' }}>Settings</strong> to enter your Anthropic key.
          </div>
        </div>
      )}

      <div className="messages-area">
        {messages.length === 0 && !streamingText && (
          <div className="empty-state" style={{ margin: 'auto' }}>
            <div className="empty-icon">💬</div>
            <p>Ask me anything — drafting, summarizing, research, or general help.</p>
          </div>
        )}

        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {streamingText && (
          <ChatMessage
            message={{ role: 'assistant', content: streamingText }}
            streaming
          />
        )}

        {error && (
          <div style={{ color: 'var(--danger)', fontSize: 13, padding: '8px 0' }}>
            ⚠️ {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
            rows={2}
            disabled={loading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            title="Send"
          >
            {loading ? '⏳' : '➤'}
          </button>
        </div>
      </div>
    </div>
  )
}
