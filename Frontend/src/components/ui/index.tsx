import { motion } from 'framer-motion'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md'

const base =
    'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/60'
const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-signal text-void border border-transparent hover:bg-signal-hover focus-visible:ring-signal/60 glow-signal',
  secondary:
    'bg-transparent text-text-muted border border-line hover:text-text-primary hover:bg-panel-raised',
  ghost:
    'text-text-muted hover:text-text-primary hover:bg-panel-raised border border-transparent',
  danger:
    'bg-failure/10 text-failure border border-failure/40 hover:bg-failure/20',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-3.5 text-sm',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...rest}>
      {children}
    </button>
  )
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  children: ReactNode
}

export function IconButton({ label, className = '', children, ...rest }: IconButtonProps) {
  return (
    <Tooltip label={label}>
      <button
        aria-label={label}
        className={`inline-flex h-9 w-9 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-panel-raised hover:text-text-primary ${className}`}
        {...rest}
      >
        {children}
      </button>
    </Tooltip>
  )
}

interface TooltipProps {
  label: string
  children: ReactNode
  side?: 'top' | 'bottom'
}

export function Tooltip({ label, children, side = 'bottom' }: TooltipProps) {
  return (
    <span className="group/tt relative inline-flex">
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-lg border border-line bg-panel-raised px-3 py-2 text-xs text-text-primary opacity-0 shadow-custom transition-opacity duration-150 group-hover/tt:opacity-100 ${
          side === 'bottom' ? 'top-full mt-2' : 'bottom-full mb-2'
        }`}
      >
        {label}
      </span>
    </span>
  )
}

interface CardProps {
  children: ReactNode
  className?: string
}

/* Capitalio DashboardCard: flat bordered panel, p-4, faint inner shadow */
export function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`shadow-custom min-w-0 rounded-lg border border-line bg-panel p-4 text-text-primary ${className}`}
    >
      {children}
    </div>
  )
}

export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={`truncate text-lg font-medium leading-6 text-text-primary ${className}`}>
      {children}
    </h3>
  )
}

export type BadgeTone = 'violet' | 'cyan' | 'highlight' | 'green' | 'red' | 'warn' | 'neutral'

/* Capitalio DetailTag: rounded pill, text in chart color on a 10% color-mix fill */
const badgeTones: Record<BadgeTone, { color: string; bg: string; text: string }> = {
  violet: { color: 'var(--color-signal)', bg: 'bg-signal/10', text: 'text-signal-hover' },
  cyan: { color: 'var(--color-electric)', bg: 'bg-electric/10', text: 'text-electric' },
  highlight: { color: 'var(--color-highlight)', bg: 'bg-highlight/10', text: 'text-highlight' },
  green: { color: 'var(--color-success)', bg: 'bg-success/10', text: 'text-success' },
  red: { color: 'var(--color-failure)', bg: 'bg-failure/10', text: 'text-failure' },
  warn: { color: 'var(--color-warn)', bg: 'bg-warn/10', text: 'text-warn' },
  neutral: { color: 'var(--color-text-muted)', bg: 'bg-text-muted/10', text: 'text-text-muted' },
}

export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  const t = badgeTones[tone]
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-lg px-3 py-1 text-sm leading-5 ${t.bg} ${t.text} ${className}`}
    >
      {children}
    </span>
  )
}

export type StatusType = 'online' | 'offline' | 'warning' | 'idle'

const statusMap: Record<StatusType, { color: string; label: string }> = {
  online: { color: 'bg-success', label: 'Connected' },
  offline: { color: 'bg-failure', label: 'Disconnected' },
  warning: { color: 'bg-warn', label: 'Degraded' },
  idle: { color: 'bg-text-dim', label: 'Idle' },
}

/* Capitalio ChartMarker: small square swatch */
export type ChartMarkerTone = 'signal' | 'electric' | 'success' | 'failure' | 'warn' | 'neutral'

const markerMap: Record<ChartMarkerTone, string> = {
  signal: 'bg-signal',
  electric: 'bg-electric',
  success: 'bg-success',
  failure: 'bg-failure',
  warn: 'bg-warn',
  neutral: 'bg-text-muted',
}

export function ChartMarker({ tone = 'neutral', className = '' }: { tone?: ChartMarkerTone; className?: string }) {
  return <span className={`size-3 shrink-0 rounded-xs ${markerMap[tone]} ${className}`} />
}

export function StatusIndicator({ status, label }: { status: StatusType; label?: string }) {
  const { color, label: defaultLabel } = statusMap[status]
  return (
    <span className="inline-flex items-center gap-2 text-xs text-text-muted">
      <span className="relative flex h-2 w-2">
        <motion.span
          className={`absolute inline-flex h-full w-full rounded-full ${color} opacity-60`}
          animate={{ scale: [1, 1.6, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${color}`} />
      </span>
      {label ?? defaultLabel}
    </span>
  )
}
