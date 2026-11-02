import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

/* Capitalio page section: full-width vertical stack, p-4 pb-8 md:p-8 */
export function PageShell({ children }: { children: ReactNode }) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex min-h-full w-full flex-col gap-4 p-4 pb-8 md:p-8"
    >
      {children}
    </motion.main>
  )
}

export function PageSection({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-3">
      <h2 className="truncate text-lg font-medium leading-6 text-text-primary">{title}</h2>
      {children}
    </section>
  )
}
