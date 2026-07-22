import { Bell, Mail, Plug, Shield } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function IntelligenceSettingsPage() {
  const rows = [
    ['Compliance failures', 'In-app toast, email for high/critical', true],
    ['Schedule delay probability over 60%', 'In-app toast and daily digest', true],
    ['Procurement ETA within 5 days', 'In-app toast', true],
    ['Pending approvals older than 7 days', 'Email digest', false],
  ]
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Users, notification preferences, API keys, and integrations</p>
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <Card><CardHeader><CardTitle><Shield className="mr-2 inline h-5 w-5 text-orange-600" />Users</CardTitle></CardHeader><CardContent className="text-sm">Ava Cole · Admin<br />Project engineers · Read/write<br />Client viewers · Read only</CardContent></Card>
        <Card><CardHeader><CardTitle><Plug className="mr-2 inline h-5 w-5 text-orange-600" />Integrations</CardTitle></CardHeader><CardContent className="text-sm">Gemini multimodal: `.env` GOOGLE_API_KEY<br />Groq RAG: `.env` GROQ_API_KEY<br />Quarto reports: system `quarto` CLI</CardContent></Card>
        <Card><CardHeader><CardTitle><Mail className="mr-2 inline h-5 w-5 text-orange-600" />Messaging</CardTitle></CardHeader><CardContent className="text-sm">SMTP optional. In-app notifications work without external messaging.</CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle><Bell className="mr-2 inline h-5 w-5 text-orange-600" />Notification Preferences</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {rows.map(([name, channel, enabled]) => (
            <label key={String(name)} className="flex items-center justify-between rounded-md border p-3">
              <span><span className="font-medium">{String(name)}</span><span className="block text-sm text-muted-foreground">{String(channel)}</span></span>
              <input type="checkbox" defaultChecked={Boolean(enabled)} className="h-5 w-5" />
            </label>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
