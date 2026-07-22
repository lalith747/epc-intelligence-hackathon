import { useQuery } from '@tanstack/react-query'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function CommunicationsPage() {
  const { data } = useQuery({ queryKey: ['communications'], queryFn: async () => (await intelligenceAPI.communications()).data })
  const actions = data?.action_items || []
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Communications</h1>
        <p className="text-muted-foreground">Email, RFI, and meeting-minute intelligence with extracted actions and linked prior answers</p>
      </div>
      <Card>
        <CardHeader><CardTitle>Action Feed</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {actions.map((item: any) => (
            <div key={item.id} className="rounded-md border p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{item.decision_summary}</p>
                </div>
                <Badge variant="orange">{item.status}</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                <span>Owner: {item.owner}</span>
                <span>Due: {item.due_date}</span>
                {item.similar_reference && <span>{item.similar_reference}</span>}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
