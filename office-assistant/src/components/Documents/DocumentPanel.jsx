import { useState, useRef } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage.js'
import { streamClaude } from '../../hooks/useClaude.js'

const SUPPORTED = ['.txt', '.md', '.csv', '.json', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.py', '.pdf']

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  const map = { pdf: '📕', txt: '📄', md: '📝', csv: '📊', json: '🗂️', js: '🟨', ts: '🔷', py: '🐍', html: '🌐' }
  return map[ext] || '📄'
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DocumentPanel() {
  const [docs, setDocs] = useLocalStorage('oa_docs', [])
  const [summaries, setSummaries] = useState({})
  const [summarizing, setSummarizing] = useState({})
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const readFile = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = e => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(file)
    })

  const processFiles = async (files) => {
    for (const file of files) {
      try {
        const content = await readFile(file)
        const doc = {
          id: Date.now() + Math.random(),
          name: file.name,
          size: file.size,
          type: file.type,
          content: content.slice(0, 50000), // limit to 50k chars
          addedAt: new Date().toISOString(),
        }
        setDocs(prev => [doc, ...prev])
      } catch {
        alert(`Could not read file: ${file.name}`)
      }
    }
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setDragOver(false)
    await processFiles([...e.dataTransfer.files])
  }

  const handleFileInput = async (e) => {
    await processFiles([...e.target.files])
    e.target.value = ''
  }

  const deleteDoc = (id) => {
    setDocs(prev => prev.filter(d => d.id !== id))
    setSummaries(prev => { const n = { ...prev }; delete n[id]; return n })
  }

  const summarize = async (doc) => {
    setSummarizing(prev => ({ ...prev, [doc.id]: true }))
    setSummaries(prev => ({ ...prev, [doc.id]: '' }))

    // Sanitize filename before embedding in prompt to prevent prompt injection
    const safeName = doc.name.replace(/[^\w.\-_ ]/g, '_').slice(0, 200)

    await streamClaude({
      messages: [{
        role: 'user',
        content: `Please provide a concise summary of the following document named "${safeName}":\n\n${doc.content}`,
      }],
      system: 'You are a document summarizer. Provide clear, structured summaries highlighting key points, main topics, and important details. Be concise but thorough.',
      onChunk: (_, full) => {
        setSummaries(prev => ({ ...prev, [doc.id]: full }))
      },
      onDone: (full) => {
        setSummarizing(prev => ({ ...prev, [doc.id]: false }))
        setSummaries(prev => ({ ...prev, [doc.id]: full }))
      },
      onError: (err) => {
        setSummarizing(prev => ({ ...prev, [doc.id]: false }))
        setSummaries(prev => ({ ...prev, [doc.id]: `Error: ${err}` }))
      },
    })
  }

  return (
    <>
      <div className="panel-header">
        <span>📄</span>
        <h1>Documents</h1>
        <span className="subtitle">— upload files for AI summarization</span>
      </div>

      <div className="panel-body">
        {/* Upload zone */}
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <div className="upload-icon">📂</div>
          <p>Drop files here or click to browse</p>
          <small>Supported: {SUPPORTED.join(', ')}</small>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={SUPPORTED.join(',')}
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
        </div>

        {/* Document list */}
        {docs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📁</div>
            <p>No documents uploaded yet.</p>
          </div>
        ) : (
          docs.map(doc => (
            <div key={doc.id} className="doc-item">
              <div className="doc-header">
                <span className="doc-icon">{fileIcon(doc.name)}</span>
                <span className="doc-name">{doc.name}</span>
                <span className="doc-size">{formatSize(doc.size)}</span>
                <div className="doc-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => summarize(doc)}
                    disabled={summarizing[doc.id]}
                  >
                    {summarizing[doc.id] ? '⏳ Summarizing…' : '✨ Summarize'}
                  </button>
                  <button className="btn btn-danger" onClick={() => deleteDoc(doc.id)}>Remove</button>
                </div>
              </div>

              {summaries[doc.id] !== undefined && (
                <div className={`doc-summary ${summarizing[doc.id] ? 'streaming' : ''}`}>
                  {summaries[doc.id] || '…'}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  )
}
