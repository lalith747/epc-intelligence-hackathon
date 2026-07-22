import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { risksAPI, agentsAPI, recommendationsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, severityBadgeVariant } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Modal, DetailRow } from '@/components/ui/modal'
import { Zap, AlertTriangle, Wrench } from 'lucide-react'
import { formatDate } from '@/lib/utils'

interface Risk {
  id: string
  risk_code: string
  title: string
  description: string | null
  category: string
  risk_source: string | null
  probability: number
  impact: number
  confidence: number
  risk_score: number
  severity: string
  status: string
  identified_date: string
  target_closure_date: string | null
  related_activities: string[] | null
  related_suppliers: string[] | null
  explanation: string | null
}

interface Recommendation {
  id: string
  title: string
  description: string
  recommendation_type: string | null
  confidence: number | null
  estimated_days_saved: number | null
  priority: string | null
  status: string
  related_risks: string[] | null
  explanation: string | null
}

// Fallback mitigation guidance by risk category when no specific
// recommendation is linked to the risk yet.
const CATEGORY_MEASURES: Record<string, string[]> = {
  schedule: [
    'Re-run the critical path and fast-track non-dependent activities in parallel.',
    'Add shifts or crews to critical activities to recover float.',
    'Escalate long-lead approvals and permit dependencies now.',
  ],
  procurement: [
    'Split the order across an alternate qualified supplier.',
    'Expedite freight (air vs sea) for critical-path materials.',
    'Draw down from buffer stock or transfer inventory from lower-priority work fronts.',
  ],
  supplier: [
    'Trigger the contract escalation clause and request a recovery plan with dates.',
    'Qualify a backup supplier before the situation becomes critical.',
    'Increase inspection/expediting visits to keep quality and dates honest.',
  ],
  resource: [
    'Rebalance crews from non-critical work fronts.',
    'Pre-book scarce specialist labour (commissioning, HV jointing) early.',
  ],
}

export default function RisksPage() {
  const { selectedProject } = useProjectStore()
  const queryClient = useQueryClient()
  const [selectedRisk, setSelectedRisk] = useState<Risk | null>(null)

  const { data: risks, isLoading } = useQuery<Risk[]>({
    queryKey: ['risks', selectedProject?.id],
    queryFn: async () => (await risksAPI.list(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const { data: recommendations } = useQuery<Recommendation[]>({
    queryKey: ['recommendations', selectedProject?.id],
    queryFn: async () => (await recommendationsAPI.list(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const mitigationsFor = (risk: Risk): Recommendation[] =>
    (recommendations || []).filter((rec) => rec.related_risks?.includes(risk.risk_code))

  const runAgent = useMutation({
    mutationFn: () =>
      agentsAPI.execute({
        agent_name: 'risk_agent',
        project_id: selectedProject!.id,
        execution_type: 'on_demand',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['risks', selectedProject?.id] }),
  })

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view risks</p>
      </div>
    )
  }

  const critical = risks?.filter((r) => r.severity === 'critical' && r.status === 'open').length || 0
  const open = risks?.filter((r) => r.status === 'open').length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Risks</h1>
          <p className="text-muted-foreground">{selectedProject.name}</p>
        </div>
        <Button className="orange-glow" onClick={() => runAgent.mutate()} disabled={runAgent.isPending}>
          <Zap className="w-4 h-4 mr-2" />
          {runAgent.isPending ? 'Running...' : 'Run Risk Agent'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Open Risks</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{open}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Critical Risks</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-400">{critical}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-600" />
            Risk Register
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : !risks || risks.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No risks identified yet for this project.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Risk</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Probability</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {risks.map((r) => (
                  <TableRow key={r.id} className="cursor-pointer" onClick={() => setSelectedRisk(r)}>
                    <TableCell>
                      <p className="font-medium">{r.title}</p>
                      <p className="text-xs text-muted-foreground">{r.risk_code}</p>
                      {r.explanation && (
                        <p className="text-xs text-muted-foreground mt-1 max-w-md">{r.explanation}</p>
                      )}
                    </TableCell>
                    <TableCell className="capitalize">{r.category}</TableCell>
                    <TableCell>{Math.round(r.probability)}%</TableCell>
                    <TableCell>{Math.round(r.impact)}%</TableCell>
                    <TableCell className="font-semibold">{Math.round(r.risk_score)}</TableCell>
                    <TableCell>
                      <Badge variant={severityBadgeVariant(r.severity)} className="capitalize">
                        {r.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={r.status === 'open' ? 'outline' : 'secondary'} className="capitalize">
                        {r.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Modal
        open={!!selectedRisk}
        onClose={() => setSelectedRisk(null)}
        title={selectedRisk?.title || ''}
        subtitle={selectedRisk?.risk_code}
      >
        {selectedRisk && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <Badge variant={severityBadgeVariant(selectedRisk.severity)} className="capitalize">
                {selectedRisk.severity}
              </Badge>
              <Badge variant={selectedRisk.status === 'open' ? 'outline' : 'secondary'} className="capitalize">
                {selectedRisk.status}
              </Badge>
            </div>
            {selectedRisk.description && (
              <p className="text-sm text-muted-foreground">{selectedRisk.description}</p>
            )}
            {selectedRisk.explanation && (
              <div className="p-3 rounded-lg bg-secondary/60 text-sm">{selectedRisk.explanation}</div>
            )}
            <div>
              <DetailRow label="Category" value={<span className="capitalize">{selectedRisk.category}</span>} />
              <DetailRow label="Source" value={selectedRisk.risk_source} />
              <DetailRow label="Probability" value={`${Math.round(selectedRisk.probability)}%`} />
              <DetailRow label="Impact" value={`${Math.round(selectedRisk.impact)}%`} />
              <DetailRow label="Risk Score" value={Math.round(selectedRisk.risk_score)} />
              <DetailRow label="Confidence" value={`${Math.round(selectedRisk.confidence)}%`} />
              <DetailRow label="Identified" value={formatDate(selectedRisk.identified_date)} />
              <DetailRow
                label="Target Closure"
                value={selectedRisk.target_closure_date ? formatDate(selectedRisk.target_closure_date) : null}
              />
              <DetailRow label="Related Activities" value={selectedRisk.related_activities?.join(', ')} />
              <DetailRow label="Related Suppliers" value={selectedRisk.related_suppliers?.join(', ')} />
            </div>

            <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/30 space-y-2">
              <p className="font-semibold text-sm flex items-center gap-2">
                <Wrench className="w-4 h-4 text-orange-600" />
                Mitigation Measures
              </p>
              {mitigationsFor(selectedRisk).length > 0 ? (
                mitigationsFor(selectedRisk).map((rec) => (
                  <div key={rec.id} className="text-sm border-l-2 border-orange-500/50 pl-3 py-1">
                    <p className="font-medium">{rec.title}</p>
                    <p className="text-muted-foreground text-xs mt-0.5">{rec.description}</p>
                    <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                      {rec.estimated_days_saved != null && (
                        <span className="text-green-600 font-medium">Saves ~{rec.estimated_days_saved} days</span>
                      )}
                      {rec.confidence != null && <span>{Math.round(rec.confidence)}% confidence</span>}
                      {rec.priority && <span className="capitalize">{rec.priority} priority</span>}
                    </div>
                  </div>
                ))
              ) : (
                <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1">
                  {(CATEGORY_MEASURES[selectedRisk.category] || [
                    'Assign an owner and a target closure date.',
                    'Review at the next project risk meeting and agree a response plan.',
                  ]).map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
