import { useState } from 'react'
import { MessageSquare, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { intelligenceAPI } from '@/lib/api'

export default function FloatingChat() {
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('What is the redundancy requirement for UPS in Hall 3?')
  const [sessionId, setSessionId] = useState<string>()
  const [history, setHistory] = useState<Array<{ role: string; message: string }>>([])
  const [loading, setLoading] = useState(false)

  async function send() {
    if (!message.trim()) return
    const userMessage = message
    setHistory((items) => [...items, { role: 'user', message: userMessage }])
    setMessage('')
    setLoading(true)
    try {
      const response = await intelligenceAPI.chat(userMessage, sessionId)
      setSessionId(response.data.session_id)
      setHistory((items) => [...items, { role: 'assistant', message: response.data.answer }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Button className="fixed bottom-5 right-5 z-50 orange-glow" onClick={() => setOpen(true)} size="icon" title="Open AI assistant">
        <MessageSquare className="h-5 w-5" />
      </Button>
      {open && (
        <aside className="fixed bottom-20 right-5 z-50 w-[380px] max-w-[calc(100vw-2rem)] rounded-lg border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b p-3">
            <div>
              <p className="font-semibold">AI Knowledge Assistant</p>
              <p className="text-xs text-muted-foreground">RAG answers with source citations</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)} title="Close chat">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="h-72 overflow-y-auto p-3 space-y-3">
            {history.length === 0 && (
              <div className="text-sm text-muted-foreground">Ask about specifications, RFIs, schedules, procurement, or compliance flags.</div>
            )}
            {history.map((item, index) => (
              <div key={index} className={item.role === 'user' ? 'text-right' : 'text-left'}>
                <span className={`inline-block rounded-lg px-3 py-2 text-sm ${item.role === 'user' ? 'bg-orange-600 text-white' : 'bg-secondary'}`}>
                  {item.message}
                </span>
              </div>
            ))}
            {loading && <div className="text-sm text-muted-foreground">Searching indexed project records...</div>}
          </div>
          <div className="flex gap-2 border-t p-3">
            <input className="flex-1 rounded-md border bg-background px-3 py-2 text-sm" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} />
            <Button onClick={send} size="icon" title="Send">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </aside>
      )}
    </>
  )
}
