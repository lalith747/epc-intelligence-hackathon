import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FilePlus2 } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function ReportsPage() {
  const qc = useQueryClient()
  const { data: reports = [] } = useQuery({ queryKey: ['intelligence-reports'], queryFn: async () => (await intelligenceAPI.reports()).data })
  const generate = useMutation({
    mutationFn: () => intelligenceAPI.generateReport('weekly', 7),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['intelligence-reports'] }),
  })
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Weekly, monthly, and annual project intelligence reports rendered through Quarto when available</p>
        </div>
        <Button onClick={() => generate.mutate()} disabled={generate.isPending}><FilePlus2 className="mr-2 h-4 w-4" />Generate Weekly</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>Report History</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {reports.map((report: any) => (
            <div key={report.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-4">
              <div>
                <p className="font-medium">{report.report_type} report</p>
                <p className="text-sm text-muted-foreground">{report.period_start} to {report.period_end} · {report.summary}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={report.status.includes('fallback') ? 'warning' : 'success'}>{report.status}</Badge>
                <a href={`/api/v1/intelligence/reports/${report.id}/download`}><Button variant="outline"><Download className="mr-2 h-4 w-4" />Download</Button></a>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
