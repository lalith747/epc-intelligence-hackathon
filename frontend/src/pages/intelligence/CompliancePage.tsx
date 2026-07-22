import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge, severityBadgeVariant } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export default function CompliancePage() {
  const { data: issues = [] } = useQuery({ queryKey: ['compliance'], queryFn: async () => (await intelligenceAPI.compliance()).data })
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Compliance</h1>
          <p className="text-muted-foreground">Automated checks against the supplied compliance standard</p>
        </div>
        <Button variant="outline"><Download className="mr-2 h-4 w-4" />Export</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>Open Issues</CardTitle></CardHeader>
        <CardContent className="overflow-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-secondary text-left"><tr><th className="p-3">Severity</th><th>Document</th><th>Category</th><th>Description</th><th>Recommendation</th></tr></thead>
            <tbody>
              {issues.map((issue: any) => (
                <tr key={issue.id} className="border-t">
                  <td className="p-3"><Badge variant={severityBadgeVariant(issue.severity)}>{issue.severity}</Badge></td>
                  <td>{issue.document_title}</td>
                  <td>{issue.category}</td>
                  <td className="max-w-md py-3">{issue.description}<div className="text-xs text-muted-foreground">{issue.evidence}</div></td>
                  <td className="max-w-sm">{issue.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
