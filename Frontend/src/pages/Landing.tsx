import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

/* Flowing blue-violet contour-line artwork (decorative only) */
function ContourArt({ animate }: { animate: boolean }) {
  const drift = animate
    ? { y: [0, -10, 0], opacity: [0.5, 0.75, 0.5] }
    : { y: 0, opacity: 0.6 }
  return (
    <motion.svg
      aria-hidden="true"
      viewBox="0 0 600 400"
      className="absolute inset-y-0 right-0 h-full w-[60%] max-w-2xl"
      animate={drift}
      transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
      style={{ opacity: 0.55 }}
      fill="none"
    >
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <path
          key={i}
          d={`M -40 ${80 + i * 44} C 120 ${20 + i * 40}, 240 ${150 + i * 30}, 420 ${90 + i * 34} S 640 ${60 + i * 28}, 720 ${140 + i * 26}`}
          stroke={i % 2 === 0 ? 'var(--color-signal)' : 'var(--color-electric)'}
          strokeWidth={1.25}
          strokeOpacity={0.5 - i * 0.045}
          strokeLinecap="round"
        />
      ))}
    </motion.svg>
  )
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const [reduceMotion, setReduceMotion] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('vcl-settings')
      if (raw && JSON.parse(raw).reduceMotion) setReduceMotion(true)
    } catch {
      // ignore storage errors
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') onEnter()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onEnter])

  return (
    <div
      onClick={onEnter}
      role="button"
      aria-label="Enter VoiceCrashLab dashboard"
      tabIndex={0}
      className="aurora-outer flex h-screen w-full cursor-pointer items-center justify-center p-3 sm:p-6"
    >
      <div className="relative flex h-full w-full max-w-[1400px] flex-col overflow-hidden rounded-[2rem] border border-line bg-void shadow-custom">
        {/* Minimal header */}
        <div className="flex shrink-0 items-center justify-between px-8 py-6">
          <div className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-signal glow-signal" />
            <span className="text-sm font-semibold tracking-tight text-text-primary">
              VoiceCrashLab
            </span>
          </div>
          <span className="text-xs text-text-dim">v1.0.0</span>
        </div>

        {/* Title + contour artwork */}
      <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center px-8">
          <ContourArt animate={!reduceMotion} />
          <motion.h1
            initial={reduceMotion ? false : { opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
            className="relative z-10 cursor-pointer select-none text-center text-6xl font-bold tracking-tight text-text-primary md:text-8xl"
          >
            Voice<span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: 'linear-gradient(90deg, var(--color-signal), var(--color-electric))',
              }}
            >
              Crash
            </span>
            Lab
          </motion.h1>
          <motion.p
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: 'easeOut' }}
            className="relative z-10 mt-6 cursor-pointer select-none text-center text-base font-medium tracking-tight text-text-muted md:text-lg"
          >
            Break the voice.{' '}
            <span style={{ color: 'var(--color-signal)' }}>Expose the failure.</span> Build trust in
            every conversation.
          </motion.p>
        </div>

        {/* Invisible footer spacer preserves breathing room */}
        <div className="h-20 shrink-0" />
      </div>
    </div>
  )
}
