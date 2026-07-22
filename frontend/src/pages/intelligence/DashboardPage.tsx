import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Clock, FileText, Package, TrendingUp } from 'lucide-react'
import { Pie, PieChart, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const colors = ['#ea580c', '#0f766e', '#2563eb', '#dc2626', '#7c3aed']

export default function IntelligenceDashboardPage() {
  const { data } = useQuery({ queryKey: ['intelligence-dashboard'], queryFn: async () => (await intelligenceAPI.dashboard()).data })
  const kpis = data?.kpis || {}
  const cards = [
    ['Health Score', kpis.health_score, CheckCircle2, '/dashboard'],
    ['Schedule %', kpis.schedule_percent, Clock, '/schedule'],
    ['Compliance Issues', kpis.compliance_issues, AlertTriangle, '/compliance'],
    ['Procurement Risks', kpis.procurement_risks, Package, '/procurement'],
    ['Docs Processed', kpis.docs_processed, FileText, '/documents'],
    ['Hours Saved', kpis.hours_saved, TrendingUp, '/reports'],
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Unified AI intelligence for the Orion data-centre construction program</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        {cards.map(([title, value, Icon, href]) => (
          <Link key={String(title)} to={String(href)}>
            <Card className="h-full transition-colors hover:bg-accent">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">{String(title)}</p>
                  <Icon className="h-4 w-4 text-orange-600" />
                </div>
                <p className="mt-3 text-2xl font-bold">{Math.round(Number(value || 0))}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_.8fr]">
        <Card>
          <CardHeader><CardTitle>Risk Over Time</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data?.risk_over_time || []}>
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="risk" stroke="#ea580c" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Compliance By Category</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data?.compliance_by_category || []} dataKey="value" nameKey="category" innerRadius={55} outerRadius={90}>
                  {(data?.compliance_by_category || []).map((_: any, index: number) => <Cell key={index} fill={colors[index % colors.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <MiniTable title="Critical Path Tasks At Risk" rows={data?.critical_tasks || []} fields={['id', 'name', 'risk', 'mitigation']} href="/schedule" />
        <MiniTable title="Top Procurement Risks" rows={data?.top_procurement_risks || []} fields={['id', 'material', 'supplier', 'risk']} href="/procurement" />
        <Card>
          <CardHeader><CardTitle>Live Activity Feed</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(data?.activity || []).map((item: any) => (
              <Link to="/documents" key={`${item.title}-${item.created_at}`} className="block rounded-md border p-3 hover:bg-accent">
                <p className="text-sm font-medium">{item.title}</p>
                <p className="text-xs text-muted-foreground">{item.document_type} · {item.created_at}</p>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function MiniTable({ title, rows, fields, href }: { title: string; rows: any[]; fields: string[]; href: string }) {
  return (
    <Card>
      <CardHeader><CardTitle><Link to={href}>{title}</Link></CardTitle></CardHeader>
      <CardContent className="overflow-auto">
        <table className="w-full text-sm">
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t">
                {fields.map((field) => <td key={field} className="py-2 pr-3 align-top">{row[field]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
