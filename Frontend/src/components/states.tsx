import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-text-muted">
      <div className="relative h-8 w-8">
        <motion.span
          className="absolute inset-0 rounded-full border-2 border-signal border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
        />
        <motion.span
          className="absolute inset-1 rounded-full border-2 border-electric border-b-transparent"
          animate={{ rotate: -360 }}
          transition={{ duration: 1.4, repeat: Infinity, ease: 'linear' }}
        />
      </div>
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-line py-16 text-center">
      {icon && <div className="text-3xl opacity-70">{icon}</div>}
      <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      {description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
}: {
  title?: string
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-failure/30 bg-failure/5 py-16 text-center">
      <div className="text-3xl">⚠️</div>
      <h3 className="text-sm font-semibold text-failure">{title}</h3>
      {message && <p className="max-w-sm text-sm text-text-muted">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-lg border border-failure/40 bg-failure/15 px-4 py-2 text-xs font-medium text-failure transition-colors hover:bg-failure/25"
        >
          Retry
        </button>
      )}
    </div>
  )
}
