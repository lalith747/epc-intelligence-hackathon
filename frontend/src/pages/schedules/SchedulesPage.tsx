import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { schedulesAPI, agentsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Modal, DetailRow } from '@/components/ui/modal'
import { Zap, ListTree, AlertCircle, Flag, Diamond } from 'lucide-react'
import { formatDate, cn } from '@/lib/utils'

interface ScheduleRecord {
  id: string
  name: string
  version: string
  source_type: string | null
  baseline_date: string
  data_date: string | null
  total_activities: number
}

interface Activity {
  id: string
  activity_id: string
  activity_name: string
  wbs_code: string | null
  original_duration: number | null
  remaining_duration: number | null
  percent_complete: number
  start_date: string | null
  finish_date: string | null
  early_start: string | null
  early_finish: string | null
  is_critical: boolean
  is_milestone: boolean
}

function activityDates(a: Activity): { start: Date | null; finish: Date | null } {
  const start = a.start_date || a.early_start
  const finish = a.finish_date || a.early_finish
  return { start: start ? new Date(start) : null, finish: finish ? new Date(finish) : null }
}

/** Behind schedule if remaining work exceeds what the calendar says is left. */
function isBehind(a: Activity, today: Date): boolean {
  const { start, finish } = activityDates(a)
  if (!start || !finish || a.percent_complete >= 100) return false
  const total = finish.getTime() - start.getTime()
  if (total <= 0) return false
  const elapsed = Math.min(Math.max(today.getTime() - start.getTime(), 0), total)
  const expectedProgress = (elapsed / total) * 100
  return expectedProgress - a.percent_complete > 10
}

