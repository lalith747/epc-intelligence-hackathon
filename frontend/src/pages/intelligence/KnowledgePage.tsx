import { useQuery } from '@tanstack/react-query'
import { Database, HardDrive, ShieldCheck, SlidersHorizontal, Truck } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge, severityBadgeVariant } from '@/components/ui/badge'

export default function KnowledgePage() {
  const { data: equipment = [] } = useQuery({ queryKey: ['kb-equipment'], queryFn: async () => (await intelligenceAPI.equipment()).data })
  const { data: vendors = [] } = useQuery({ queryKey: ['kb-vendors'], queryFn: async () => (await intelligenceAPI.vendors()).data })
  const { data: requirements = [] } = useQuery({ queryKey: ['kb-requirements'], queryFn: async () => (await intelligenceAPI.requirements()).data })
  const { data: standards = [] } = useQuery({ queryKey: ['kb-standards'], queryFn: async () => (await intelligenceAPI.standards()).data })
  const { data: rules = [] } = useQuery({ queryKey: ['kb-rule-evaluations'], queryFn: async () => (await intelligenceAPI.ruleEvaluations()).data })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Knowledge Base</h1>
        <p className="text-muted-foreground">
          Structured records extracted into the unified DB hub and used by compliance, RAG, notifications, dashboard, and reports
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-5">
        <Metric icon={HardDrive} label="Equipment" value={equipment.length} />
        <Metric icon={Truck} label="Submittals" value={vendors.length} />
        <Metric icon={SlidersHorizontal} label="Requirements" value={requirements.length} />
        <Metric icon={Database} label="Standards" value={standards.length} />
        <Metric icon={ShieldCheck} label="Rule Checks" value={rules.length} />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Equipment Assets</CardTitle></CardHeader>
          <CardContent className="overflow-auto p-0">
            <DataTable rows={equipment} fields={['name', 'tag', 'equipment_type', 'document_title']} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Vendor Submittals</CardTitle></CardHeader>
          <CardContent className="overflow-auto p-0">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-left"><tr><th className="p-3">Vendor</th><th>Equipment</th><th>Score</th><th>Status</th></tr></thead>
              <tbody>
                {vendors.map((row: any) => (
                  <tr key={row.id} className="border-t">
                    <td className="p-3">{row.vendor}</td>
                    <td>{row.equipment_name}</td>
                    <td>{row.score_percent}</td>
                    <td><Badge variant={row.status === 'rejected' ? 'destructive' : row.status === 'conditional' ? 'warning' : 'success'}>{row.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Engineering Requirements</CardTitle></CardHeader>
          <CardContent className="overflow-auto p-0">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-left"><tr><th className="p-3">Equipment</th><th>Field</th><th>Rule</th><th>Required</th><th>Severity</th></tr></thead>
              <tbody>
                {requirements.map((row: any) => (
                  <tr key={row.id} className="border-t">
                    <td className="p-3">{row.equipment_type}</td>
                    <td>{row.field_name}</td>
                    <td>{row.operator}</td>
                    <td>{row.value}</td>
                    <td><Badge variant={severityBadgeVariant(row.severity)}>{row.severity}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Standards</CardTitle></CardHeader>
          <CardContent className="overflow-auto p-0">
            <DataTable rows={standards} fields={['title', 'category', 'created_at']} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Deterministic Rule Evaluations</CardTitle></CardHeader>
        <CardContent className="overflow-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-secondary text-left"><tr><th className="p-3">Document</th><th>Field</th><th>Rule</th><th>Status</th><th>Explanation</th></tr></thead>
            <tbody>
              {rules.slice(0, 120).map((row: any) => (
                <tr key={row.id} className="border-t">
                  <td className="p-3">{row.document_title}</td>
                  <td>{row.field_name}</td>
                  <td>{row.operator}</td>
                  <td><Badge variant={row.status === 'fail' ? 'destructive' : row.status === 'not_available' ? 'warning' : 'success'}>{row.status}</Badge></td>
                  <td className="max-w-xl py-3">{row.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}

function Metric({ icon: Icon, label, value }: { icon: typeof Database; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <Icon className="h-5 w-5 text-orange-600" />
      </CardContent>
    </Card>
  )
}

function DataTable({ rows, fields }: { rows: any[]; fields: string[] }) {
  return (
    <table className="w-full text-sm">
      <thead className="bg-secondary text-left">
        <tr>{fields.map((field) => <th key={field} className="p-3 capitalize">{field.replaceAll('_', ' ')}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} className="border-t">
            {fields.map((field, index) => <td key={field} className={index === 0 ? 'p-3' : ''}>{row[field]}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
