import { useUIStore, useProjectStore } from '@/lib/store'
import { useAuthStore } from '@/lib/store'
import { Menu, LogOut, FolderKanban, ChevronRight, ChevronDown } from 'lucide-react'
import { Button } from '../ui/button'
import NotificationBell from './NotificationBell'
import { useLocation, useNavigate } from 'react-router-dom'

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/projects': 'Projects',
  '/documents': 'Documents',
  '/compliance': 'Compliance',
  '/schedule': 'Schedule',
  '/procurement': 'Procurement',
  '/communications': 'Communications',
  '/knowledge': 'Knowledge Base',
  '/chat': 'Chat',
  '/suppliers': 'Suppliers',
  '/risks': 'Risks',
  '/analytics': 'Analytics',
  '/reports': 'Reports',
  '/settings': 'Settings',
}

export default function Header() {
  const { setSidebarOpen } = useUIStore()
  const { user, logout } = useAuthStore()
  const { selectedProject } = useProjectStore()
  const navigate = useNavigate()
  const location = useLocation()

  const pageTitle = pageTitles[location.pathname] || 'AI Monitor'

  return (
    <header className="h-16 border-b border-border/50 glass-card flex items-center justify-between px-6 gap-4">
      <div className="flex items-center space-x-4 min-w-0">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarOpen(true)}
          className="lg:hidden shrink-0"
        >
          <Menu className="w-6 h-6" />
        </Button>

        <div className="flex items-center gap-2 min-w-0">
          <h1 className="text-lg font-semibold shrink-0">{pageTitle}</h1>

          {selectedProject && (
            <>
              <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 hidden sm:block" />
              <button
                onClick={() => navigate('/projects')}
                title="Switch project"
                className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border/70 bg-secondary/60 hover:bg-secondary transition-colors min-w-0"
              >
                <FolderKanban className="w-4 h-4 text-orange-600 shrink-0" />
                <span className="text-sm font-medium truncate max-w-[220px]">{selectedProject.name}</span>
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              </button>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4 shrink-0">
        <NotificationBell />

        <div className="flex items-center space-x-3">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium">{user?.first_name} {user?.last_name}</p>
            <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white font-semibold cursor-pointer">
            {user?.first_name?.[0]}{user?.last_name?.[0]}
          </div>
          <Button
            variant="ghost"
            size="icon"
            title="Sign out"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </header>
  )
}
