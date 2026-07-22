import { useMutation, useQuery } from '@tanstack/react-query'
import { reportsAPI, agentsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Zap, Lightbulb } from 'lucide-react'
import { formatDate } from '@/lib/utils'

interface Report {
  id: string
  report_type: string
  report_name: string
  report_date: string
  summary: string | null
  key_insights: string[] | null
}

interface ExecutiveSummaryResult {
  summary: string
  key_insights: string[]
  root_causes: string[]
  future_risks: string[]
  recommended_actions: string[]
  project_health_assessment: string
}

export default function ReportsPage() {
  const { selectedProject } = useProjectStore()

  const { data: reports, isLoading } = useQuery<Report[]>({
    queryKey: ['reports', selectedProject?.id],
    queryFn: async () => (await reportsAPI.list(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const generateSummary = useMutation({
    mutationFn: async () => {
      const res = await agentsAPI.execute({
        agent_name: 'executive_agent',
        project_id: selectedProject!.id,
        execution_type: 'on_demand',
      })
      return res.data.output_data as ExecutiveSummaryResult
    },
  })

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view reports</p>
      </div>
    )
  }

  const result = generateSummary.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Reports</h1>
          <p className="text-muted-foreground">{selectedProject.name}</p>
        </div>
        <Button className="orange-glow" onClick={() => generateSummary.mutate()} disabled={generateSummary.isPending}>
          <Zap className="w-4 h-4 mr-2" />
          {generateSummary.isPending ? 'Generating...' : 'Generate Executive Summary'}
        </Button>
      </div>

      {result && (
        <Card className="border-orange-600/30">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-orange-600" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p>{result.summary}</p>
            <p className="text-muted-foreground">{result.project_health_assessment}</p>

            {result.key_insights?.length > 0 && (
              <div>
                <p className="font-semibold mb-1">Key Insights</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  {result.key_insights.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.recommended_actions?.length > 0 && (
              <div>
                <p className="font-semibold mb-1">Recommended Actions</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                  {result.recommended_actions.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="w-5 h-5 text-orange-600" />
            Saved Reports
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : !reports || reports.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No reports saved yet for this project.</p>
          ) : (
            reports.map((r) => (
              <div key={r.id} className="p-4 rounded-lg border border-border/50">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{r.report_name}</p>
                  <span className="text-xs text-muted-foreground">{formatDate(r.report_date)}</span>
                </div>
                <p className="text-xs text-muted-foreground capitalize mt-1">{r.report_type.replace('_', ' ')}</p>
                {r.summary && <p className="text-sm mt-2">{r.summary}</p>}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
