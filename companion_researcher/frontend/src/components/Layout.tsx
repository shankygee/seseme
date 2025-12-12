import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, Settings, History, BookOpen, Sliders } from 'lucide-react'
import { useStore } from '../hooks/useStore'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const {
    activePersonality,
    toggleControlPanel,
    toggleSessionsPanel,
    showControlPanel,
    showSessionsPanel,
  } = useStore()

  const navItems = [
    { path: '/', icon: MessageSquare, label: 'Chat' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="flex h-screen bg-companion-bg">
      {/* Sidebar */}
      <aside className="w-16 flex flex-col items-center py-4 bg-companion-surface border-r border-companion-border">
        {/* Logo */}
        <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center mb-8">
          <BookOpen className="w-6 h-6 text-white" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 flex flex-col gap-2">
          {navItems.map(({ path, icon: Icon, label }) => (
            <Link
              key={path}
              to={path}
              className={clsx(
                'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
                location.pathname === path
                  ? 'bg-primary-600 text-white'
                  : 'text-companion-muted hover:text-companion-text hover:bg-companion-border'
              )}
              title={label}
            >
              <Icon className="w-5 h-5" />
            </Link>
          ))}

          <button
            onClick={toggleSessionsPanel}
            className={clsx(
              'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
              showSessionsPanel
                ? 'bg-primary-600 text-white'
                : 'text-companion-muted hover:text-companion-text hover:bg-companion-border'
            )}
            title="Sessions"
          >
            <History className="w-5 h-5" />
          </button>

          <button
            onClick={toggleControlPanel}
            className={clsx(
              'w-10 h-10 rounded-lg flex items-center justify-center transition-colors',
              showControlPanel
                ? 'bg-primary-600 text-white'
                : 'text-companion-muted hover:text-companion-text hover:bg-companion-border'
            )}
            title="Control Panel"
          >
            <Sliders className="w-5 h-5" />
          </button>
        </nav>

        {/* Active Personality Indicator */}
        {activePersonality && (
          <div
            className="w-10 h-10 rounded-lg bg-companion-border flex items-center justify-center text-xs font-medium"
            title={activePersonality.name}
          >
            {activePersonality.id.slice(0, 2).toUpperCase()}
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">{children}</main>
    </div>
  )
}
