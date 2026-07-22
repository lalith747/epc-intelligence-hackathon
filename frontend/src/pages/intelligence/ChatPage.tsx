import { useState } from 'react'
import { Send } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const suggestions = [
  'What is the redundancy requirement for UPS in Hall 3?',
  'Which procurement items are at risk of delaying critical path tasks?',
  'Summarize open compliance issues by severity.',
  'What action items were extracted from emails and RFIs?',
]

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>()
  const [message, setMessage] = useState(suggestions[0])
  const [turns, setTurns] = useState<any[]>([])
  const [sources, setSources] = useState<any[]>([])

  async function send(text = message) {
    if (!text.trim()) return
    setTurns((items) => [...items, { role: 'user', message: text }])
    setMessage('')
    const response = await intelligenceAPI.chat(text, sessionId)
    setSessionId(response.data.session_id)
    setSources(response.data.citations || [])
    setTurns((items) => [...items, { role: 'assistant', message: response.data.answer }])
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Chat</h1>
          <p className="text-muted-foreground">Full RAG chatbot backed by sentence-transformer embeddings, FAISS vector files, and Groq generation when configured</p>
        </div>
        <Card>
          <CardContent className="h-[560px] overflow-auto p-4 space-y-4">
            {turns.map((turn, index) => <div key={index} className={turn.role === 'user' ? 'text-right' : 'text-left'}><span className={`inline-block max-w-[84%] rounded-lg px-3 py-2 ${turn.role === 'user' ? 'bg-orange-600 text-white' : 'bg-secondary'}`}>{turn.message}</span></div>)}
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <input className="flex-1 rounded-md border bg-background px-3 py-2" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && send()} />
          <Button onClick={() => send()}><Send className="mr-2 h-4 w-4" />Send</Button>
        </div>
      </div>
      <div className="space-y-6">
        <Card>
          <CardHeader><CardTitle>Suggested Questions</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {suggestions.map((item) => <button key={item} onClick={() => send(item)} className="block w-full rounded-md border p-3 text-left text-sm hover:bg-accent">{item}</button>)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Source Preview</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {sources.map((source, index) => (
              <div key={`${source.document_id}-${index}`} className="rounded-md border p-3">
                <p className="font-medium">{source.document_name}</p>
                <p className="text-xs text-muted-foreground">Page {source.page_number}</p>
                <p className="mt-2 text-sm">{source.snippet}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
