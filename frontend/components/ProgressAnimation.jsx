'use client'

export function ScoreRing({ score, display, size = 120 }) {
  const r = (size / 2) - 8
  const circ = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(10, display)) / 10
  const dash = pct * circ
  const color = score >= 3 ? 'var(--accent3)' : score >= 0 ? 'var(--accent2)' : 'var(--danger)'

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r}
          fill="none" stroke="var(--border)" strokeWidth={6} />
        <circle cx={size/2} cy={size/2} r={r}
          fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={`${dash.toFixed(1)} ${circ.toFixed(1)}`}
          strokeLinecap="round" />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          fontFamily: 'var(--font-head)',
          fontSize: size * 0.25, fontWeight: 800, color,
        }}>
          {display}
        </div>
        <div style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '0.1em' }}>
          /10
        </div>
      </div>
    </div>
  )
}

const PHASES = ['Setup', 'Prereqs', 'Approach', 'Roadmap', 'Weekly', 'Done']

export function PhaseProgress({ activeIndex }) {
  const pct = (activeIndex / (PHASES.length - 1)) * 100

  return (
    <div>
      <div style={{
        height: 2, background: 'var(--border)',
        borderRadius: 2, position: 'relative', marginBottom: 24,
      }}>
        <div style={{
          height: '100%',
          background: 'linear-gradient(90deg, var(--accent), var(--accent3))',
          borderRadius: 2,
          width: `${pct}%`,
          transition: 'width 0.6s cubic-bezier(.4,0,.2,1)',
        }} />
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          position: 'absolute', top: -5, left: 0, right: 0,
        }}>
          {PHASES.map((_, i) => (
            <div key={i} style={{
              width: 12, height: 12, borderRadius: '50%',
              border: '2px solid var(--bg)',
              background: i < activeIndex ? 'var(--accent3)'
                        : i === activeIndex ? 'var(--accent)'
                        : 'var(--border)',
              boxShadow: i === activeIndex ? '0 0 12px var(--accent)' : 'none',
              transition: 'all 0.4s',
            }} />
          ))}
        </div>
      </div>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: 10, color: 'var(--muted)', letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}>
        {PHASES.map((p, i) => (
          <span key={i} style={{
            color: i === activeIndex ? 'var(--accent)' : 'var(--muted)',
            transition: 'color 0.3s',
          }}>
            {p}
          </span>
        ))}
      </div>
    </div>
  )
}

export function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size, height: size,
      border: '2px solid var(--border)',
      borderTopColor: 'var(--accent)',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
      display: 'inline-block',
    }} />
  )
}