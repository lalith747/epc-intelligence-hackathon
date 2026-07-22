import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { motion } from 'framer-motion'
import { Plus, MapPin, Calendar, ArrowRight, FolderKanban, X } from 'lucide-react'
import { formatDate, getHealthColor } from '@/lib/utils'

interface ProjectSummary {
  id: string
  name: string
  code: string
  status: string
  progress_percentage: number
  start_date: string
  planned_end_date: string
  overall_health_score: number | null
  location?: string
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { setSelectedProject } = useProjectStore()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    code: '',
    client_name: '',
    location: '',
    start_date: '',
    planned_end_date: '',
  })
  const [error, setError] = useState('')

  const { data: projects, isLoading } = useQuery<ProjectSummary[]>({
    queryKey: ['projects'],
    queryFn: async () => (await projectsAPI.list()).data,
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => projectsAPI.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowForm(false)
      setForm({ name: '', code: '', client_name: '', location: '', start_date: '', planned_end_date: '' })
      setError('')
    },
    onError: (err: any) => setError(err.response?.data?.detail || 'Failed to create project'),
  })

  const selectProject = (project: ProjectSummary) => {
    setSelectedProject(project)
    navigate('/dashboard')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground">Select a project to monitor, or create a new one</p>
        </div>
        <Button className="orange-glow" onClick={() => setShowForm((v) => !v)}>
          {showForm ? <X className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
          {showForm ? 'Cancel' : 'New Project'}
        </Button>
      </div>

      {showForm && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Create Project</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
                onSubmit={(e) => {
                  e.preventDefault()
                  createMutation.mutate(form)
                }}
              >
                {error && (
                  <div className="md:col-span-2 bg-destructive/10 text-destructive text-sm p-3 rounded-lg">
                    {error}
                  </div>
                )}
                <div>
                  <label className="text-sm font-medium mb-2 block">Project Name</label>
                  <input
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                    placeholder="Orion Data Centre Campus"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Project Code</label>
                  <input
                    required
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                    placeholder="ORN-001"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Client</label>
                  <input
                    value={form.client_name}
                    onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Location</label>
                  <input
                    value={form.location}
                    onChange={(e) => setForm({ ...form, location: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Start Date</label>
                  <input
                    required
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Planned End Date</label>
                  <input
                    required
                    type="date"
                    value={form.planned_end_date}
                    onChange={(e) => setForm({ ...form, planned_end_date: e.target.value })}
                    className="w-full px-4 py-2 bg-background border border-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600/50"
                  />
                </div>
                <Button type="submit" className="orange-glow md:col-span-2" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Project'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {isLoading ? (
        <div className="text-center py-20 text-muted-foreground">Loading projects...</div>
      ) : !projects || projects.length === 0 ? (
        <div className="glass-card p-12 rounded-lg text-center">
          <FolderKanban className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
          <p className="text-muted-foreground">No projects yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project, index) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                className="hover:orange-glow transition-all duration-300 cursor-pointer h-full"
                onClick={() => selectProject(project)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    <Badge variant="outline">{project.code}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <Badge variant={project.status === 'active' ? 'success' : 'secondary'} className="capitalize">
                      {project.status}
                    </Badge>
                    {project.overall_health_score != null && (
                      <span className={`font-semibold ${getHealthColor(project.overall_health_score)}`}>
                        {Math.round(project.overall_health_score)}% health
                      </span>
                    )}
                  </div>

                  {project.location && (
                    <div className="flex items-center text-sm text-muted-foreground">
                      <MapPin className="w-4 h-4 mr-2" />
                      {project.location}
                    </div>
                  )}

                  <div className="flex items-center text-sm text-muted-foreground">
                    <Calendar className="w-4 h-4 mr-2" />
                    {formatDate(project.start_date)} &ndash; {formatDate(project.planned_end_date)}
                  </div>

                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-orange-600 h-2 rounded-full"
                      style={{ width: `${Math.min(100, project.progress_percentage || 0)}%` }}
                    />
                  </div>

                  <Button variant="ghost" className="w-full justify-between px-0">
                    Open Dashboard
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
