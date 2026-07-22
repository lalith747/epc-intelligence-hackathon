import { ReactNode } from 'react'
import Sidebar from '../dashboard/Sidebar'
import Header from '../dashboard/Header'
import FloatingChat from '../chat/FloatingChat'

export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <Sidebar />
        <div className="flex-1">
          <Header />
          <main className="p-6">
            {children}
          </main>
          <FloatingChat />
        </div>
      </div>
    </div>
  )
}
