import { useQuery } from '@tanstack/react-query'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const riskClass: Record<string, string> = { green: 'bg-green-500', yellow: 'bg-yellow-500', red: 'bg-red-600' }

export default function SchedulePage() {
  const { data } = useQuery({ queryKey: ['schedule-risk'], queryFn: async () => (await intelligenceAPI.scheduleRisk()).data })
  const tasks = data?.tasks || []
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Schedule</h1>
        <p className="text-muted-foreground">Predictive delay risk based on schedule, dependencies, procurement, workforce, and weather signals</p>
      </div>
      <Card>
        <CardHeader><CardTitle>Risk Gantt</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {tasks.map((task: any, index: number) => (
            <div key={task.id} className="grid gap-2 md:grid-cols-[220px_1fr_280px] md:items-center">
              <div>
                <p className="font-medium">{task.name}</p>
                <p className="text-xs text-muted-foreground">{task.start} to {task.finish}</p>
              </div>
              <div className="h-8 rounded-md bg-secondary">
                <div className={`h-8 rounded-md ${riskClass[task.risk] || riskClass.green}`} style={{ width: `${Math.min(95, 22 + index * 9)}%` }} />
              </div>
              <div className="rounded-md border p-3 text-sm">
                <Badge variant={task.risk === 'red' ? 'destructive' : task.risk === 'yellow' ? 'warning' : 'success'}>{Math.round(task.delay_probability * 100)}% delay</Badge>
                <p className="mt-2 text-muted-foreground">{task.mitigation}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
