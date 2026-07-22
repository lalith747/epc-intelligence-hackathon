import { useQuery } from '@tanstack/react-query'
import { analyticsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { formatDate } from '@/lib/utils'

interface RiskTrendPoint {
  date: string
  risk_score: number
  open_risks: number
  critical_risks: number
}

interface ScheduleProgressPoint {
  date: string
  completion: number
  on_time_percentage: number
}

const tooltipStyle = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '8px',
}

export default function AnalyticsPage() {
  const { selectedProject } = useProjectStore()

  const { data: riskTrend, isLoading: loadingRisk } = useQuery({
    queryKey: ['risk-trend', selectedProject?.id],
    queryFn: async () => (await analyticsAPI.getRiskTrend(selectedProject!.id, 30)).data.data as RiskTrendPoint[],
    enabled: !!selectedProject,
  })

  const { data: scheduleProgress, isLoading: loadingSchedule } = useQuery({
    queryKey: ['schedule-progress', selectedProject?.id],
    queryFn: async () => (await analyticsAPI.getScheduleProgress(selectedProject!.id)).data.data as ScheduleProgressPoint[],
    enabled: !!selectedProject,
  })

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view analytics</p>
      </div>
    )
  }

  const riskData = (riskTrend || []).map((p) => ({ ...p, date: formatDate(p.date) }))
  const scheduleData = (scheduleProgress || []).map((p) => ({ ...p, date: formatDate(p.date) }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">{selectedProject.name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Risk Trend (30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingRisk ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : riskData.length === 0 ? (
            <p className="text-muted-foreground text-center py-12">No health history recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={riskData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
                <Line type="monotone" dataKey="risk_score" name="Risk Score" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="open_risks" name="Open Risks" stroke="#facc15" strokeWidth={2} />
                <Line type="monotone" dataKey="critical_risks" name="Critical Risks" stroke="#ef4444" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Schedule Progress</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSchedule ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : scheduleData.length === 0 ? (
            <p className="text-muted-foreground text-center py-12">No health history recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={scheduleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
                <Bar dataKey="completion" name="Completion %" fill="#f97316" radius={[4, 4, 0, 0]} />
                <Bar dataKey="on_time_percentage" name="On-Time %" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
