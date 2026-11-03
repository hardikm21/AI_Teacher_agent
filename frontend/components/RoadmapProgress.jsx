'use client'

const DIFF_STYLE = {
  easy:   { bg: 'rgba(61,217,164,0.15)',  color: 'var(--accent3)' },
  medium: { bg: 'rgba(240,165,0,0.15)',   color: 'var(--accent2)' },
  hard:   { bg: 'rgba(240,93,93,0.15)',   color: 'var(--danger)'  },
}

export default function RoadmapProgress({ roadmap, currentWeek }) {
  if (!roadmap) return null
  const { weeks = [], milestones = [] } = roadmap

  return (
    <div>
      {/* week grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 12,
        marginBottom: 28,
      }}>
        {weeks.map((w) => {
          const done   = w.week_number < currentWeek
          const active = w.week_number === currentWeek
          const diff   = DIFF_STYLE[w.difficulty] || DIFF_STYLE.medium

          return (
            <div key={w.week_number} style={{
              background: 'var(--surface)',
              border: `1px solid ${active ? 'var(--accent)' : done ? 'var(--accent3)' : 'var(--border)'}`,
              borderRadius: 10,
              padding: 18,
              transition: 'all 0.2s',
              opacity: done ? 0.7 : 1,
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 6,
              }}>
                <span style={{ fontSize: 11, color: 'var(--muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  Week {w.week_number}
                </span>
                {done && <span style={{ fontSize: 12, color: 'var(--accent3)' }}>✓</span>}
                {active && <span style={{ fontSize: 10, color: 'var(--accent)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Current</span>}
              </div>

              <div style={{
                fontFamily: 'var(--font-head)', fontSize: 14,
                fontWeight: 700, lineHeight: 1.3, marginBottom: 8,
              }}>
                {w.theme}
              </div>

              <div style={{
                fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase',
                padding: '3px 10px', borderRadius: 20, fontWeight: 500,
                display: 'inline-block',
                background: diff.bg, color: diff.color,
              }}>
                {w.difficulty}
              </div>
            </div>
          )
        })}
      </div>

      {/* milestones */}
      {milestones.length > 0 && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 10, padding: 20,
        }}>
          <div style={{
            fontFamily: 'var(--font-head)', fontSize: 16,
            fontWeight: 700, marginBottom: 16,
          }}>
            Milestones
          </div>
          {milestones.map((m, i) => (
            <div key={i} style={{
              display: 'flex', gap: 16, alignItems: 'flex-start',
              paddingBottom: 14, marginBottom: 14,
              borderBottom: i < milestones.length - 1 ? '1px solid var(--border)' : 'none',
            }}>
              <span style={{
                fontSize: 11, color: 'var(--accent2)',
                letterSpacing: '0.08em', textTransform: 'uppercase',
                minWidth: 56, marginTop: 2,
              }}>
                Wk {m.week}
              </span>
              <span style={{ fontSize: 14, lineHeight: 1.5 }}>{m.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}