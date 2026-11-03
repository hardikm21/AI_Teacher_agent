'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { loginUser } from '@/lib/api'
import { saveAuth } from '@/lib/auth'

export default function SignInPage() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!email || !password) { setError('Email and password required.'); return }
    setLoading(true)
    try {
      const res = await loginUser({ email, password })
      saveAuth({ token: res.token, user: res.user })
      router.push('/classes')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={pageStyle}>
      <div className="tf-aurora" style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }} />
      <form onSubmit={submit} style={cardStyle}>
        <div style={{ textAlign: 'center', marginBottom: 12 }}>
          <div style={{
            fontFamily: 'var(--font-head)',
            fontSize: 30,
            fontWeight: 800,
            letterSpacing: '-0.5px',
          }}>
            ai<span style={{ color: 'var(--accent)' }}>teacher</span>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 14, marginTop: 8 }}>
            Sign in to continue learning
          </div>
        </div>

        <label className="tf-label">Email</label>
        <input
          className="tf-input"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label className="tf-label" style={{ marginTop: 4 }}>Password</label>
        <input
          className="tf-input"
          type="password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div style={errorStyle}>{error}</div>}

        <button className="tf-btn" disabled={loading} style={{ marginTop: 10, width: '100%', justifyContent: 'center' }}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>

        <div style={{ textAlign: 'center', fontSize: 14, color: 'var(--muted)', marginTop: 16 }}>
          New here? <Link href="/signup" style={{ color: 'var(--accent)', fontWeight: 600, textDecoration: 'none' }}>Create an account</Link>
        </div>
      </form>
    </main>
  )
}

const pageStyle = {
  minHeight: '100vh',
  display: 'grid',
  placeItems: 'center',
  padding: 24,
  position: 'relative',
  overflow: 'hidden',
}
const cardStyle = {
  position: 'relative',
  zIndex: 1,
  width: '100%',
  maxWidth: 420,
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 16,
  padding: '36px 32px',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
}
const errorStyle = {
  background: 'rgba(224,68,68,0.06)',
  border: '1px solid rgba(224,68,68,0.2)',
  color: 'var(--danger)',
  padding: '10px 12px',
  borderRadius: 8,
  fontSize: 13,
}
