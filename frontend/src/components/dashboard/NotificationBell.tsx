import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { intelligenceAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Bell, AlertTriangle, Clock, ShoppingCart, CheckCircle2, ShieldAlert } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Notification {
  id: string
  notification_type: string
  severity: string
  title: string
  message: string
  related_entity_type: string | null
  is_read: boolean
  created_at: string
}

const TYPE_ICON: Record<string, typeof Bell> = {
  risk_alert: ShieldAlert,
  procurement_issue: ShoppingCart,
  schedule_delay: Clock,
  pending_approval: CheckCircle2,
  compliance_failure: AlertTriangle,
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500',
}

const ENTITY_ROUTE: Record<string, string> = {
  risk: '/risks',
  purchase_order: '/procurement',
  compliance_issue: '/compliance',
  schedule_task: '/schedule',
  recommendation: '/reports',
  project: '/dashboard',
}

const PANEL_WIDTH = 384 // 24rem

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState({ top: 0, right: 0 })
  const buttonRef = useRef<HTMLButtonElement>(null)
  const { selectedProject } = useProjectStore()
  const navigate = useNavigate()

  const { data: allNotifications = [] } = useQuery<Notification[]>({
    queryKey: ['intelligence-notifications'],
    queryFn: async () => (await intelligenceAPI.notifications()).data,
    refetchInterval: 20000,
  })

  const { data: notifications } = useQuery<Notification[]>({
    queryKey: ['intelligence-notifications-open'],
    queryFn: async () => (await intelligenceAPI.notifications()).data,
    enabled: open,
  })

  const unread = allNotifications.filter((item) => !item.is_read).length

  const toggleOpen = () => {
    if (!open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      setCoords({
        top: rect.bottom + 8,
        right: Math.max(8, window.innerWidth - rect.right),
      })
    }
    setOpen((v) => !v)
  }

  // Close on scroll/resize so the panel never drifts away from the bell.
  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    return () => {
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
    }
  }, [open])

  const handleClickNotification = (n: Notification) => {
    setOpen(false)
    const route = n.related_entity_type ? ENTITY_ROUTE[n.related_entity_type] : null
    if (route) navigate(route)
  }

  return (
    <>
      <button
        ref={buttonRef}
        className="relative p-2 rounded-lg hover:bg-accent transition-colors"
        onClick={toggleOpen}
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 rounded-full bg-orange-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open &&
        createPortal(
          <>
            <div className="fixed inset-0 z-[100]" onClick={() => setOpen(false)} />
            <div
              className="fixed max-h-[70vh] overflow-hidden flex flex-col bg-card border border-border rounded-xl shadow-2xl z-[101]"
              style={{
                top: coords.top,
                right: coords.right,
                width: `min(${PANEL_WIDTH}px, calc(100vw - 16px))`,
              }}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/50 shrink-0">
                <p className="font-semibold text-sm">
                  Notifications
                  {unread > 0 && (
                    <span className="ml-2 text-xs font-normal text-muted-foreground">{unread} unread</span>
                  )}
                </p>
                {unread > 0 && <span className="text-xs text-muted-foreground">Auto-refreshed</span>}
              </div>

              <div className="overflow-y-auto">
                {!selectedProject ? (
                  <p className="text-sm text-muted-foreground text-center py-10">Select a project to see alerts.</p>
                ) : !notifications || notifications.length === 0 ? (
                  <div className="text-center py-10">
                    <Bell className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">No notifications yet.</p>
                  </div>
                ) : (
                  notifications.map((n) => {
                    const Icon = TYPE_ICON[n.notification_type] || Bell
                    return (
                      <button
                        key={n.id}
                        onClick={() => handleClickNotification(n)}
                        className={cn(
                          'w-full text-left flex gap-3 px-4 py-3 border-b border-border/50 last:border-0 hover:bg-accent transition-colors',
                          !n.is_read && 'bg-orange-500/10'
                        )}
                      >
                        <div
                          className={cn(
                            'shrink-0 mt-0.5 w-8 h-8 rounded-full flex items-center justify-center',
                            n.severity === 'critical' && 'bg-red-500/15 text-red-500',
                            n.severity === 'high' && 'bg-orange-500/15 text-orange-600',
                            n.severity === 'medium' && 'bg-yellow-500/15 text-yellow-600',
                            n.severity === 'low' && 'bg-blue-500/15 text-blue-500'
                          )}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <p className={cn('text-sm leading-snug', !n.is_read ? 'font-semibold' : 'font-medium')}>
                              {n.title}
                            </p>
                            {!n.is_read && (
                              <span
                                className={cn(
                                  'shrink-0 mt-1 w-2 h-2 rounded-full',
                                  SEVERITY_DOT[n.severity] || 'bg-gray-400'
                                )}
                              />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{n.message}</p>
                        </div>
                      </button>
                    )
                  })
                )}
              </div>
            </div>
          </>,
          document.body
        )}
    </>
  )
}
