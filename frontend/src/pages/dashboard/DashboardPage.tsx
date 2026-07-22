import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { analyticsAPI, agentsAPI, projectsAPI, notificationsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  ShoppingCart,
  ArrowUpRight,
  Zap,
  Building2,
  MapPin,
  Calendar,
  Wallet
} from 'lucide-react'
import { getHealthColor, getHealthBgColor, formatNumber, formatDate, formatCurrency } from '@/lib/utils'

interface ProjectDetail {
  name: string
  code: string
  description: string | null
  client_name: string | null
  location: string | null
  project_type: string | null
  status: string
  start_date: string
  planned_end_date: string
  total_budget: number | null
  budget_consumed: number
  currency: string
  progress_percentage: number
}

export default function DashboardPage() {
  const { selectedProject } = useProjectStore()
  const queryClient = useQueryClient()

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['dashboard-metrics', selectedProject?.id],
    queryFn: async () => (await analyticsAPI.getDashboardMetrics(selectedProject?.id || '')).data,
    enabled: !!selectedProject
  })

  const { data: project } = useQuery<ProjectDetail>({
    queryKey: ['project-detail', selectedProject?.id],
    queryFn: async () => (await projectsAPI.get(selectedProject!.id)).data,
    enabled: !!selectedProject
  })

  const runAnalysis = useMutation({
    mutationFn: () => agentsAPI.triggerAll(selectedProject!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-metrics', selectedProject?.id] })
      queryClient.invalidateQueries({ queryKey: ['risk-trend', selectedProject?.id] })
      queryClient.invalidateQueries({ queryKey: ['schedule-progress', selectedProject?.id] })
      queryClient.invalidateQueries({ queryKey: ['notifications', selectedProject?.id] })
      queryClient.invalidateQueries({ queryKey: ['notification-count', selectedProject?.id] })
    },
  })

  // Keep the notification engine current whenever the dashboard is viewed,
  // not only right after an agent run.
  useEffect(() => {
    if (!selectedProject) return
    notificationsAPI.scan(selectedProject.id).then(() => {
      queryClient.invalidateQueries({ queryKey: ['notification-count', selectedProject.id] })
    }).catch(() => {})
  }, [selectedProject?.id])

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view the dashboard</p>
      </div>
    )
  }

  if (isLoading) {
    return <div className="text-center py-20">Loading dashboard...</div>
  }

  const cards = [
    {
      title: 'Project Health',
      value: metrics?.project_health || 0,
      icon: TrendingUp,
      color: getHealthColor(metrics?.project_health || 0),
      bgColor: getHealthBgColor(metrics?.project_health || 0),
      suffix: '%'
    },
    {
      title: 'Schedule Health',
      value: metrics?.schedule_health || 0,
      icon: Clock,
      color: getHealthColor(metrics?.schedule_health || 0),
      bgColor: getHealthBgColor(metrics?.schedule_health || 0),
      suffix: '%'
    },
    {
      title: 'Procurement Health',
      value: metrics?.procurement_health || 0,
      icon: ShoppingCart,
      color: getHealthColor(metrics?.procurement_health || 0),
      bgColor: getHealthBgColor(metrics?.procurement_health || 0),
      suffix: '%'
    },
    {
      title: 'Risk Score',
      value: metrics?.risk_score || 0,
      icon: AlertTriangle,
      color: getHealthColor(100 - (metrics?.risk_score || 0)),
      bgColor: getHealthBgColor(100 - (metrics?.risk_score || 0)),
      suffix: ''
    },
    {
      title: 'Supplier Health',
      value: metrics?.supplier_health || 0,
      icon: CheckCircle,
      color: getHealthColor(metrics?.supplier_health || 0),
      bgColor: getHealthBgColor(metrics?.supplier_health || 0),
      suffix: '%'
    },
    {
      title: 'Completion',
      value: metrics?.completion_percentage || 0,
      icon: TrendingUp,
      color: getHealthColor(metrics?.completion_percentage || 0),
      bgColor: getHealthBgColor(metrics?.completion_percentage || 0),
      suffix: '%'
    }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">{selectedProject.name}</p>
        </div>
        <Button className="orange-glow" onClick={() => runAnalysis.mutate()} disabled={runAnalysis.isPending}>
          <Zap className="w-4 h-4 mr-2" />
          {runAnalysis.isPending ? 'Running...' : 'Run AI Analysis'}
        </Button>
      </div>

      {/* Project Overview */}
      {project && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Building2 className="w-5 h-5 text-orange-600" />
                Project Overview
              </CardTitle>
              <Badge variant={project.status === 'execution' ? 'success' : 'secondary'} className="capitalize">
                {project.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {project.description && (
              <p className="text-sm text-muted-foreground">{project.description}</p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {project.client_name && (
                <div>
                  <p className="text-muted-foreground text-xs mb-1">Client</p>
                  <p className="font-medium">{project.client_name}</p>
                </div>
              )}
              {project.location && (
                <div>
                  <p className="text-muted-foreground text-xs mb-1 flex items-center gap-1">
                    <MapPin className="w-3 h-3" /> Location
                  </p>
                  <p className="font-medium">{project.location}</p>
                </div>
              )}
              <div>
                <p className="text-muted-foreground text-xs mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> Timeline
                </p>
                <p className="font-medium">
                  {formatDate(project.start_date)} &ndash; {formatDate(project.planned_end_date)}
                </p>
              </div>
              {project.total_budget != null && (
                <div>
                  <p className="text-muted-foreground text-xs mb-1 flex items-center gap-1">
                    <Wallet className="w-3 h-3" /> Budget
                  </p>
                  <p className="font-medium">
                    {formatCurrency(project.budget_consumed, project.currency)} / {formatCurrency(project.total_budget, project.currency)}
                  </p>
                </div>
              )}
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-orange-600 h-2 rounded-full"
                style={{ width: `${Math.min(100, project.progress_percentage || 0)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{Math.round(project.progress_percentage)}% complete</p>
          </CardContent>
        </Card>
      )}

      {/* Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards.map((card, index) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className={`${card.bgColor} hover:orange-glow transition-all duration-300`}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center justify-between">
                  {card.title}
                  <card.icon className="w-4 h-4" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end justify-between">
                  <div>
                    <p className={`text-3xl font-bold ${card.color}`}>
                      {formatNumber(card.value)}{card.suffix}
                    </p>
                  </div>
                  <ArrowUpRight className={`w-5 h-5 ${card.color}`} />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Open Risks</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{metrics?.open_risks || 0}</p>
            <p className="text-sm text-muted-foreground mt-1">
              {metrics?.critical_risks || 0} critical
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{metrics?.active_recommendations || 0}</p>
            <p className="text-sm text-muted-foreground mt-1">
              Pending action
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">AI Agent Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <p className="text-2xl font-bold">Active</p>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              All systems operational
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
