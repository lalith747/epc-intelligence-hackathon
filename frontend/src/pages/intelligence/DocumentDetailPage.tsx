import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Download, RefreshCw } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function DocumentDetailPage() {
  const { id = '' } = useParams()
  const qc = useQueryClient()
  const { data: doc } = useQuery({ queryKey: ['document', id], queryFn: async () => (await intelligenceAPI.document(id)).data, enabled: !!id })
  const { data: preview } = useQuery({ queryKey: ['preview', id], queryFn: async () => (await intelligenceAPI.preview(id)).data, enabled: !!id })
  const recheck = useMutation({ mutationFn: () => intelligenceAPI.recheck(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['document', id] }) })

  if (!doc) return <div>Loading document...</div>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold">{doc.title}</h1>
          <p className="text-muted-foreground">{doc.document_type} · {doc.extraction_method}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => recheck.mutate()}><RefreshCw className="mr-2 h-4 w-4" />Re-check</Button>
          <a href={intelligenceAPI.downloadUrl(id)}><Button><Download className="mr-2 h-4 w-4" />Download</Button></a>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <Card>
          <CardHeader><CardTitle>Preview Before Upload / Source View</CardTitle></CardHeader>
          <CardContent>
            {preview?.data_url ? (
              <img className="max-h-[620px] w-full rounded-md object-contain" src={`data:${preview.data_url}`} />
            ) : (
              <pre className="max-h-[620px] overflow-auto whitespace-pre-wrap rounded-md bg-secondary p-4 text-xs">{preview?.text || doc.extracted_text}</pre>
            )}
          </CardContent>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Extracted Metadata</CardTitle></CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 text-sm">
              {Object.entries(doc.metadata || {}).map(([key, value]) => (
                <div key={key} className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">{key}</p>
                  <p className="break-words font-medium">{Array.isArray(value) ? value.join(', ') : String(value || 'N/A')}</p>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Compliance Flags</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {doc.issues.map((issue: any) => (
                <div key={issue.id} className="rounded-md border p-3">
                  <Badge variant={issue.severity === 'critical' || issue.severity === 'high' ? 'destructive' : 'secondary'}>{issue.severity}</Badge>
                  <p className="mt-2 font-medium">{issue.description}</p>
                  <p className="text-sm text-muted-foreground">{issue.evidence}</p>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Version History</CardTitle></CardHeader>
            <CardContent>
              {doc.versions.map((version: any) => <div key={version.created_at} className="border-t py-2 text-sm">Revision {version.version} · {version.status} · {version.created_at}</div>)}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
