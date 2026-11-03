'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/Sidebar'
import { Spinner } from '@/components/ProgressAnimation'
import * as api from '@/lib/api'
import { getUser, isAuthed } from '@/lib/auth'

export default function ClassesPage() {
  const router = useRouter()
  const [user, setUser] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  // join-class state (student only)
  const [joinCode, setJoinCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinMsg, setJoinMsg] = useState('')

  // create-class state (teacher only)
  const [showCreate, setShowCreate] = useState(false)
  const [newSubject, setNewSubject] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newCode, setNewCode] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!isAuthed()) { router.replace('/signin'); return }
    setUser(getUser())
    api.listClasses()
      .then(setItems)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [router])

  async function handleJoin(e) {
    e.preventDefault()
    if (!joinCode.trim()) return
    setJoining(true); setJoinMsg(''); setErr('')
    try {
      await api.joinClass({ class_code: joinCode.trim() })
      setJoinCode('')
      setJoinMsg('Joined successfully!')
      const updated = await api.listClasses()
      setItems(updated)
    } catch (e) {
      setErr(e.message)
    } finally {
      setJoining(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!newSubject.trim() || !newCode.trim()) return
    setCreating(true); setErr('')
    try {
      await api.createClass({ subject: newSubject.trim(), description: newDesc.trim(), class_code: newCode.trim() })
      setNewSubject(''); setNewDesc(''); setNewCode(''); setShowCreate(false)
      const updated = await api.listClasses()
      setItems(updated)
    } catch (e) { setErr(e.message) }
    finally { setCreating(false) }
  }

  if (!user) return null
  const role = user.role

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar role={role} />
      <main style={{ flex: 1, padding: '40px 48px', overflowY: 'auto', maxWidth: 1100 }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 28, fontFamily: 'var(--font-head)', fontWeight: 700, margin: 0 }}>
            {role === 'teacher' ? 'Your Classrooms' : 'My Classes'}
          </h1>
          <p style={{ color: 'var(--muted)', marginTop: 6, fontSize: 15 }}>
            {role === 'teacher'
              ? 'Manage your classes, upload materials, generate quizzes and evaluate submissions.'
              : 'View your enrolled classes, take assignments, and practice quizzes.'}
          </p>
        </div>

        {/* teacher create-class */}
        {role === 'teacher' && !showCreate && (
          <button type="button" className="tf-btn" onClick={() => setShowCreate(true)} style={{ marginBottom: 20 }}>
            + Create Class
          </button>
        )}
        {role === 'teacher' && showCreate && (
          <form onSubmit={handleCreate} style={joinCard}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>Create a New Class</div>
            <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>
              Students will join using the class code you set below.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: 10 }}>
                <div>
                  <label className="tf-label">Subject</label>
                  <input className="tf-input" placeholder="e.g. Data Structures & Algorithms" value={newSubject} onChange={(e) => setNewSubject(e.target.value)} />
                </div>
                <div>
                  <label className="tf-label">Class Code</label>
                  <input className="tf-input" placeholder="e.g. DSA-301" value={newCode} onChange={(e) => setNewCode(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="tf-label">Description (optional)</label>
                <input className="tf-input" placeholder="Brief description of the class" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                <button className="tf-btn" disabled={creating || !newSubject.trim() || !newCode.trim()}>
                  {creating ? 'Creating...' : 'Create Class'}
                </button>
                <button type="button" className="tf-btn-outline" onClick={() => setShowCreate(false)}>Cancel</button>
              </div>
            </div>
          </form>
        )}

        {/* student join-class */}
        {role === 'student' && (
          <form onSubmit={handleJoin} style={joinCard}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>Join a Class</div>
            <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>
              Enter the class code your teacher shared with you.
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <input
                className="tf-input"
                placeholder="e.g. DSA-101"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                style={{ maxWidth: 240 }}
              />
              <button className="tf-btn" disabled={joining || !joinCode.trim()}>
                {joining ? 'Joining...' : 'Join'}
              </button>
            </div>
            {joinMsg && <div style={{ color: 'var(--accent3)', fontSize: 13, marginTop: 8, fontWeight: 500 }}>{joinMsg}</div>}
          </form>
        )}

        {loading && <div style={{ marginTop: 20 }}><Spinner /></div>}
        {err && <div style={errBox}>{err}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16, marginTop: 8 }}>
          {items.map((c) => (
            <Link key={c.id} href={`/classes/${c.id}`} style={{
              display: 'block',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 14,
              padding: 22,
              textDecoration: 'none',
              color: 'var(--text)',
              transition: 'border-color 0.15s, box-shadow 0.15s',
              boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span style={{
                  fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
                  color: 'var(--accent)', background: 'rgba(108,92,231,0.07)', padding: '3px 10px', borderRadius: 6,
                }}>
                  {c.class_code}
                </span>
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6, lineHeight: 1.3 }}>
                {c.subject}
              </div>
              <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 14 }}>
                {c.description}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--muted)' }}>
                <span>{c.teacher_name}</span>
                <span>{c.student_count} student{c.student_count === 1 ? '' : 's'}</span>
              </div>
            </Link>
          ))}
        </div>

        {!loading && !items.length && (
          <div style={{ color: 'var(--muted)', fontSize: 14, marginTop: 20 }}>
            {role === 'student' ? 'You haven\'t joined any classes yet. Enter a class code above to join.' : 'No classes yet.'}
          </div>
        )}
      </main>
    </div>
  )
}

const joinCard = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 14,
  padding: 20,
  marginBottom: 20,
  boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
}

const errBox = {
  background: 'rgba(224,68,68,0.06)',
  border: '1px solid rgba(224,68,68,0.15)',
  color: 'var(--danger)',
  padding: '10px 14px',
  borderRadius: 10,
  fontSize: 13,
  marginBottom: 16,
}
