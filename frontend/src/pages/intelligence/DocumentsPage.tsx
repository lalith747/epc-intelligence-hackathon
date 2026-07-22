import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileSearch, Upload } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function DocumentsPage() {
  const [query, setQuery] = useState('')
  const [type, setType] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<any>(null)
  const qc = useQueryClient()
  const { data: docs = [] } = useQuery({ queryKey: ['documents'], queryFn: async () => (await intelligenceAPI.documents()).data })
  const upload = useMutation({
    mutationFn: (file: File) => intelligenceAPI.uploadDocument(file, file.name),
    onSuccess: () => {
      setSelectedFile(null)
      setPreview(null)
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
  })
  const previewUpload = useMutation({
    mutationFn: (file: File) => intelligenceAPI.previewUpload(file),
    onSuccess: (response) => setPreview(response.data),
  })
  const types = Array.from(new Set(docs.map((doc: any) => doc.document_type))).filter(Boolean)
  const filtered = useMemo(() => docs.filter((doc: any) => {
    const haystack = `${doc.title} ${doc.file_name} ${doc.document_type} ${doc.vendor}`.toLowerCase()
    return haystack.includes(query.toLowerCase()) && (!type || doc.document_type === type)
  }), [docs, query, type])

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_1fr]">
      <Card>
        <CardHeader><CardTitle>Folders</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          {types.map((item) => <button key={item} onClick={() => setType(String(item))} className="block w-full rounded-md px-3 py-2 text-left hover:bg-accent">{String(item)}</button>)}
          <button onClick={() => setType('')} className="block w-full rounded-md px-3 py-2 text-left hover:bg-accent">All Documents</button>
        </CardContent>
      </Card>
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Documents</h1>
            <p className="text-muted-foreground">Preview, upload, extract, compliance-check, and index project records</p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-orange-600 px-4 py-2 text-sm font-medium text-white">
            <Upload className="h-4 w-4" />
            Select file
            <input
              type="file"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0] || null
                setSelectedFile(file)
                setPreview(null)
                if (file) previewUpload.mutate(file)
              }}
            />
          </label>
        </div>
        {selectedFile && (
          <Card>
            <CardHeader>
              <CardTitle>Preview Before Upload</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-4 text-sm">
                <div><p className="text-muted-foreground text-xs">File</p><p className="font-medium">{selectedFile.name}</p></div>
                <div><p className="text-muted-foreground text-xs">Detected type</p><p className="font-medium">{preview?.document_type || 'Analyzing...'}</p></div>
                <div><p className="text-muted-foreground text-xs">Extraction</p><p className="font-medium">{preview?.extraction_method || 'Pending'}</p></div>
                <div><p className="text-muted-foreground text-xs">Pipeline</p><p className="font-medium">{preview?.will_trigger?.join(', ') || 'extract, compliance, RAG'}</p></div>
              </div>
              {preview?.data_url ? (
                <img className="max-h-72 rounded-md border object-contain" src={`data:${preview.data_url}`} />
              ) : (
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-secondary p-3 text-xs">{preview?.text || 'Preview will appear here.'}</pre>
              )}
              <Button onClick={() => selectedFile && upload.mutate(selectedFile)} disabled={!preview || upload.isPending}>
                Commit Upload
              </Button>
            </CardContent>
          </Card>
        )}
        <div className="flex gap-3">
          <input className="w-full rounded-md border bg-background px-3 py-2" placeholder="Search documents, vendors, metadata..." value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
        <Card>
          <CardContent className="overflow-auto p-0">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-left">
                <tr><th className="p-3">Document</th><th>Type</th><th>Vendor</th><th>Extraction</th><th>Flags</th><th></th></tr>
              </thead>
              <tbody>
                {filtered.map((doc: any) => (
                  <tr key={doc.id} className="border-t">
                    <td className="p-3 font-medium">{doc.title}<div className="text-xs text-muted-foreground">{doc.file_name}</div></td>
                    <td>{doc.document_type}</td>
                    <td>{doc.vendor}</td>
                    <td>{doc.extraction_method}</td>
                    <td><Badge variant={doc.issue_count ? 'destructive' : 'success'}>{doc.issue_count}</Badge></td>
                    <td><Link to={`/documents/${doc.id}`} className="inline-flex items-center gap-1 text-orange-600"><FileSearch className="h-4 w-4" />Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
