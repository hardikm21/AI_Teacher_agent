'use client'
import { useState } from 'react'

const DAY_LABELS = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']

export default function TaskCard({ task }) {
  const [done,   setDone]   = useState(false)
  const [copied, setCopied] = useState(false)

  const submissionPath = `${task.submission.github_folder}/${task.submission.filename}`
  const gitCommand = `git add ${submissionPath} && git commit -m "${task.submission.commit_message}"`

  async function copy() {
    try {
      await navigator.clipboard.writeText(gitCommand)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard unavailable, ignore */ }
  }

  return (
    <div style={{
      background: 'var(--surface2)',
      border: `1px solid ${done ? 'rgba(61,217,164,0.4)' : 'var(--border)'}`,
      borderRadius: 12,
      padding: 20,
      marginBottom: 12,
      opacity: done ? 0.72 : 1,
      transition: 'border-color 0.2s, opacity 0.2s',
    }}>
      {/* header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <button
          onClick={() => setDone(d => !d)}
          aria-label={done ? 'Mark task incomplete' : 'Mark task complete'}
          style={{
            width: 32, height: 32, borderRadius: 8,
            background: done ? 'var(--accent3)' : 'var(--surface)',
            border: `1px solid ${done ? 'var(--accent3)' : 'var(--border)'}`,
            color: done ? '#0a0a0f' : 'var(--muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 600, flexShrink: 0,
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {done ? '✓' : `D${task.day}`}
        </button>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-head)', fontSize: 15, fontWeight: 700, lineHeight: 1.3 }}>
            {task.title}
          </div>
          <div style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 2 }}>
            {DAY_LABELS[task.day] || `Day ${task.day}`}
          </div>
        </div>

        <div style={{
          fontSize: 11,
          color: 'var(--muted)',
          whiteSpace: 'nowrap',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 20,
          padding: '4px 10px',
        }}>
          ≈ {task.estimated_hours}h
        </div>
      </div>

      {/* description */}
      <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 12 }}>
        {task.description}
      </p>

      {/* steps */}
      <ul style={{ listStyle: 'none', marginBottom: 14 }}>
        {task.steps.map((step, i) => (
          <li key={i} style={{
            display: 'flex', gap: 10, fontSize: 13,
            color: 'var(--text)', marginBottom: 6, lineHeight: 1.5,
          }}>
            <span style={{ color: 'var(--accent)', flexShrink: 0, fontFamily: 'var(--font-mono)' }}>{i + 1}.</span>
            {step}
          </li>
        ))}
      </ul>

      {/* submission + copy */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          fontSize: 11, color: 'var(--accent2)',
          background: 'rgba(240,165,0,0.08)',
          border: '1px solid rgba(240,165,0,0.2)',
          borderRadius: 6, padding: '4px 10px',
          fontFamily: 'var(--font-mono)',
        }}>
          <span>📁</span>
          <span>{submissionPath}</span>
        </div>

        <span style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          “{task.submission.commit_message}”
        </span>

        <button
          onClick={copy}
          style={{
            fontSize: 11,
            padding: '4px 10px',
            borderRadius: 6,
            border: '1px solid var(--border)',
            background: 'var(--surface)',
            color: copied ? 'var(--accent3)' : 'var(--muted)',
            cursor: 'pointer',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {copied ? '✓ copied' : 'copy git cmd'}
        </button>
      </div>
    </div>
  )
}