export default function SchedulesPage() {
  const { selectedProject } = useProjectStore()
  const queryClient = useQueryClient()
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null)

  const { data: schedules } = useQuery<ScheduleRecord[]>({
    queryKey: ['schedules', selectedProject?.id],
    queryFn: async () => (await schedulesAPI.list(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const schedule = schedules?.[0]

  const { data: activities, isLoading } = useQuery<Activity[]>({
    queryKey: ['activities', schedule?.id],
    queryFn: async () => (await schedulesAPI.activities(schedule!.id)).data,
    enabled: !!schedule,
  })

  const runAgent = useMutation({
    mutationFn: () =>
      agentsAPI.execute({
        agent_name: 'schedule_agent',
        project_id: selectedProject!.id,
        execution_type: 'on_demand',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules', selectedProject?.id] })
      queryClient.invalidateQueries({ queryKey: ['activities', schedule?.id] })
    },
  })

  const today = useMemo(() => new Date(), [])

  // Overall timeline window for the Gantt bars
  const window = useMemo(() => {
    if (!activities || activities.length === 0) return null
    let min = Infinity
    let max = -Infinity
    activities.forEach((a) => {
      const { start, finish } = activityDates(a)
      if (start) min = Math.min(min, start.getTime())
      if (finish) max = Math.max(max, finish.getTime())
    })
    if (!isFinite(min) || !isFinite(max) || max <= min) return null
    return { min, max, span: max - min }
  }, [activities])

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view schedules</p>
      </div>
    )
  }

  const behindCount = activities?.filter((a) => isBehind(a, today)).length || 0
  const criticalCount = activities?.filter((a) => a.is_critical).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Schedule</h1>
          <p className="text-muted-foreground">
            {schedule ? `${schedule.name} · ${schedule.version} · Data date ${schedule.data_date ? formatDate(schedule.data_date) : '—'}` : selectedProject.name}
          </p>
        </div>
        <Button className="orange-glow" onClick={() => runAgent.mutate()} disabled={runAgent.isPending}>
          <Zap className="w-4 h-4 mr-2" />
          {runAgent.isPending ? 'Running...' : 'Run Schedule Agent'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Activities</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{activities?.length || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">On Critical Path</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-orange-600">{criticalCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Behind Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={cn('text-2xl font-bold', behindCount > 0 ? 'text-red-500' : 'text-green-500')}>
              {behindCount}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ListTree className="w-5 h-5 text-orange-600" />
            Activity Schedule
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : !activities || activities.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No activities loaded yet. Upload a schedule to populate this view.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[900px]">
                <thead>
                  <tr className="border-b border-border/60 text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="text-left py-2 px-3 w-24">ID</th>
                    <th className="text-left py-2 px-3">Activity</th>
                    <th className="text-left py-2 px-3 w-28">Start</th>
                    <th className="text-left py-2 px-3 w-28">Finish</th>
                    <th className="text-right py-2 px-3 w-16">Dur.</th>
                    <th className="text-left py-2 px-3 w-36">Progress</th>
                    <th className="text-left py-2 px-3 min-w-[220px]">Timeline</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.map((a) => {
                    const { start, finish } = activityDates(a)
                    const behind = isBehind(a, today)
                    const barColor = a.is_critical ? '#ea580c' : '#3b82f6'
                    let left = 0
                    let width = 0
                    if (window && start && finish) {
                      left = ((start.getTime() - window.min) / window.span) * 100
                      width = Math.max(((finish.getTime() - start.getTime()) / window.span) * 100, 1.5)
                    }
                    const todayPct = window
                      ? Math.min(Math.max(((today.getTime() - window.min) / window.span) * 100, 0), 100)
                      : null

                    return (
                      <tr
                        key={a.id}
                        className="border-b border-border/40 hover:bg-accent/50 cursor-pointer"
                        onClick={() => setSelectedActivity(a)}
                      >
                        <td className="py-2.5 px-3 font-mono text-xs">{a.activity_id}</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{a.activity_name}</span>
                            {a.is_critical && (
                              <span title="Critical path">
                                <Flag className="w-3.5 h-3.5 text-orange-600 shrink-0" />
                              </span>
                            )}
                            {a.is_milestone && (
                              <span title="Milestone">
                                <Diamond className="w-3.5 h-3.5 text-purple-500 shrink-0" />
                              </span>
                            )}
                            {behind && (
                              <span title="Behind schedule">
                                <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">{start ? formatDate(start) : '—'}</td>
                        <td className="py-2.5 px-3 whitespace-nowrap">{finish ? formatDate(finish) : '—'}</td>
                        <td className="py-2.5 px-3 text-right">{a.original_duration ?? '—'}d</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-secondary rounded-full h-2 min-w-[60px]">
                              <div
                                className={cn('h-2 rounded-full', behind ? 'bg-red-500' : 'bg-green-500')}
                                style={{ width: `${Math.min(100, a.percent_complete)}%` }}
                              />
                            </div>
                            <span className="text-xs w-9 text-right">{Math.round(a.percent_complete)}%</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="relative h-5 bg-secondary/60 rounded">
                            {window && start && finish && (
                              <div
                                className="absolute top-1 bottom-1 rounded-sm"
                                style={{
                                  left: `${left}%`,
                                  width: `${width}%`,
                                  background: barColor,
                                  opacity: 0.35,
                                }}
                              />
                            )}
                            {window && start && finish && (
                              <div
                                className="absolute top-1 bottom-1 rounded-sm"
                                style={{
                                  left: `${left}%`,
                                  width: `${(width * Math.min(100, a.percent_complete)) / 100}%`,
                                  background: barColor,
                                }}
                              />
                            )}
                            {todayPct !== null && (
                              <div
                                className="absolute top-0 bottom-0 w-px bg-red-500/80"
                                style={{ left: `${todayPct}%` }}
                                title="Today"
                              />
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div className="flex items-center gap-5 mt-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-2 rounded-sm inline-block" style={{ background: '#ea580c' }} /> Critical path
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-2 rounded-sm inline-block" style={{ background: '#3b82f6' }} /> Non-critical
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-px h-3 bg-red-500 inline-block" /> Today
                </span>
                <span className="flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3 text-red-500" /> Behind schedule
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Modal
        open={!!selectedActivity}
        onClose={() => setSelectedActivity(null)}
        title={selectedActivity?.activity_name || ''}
        subtitle={selectedActivity?.activity_id}
      >
        {selectedActivity && (
          <div className="space-y-4">
            <div className="flex gap-2">
              {selectedActivity.is_critical && <Badge variant="orange">Critical Path</Badge>}
              {selectedActivity.is_milestone && <Badge variant="secondary">Milestone</Badge>}
              {isBehind(selectedActivity, today) && <Badge variant="destructive">Behind Schedule</Badge>}
            </div>
            <div>
              <DetailRow label="WBS Code" value={selectedActivity.wbs_code} />
              <DetailRow
                label="Start"
                value={activityDates(selectedActivity).start ? formatDate(activityDates(selectedActivity).start!) : null}
              />
              <DetailRow
                label="Finish"
                value={activityDates(selectedActivity).finish ? formatDate(activityDates(selectedActivity).finish!) : null}
              />
              <DetailRow label="Original Duration" value={selectedActivity.original_duration != null ? `${selectedActivity.original_duration} days` : null} />
              <DetailRow label="Remaining Duration" value={selectedActivity.remaining_duration != null ? `${selectedActivity.remaining_duration} days` : null} />
              <DetailRow label="% Complete" value={`${Math.round(selectedActivity.percent_complete)}%`} />
            </div>
            {isBehind(selectedActivity, today) && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm space-y-1">
                <p className="font-semibold text-red-500">Recovery measures</p>
                <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                  {selectedActivity.is_critical && (
                    <li>This activity is on the critical path — every day lost here delays project completion directly.</li>
                  )}
                  <li>Consider adding a second shift or weekend working to recover the progress gap.</li>
                  <li>Check whether predecessor handover or material availability is the constraint before adding labour.</li>
                  <li>Re-sequence remaining work to run non-dependent tasks in parallel where possible.</li>
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
