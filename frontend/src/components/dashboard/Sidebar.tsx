import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useUIStore, useAuthStore } from '@/lib/store'
import { 
  LayoutDashboard, 
  FolderKanban, 
  Calendar, 
  ShoppingCart, 
  AlertTriangle, 
  FileText, 
  Settings,
  X,
  MessageSquare,
  ShieldCheck,
  Mail,
  Bot,
  Database,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Documents', href: '/documents', icon: FolderKanban },
  { name: 'Compliance', href: '/compliance', icon: ShieldCheck },
  { name: 'Schedule', href: '/schedule', icon: Calendar },
  { name: 'Procurement', href: '/procurement', icon: ShoppingCart },
  { name: 'Communications', href: '/communications', icon: Mail },
  { name: 'Knowledge Base', href: '/knowledge', icon: Database },
  { name: 'Chat', href: '/chat', icon: Bot },
  { name: 'Risks', href: '/risks', icon: AlertTriangle },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const location = useLocation()
  const { sidebarOpen, setSidebarOpen } = useUIStore()
  const { user } = useAuthStore()

  // On desktop the sidebar is a static column and must always be visible,
  // regardless of `sidebarOpen` (which only controls the mobile overlay and
  // may be persisted as `false` from a previous mobile session).
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== 'undefined' && window.innerWidth >= 1024
  )
  useEffect(() => {
    const mql = window.matchMedia('(min-width: 1024px)')
    const update = () => setIsDesktop(mql.matches)
    update()
    mql.addEventListener('change', update)
    return () => mql.removeEventListener('change', update)
  }, [])

  const isOpen = isDesktop || sidebarOpen

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && !isDesktop && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        />
      )}

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ x: isOpen ? 0 : -320 }}
        className={cn(
          "fixed top-0 left-0 z-50 h-screen w-80 bg-card border-r border-border/50 lg:static lg:translate-x-0",
          "glass-card"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex items-center justify-between p-6 border-b border-border/50">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center">
                <LayoutDashboard className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gradient">AI Monitor</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-muted-foreground hover:text-foreground"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => {
                    // Only auto-close the overlay sidebar on mobile — on desktop
                    // (lg breakpoint) it's a static column and should stay open.
                    if (window.innerWidth < 1024) setSidebarOpen(false)
                  }}
                  className={cn(
                    "flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200",
                    "hover:bg-accent hover:text-accent-foreground",
                    isActive
                      ? "bg-orange-600/20 text-orange-600 border border-orange-600/30"
                      : "text-muted-foreground"
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* User info */}
          <div className="p-4 border-t border-border/50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-semibold">
                {user?.first_name?.[0]}{user?.last_name?.[0]}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">{user?.first_name} {user?.last_name}</p>
                <p className="text-xs text-muted-foreground capitalize">{user?.role?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
