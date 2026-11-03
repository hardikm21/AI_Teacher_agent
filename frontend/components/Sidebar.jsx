'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { getUser, clearAuth } from '@/lib/auth'
import { logoutUser, getUnreadCount, getNotifications, markNotificationsRead } from '@/lib/api'

const studentLinks = [
  { href: '/classes', label: 'My Classes', icon: '📚' },
]

const teacherLinks = [
  { href: '/classes', label: 'My Classes', icon: '📚' },
]

export default function Sidebar({ role = 'student' }) {
  const pathname = usePathname()
  const router   = useRouter()
  const user     = typeof window !== 'undefined' ? getUser() : null
  const links    = role === 'teacher' ? teacherLinks : studentLinks

  const [unread, setUnread] = useState(0)
  const [showNotifs, setShowNotifs] = useState(false)
  const [notifs, setNotifs] = useState([])

  useEffect(() => {
    if (!user) return
    getUnreadCount().then((r) => setUnread(r.count)).catch(() => {})
    const iv = setInterval(() => {
      getUnreadCount().then((r) => setUnread(r.count)).catch(() => {})
    }, 15000)
    return () => clearInterval(iv)
  }, [user])

  async function toggleNotifs() {
    if (showNotifs) { setShowNotifs(false); return }
    try {
      const list = await getNotifications()
      setNotifs(list)
      setShowNotifs(true)
      if (unread > 0) {
        await markNotificationsRead()
        setUnread(0)
      }
    } catch {}
  }

  async function signOut() {
    if (typeof window === 'undefined') return
    const ok = window.confirm('Sign out of your account?')
    if (!ok) return
    try { await logoutUser() } catch { /* best-effort */ }
    clearAuth()
    sessionStorage.removeItem('sessionId')
    sessionStorage.removeItem('totalConcepts')
    router.push('/signin')
  }

  return (
    <aside style={{
      width: 240,
      minHeight: '100vh',
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '28px 16px',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      alignSelf: 'flex-start',
    }}>
      {/* logo */}
      <Link href="/classes" style={{
        fontFamily: 'var(--font-head)',
        fontSize: 22,
        fontWeight: 800,
        letterSpacing: '-0.5px',
        marginBottom: 8,
        padding: '0 12px',
        textDecoration: 'none',
        color: 'var(--text)',
      }}>
        ai<span style={{ color: 'var(--accent)' }}>teacher</span>
      </Link>

      {/* role pill */}
      <div style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: role === 'teacher' ? 'var(--accent2)' : 'var(--accent3)',
        background: role === 'teacher' ? 'rgba(224,136,0,0.08)' : 'rgba(0,184,148,0.08)',
        border: `1px solid ${role === 'teacher' ? 'rgba(224,136,0,0.15)' : 'rgba(0,184,148,0.15)'}`,
        borderRadius: 20,
        padding: '4px 14px',
        display: 'inline-block',
        alignSelf: 'flex-start',
        margin: '0 12px 24px',
      }}>
        {role}
      </div>

      {/* nav links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {links.map(({ href, label, icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link key={href} href={href} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
              borderRadius: 10,
              fontSize: 14,
              fontWeight: active ? 600 : 400,
              color: active ? 'var(--accent)' : 'var(--muted)',
              background: active ? 'rgba(108,92,231,0.06)' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.15s',
            }}>
              <span style={{ fontSize: 16 }}>{icon}</span>
              {label}
            </Link>
          )
        })}
      </nav>

      {/* notification bell */}
      <div style={{ position: 'relative', margin: '16px 12px 0' }}>
        <button type="button" onClick={toggleNotifs} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 10, fontSize: 14,
          color: showNotifs ? 'var(--accent)' : 'var(--muted)',
          background: showNotifs ? 'rgba(108,92,231,0.06)' : 'transparent',
          border: 'none', cursor: 'pointer', width: '100%', textAlign: 'left',
          fontWeight: showNotifs ? 600 : 400, transition: 'all 0.15s',
        }}>
          <span style={{ fontSize: 16 }}>🔔</span>
          Notifications
          {unread > 0 && (
            <span style={{
              background: 'var(--danger)', color: '#fff', fontSize: 11,
              fontWeight: 700, borderRadius: 10, padding: '1px 7px', marginLeft: 'auto',
            }}>
              {unread}
            </span>
          )}
        </button>

        {showNotifs && (
          <div style={{
            position: 'absolute', left: '100%', bottom: 0, marginLeft: 8,
            width: 320, maxHeight: 400, overflowY: 'auto',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
            zIndex: 100, padding: 8,
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', padding: '8px 10px', borderBottom: '1px solid var(--border)', marginBottom: 4 }}>
              Notifications
            </div>
            {notifs.length === 0 && (
              <div style={{ padding: '16px 10px', fontSize: 13, color: 'var(--muted)', textAlign: 'center' }}>
                No notifications yet
              </div>
            )}
            {notifs.slice(0, 20).map((n) => (
              <div key={n.id} style={{
                padding: '10px 10px', borderRadius: 8, marginBottom: 2,
                background: n.read ? 'transparent' : 'rgba(108,92,231,0.04)',
                fontSize: 13,
              }}>
                <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{n.title}</div>
                {n.body && <div style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.4 }}>{n.body.slice(0, 100)}</div>}
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ flex: 1 }} />

      {user && (
        <div style={{
          borderTop: '1px solid var(--border)',
          paddingTop: 16,
          margin: '0 4px',
        }}>
          <div style={{ fontSize: 14, color: 'var(--text)', fontWeight: 600 }}>
            {user.name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12, wordBreak: 'break-all' }}>
            {user.email}
          </div>
          <button
            onClick={signOut}
            style={{
              width: '100%',
              padding: '9px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              color: 'var(--muted)',
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'border-color 0.15s',
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  )
}
