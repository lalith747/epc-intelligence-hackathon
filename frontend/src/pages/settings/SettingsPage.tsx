import { useAuthStore, useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { User, FolderKanban, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function SettingsPage() {
  const { user, logout } = useAuthStore()
  const { selectedProject } = useProjectStore()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <User className="w-5 h-5 text-orange-600" />
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center text-white text-xl font-semibold">
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
            <div>
              <p className="text-lg font-medium">{user?.first_name} {user?.last_name}</p>
              <p className="text-muted-foreground">{user?.email}</p>
              <Badge variant="orange" className="capitalize mt-1">{user?.role?.replace('_', ' ')}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-orange-600" />
            Active Project
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {selectedProject ? (
            <div className="space-y-1">
              <p className="font-medium">{selectedProject.name} <span className="text-muted-foreground">({selectedProject.code})</span></p>
              <p className="text-muted-foreground capitalize">Status: {selectedProject.status}</p>
              <p className="text-muted-foreground">Progress: {Math.round(selectedProject.progress_percentage || 0)}%</p>
            </div>
          ) : (
            <p className="text-muted-foreground">No project selected. Choose one from the Projects page.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Session</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
