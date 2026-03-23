export default function ChatMessage({ message, streaming = false }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div className={`message-bubble ${streaming ? 'streaming' : ''}`}>
        {message.content}
      </div>
    </div>
  )
}
