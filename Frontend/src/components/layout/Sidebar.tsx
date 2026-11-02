import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity,
  AudioLines,
  FileWarning,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Settings,
  X,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { cn } from '../../lib/cn'

export interface NavItem {
  to: string
  label: string
  icon: ReactNode
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Overview', icon: <LayoutDashboard size={20} strokeWidth={1.75} /> },
  { to: '/scenario-lab', label: 'Scenario Lab', icon: <FlaskConical size={20} strokeWidth={1.75} /> },
  { to: '/test-execution', label: 'Test Execution', icon: <Activity size={20} strokeWidth={1.75} /> },
  { to: '/audio-analysis', label: 'Audio Analysis', icon: <AudioLines size={20} strokeWidth={1.75} /> },
  { to: '/failure-reports', label: 'Failure Reports', icon: <FileWarning size={20} strokeWidth={1.75} /> },
  { to: '/settings', label: 'Settings', icon: <Settings size={20} strokeWidth={1.75} /> },
]

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1 px-3">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'group relative flex items-center gap-2 rounded-lg px-3 py-3 text-base leading-5 transition-colors',
              isActive
                ? 'active-sidebar-item bg-signal/10 text-text-primary'
                : 'bg-transparent text-text-muted hover:bg-panel-raised/60 hover:text-text-primary',
            )
          }
        >
          {item.icon}
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

function BrandBadge({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-4', compact && 'pt-14 md:pt-4')}>
      <div
        className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-signal bg-linear-to-t from-[color-mix(in_oklab,var(--color-signal)_80%,black)] to-signal"
        aria-hidden="true"
      >
        <span className="text-void">🎙️</span>
      </div>
      <div className="min-w-0 leading-tight">
        <div className="truncate text-base font-medium text-text-primary">VoiceCrashLab</div>
        <div className="truncate text-xs text-text-muted">Adversarial audio testing</div>
      </div>
    </div>
  )
}

function SidebarSectionLabel() {
  return (
    <div className="px-5 py-3 text-base font-normal tracking-tight text-text-muted/70">
      Workspace
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="no-scrollbar hidden w-60 shrink-0 flex-col overflow-y-auto bg-charcoal md:flex">
      <BrandBadge />
      <SidebarSectionLabel />
      <SidebarNav />
      <div className="mt-auto flex items-center justify-between gap-3 px-4 py-4">
        <div className="min-w-0">
          <div className="truncate text-base font-medium leading-none text-text-primary">v1.0.0</div>
          <div className="mt-1 text-xs leading-none text-text-muted">voicecrashlab</div>
        </div>
        <span className="premium-badge">Local</span>
      </div>
    </aside>
  )
}

export function MobileSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-void/75 md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-y-auto bg-charcoal md:hidden"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'tween', duration: 0.25 }}
          >
            <div className="flex items-center justify-between">
              <BrandBadge compact />
              <button
                onClick={onClose}
                aria-label="Close navigation"
                className="mr-3 rounded-lg p-2 text-text-muted hover:bg-panel-raised hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>
            <SidebarSectionLabel />
            <SidebarNav onNavigate={onClose} />
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}

export function Header({ toggleSidebar }: { toggleSidebar: () => void }) {
  const { pathname } = useLocation()
  const label = navItems.find((i) => i.to === pathname)?.label ?? 'Overview'
  return (
    <header className="flex shrink-0 flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={toggleSidebar}
          aria-label="Open navigation"
          className="rounded-lg p-2 text-text-muted hover:bg-panel-raised hover:text-text-primary md:hidden"
        >
          <Menu size={20} />
        </button>
        <motion.h1
          key={label}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="truncate text-lg font-semibold leading-none text-text-primary md:text-xl"
        >
          {label}
        </motion.h1>
        <span className="hidden size-2 shrink-0 rounded-full bg-text-muted/50 sm:block" />
        <span className="hidden truncate text-sm text-text-muted md:block">
          Adversarial voice-agent testing
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="h-9 items-center rounded-md border border-line bg-panel px-3 text-sm text-text-muted sm:flex">
          v1.0.0
        </span>
        <SettingsButton />
      </div>
    </header>
  )
}

function SettingsButton() {
  const { pathname } = useLocation()
  if (pathname === '/settings') return null
  return (
    <NavLink
      to="/settings"
      aria-label="Settings"
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line bg-panel text-text-muted transition-colors hover:bg-panel-raised hover:text-text-primary"
    >
      <Settings size={16} />
    </NavLink>
  )
}

export function MainLayout({ children }: { children: ReactNode }) {
  return (
    <div className="no-scrollbar flex h-screen w-full overflow-hidden bg-void">
      {children}
    </div>
  )
}

export function MainPane({ children }: { children: ReactNode }) {
  return (
    <main className="my-0.5 mr-0.5 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg bg-charcoal shadow-custom">
      {children}
    </main>
  )
}
