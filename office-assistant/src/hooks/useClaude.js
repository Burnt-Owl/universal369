import { useState, useCallback } from 'react'

const API_URL = 'https://api.anthropic.com/v1/messages'
const MODEL = 'claude-haiku-4-5-20251001'

function getApiKey() {
  return localStorage.getItem('oa_api_key') || ''
}

/**
 * Send a one-shot message and stream the response via the callback.
 * Returns the full response text when done.
 */
export async function streamClaude({ messages, system, onChunk, onDone, onError }) {
  const apiKey = getApiKey()
  if (!apiKey) {
    onError?.('No API key set. Go to Settings and enter your Anthropic API key.')
    return
  }

  const body = {
    model: MODEL,
    max_tokens: 1024,
    stream: true,
    messages,
    ...(system ? { system } : {}),
  }

  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      onError?.(err?.error?.message || `API error ${res.status}`)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let full = ''
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const evt = JSON.parse(data)
          if (evt.type === 'content_block_delta' && evt.delta?.type === 'text_delta') {
            full += evt.delta.text
            onChunk?.(evt.delta.text, full)
          }
        } catch {
          // ignore parse errors on individual SSE frames
        }
      }
    }

    onDone?.(full)
  } catch (err) {
    onError?.(err.message || 'Network error')
  }
}

/**
 * Hook for managing a streaming Claude call state.
 */
export function useClaude() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const send = useCallback(async ({ messages, system, onChunk, onDone }) => {
    setLoading(true)
    setError(null)
    await streamClaude({
      messages,
      system,
      onChunk,
      onDone: (text) => {
        setLoading(false)
        onDone?.(text)
      },
      onError: (msg) => {
        setLoading(false)
        setError(msg)
      },
    })
  }, [])

  return { send, loading, error }
}
