'use client'
import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import Sidebar from '@/components/Sidebar'
import QuizRunner from '@/components/QuizRunner'
import { Spinner } from '@/components/ProgressAnimation'
import * as api from '@/lib/api'
import { getUser, isAuthed } from '@/lib/auth'

export default function ClassroomPage() {
  const { id } = useParams()
  const router = useRouter()
  const [user, setUser] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [tab, setTab] = useState('stream')

  // quiz generation
  const [difficulty, setDifficulty] = useState('medium')
  const [count, setCount] = useState(5)
  const [dueDate, setDueDate] = useState('')
  const [genLoading, setGenLoading] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [quizKind, setQuizKind] = useState('')

  // stream
  const [stream, setStream] = useState([])

  // assignments (student)
  const [assignments, setAssignments] = useState([])
  const [activeAssignment, setActiveAssignment] = useState(null)
  const [mySubs, setMySubs] = useState([])

  // submissions (teacher)
  const [subs, setSubs] = useState([])
  const [subsLoading, setSubsLoading] = useState(false)

  useEffect(() => {
    if (!isAuthed()) { router.replace('/signin'); return }
    setUser(getUser())
    api.getClass(id)
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [id, router])

  const refreshStream = useCallback(() => {
    api.getStream(id).then(setStream).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!user || !id) return
    refreshStream()
    if (user.role === 'teacher') {
      setSubsLoading(true)
      api.listClassSubmissions(id).then(setSubs).catch(() => {}).finally(() => setSubsLoading(false))
    }
    if (user.role === 'student') {
      api.listAssignments(id).then(setAssignments).catch(() => {})
      api.mySubmissions(id).then(setMySubs).catch(() => {})
    }
  }, [user, id, refreshStream])

  async function handleGenerate(kind) {
    setGenLoading(true); setErr(''); setQuiz(null)
    try {
      const call = kind === 'assignment' ? api.generateClassQuiz : api.generatePracticeQuiz
      const body = { difficulty, count }
      if (kind === 'assignment' && dueDate) body.due_date = new Date(dueDate).toISOString()
      const q = await call(id, body)
      setQuiz(q); setQuizKind(kind)
      if (kind === 'assignment') {
        api.listAssignments(id).then(setAssignments).catch(() => {})
        refreshStream()
      }
    } catch (e) { setErr(e.message) }
    finally { setGenLoading(false) }
  }

  async function handleStudentSubmit(quizId, answers) {
    const sub = await api.submitQuizAnswers(quizId, answers)
    setMySubs((prev) => [sub, ...prev])
    api.listAssignments(id).then(setAssignments).catch(() => {})
  }

  function reload() {
    api.getClass(id).then(setData)
    refreshStream()
  }

  if (!user) return null
  const role = user.role
  const tabs = role === 'teacher'
    ? ['stream', 'materials', 'projects', 'lectures', 'quizzes', 'submissions', 'leaderboard', 'analytics']
    : ['stream', 'tutor', 'voice', 'materials', 'projects', 'lectures', 'assignments', 'results', 'leaderboard', 'analytics']

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar role={role} />
      <main style={{ flex: 1, padding: '32px 44px', overflowY: 'auto', maxWidth: 960 }}>
        <Link href="/classes" style={{ fontSize: 13, color: 'var(--muted)', textDecoration: 'none', fontWeight: 500 }}>
          ← Back to classes
        </Link>

        {loading && <div style={{ marginTop: 24 }}><Spinner /></div>}
        {err && <div style={errBox}>{err}</div>}

        {data && (
          <>
            {/* header */}
            <div style={{ marginTop: 14, marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <span style={codeBadge}>{data.class_code}</span>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>by {data.teacher_name}</span>
              </div>
              <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 26, fontWeight: 700, margin: 0 }}>
                {data.subject}
              </h1>
              {data.description && <p style={{ color: 'var(--muted)', marginTop: 4, fontSize: 14 }}>{data.description}</p>}
            </div>

            {/* tabs */}
            <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
              {tabs.map((t) => (
                <button key={t} type="button" onClick={() => setTab(t)} style={{
                  padding: '10px 20px', fontSize: 14, fontWeight: tab === t ? 600 : 400, cursor: 'pointer',
                  color: tab === t ? 'var(--accent)' : 'var(--muted)', background: 'transparent', border: 'none',
                  borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
                  textTransform: 'capitalize', transition: 'all 0.12s',
                }}>
                  {t}
                </button>
              ))}
            </div>

            {/* ── STREAM TAB ── */}
            {tab === 'stream' && (
              <div>
                {role === 'teacher' && <TeacherBroadcast classId={id} onPosted={refreshStream} />}
                <StreamFeed stream={stream} userId={user.id} onVoted={refreshStream} />
              </div>
            )}

            {/* ── TUTOR TAB ── */}
            {tab === 'tutor' && (
              <TutorChat classId={id} />
            )}

            {/* ── VOICE TUTOR TAB ── */}
            {tab === 'voice' && (
              <VoiceTutor classId={id} />
            )}

            {/* ── MATERIALS TAB ── */}
            {tab === 'materials' && (
              <MaterialsPanel data={data} onChange={reload} />
            )}

            {/* ── QUIZZES TAB (teacher) ── */}
            {tab === 'quizzes' && role === 'teacher' && (
              <div>
                <div style={card}>
                  <SectionTitle>Generate Assignment Quiz</SectionTitle>
                  <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 16 }}>
                    AI generates from your study materials. Students see it as an assignment in their Stream.
                  </p>
                  <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'end', marginBottom: 16 }}>
                    <div>
                      <label className="tf-label">Difficulty</label>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {['easy', 'medium', 'hard'].map((d) => (
                          <button key={d} type="button" onClick={() => setDifficulty(d)}
                                  style={pillStyle(difficulty === d)}>{d}</button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="tf-label">Questions</label>
                      <input className="tf-input" type="number" min={3} max={10} value={count}
                             onChange={(e) => setCount(Math.max(3, Math.min(10, +e.target.value || 5)))}
                             style={{ width: 80 }} />
                    </div>
                    <div>
                      <label className="tf-label">Due Date (optional)</label>
                      <input className="tf-input" type="datetime-local" value={dueDate}
                             onChange={(e) => setDueDate(e.target.value)}
                             style={{ width: 200 }} />
                    </div>
                    <button type="button" className="tf-btn" disabled={genLoading} onClick={() => handleGenerate('assignment')}>
                      {genLoading ? 'Generating...' : 'Generate quiz'}
                    </button>
                  </div>
                </div>
                {quiz && quizKind === 'assignment' && (
                  <div style={card}>
                    <SectionTitle color="var(--accent2)">Quiz Preview (Published)</SectionTitle>
                    <QuizRunner quiz={quiz} mode="practice" onFinish={() => setQuiz(null)} />
                  </div>
                )}
              </div>
            )}

            {/* ── ASSIGNMENTS TAB (student) ── */}
            {tab === 'assignments' && role === 'student' && (
              <div>
                {/* practice quiz */}
                <div style={card}>
                  <SectionTitle color="var(--accent3)">Practice Quiz</SectionTitle>
                  <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 16 }}>
                    Practice with AI-generated questions. Scored locally, nothing submitted.
                  </p>
                  <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'end', marginBottom: 16 }}>
                    <div>
                      <label className="tf-label">Difficulty</label>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {['easy', 'medium', 'hard'].map((d) => (
                          <button key={d} type="button" onClick={() => setDifficulty(d)}
                                  style={pillStyle(difficulty === d)}>{d}</button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="tf-label">Questions</label>
                      <input className="tf-input" type="number" min={3} max={10} value={count}
                             onChange={(e) => setCount(Math.max(3, Math.min(10, +e.target.value || 5)))}
                             style={{ width: 80 }} />
                    </div>
                    <button type="button" className="tf-btn" disabled={genLoading} onClick={() => handleGenerate('practice')}>
                      {genLoading ? 'Generating...' : 'Start practice'}
                    </button>
                  </div>
                </div>
                {quiz && quizKind === 'practice' && (
                  <div style={card}>
                    <SectionTitle color="var(--accent3)">Practice Quiz</SectionTitle>
                    <QuizRunner quiz={quiz} mode="practice" onFinish={() => setQuiz(null)} />
                  </div>
                )}

                {/* assigned quizzes */}
                {assignments.length > 0 && (
                  <div style={card}>
                    <SectionTitle color="var(--accent2)">Assigned Quizzes</SectionTitle>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {assignments.map((a) => {
                        const taken = mySubs.some((s) => s.quiz_id === a.id)
                        const isActive = activeAssignment?.id === a.id
                        return (
                          <div key={a.id}>
                            <div style={{
                              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                              background: 'var(--surface2)', borderRadius: 10, padding: '12px 16px',
                              border: '1px solid var(--border)',
                            }}>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: 15 }}>{a.title}</div>
                                <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                                  {a.questions.length} questions · {a.difficulty}
                                  {a.due_date && (
                                    <span style={{ marginLeft: 8, color: new Date(a.due_date) < new Date() ? 'var(--danger)' : 'var(--accent2)', fontWeight: 500 }}>
                                      Due: {new Date(a.due_date).toLocaleString()}
                                    </span>
                                  )}
                                  {taken && <span style={{ color: 'var(--accent3)', fontWeight: 600, marginLeft: 8 }}>Submitted</span>}
                                </div>
                              </div>
                              {!taken && (
                                <button type="button" className="tf-btn" style={{ padding: '8px 18px', fontSize: 13 }}
                                  onClick={() => setActiveAssignment(isActive ? null : a)}>
                                  {isActive ? 'Close' : 'Take Quiz'}
                                </button>
                              )}
                            </div>
                            {isActive && !taken && (
                              <div style={{ marginTop: 12 }}>
                                <QuizRunner quiz={a} mode="assignment"
                                  onSubmit={(answers) => handleStudentSubmit(a.id, answers)}
                                  onFinish={() => setActiveAssignment(null)} />
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
                {!assignments.length && !quiz && (
                  <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>No assignments posted yet.</div>
                )}
              </div>
            )}

            {/* ── RESULTS TAB (student) ── */}
            {tab === 'results' && role === 'student' && (
              <div>
                {mySubs.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {mySubs.map((s) => (
                      <div key={s.id} style={card}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 16 }}>{s.title}</div>
                            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
                              {s.correct_count}/{s.total_count} correct · Evaluated by {s.evaluated_by}
                              {s.is_late && <span style={{ color: 'var(--danger)', fontWeight: 600, marginLeft: 8 }}>Late</span>}
                            </div>
                          </div>
                          <div style={{
                            fontSize: 26, fontWeight: 700,
                            color: s.score >= 70 ? 'var(--accent3)' : s.score >= 50 ? 'var(--accent2)' : 'var(--danger)',
                          }}>
                            {s.score}/100
                          </div>
                        </div>
                        {s.remarks && (
                          <div style={{
                            marginTop: 10, padding: '12px 14px', borderRadius: 8,
                            background: 'var(--surface2)', border: '1px solid var(--border)',
                            fontSize: 14, lineHeight: 1.6,
                          }}>
                            {s.remarks}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>No results yet. Take an assignment quiz to see your scores here.</div>
                )}
              </div>
            )}

            {/* ── SUBMISSIONS TAB (teacher) ── */}
            {tab === 'submissions' && role === 'teacher' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                  <button type="button" className="tf-btn-outline" style={{ padding: '6px 14px', fontSize: 13 }}
                    onClick={() => { setSubsLoading(true); api.listClassSubmissions(id).then(setSubs).finally(() => setSubsLoading(false)) }}>
                    Refresh
                  </button>
                </div>
                {subsLoading && <Spinner />}
                {!subsLoading && !subs.length && (
                  <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>No submissions yet.</div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {subs.map((s) => <SubmissionCard key={s.id} sub={s} onEvaluated={() => api.listClassSubmissions(id).then(setSubs)} />)}
                </div>
              </div>
            )}
            {/* ── PROJECTS TAB ── */}
            {tab === 'projects' && (
              <ProjectsPanel classId={id} role={role} userId={user.id} onRefresh={refreshStream} />
            )}

            {/* ── LECTURES TAB ── */}
            {tab === 'lectures' && (
              <LecturesPanel classId={id} role={role} userId={user.id} userName={user.name} />
            )}

            {/* ── LEADERBOARD TAB ── */}
            {tab === 'leaderboard' && (
              <LeaderboardPanel classId={id} userId={user.id} />
            )}

            {/* ── ANALYTICS TAB ── */}
            {tab === 'analytics' && (
              <AnalyticsPanel classId={id} isTeacher={role === 'teacher'} />
            )}
          </>
        )}
      </main>
    </div>
  )
}

/* ── Teacher Broadcast Panel ── */
function TeacherBroadcast({ classId, onPosted }) {
  const [mode, setMode] = useState(null) // 'message' | 'poll'
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [pollQ, setPollQ] = useState('')
  const [pollOpts, setPollOpts] = useState(['', ''])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function sendMessage(e) {
    e.preventDefault()
    if (!title.trim() || !body.trim()) return
    setBusy(true); setErr('')
    try {
      await api.postMessage(classId, { title: title.trim(), body: body.trim() })
      setTitle(''); setBody(''); setMode(null)
      onPosted && onPosted()
    } catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  async function sendPoll(e) {
    e.preventDefault()
    const opts = pollOpts.map(o => o.trim()).filter(Boolean)
    if (!pollQ.trim() || opts.length < 2) return
    setBusy(true); setErr('')
    try {
      await api.createPoll(classId, { question: pollQ.trim(), options: opts })
      setPollQ(''); setPollOpts(['', '']); setMode(null)
      onPosted && onPosted()
    } catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  if (!mode) {
    return (
      <div style={{ ...card, display: 'flex', gap: 10 }}>
        <button type="button" className="tf-btn" onClick={() => setMode('message')}>
          Post Announcement
        </button>
        <button type="button" className="tf-btn-outline" onClick={() => setMode('poll')}>
          Create Poll
        </button>
      </div>
    )
  }

  if (mode === 'message') {
    return (
      <form onSubmit={sendMessage} style={card}>
        <SectionTitle>Post an Announcement</SectionTitle>
        <input className="tf-input" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} style={{ marginBottom: 8 }} />
        <textarea className="tf-input" placeholder="Write your message to students..." value={body} onChange={(e) => setBody(e.target.value)}
          rows={3} style={{ resize: 'vertical', minHeight: 80, marginBottom: 8 }} />
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 8 }}>{err}</div>}
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="tf-btn" disabled={busy || !title.trim() || !body.trim()}>
            {busy ? 'Posting...' : 'Post'}
          </button>
          <button type="button" className="tf-btn-outline" onClick={() => setMode(null)}>Cancel</button>
        </div>
      </form>
    )
  }

  return (
    <form onSubmit={sendPoll} style={card}>
      <SectionTitle>Create a Poll</SectionTitle>
      <input className="tf-input" placeholder="Poll question" value={pollQ} onChange={(e) => setPollQ(e.target.value)} style={{ marginBottom: 8 }} />
      {pollOpts.map((o, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
          <input className="tf-input" placeholder={`Option ${i + 1}`} value={o}
            onChange={(e) => { const c = [...pollOpts]; c[i] = e.target.value; setPollOpts(c) }} />
          {i >= 2 && (
            <button type="button" onClick={() => setPollOpts(pollOpts.filter((_, j) => j !== i))}
              style={{ background: 'transparent', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: 18, padding: '0 8px' }}>×</button>
          )}
        </div>
      ))}
      {pollOpts.length < 6 && (
        <button type="button" onClick={() => setPollOpts([...pollOpts, ''])}
          style={{ background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: 13, fontWeight: 600, padding: '4px 0', marginBottom: 8 }}>
          + Add option
        </button>
      )}
      {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 8 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
        <button className="tf-btn" disabled={busy || !pollQ.trim() || pollOpts.filter(o => o.trim()).length < 2}>
          {busy ? 'Creating...' : 'Create Poll'}
        </button>
        <button type="button" className="tf-btn-outline" onClick={() => setMode(null)}>Cancel</button>
      </div>
    </form>
  )
}

/* ── Stream Feed ── */
function StreamFeed({ stream, userId, onVoted }) {
  if (!stream.length) {
    return <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>No activity yet. Posts, quizzes, and polls will appear here.</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {stream.map((item) => (
        <div key={item.id} style={card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4, textTransform: 'uppercase',
              background: kindColor(item.kind).bg, color: kindColor(item.kind).text,
            }}>
              {item.kind}
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{item.author_name}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)', marginLeft: 'auto' }}>
              {new Date(item.created_at).toLocaleDateString()}
            </span>
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{item.title}</div>
          {item.body && <div style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.6 }}>{item.body}</div>}

          {/* inline poll */}
          {item.kind === 'poll' && item.poll && (
            <PollWidget poll={item.poll} userId={userId} onVoted={onVoted} />
          )}

          {/* quiz info */}
          {item.kind === 'quiz' && item.quiz_info && (
            <div style={{ marginTop: 8, padding: '8px 12px', borderRadius: 8, background: 'var(--surface2)', border: '1px solid var(--border)', fontSize: 13 }}>
              {item.quiz_info.question_count} questions · {item.quiz_info.difficulty} difficulty
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function PollWidget({ poll, userId, onVoted }) {
  const [voting, setVoting] = useState(false)
  const totalVotes = poll.options.reduce((s, o) => s + o.votes, 0)
  const voted = poll.voted

  async function vote(idx) {
    setVoting(true)
    try {
      await api.votePoll(poll.id, idx)
      onVoted && onVoted()
    } catch { }
    finally { setVoting(false) }
  }

  return (
    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
      {poll.options.map((opt, i) => {
        const pct = totalVotes > 0 ? Math.round((opt.votes / totalVotes) * 100) : 0
        return (
          <button key={i} type="button" disabled={voted || voting}
            onClick={() => vote(i)}
            style={{
              position: 'relative', textAlign: 'left', padding: '10px 14px', borderRadius: 8,
              border: '1px solid var(--border)', background: 'var(--surface2)',
              cursor: voted ? 'default' : 'pointer', overflow: 'hidden', fontSize: 14,
            }}>
            {voted && (
              <div style={{
                position: 'absolute', left: 0, top: 0, bottom: 0,
                width: `${pct}%`, background: 'rgba(108,92,231,0.08)',
                transition: 'width 0.3s',
              }} />
            )}
            <span style={{ position: 'relative', fontWeight: 500 }}>{opt.label}</span>
            {voted && <span style={{ position: 'relative', float: 'right', color: 'var(--muted)', fontSize: 13 }}>{pct}%</span>}
          </button>
        )
      })}
      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{totalVotes} vote{totalVotes !== 1 ? 's' : ''}</div>
    </div>
  )
}

function kindColor(kind) {
  switch (kind) {
    case 'message':  return { bg: 'rgba(108,92,231,0.08)', text: 'var(--accent)' }
    case 'material': return { bg: 'rgba(0,184,148,0.08)', text: 'var(--accent3)' }
    case 'quiz':     return { bg: 'rgba(224,136,0,0.08)', text: 'var(--accent2)' }
    case 'poll':     return { bg: 'rgba(108,92,231,0.08)', text: 'var(--accent)' }
    default:         return { bg: 'var(--surface2)', text: 'var(--muted)' }
  }
}

/* ── Shared components ── */

function SectionTitle({ children, color }) {
  return (
    <div style={{
      fontSize: 13, fontWeight: 700, letterSpacing: '0.03em', textTransform: 'uppercase',
      color: color || 'var(--accent)', marginBottom: 12,
    }}>
      {children}
    </div>
  )
}

function MaterialsPanel({ data, onChange }) {
  const materials = data.materials || []
  const isOwner = data.is_owner
  const [title, setTitle] = useState('')
  const [text, setText]   = useState('')
  const [file, setFile]   = useState(null)
  const [busy, setBusy]   = useState(false)
  const [err, setErr]     = useState('')

  function handleFile(f) {
    if (!f) return
    setFile(f)
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''))
  }

  async function upload() {
    setErr('')
    if (!title.trim()) { setErr('Title is required.'); return }
    if (!file && !text.trim()) { setErr('Choose a file or paste text.'); return }
    setBusy(true)
    try {
      if (file) {
        await api.uploadClassMaterialFile(data.id, title.trim(), file)
      } else {
        await api.uploadClassMaterial(data.id, { title: title.trim(), text: text.trim() })
      }
      setTitle(''); setText(''); setFile(null)
      onChange && onChange()
    } catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  async function remove(mid) {
    if (!window.confirm('Delete this material?')) return
    try { await api.deleteClassMaterial(data.id, mid); onChange && onChange() }
    catch (e) { setErr(e.message) }
  }

  return (
    <div>
      {!materials.length && (
        <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>
          {isOwner ? 'No materials yet. Upload study content so the AI can use it for quizzes.' : 'No materials uploaded yet.'}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {materials.map((m) => (
          <details key={m.id} style={card}>
            <summary style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, fontSize: 14 }}>
              <span style={{ fontWeight: 600 }}>{m.title}</span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(m.uploaded_at).toLocaleDateString()}</span>
            </summary>
            <pre style={{ marginTop: 10, whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, fontFamily: 'var(--font-mono)' }}>{m.text}</pre>
            {isOwner && (
              <button type="button" onClick={() => remove(m.id)} style={{
                fontSize: 12, color: 'var(--danger)', background: 'transparent',
                border: '1px solid rgba(224,68,68,0.2)', borderRadius: 6,
                padding: '4px 12px', cursor: 'pointer', marginTop: 8,
              }}>Delete</button>
            )}
          </details>
        ))}
      </div>

      {isOwner && (
        <div style={{ ...card, marginTop: 12 }}>
          <SectionTitle>Upload Material</SectionTitle>
          <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>
            Upload a file (PDF, DOCX, PPTX, TXT, MD, CSV, code files) or paste text directly.
          </div>

          <input className="tf-input" placeholder="Title (e.g. Week 4 — Trees)" value={title}
            onChange={(e) => setTitle(e.target.value)} style={{ marginBottom: 10 }} />

          <label style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            background: file ? 'rgba(108,92,231,0.06)' : 'var(--surface2)',
            border: `1.5px dashed ${file ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 10, padding: '16px 12px', fontSize: 14,
            color: file ? 'var(--accent)' : 'var(--muted)', cursor: 'pointer',
            marginBottom: 10, transition: 'all 0.15s',
          }}>
            {file ? file.name : 'Click to choose a file — PDF, DOCX, PPTX, TXT, CSV, and more'}
            <input type="file"
              accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md,.csv,.json,.xml,.py,.js,.java,.c,.cpp,.h,.css,.html,.yaml,.yml,.sql,.log,.r,.tex"
              onChange={(e) => handleFile(e.target.files?.[0])} style={{ display: 'none' }} />
          </label>

          {!file && (
            <>
              <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--muted)', margin: '4px 0 8px' }}>or paste text below</div>
              <textarea className="tf-input" placeholder="Paste your notes or material text here..."
                value={text} onChange={(e) => setText(e.target.value)}
                rows={5} style={{ resize: 'vertical', minHeight: 100, fontFamily: 'var(--font-mono)', fontSize: 13, marginBottom: 8 }} />
            </>
          )}

          {file && (
            <button type="button" onClick={() => setFile(null)} style={{
              fontSize: 12, color: 'var(--muted)', background: 'transparent', border: 'none',
              cursor: 'pointer', marginBottom: 8, textDecoration: 'underline',
            }}>Remove file (paste text instead)</button>
          )}

          {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 6 }}>{err}</div>}
          <button type="button" className="tf-btn" onClick={upload} disabled={busy}>
            {busy ? 'Uploading...' : 'Upload material'}
          </button>
        </div>
      )}
    </div>
  )
}

function SubmissionCard({ sub, onEvaluated }) {
  const [remarks, setRemarks] = useState(sub.remarks || '')
  const [score, setScore]     = useState(sub.score ?? 80)
  const [saving, setSaving]   = useState(false)
  const [err, setErr]         = useState('')

  async function save() {
    setSaving(true); setErr('')
    try { await api.evaluateSubmission(sub.id, { remarks, score }); onEvaluated && onEvaluated() }
    catch (e) { setErr(e.message) }
    finally { setSaving(false) }
  }

  const graded = !!sub.evaluated_at

  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>{sub.student_name}</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 2 }}>{sub.title}</div>
          {sub.correct_count != null && (
            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
              {sub.correct_count}/{sub.total_count} correct
              {sub.is_late && <span style={{ color: 'var(--danger)', fontWeight: 600, marginLeft: 8 }}>Late</span>}
            </div>
          )}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{new Date(sub.submitted_at).toLocaleDateString()}</div>
          {graded && (
            <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4,
              color: sub.score >= 70 ? 'var(--accent3)' : sub.score >= 50 ? 'var(--accent2)' : 'var(--danger)' }}>
              {sub.score}/100
            </div>
          )}
        </div>
      </div>

      {graded && sub.evaluated_by === 'AI' && (
        <div style={{
          marginTop: 10, padding: '10px 14px', borderRadius: 8,
          background: 'rgba(108,92,231,0.04)', border: '1px solid rgba(108,92,231,0.1)',
          fontSize: 13, lineHeight: 1.6,
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', marginRight: 6 }}>AI:</span>
          {sub.remarks}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 10, marginTop: 12 }}>
        <div>
          <label className="tf-label">Teacher remarks</label>
          <textarea className="tf-input" value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={3}
            placeholder="Add your feedback..." style={{ resize: 'vertical', minHeight: 70 }} />
        </div>
        <div>
          <label className="tf-label">Score / 100</label>
          <input className="tf-input" type="number" min={0} max={100} value={score}
            onChange={(e) => setScore(Math.max(0, Math.min(100, +e.target.value || 0)))} />
        </div>
      </div>
      {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 6 }}>{err}</div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
        <div style={{ fontSize: 12, color: graded ? 'var(--accent3)' : 'var(--muted)', fontWeight: 500 }}>
          {graded ? `Evaluated by ${sub.evaluated_by} · ${sub.score}/100` : 'Not yet evaluated'}
        </div>
        <button type="button" className="tf-btn" onClick={save} disabled={saving || !remarks.trim()}
          style={{ padding: '8px 18px', fontSize: 13 }}>
          {saving ? 'Saving...' : (graded ? 'Update' : 'Submit evaluation')}
        </button>
      </div>
    </div>
  )
}

/* ── Projects Panel ── */
function ProjectsPanel({ classId, role, userId, onRefresh }) {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const refresh = useCallback(() => {
    api.listProjects(classId).then(setProjects).catch(() => {}).finally(() => setLoading(false))
  }, [classId])

  useEffect(() => { refresh() }, [refresh])

  if (loading) return <div style={{ textAlign: 'center', padding: 40 }}><Spinner /></div>

  return (
    <div>
      {/* teacher: create project */}
      {role === 'teacher' && (
        <>
          {!showCreate ? (
            <div style={{ ...card, display: 'flex', gap: 10 }}>
              <button type="button" className="tf-btn" onClick={() => setShowCreate(true)}>
                + Create Project
              </button>
            </div>
          ) : (
            <CreateProjectForm classId={classId} onCreated={() => { setShowCreate(false); refresh(); onRefresh && onRefresh() }} onCancel={() => setShowCreate(false)} />
          )}
        </>
      )}

      {/* project list */}
      {projects.length === 0 && (
        <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>
          {role === 'teacher' ? 'No projects yet. Create one to assign GitHub-tracked projects to students.' : 'No projects assigned yet.'}
        </div>
      )}

      {projects.map((p) => (
        <ProjectCard key={p.id} project={p} role={role} userId={userId} onRefresh={refresh} />
      ))}
    </div>
  )
}

/* ── Create Project Form ── */
function CreateProjectForm({ classId, onCreated, onCancel }) {
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) { setErr('Title is required.'); return }
    if (!file && !desc.trim()) { setErr('Upload a project brief or write a description.'); return }
    setBusy(true); setErr('')
    try {
      if (file) {
        const dueDateISO = dueDate ? new Date(dueDate).toISOString() : ''
        await api.createProjectFile(classId, title.trim(), dueDateISO, file)
      } else {
        const body = { title: title.trim(), description: desc.trim() }
        if (dueDate) body.due_date = new Date(dueDate).toISOString()
        await api.createProjectJSON(classId, body)
      }
      onCreated && onCreated()
    } catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} style={card}>
      <SectionTitle>Create Project Assignment</SectionTitle>
      <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
        Upload a PDF/DOCX with requirements, or type them below. Students will link their GitHub repos and progress will be tracked automatically.
      </p>

      <input className="tf-input" placeholder="Project title" value={title}
        onChange={(e) => setTitle(e.target.value)} style={{ marginBottom: 10 }} />

      <div style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <label className="tf-label">Due Date (optional)</label>
          <input className="tf-input" type="datetime-local" value={dueDate}
            onChange={(e) => setDueDate(e.target.value)} />
        </div>
      </div>

      {/* file upload */}
      <label style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        background: file ? 'rgba(108,92,231,0.06)' : 'var(--surface2)',
        border: `1.5px dashed ${file ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 10, padding: '16px 12px', fontSize: 14,
        color: file ? 'var(--accent)' : 'var(--muted)', cursor: 'pointer',
        marginBottom: 10,
      }}>
        {file ? file.name : 'Click to upload project brief (PDF, DOCX, TXT...)'}
        <input type="file" accept=".pdf,.docx,.doc,.pptx,.txt,.md" onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) { setFile(f); if (!title) setTitle(f.name.replace(/\.[^.]+$/, '')) }
        }} style={{ display: 'none' }} />
      </label>

      {file && (
        <button type="button" onClick={() => setFile(null)} style={{
          fontSize: 12, color: 'var(--muted)', background: 'transparent', border: 'none',
          cursor: 'pointer', marginBottom: 8, textDecoration: 'underline',
        }}>Remove file (type description instead)</button>
      )}

      {!file && (
        <textarea className="tf-input" placeholder="Project description / requirements..." value={desc}
          onChange={(e) => setDesc(e.target.value)} rows={6}
          style={{ resize: 'vertical', minHeight: 120, fontFamily: 'var(--font-mono)', fontSize: 13, marginBottom: 8 }} />
      )}

      {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 8 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 10 }}>
        <button className="tf-btn" disabled={busy}>{busy ? 'Creating...' : 'Create Project'}</button>
        <button type="button" className="tf-btn-outline" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

/* ── Project Card ── */
function ProjectCard({ project, role, userId, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [githubUrl, setGithubUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState('')
  const [subs, setSubs] = useState([])
  const [loadingSubs, setLoadingSubs] = useState(false)

  const mySub = project.my_submission
  const isTeacher = role === 'teacher'
  const isPastDue = project.due_date && new Date(project.due_date) < new Date()

  async function submitRepo(e) {
    e.preventDefault()
    if (!githubUrl.trim()) return
    setSubmitting(true); setErr('')
    try {
      await api.submitProject(project.id, githubUrl.trim())
      onRefresh && onRefresh()
    } catch (e) { setErr(e.message) }
    finally { setSubmitting(false) }
  }

  async function loadSubmissions() {
    setLoadingSubs(true)
    try {
      const list = await api.listProjectSubmissions(project.id)
      setSubs(list)
    } catch {}
    finally { setLoadingSubs(false) }
  }

  return (
    <div style={{ ...card, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', cursor: 'pointer' }}
           onClick={() => { setExpanded(!expanded); if (!expanded && isTeacher) loadSubmissions() }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 18 }}>📋</span>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{project.title}</div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {project.file_name && <span>📎 {project.file_name}</span>}
            {project.due_date && (
              <span style={{ color: isPastDue ? 'var(--danger)' : 'var(--accent2)', fontWeight: 500 }}>
                Due: {new Date(project.due_date).toLocaleString()}
              </span>
            )}
            {isTeacher && <span>{project.submission_count || 0} submissions</span>}
            {mySub && <span style={{ color: 'var(--accent3)', fontWeight: 600 }}>Submitted</span>}
          </div>
        </div>
        <span style={{ fontSize: 18, color: 'var(--muted)', transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : '' }}>▼</span>
      </div>

      {expanded && (
        <div style={{ marginTop: 16 }}>
          {/* project description */}
          <details style={{ marginBottom: 14 }}>
            <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 600, color: 'var(--accent)', marginBottom: 6 }}>
              View Full Requirements
            </summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, fontFamily: 'var(--font-mono)',
              background: 'var(--surface2)', padding: 14, borderRadius: 10, border: '1px solid var(--border)',
              maxHeight: 400, overflowY: 'auto' }}>
              {project.description}
            </pre>
          </details>

          {/* student: submit github repo */}
          {!isTeacher && !mySub && (
            <form onSubmit={submitRepo} style={{
              padding: 14, borderRadius: 10, background: 'rgba(108,92,231,0.04)',
              border: '1px solid rgba(108,92,231,0.1)', marginBottom: 12,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>
                Submit Your GitHub Repository
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="tf-input" placeholder="https://github.com/username/repo"
                  value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)}
                  style={{ flex: 1, margin: 0 }} />
                <button className="tf-btn" disabled={submitting || !githubUrl.trim()}
                  style={{ padding: '8px 18px', fontSize: 13, flexShrink: 0 }}>
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
              {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 6 }}>{err}</div>}
            </form>
          )}

          {/* student: show own submission status */}
          {!isTeacher && mySub && (
            <ProjectSubmissionView sub={mySub} onRefresh={onRefresh} showActions projectId={project.id} />
          )}

          {/* teacher: show all submissions */}
          {isTeacher && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Student Submissions
                </div>
                <button type="button" className="tf-btn-outline" style={{ padding: '4px 12px', fontSize: 12 }}
                  onClick={loadSubmissions}>Refresh</button>
              </div>
              {loadingSubs && <Spinner />}
              {!loadingSubs && subs.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>No submissions yet.</div>
              )}
              {subs.map((s) => (
                <ProjectSubmissionView key={s.id} sub={s} onRefresh={loadSubmissions} isTeacher />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Project Submission View (shared by teacher & student) ── */
function ProjectSubmissionView({ sub, onRefresh, isTeacher, showActions, projectId }) {
  const [checking, setChecking] = useState(false)
  const [snapshotting, setSnapshotting] = useState(false)
  const [aiEval, setAiEval] = useState(false)
  const [remarks, setRemarks] = useState(sub.remarks || '')
  const [score, setScore] = useState(sub.score ?? 70)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  const [showChat, setShowChat] = useState(false)

  async function checkProgress() {
    setChecking(true); setErr('')
    try { await api.checkProjectProgress(sub.id); onRefresh && onRefresh() }
    catch (e) { setErr(e.message) } finally { setChecking(false) }
  }

  async function takeSnapshot() {
    setSnapshotting(true); setErr('')
    try { await api.recordWeeklySnapshot(sub.id); onRefresh && onRefresh() }
    catch (e) { setErr(e.message) } finally { setSnapshotting(false) }
  }

  async function runAIEval() {
    setAiEval(true); setErr('')
    try { await api.evaluateProjectAI(sub.id); onRefresh && onRefresh() }
    catch (e) { setErr(e.message) } finally { setAiEval(false) }
  }

  async function saveTeacherEval() {
    setSaving(true); setErr('')
    try { await api.evaluateProjectTeacher(sub.id, { remarks, score }); onRefresh && onRefresh() }
    catch (e) { setErr(e.message) } finally { setSaving(false) }
  }

  const totalLangBytes = Object.values(sub.languages || {}).reduce((a, b) => a + b, 0)
  const graded = !!sub.evaluated_at
  const snapshots = sub.weekly_snapshots || []
  const codeFiles = sub.code_snippets || {}

  return (
    <div style={{ padding: 14, borderRadius: 10, marginBottom: 10, background: 'var(--surface2)', border: '1px solid var(--border)' }}>
      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{sub.student_name}</div>
          <a href={sub.github_url} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--accent)', wordBreak: 'break-all' }}>{sub.github_url}</a>
          <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
            Submitted: {new Date(sub.submitted_at).toLocaleString()}
            {sub.is_late && <span style={{ color: 'var(--danger)', fontWeight: 600, marginLeft: 6 }}>Late</span>}
          </div>
        </div>
        {graded && (
          <div style={{ fontSize: 24, fontWeight: 700, color: sub.score >= 70 ? 'var(--accent3)' : sub.score >= 50 ? 'var(--accent2)' : 'var(--danger)' }}>
            {sub.score}/100
          </div>
        )}
      </div>

      {/* GitHub progress */}
      {sub.last_checked && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', marginBottom: 6 }}>
            GitHub Progress (checked {new Date(sub.last_checked).toLocaleString()})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8, marginBottom: 8 }}>
            <div style={miniCard}><div style={miniLabel}>Commits</div><div style={miniValue}>{sub.total_commits}</div></div>
            <div style={miniCard}><div style={miniLabel}>Files</div><div style={miniValue}>{sub.file_tree?.length || 0}</div></div>
            <div style={miniCard}>
              <div style={miniLabel}>Languages</div>
              <div style={{ fontSize: 12 }}>
                {Object.entries(sub.languages || {}).map(([lang, bytes]) => (
                  <span key={lang} style={{ marginRight: 8 }}>{lang} {totalLangBytes > 0 ? Math.round(bytes/totalLangBytes*100) : 0}%</span>
                ))}
                {Object.keys(sub.languages || {}).length === 0 && <span style={{ color: 'var(--muted)' }}>None</span>}
              </div>
            </div>
          </div>
          {sub.last_commit_msg && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>
              Last commit: <span style={{ color: 'var(--text)' }}>{sub.last_commit_msg}</span>
            </div>
          )}

          {/* file tree */}
          {sub.file_tree?.length > 0 && (
            <details style={{ marginBottom: 6 }}>
              <summary style={{ fontSize: 12, color: 'var(--accent)', cursor: 'pointer', fontWeight: 600 }}>File tree ({sub.file_tree.length} items)</summary>
              <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', lineHeight: 1.8, marginTop: 4, padding: '8px 10px', background: 'var(--surface)', borderRadius: 6, border: '1px solid var(--border)', maxHeight: 250, overflowY: 'auto' }}>
                {sub.file_tree.map((f, i) => <div key={i}>{f}</div>)}
              </div>
            </details>
          )}

          {/* code files read by LLM */}
          {Object.keys(codeFiles).length > 0 && (
            <details style={{ marginBottom: 6 }}>
              <summary style={{ fontSize: 12, color: 'var(--accent)', cursor: 'pointer', fontWeight: 600 }}>
                Source code read ({Object.keys(codeFiles).length} files)
              </summary>
              <div style={{ marginTop: 4 }}>
                {Object.entries(codeFiles).map(([path, content]) => (
                  <details key={path} style={{ marginBottom: 4 }}>
                    <summary style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text)', cursor: 'pointer', padding: '4px 8px', background: 'var(--surface)', borderRadius: 4, border: '1px solid var(--border)' }}>
                      {path}
                    </summary>
                    <pre style={{ fontSize: 11, fontFamily: 'var(--font-mono)', lineHeight: 1.5, whiteSpace: 'pre-wrap', padding: '8px 10px', background: '#1e1e2e', color: '#cdd6f4', borderRadius: '0 0 6px 6px', maxHeight: 300, overflowY: 'auto', margin: 0 }}>
                      {content}
                    </pre>
                  </details>
                ))}
              </div>
            </details>
          )}

          {sub.readme_snippet && (
            <details style={{ marginBottom: 6 }}>
              <summary style={{ fontSize: 12, color: 'var(--accent)', cursor: 'pointer', fontWeight: 600 }}>README preview</summary>
              <pre style={{ fontSize: 12, fontFamily: 'var(--font-mono)', lineHeight: 1.6, whiteSpace: 'pre-wrap', marginTop: 4, padding: '8px 10px', background: 'var(--surface)', borderRadius: 6, border: '1px solid var(--border)', maxHeight: 200, overflowY: 'auto' }}>
                {sub.readme_snippet}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* weekly snapshots timeline */}
      {snapshots.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 8 }}>
            Weekly Progress Timeline
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {snapshots.map((snap, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'start', padding: '10px 12px', background: 'var(--surface)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ width: 50, textAlign: 'center', flexShrink: 0 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 600 }}>Week</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent)' }}>{snap.week}</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{snap.code_summary}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>{snap.remarks}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4, display: 'flex', gap: 12 }}>
                    <span>+{snap.new_commits} commits</span>
                    <span>{snap.file_count} files</span>
                    <span>{new Date(snap.checked_at).toLocaleDateString()}</span>
                  </div>
                </div>
                {snap.score != null && (
                  <div style={{ fontSize: 18, fontWeight: 700, color: snap.score >= 70 ? 'var(--accent3)' : snap.score >= 50 ? 'var(--accent2)' : 'var(--danger)', flexShrink: 0 }}>
                    {snap.score}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* evaluations */}
      {graded && sub.evaluated_by === 'AI' && (
        <div style={{ marginBottom: 10, padding: '10px 14px', borderRadius: 8, background: 'rgba(108,92,231,0.04)', border: '1px solid rgba(108,92,231,0.1)', fontSize: 13, lineHeight: 1.6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', marginRight: 6 }}>AI Evaluation:</span>{sub.remarks}
        </div>
      )}
      {graded && sub.evaluated_by && sub.evaluated_by !== 'AI' && (
        <div style={{ marginBottom: 10, padding: '10px 14px', borderRadius: 8, background: 'rgba(0,184,148,0.04)', border: '1px solid rgba(0,184,148,0.1)', fontSize: 13, lineHeight: 1.6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent3)', marginRight: 6 }}>Teacher ({sub.evaluated_by}):</span>{sub.remarks}
        </div>
      )}

      {/* action buttons */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <button type="button" className="tf-btn-outline" style={{ padding: '6px 14px', fontSize: 12 }}
          disabled={checking} onClick={checkProgress}>
          {checking ? 'Scanning repo...' : (sub.last_checked ? 'Refresh Progress' : 'Scan GitHub Repo')}
        </button>
        <button type="button" className="tf-btn-outline" style={{ padding: '6px 14px', fontSize: 12 }}
          disabled={snapshotting} onClick={takeSnapshot}>
          {snapshotting ? 'Recording...' : 'Record Weekly Snapshot'}
        </button>
        {(isTeacher || showActions) && sub.last_checked && (
          <button type="button" className="tf-btn-outline" style={{ padding: '6px 14px', fontSize: 12 }}
            disabled={aiEval} onClick={runAIEval}>
            {aiEval ? 'Evaluating...' : 'AI Evaluate (reads code)'}
          </button>
        )}
        {showActions && projectId && (
          <button type="button" className={showChat ? 'tf-btn' : 'tf-btn-outline'}
            style={{ padding: '6px 14px', fontSize: 12 }}
            onClick={() => setShowChat(!showChat)}>
            {showChat ? 'Hide Guidance' : 'Ask AI for Guidance'}
          </button>
        )}
      </div>

      {/* project guidance chat (student) */}
      {showChat && projectId && (
        <ProjectGuidanceChat projectId={projectId} />
      )}

      {/* teacher manual evaluation */}
      {isTeacher && (
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 120px', gap: 10 }}>
          <div>
            <label className="tf-label">Teacher Remarks</label>
            <textarea className="tf-input" value={remarks} onChange={(e) => setRemarks(e.target.value)}
              rows={2} placeholder="Your evaluation..." style={{ resize: 'vertical', minHeight: 60 }} />
          </div>
          <div>
            <label className="tf-label">Score / 100</label>
            <input className="tf-input" type="number" min={0} max={100} value={score}
              onChange={(e) => setScore(Math.max(0, Math.min(100, +e.target.value || 0)))} />
          </div>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}>
            <button type="button" className="tf-btn" disabled={saving || !remarks.trim()} onClick={saveTeacherEval}
              style={{ padding: '8px 18px', fontSize: 13 }}>
              {saving ? 'Saving...' : (graded ? 'Update Evaluation' : 'Submit Evaluation')}
            </button>
          </div>
        </div>
      )}

      {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 6 }}>{err}</div>}
    </div>
  )
}

/* ── Project Guidance Chat ── */
function ProjectGuidanceChat({ projectId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    api.getProjectChat(projectId).then((h) => { setMessages(h); setLoaded(true) }).catch(() => setLoaded(true))
  }, [projectId])

  async function send(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages(prev => [...prev, { role: 'student', content: text }])
    setSending(true)
    try {
      const reply = await api.sendProjectChat(projectId, text)
      setMessages(prev => [...prev, reply])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'tutor', content: `Error: ${err.message}` }])
    } finally { setSending(false) }
  }

  return (
    <div style={{ borderRadius: 10, border: '1px solid rgba(108,92,231,0.2)', overflow: 'hidden', marginBottom: 10 }}>
      <div style={{ padding: '10px 14px', background: 'rgba(108,92,231,0.06)', fontSize: 13, fontWeight: 700, color: 'var(--accent)' }}>
        AI Project Mentor — ask about your code, next steps, or debugging help
      </div>
      <div style={{ maxHeight: 300, overflowY: 'auto', padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {!loaded && <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading...</div>}
        {loaded && messages.length === 0 && (
          <div style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 16 }}>
            Ask the AI mentor about your project — it can see your code and requirements.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ alignSelf: msg.role === 'student' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
            <div style={{
              padding: '8px 12px', borderRadius: msg.role === 'student' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
              background: msg.role === 'student' ? 'var(--accent)' : 'var(--surface)',
              color: msg.role === 'student' ? '#fff' : 'var(--text)',
              fontSize: 13, lineHeight: 1.5, border: msg.role === 'tutor' ? '1px solid var(--border)' : 'none',
              whiteSpace: 'pre-wrap',
            }}>{msg.content}</div>
          </div>
        ))}
        {sending && (
          <div style={{ alignSelf: 'flex-start', fontSize: 13, color: 'var(--muted)', fontStyle: 'italic' }}>Thinking...</div>
        )}
      </div>
      <form onSubmit={send} style={{ display: 'flex', gap: 8, padding: '8px 12px', borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
        <input className="tf-input" value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="How should I structure my code? / What's wrong with my implementation?"
          disabled={sending} style={{ flex: 1, margin: 0, fontSize: 13 }} />
        <button type="submit" className="tf-btn" disabled={sending || !input.trim()}
          style={{ padding: '6px 16px', fontSize: 12, flexShrink: 0 }}>Send</button>
      </form>
    </div>
  )
}

/* ── Leaderboard Panel ── */
function LeaderboardPanel({ classId, userId }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getLeaderboard(classId).then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [classId])

  if (loading) return <div style={{ textAlign: 'center', padding: 40 }}><Spinner /></div>
  if (!data.length) return <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>No scores yet. The leaderboard will appear once students complete quizzes or projects.</div>

  const medals = ['🥇', '🥈', '🥉']

  return (
    <div style={card}>
      <SectionTitle>Class Leaderboard</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {data.map((entry) => {
          const isMe = entry.student_id === userId
          return (
            <div key={entry.student_id} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '12px 16px', borderRadius: 10,
              background: isMe ? 'rgba(108,92,231,0.06)' : 'var(--surface2)',
              border: isMe ? '1.5px solid var(--accent)' : '1px solid var(--border)',
              transition: 'all 0.15s',
            }}>
              {/* rank */}
              <div style={{ width: 36, textAlign: 'center', fontSize: entry.rank <= 3 ? 24 : 18, fontWeight: 700, color: entry.rank <= 3 ? 'var(--accent2)' : 'var(--muted)' }}>
                {entry.rank <= 3 ? medals[entry.rank - 1] : `#${entry.rank}`}
              </div>

              {/* name */}
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: isMe ? 'var(--accent)' : 'var(--text)' }}>
                  {entry.student_name} {isMe && <span style={{ fontSize: 12, fontWeight: 400 }}>(you)</span>}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', gap: 12, marginTop: 2, flexWrap: 'wrap' }}>
                  {entry.quiz_avg != null && <span>Quiz avg: {entry.quiz_avg}</span>}
                  {entry.project_avg != null && <span>Project: {entry.project_avg}</span>}
                  {entry.weekly_avg != null && <span>Weekly: {entry.weekly_avg}</span>}
                  <span>{entry.total_commits} commits</span>
                  <span>{entry.total_submissions} submissions</span>
                </div>
              </div>

              {/* overall score bar */}
              <div style={{ width: 120, display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ flex: 1, background: 'var(--surface)', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                  <div style={{
                    width: `${entry.overall_avg}%`, height: '100%',
                    background: entry.overall_avg >= 70 ? 'var(--accent3)' : entry.overall_avg >= 50 ? 'var(--accent2)' : 'var(--danger)',
                    borderRadius: 4, transition: 'width 0.4s',
                  }} />
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, width: 40, textAlign: 'right',
                  color: entry.overall_avg >= 70 ? 'var(--accent3)' : entry.overall_avg >= 50 ? 'var(--accent2)' : 'var(--danger)' }}>
                  {entry.overall_avg}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const miniCard = {
  background: 'var(--surface)', borderRadius: 8, padding: '8px 10px',
  border: '1px solid var(--border)',
}
const miniLabel = { fontSize: 11, color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: 2 }
const miniValue = { fontSize: 18, fontWeight: 700, color: 'var(--text)' }

/* ── Analytics Panel ── */
function AnalyticsPanel({ classId, isTeacher }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAnalytics(classId).then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [classId])

  if (loading) return <div style={{ textAlign: 'center', padding: 40 }}><Spinner /></div>
  if (!data || !data.scores.length) {
    return <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>
      {isTeacher ? 'No student submissions yet. Analytics will appear once students take quizzes.' : 'No submissions yet. Take a quiz to see your analytics here.'}
    </div>
  }

  const maxScore = 100
  const barColors = (score) => score >= 70 ? 'var(--accent3)' : score >= 50 ? 'var(--accent2)' : 'var(--danger)'

  return (
    <div>
      {/* summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Average', value: data.average, suffix: '/100', color: barColors(data.average) },
          { label: 'Best Score', value: data.best, suffix: '/100', color: 'var(--accent3)' },
          { label: 'Lowest', value: data.worst, suffix: '/100', color: 'var(--danger)' },
          { label: 'Submissions', value: data.total_submissions, suffix: '', color: 'var(--accent)' },
          { label: 'Class Average', value: data.class_average, suffix: '/100', color: 'var(--accent)' },
          { label: 'Students', value: data.student_count, suffix: '', color: 'var(--muted)' },
        ].map((item, i) => (
          <div key={i} style={{ ...card, textAlign: 'center', padding: '16px 12px', marginBottom: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 6 }}>
              {item.label}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: item.color }}>
              {item.value ?? '—'}<span style={{ fontSize: 14, fontWeight: 400 }}>{item.suffix}</span>
            </div>
          </div>
        ))}
      </div>

      {/* score bar chart */}
      <div style={card}>
        <SectionTitle>Score History</SectionTitle>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.scores.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 160, fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {isTeacher ? s.student_name : s.title}
              </div>
              <div style={{ flex: 1, background: 'var(--surface2)', borderRadius: 6, height: 24, position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  width: `${(s.score / maxScore) * 100}%`, height: '100%',
                  background: barColors(s.score), borderRadius: 6,
                  transition: 'width 0.4s ease',
                }} />
              </div>
              <div style={{ width: 50, textAlign: 'right', fontSize: 14, fontWeight: 700, color: barColors(s.score) }}>
                {s.score}
              </div>
              <div style={{ width: 70, fontSize: 12, color: 'var(--muted)', textAlign: 'right' }}>
                {new Date(s.date).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ── AI Tutor Chat (text only) ── */
function TutorChat({ classId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const bottomRef = { current: null }

  useEffect(() => {
    api.getChatHistory(classId).then((h) => { setMessages(h); setLoaded(true) }).catch(() => setLoaded(true))
  }, [classId])

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'student', content: text, created_at: new Date().toISOString() }])
    setSending(true)
    try {
      const reply = await api.sendChatMessage(classId, text)
      setMessages((prev) => [...prev, reply])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'tutor', content: `Error: ${err.message}`, created_at: new Date().toISOString() }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', height: 520, padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent)' }}>AI Tutor</div>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Ask questions about the course materials</div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {!loaded && <div style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', marginTop: 40 }}>Loading...</div>}
        {loaded && messages.length === 0 && (
          <div style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', marginTop: 40, lineHeight: 1.8 }}>
            No messages yet. Ask a question about the study materials!<br />
            <span style={{ fontSize: 13 }}>e.g. &quot;Explain binary search&quot; or &quot;What is overfitting?&quot;</span>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            alignSelf: msg.role === 'student' ? 'flex-end' : 'flex-start',
            maxWidth: '80%',
          }}>
            <div style={{
              padding: '10px 14px',
              borderRadius: msg.role === 'student' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
              background: msg.role === 'student' ? 'var(--accent)' : 'var(--surface2)',
              color: msg.role === 'student' ? '#fff' : 'var(--text)',
              fontSize: 14, lineHeight: 1.6,
              border: msg.role === 'tutor' ? '1px solid var(--border)' : 'none',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3, textAlign: msg.role === 'student' ? 'right' : 'left' }}>
              {msg.role === 'student' ? 'You' : 'AI Tutor'}
            </div>
          </div>
        ))}
        {sending && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
            <div style={{
              padding: '10px 14px', borderRadius: '14px 14px 14px 4px',
              background: 'var(--surface2)', border: '1px solid var(--border)',
              fontSize: 14, color: 'var(--muted)',
            }}>
              Thinking...
            </div>
          </div>
        )}
        <div ref={(el) => { bottomRef.current = el }} />
      </div>

      <form onSubmit={send} style={{
        display: 'flex', gap: 8, padding: '12px 16px',
        borderTop: '1px solid var(--border)', background: 'var(--surface)',
      }}>
        <input
          className="tf-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the AI tutor a question..."
          disabled={sending}
          style={{ flex: 1, margin: 0 }}
        />
        <button type="submit" className="tf-btn" disabled={sending || !input.trim()}
          style={{ padding: '8px 20px', fontSize: 13, flexShrink: 0 }}>
          Send
        </button>
      </form>
    </div>
  )
}

/* ── Sarvam AI Voice Tutor ── */
function VoiceTutor({ classId }) {
  const [languages, setLanguages] = useState(null)
  const [voiceLang, setVoiceLang] = useState('hi-IN')
  const [recording, setRecording] = useState(false)
  const [mediaRec, setMediaRec] = useState(null)
  const [busy, setBusy] = useState(false)
  const [conversation, setConversation] = useState([])
  const [loaded, setLoaded] = useState(false)
  const bottomRef = { current: null }

  useEffect(() => {
    api.getVoiceLanguages(classId).then((l) => { setLanguages(l); setLoaded(true) }).catch(() => setLoaded(true))
  }, [classId])

  useEffect(() => {
    if (bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [conversation])

  const isConfigured = languages?.configured
  const langMap = languages?.languages || {
    'hi-IN': 'Hindi', 'bn-IN': 'Bengali', 'ta-IN': 'Tamil', 'te-IN': 'Telugu',
    'mr-IN': 'Marathi', 'gu-IN': 'Gujarati', 'kn-IN': 'Kannada', 'ml-IN': 'Malayalam',
    'pa-IN': 'Punjabi', 'od-IN': 'Odia', 'en-IN': 'English',
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks = []
      mr.ondataavailable = (e) => chunks.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const reader = new FileReader()
        reader.onloadend = async () => {
          const b64 = reader.result.split(',')[1]
          setBusy(true)
          setConversation(prev => [...prev, { role: 'student', content: `Recording in ${langMap[voiceLang] || voiceLang}...`, processing: true }])
          try {
            const result = await api.sendVoiceChat(classId, b64, voiceLang)
            setConversation(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                role: 'student',
                content: result.student_text || result.student_text_english,
                lang: langMap[voiceLang],
              }
              return [...updated, {
                role: 'tutor',
                content: result.tutor_reply || result.tutor_reply_english,
                englishContent: result.tutor_reply_english,
                audio_b64: result.audio_b64,
                lang: langMap[result.language] || langMap[voiceLang],
              }]
            })
            if (result.audio_b64) {
              try {
                const audioBytes = Uint8Array.from(atob(result.audio_b64), c => c.charCodeAt(0))
                const audioBlob = new Blob([audioBytes], { type: 'audio/wav' })
                const url = URL.createObjectURL(audioBlob)
                new Audio(url).play()
              } catch {}
            }
          } catch (err) {
            setConversation(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = { role: 'student', content: 'Could not process audio' }
              return [...updated, { role: 'tutor', content: `Error: ${err.message}` }]
            })
          } finally {
            setBusy(false)
          }
        }
        reader.readAsDataURL(blob)
      }
      mr.start()
      setMediaRec(mr)
      setRecording(true)
    } catch {
      alert('Microphone access denied. Please allow microphone access in your browser settings.')
    }
  }

  function stopRecording() {
    if (mediaRec) { mediaRec.stop(); setMediaRec(null) }
    setRecording(false)
  }

  function playAudio(b64) {
    if (!b64) return
    try {
      const audioBytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
      const audioBlob = new Blob([audioBytes], { type: 'audio/wav' })
      new Audio(URL.createObjectURL(audioBlob)).play()
    } catch {}
  }

  return (
    <div>
      {/* header card */}
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(108,92,231,0.06), rgba(0,184,148,0.06))', border: '1.5px solid rgba(108,92,231,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <span style={{ fontSize: 32 }}>🎙️</span>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--font-head)' }}>
              Multilingual Voice Tutor
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>
              Powered by Sarvam AI — speak in your language, get answers spoken back
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
          {Object.entries(langMap).map(([code, name]) => (
            <button key={code} type="button" onClick={() => setVoiceLang(code)} style={{
              padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 500, cursor: 'pointer',
              background: voiceLang === code ? 'rgba(108,92,231,0.1)' : 'var(--surface)',
              color: voiceLang === code ? 'var(--accent)' : 'var(--muted)',
              border: `1.5px solid ${voiceLang === code ? 'var(--accent)' : 'var(--border)'}`,
              transition: 'all 0.12s',
            }}>
              {name}
            </button>
          ))}
        </div>

        {!isConfigured && loaded && (
          <div style={{
            padding: '14px 16px', borderRadius: 10, marginBottom: 12,
            background: 'rgba(224,136,0,0.06)', border: '1px solid rgba(224,136,0,0.15)',
            fontSize: 13, lineHeight: 1.6, color: 'var(--text)',
          }}>
            <strong style={{ color: 'var(--accent2)' }}>Setup Required:</strong> To enable voice chat, add your Sarvam AI API key to the backend <code>.env</code> file:
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, marginTop: 8, padding: '8px 12px', background: 'var(--surface)', borderRadius: 6, border: '1px solid var(--border)' }}>
              SARVAM_API_KEY=your_api_key_here
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
              Get a free API key at <strong>sarvam.ai</strong> — supports Hindi, Tamil, Telugu, Bengali, Marathi, and 6 more Indian languages.
            </div>
          </div>
        )}

        {/* record button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {!recording ? (
            <button type="button" onClick={startRecording} disabled={busy || !isConfigured}
              style={{
                padding: '14px 32px', borderRadius: 30, fontSize: 15, fontWeight: 700,
                background: isConfigured ? 'var(--accent)' : 'var(--surface2)',
                color: isConfigured ? '#fff' : 'var(--muted)',
                border: 'none', cursor: isConfigured ? 'pointer' : 'not-allowed',
                display: 'flex', alignItems: 'center', gap: 10,
                boxShadow: isConfigured ? '0 4px 16px rgba(108,92,231,0.3)' : 'none',
                transition: 'all 0.2s',
              }}>
              <span style={{ fontSize: 20 }}>🎤</span>
              {busy ? 'Processing...' : 'Start Recording'}
            </button>
          ) : (
            <button type="button" onClick={stopRecording}
              style={{
                padding: '14px 32px', borderRadius: 30, fontSize: 15, fontWeight: 700,
                background: 'var(--danger)', color: '#fff', border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 10,
                boxShadow: '0 4px 16px rgba(224,68,68,0.3)',
              }}>
              <span style={{ fontSize: 20, display: 'inline-block', animation: 'pulse 1s infinite' }}>⏹️</span>
              Stop Recording
            </button>
          )}
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>
            Selected: <strong style={{ color: 'var(--text)' }}>{langMap[voiceLang]}</strong>
          </div>
        </div>
      </div>

      {/* conversation */}
      {conversation.length > 0 && (
        <div style={card}>
          <SectionTitle>Conversation</SectionTitle>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {conversation.map((msg, i) => (
              <div key={i} style={{
                alignSelf: msg.role === 'student' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}>
                <div style={{
                  padding: '12px 16px',
                  borderRadius: msg.role === 'student' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                  background: msg.role === 'student' ? 'var(--accent)' : 'var(--surface2)',
                  color: msg.role === 'student' ? '#fff' : 'var(--text)',
                  fontSize: 14, lineHeight: 1.6,
                  border: msg.role === 'tutor' ? '1px solid var(--border)' : 'none',
                  whiteSpace: 'pre-wrap',
                  opacity: msg.processing ? 0.6 : 1,
                }}>
                  {msg.content}
                  {msg.englishContent && msg.content !== msg.englishContent && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(0,0,0,0.08)', fontSize: 12, opacity: 0.7 }}>
                      (English: {msg.englishContent})
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                    {msg.role === 'student' ? 'You' : 'AI Tutor'}{msg.lang ? ` · ${msg.lang}` : ''}
                  </span>
                  {msg.audio_b64 && (
                    <button type="button" onClick={() => playAudio(msg.audio_b64)}
                      style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, padding: 0 }}>
                      🔊 Play again
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          {busy && (
            <div style={{ marginTop: 12, fontSize: 14, color: 'var(--muted)', fontStyle: 'italic' }}>
              Processing your voice... (STT → Translate → AI → Translate → TTS)
            </div>
          )}
          <div ref={(el) => { bottomRef.current = el }} />
        </div>
      )}
    </div>
  )
}

/* ── styles ── */
/* ── Lectures (attendance via class-summary grading) ── */
function LecturesPanel({ classId, role, userId, userName }) {
  const isTeacher = role === 'teacher'
  const [lectures, setLectures]   = useState([])
  const [loading,  setLoading]    = useState(true)
  const [err,      setErr]        = useState('')
  const [creating, setCreating]   = useState(false)
  const [report,   setReport]     = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    api.listLectures(classId)
      .then((data) => { setLectures(data); setErr('') })
      .catch((e)   => setErr(String(e.message || e)))
      .finally(()  => setLoading(false))
    if (isTeacher) {
      api.getAttendanceReport(classId).then(setReport).catch(() => {})
    }
  }, [classId, isTeacher])

  useEffect(() => { load() }, [load])

  return (
    <div>
      {isTeacher && (
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <SectionTitle>Lectures</SectionTitle>
            <button type="button" className="tf-btn-outline" style={{ padding: '4px 12px', fontSize: 12 }}
                    onClick={() => setCreating((v) => !v)}>
              {creating ? 'Cancel' : '+ New lecture'}
            </button>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 13, margin: 0 }}>
            Upload a class transcript. Students submit summaries, AI grades them, and attendance is auto-granted above your threshold (you can override).
          </p>
          {creating && (
            <div style={{ marginTop: 14 }}>
              <CreateLectureForm classId={classId} onCreated={() => { setCreating(false); load() }} onCancel={() => setCreating(false)} />
            </div>
          )}
        </div>
      )}

      {isTeacher && report && report.length > 0 && (
        <div style={card}>
          <SectionTitle color="var(--accent2)">Attendance Summary</SectionTitle>
          <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--muted)', borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '6px 8px' }}>Student</th>
                <th style={{ padding: '6px 8px' }}>Attended</th>
                <th style={{ padding: '6px 8px' }}>%</th>
              </tr>
            </thead>
            <tbody>
              {report.map((r) => (
                <tr key={r.student_id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '6px 8px' }}>{r.student_name}</td>
                  <td style={{ padding: '6px 8px' }}>{r.attended} / {r.total_lectures}</td>
                  <td style={{ padding: '6px 8px', fontWeight: 600,
                              color: r.percent >= 75 ? 'var(--accent3)' : r.percent >= 50 ? 'var(--accent2)' : 'var(--danger)' }}>
                    {r.percent}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {err && <div style={errBox}>{err}</div>}
      {loading && <Spinner />}
      {!loading && lectures.length === 0 && (
        <div style={{ ...card, color: 'var(--muted)', fontSize: 14 }}>
          {isTeacher ? 'No lectures yet. Upload a transcript to get started.' : 'No lectures yet.'}
        </div>
      )}
      {lectures.map((lec) => (
        <LectureCard key={lec.id} classId={classId} lecture={lec}
                     isTeacher={isTeacher} userId={userId} userName={userName} onRefresh={load} />
      ))}
    </div>
  )
}

function CreateLectureForm({ classId, onCreated, onCancel }) {
  const [title, setTitle]         = useState('')
  const [threshold, setThreshold] = useState(6)
  const [heldAt, setHeldAt]       = useState('')
  const [transcriptText, setText] = useState('')
  const [file, setFile]           = useState(null)
  const [busy, setBusy]           = useState(false)
  const [err, setErr]             = useState('')

  async function submit(e) {
    e.preventDefault()
    if (!title.trim()) { setErr('Title is required.'); return }
    if (!file && !transcriptText.trim()) { setErr('Provide a transcript file or paste the text.'); return }
    setBusy(true); setErr('')
    try {
      await api.createLecture(classId, { title: title.trim(), threshold, heldAt, transcriptText, file })
      onCreated()
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} style={{ padding: 14, borderRadius: 10, background: 'rgba(108,92,231,0.04)',
                                     border: '1px solid rgba(108,92,231,0.1)' }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
        <div style={{ flex: '1 1 240px' }}>
          <label className="tf-label">Title</label>
          <input className="tf-input" placeholder="e.g. Lecture 7 — Hash Tables" value={title}
                 onChange={(e) => setTitle(e.target.value)} style={{ width: '100%', margin: 0 }} />
        </div>
        <div>
          <label className="tf-label">Threshold (0–10)</label>
          <input className="tf-input" type="number" min={0} max={10} value={threshold}
                 onChange={(e) => setThreshold(Math.max(0, Math.min(10, +e.target.value || 0)))}
                 style={{ width: 100 }} />
        </div>
        <div>
          <label className="tf-label">Held at (optional)</label>
          <input className="tf-input" type="datetime-local" value={heldAt}
                 onChange={(e) => setHeldAt(e.target.value)} style={{ width: 200 }} />
        </div>
      </div>
      <div style={{ marginBottom: 10 }}>
        <label className="tf-label">Transcript file (PDF, DOCX, TXT…)</label>
        <input type="file" accept=".pdf,.docx,.doc,.txt,.md,.pptx"
               onChange={(e) => setFile(e.target.files?.[0] || null)}
               style={{ fontSize: 13 }} />
      </div>
      <div style={{ marginBottom: 10 }}>
        <label className="tf-label">…or paste transcript text</label>
        <textarea className="tf-input" rows={6} placeholder="Paste the lecture transcript here"
                  value={transcriptText} onChange={(e) => setText(e.target.value)}
                  style={{ width: '100%', margin: 0, resize: 'vertical' }} />
      </div>
      {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 8 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8 }}>
        <button type="submit" className="tf-btn" disabled={busy}>{busy ? 'Creating…' : 'Create lecture'}</button>
        <button type="button" className="tf-btn-outline" onClick={onCancel} disabled={busy}>Cancel</button>
      </div>
    </form>
  )
}

function LectureCard({ classId, lecture, isTeacher, userId, userName, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [summary,  setSummary]  = useState('')
  const [busy,     setBusy]     = useState(false)
  const [err,      setErr]      = useState('')
  const [subs,     setSubs]     = useState([])
  const [loadingSubs, setLoadingSubs] = useState(false)

  const mySub = lecture.my_submission

  async function submitSummary(e) {
    e.preventDefault()
    if (!summary.trim()) return
    setBusy(true); setErr('')
    try {
      await api.submitLectureSummary(classId, lecture.id, summary.trim())
      setSummary('')
      onRefresh()
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setBusy(false)
    }
  }

  function loadSubs() {
    setLoadingSubs(true)
    api.listLectureSummaries(classId, lecture.id)
      .then(setSubs)
      .catch(() => {})
      .finally(() => setLoadingSubs(false))
  }

  async function override(ssid, granted) {
    try {
      await api.overrideAttendance(classId, ssid, granted)
      loadSubs()
      onRefresh()
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  async function removeLecture() {
    if (!confirm(`Delete lecture "${lecture.title}" and all its summaries?`)) return
    try {
      await api.deleteLecture(classId, lecture.id)
      onRefresh()
    } catch (e) {
      setErr(String(e.message || e))
    }
  }

  return (
    <div style={{ ...card, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', cursor: 'pointer' }}
           onClick={() => { const next = !expanded; setExpanded(next); if (next && isTeacher) loadSubs() }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 18 }}>🎓</span>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{lecture.title}</div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {lecture.file_name && <span>📎 {lecture.file_name}</span>}
            <span>Threshold: {lecture.threshold}/10</span>
            {lecture.held_at && <span>Held: {new Date(lecture.held_at).toLocaleString()}</span>}
            {isTeacher && <span>{lecture.submission_count || 0} summaries</span>}
            {!isTeacher && mySub && (
              <span style={{ color: mySub.attendance_granted ? 'var(--accent3)' : 'var(--danger)', fontWeight: 600 }}>
                {mySub.attendance_granted ? '✓ Attendance granted' : '✗ Attendance not granted'} (score {mySub.ai_score != null ? `${mySub.ai_score}/10` : '—'})
              </span>
            )}
          </div>
        </div>
        <span style={{ fontSize: 18, color: 'var(--muted)', transform: expanded ? 'rotate(180deg)' : '' }}>▼</span>
      </div>

      {expanded && (
        <div style={{ marginTop: 16 }}>
          {/* student: submit/edit summary */}
          {!isTeacher && (
            <form onSubmit={submitSummary} style={{ padding: 14, borderRadius: 10,
                                                    background: 'rgba(108,92,231,0.04)',
                                                    border: '1px solid rgba(108,92,231,0.1)', marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>
                {mySub ? 'Resubmit your summary' : 'Submit your class summary'}
              </div>
              <textarea className="tf-input" rows={6} placeholder="In your own words, summarise what was covered…"
                        value={summary} onChange={(e) => setSummary(e.target.value)}
                        style={{ width: '100%', margin: 0, resize: 'vertical' }} />
              {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 6 }}>{err}</div>}
              <button type="submit" className="tf-btn" disabled={busy || !summary.trim()}
                      style={{ marginTop: 10, padding: '8px 18px', fontSize: 13 }}>
                {busy ? 'Grading…' : 'Submit'}
              </button>
            </form>
          )}

          {/* student: own grading detail */}
          {!isTeacher && mySub && <SummaryDetail sub={mySub} />}

          {/* teacher: see transcript + all submissions */}
          {isTeacher && lecture.transcript && (
            <details style={{ marginBottom: 12 }}>
              <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 600, color: 'var(--accent)' }}>
                View transcript
              </summary>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, fontFamily: 'var(--font-mono)',
                             background: 'var(--surface2)', padding: 14, borderRadius: 10,
                             border: '1px solid var(--border)', maxHeight: 400, overflowY: 'auto', marginTop: 6 }}>
                {lecture.transcript}
              </pre>
            </details>
          )}

          {isTeacher && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                  Student Summaries
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="button" className="tf-btn-outline" style={{ padding: '4px 12px', fontSize: 12 }}
                          onClick={loadSubs}>Refresh</button>
                  <button type="button" className="tf-btn-outline"
                          style={{ padding: '4px 12px', fontSize: 12, color: 'var(--accent3)', borderColor: 'rgba(16,185,129,0.3)' }}
                          onClick={() => api.downloadAttendanceExcel(classId, lecture.id, lecture.title)}>⬇ Download Excel</button>
                  <button type="button" className="tf-btn-outline"
                          style={{ padding: '4px 12px', fontSize: 12, color: 'var(--danger)', borderColor: 'rgba(224,68,68,0.3)' }}
                          onClick={removeLecture}>Delete lecture</button>
                </div>
              </div>
              {loadingSubs && <Spinner />}
              {!loadingSubs && subs.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>No summaries submitted yet.</div>
              )}
              {subs.map((s) => (
                <TeacherSummaryRow key={s.id} sub={s} onOverride={(g) => override(s.id, g)} />
              ))}
              {err && <div style={errBox}>{err}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SummaryDetail({ sub }) {
  return (
    <div style={{ marginTop: 12, padding: 14, borderRadius: 10, background: 'var(--surface2)',
                  border: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: 28, fontWeight: 700,
                      color: sub.attendance_granted ? 'var(--accent3)' : 'var(--danger)' }}>
          {sub.ai_score != null ? `${sub.ai_score}/10` : '—'}
        </div>
        <div style={{ fontSize: 13, color: 'var(--muted)' }}>
          {sub.teacher_override !== null && sub.teacher_override !== undefined
            ? `Teacher ${sub.teacher_override ? 'granted' : 'denied'} attendance.`
            : sub.attendance_granted ? 'Attendance auto-granted by AI.' : 'AI score below threshold — attendance not granted.'}
        </div>
      </div>
      {sub.ai_feedback && (
        <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text)', marginBottom: 8 }}>
          {sub.ai_feedback}
        </div>
      )}
      {(sub.concepts_covered?.length || 0) > 0 && (
        <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 4 }}>
          <strong style={{ color: 'var(--accent3)' }}>Covered:</strong> {sub.concepts_covered.join(', ')}
        </div>
      )}
      {(sub.concepts_missed?.length || 0) > 0 && (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          <strong style={{ color: 'var(--danger)' }}>Missed:</strong> {sub.concepts_missed.join(', ')}
        </div>
      )}
    </div>
  )
}

function TeacherSummaryRow({ sub, onOverride }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ padding: 12, borderRadius: 10, border: '1px solid var(--border)', marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
           onClick={() => setOpen((v) => !v)}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{sub.student_name}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
            Submitted {new Date(sub.submitted_at).toLocaleString()}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18, fontWeight: 700,
                        color: sub.attendance_granted ? 'var(--accent3)' : 'var(--danger)' }}>
            {sub.ai_score != null ? `${sub.ai_score}/10` : '—'}
          </span>
          <span style={{ fontSize: 12, fontWeight: 600,
                        color: sub.attendance_granted ? 'var(--accent3)' : 'var(--danger)' }}>
            {sub.attendance_granted ? '✓ present' : '✗ absent'}
          </span>
          <span style={{ fontSize: 16, color: 'var(--muted)', transform: open ? 'rotate(180deg)' : '' }}>▼</span>
        </div>
      </div>
      {open && (
        <div style={{ marginTop: 10 }}>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.5,
                         background: 'var(--surface2)', padding: 10, borderRadius: 8,
                         border: '1px solid var(--border)', marginBottom: 8 }}>
            {sub.summary_text}
          </pre>
          {sub.ai_feedback && (
            <div style={{ fontSize: 13, color: 'var(--text)', marginBottom: 8 }}>
              <strong>AI feedback: </strong>{sub.ai_feedback}
            </div>
          )}
          {(sub.concepts_covered?.length || 0) > 0 && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 2 }}>
              <strong style={{ color: 'var(--accent3)' }}>Covered:</strong> {sub.concepts_covered.join(', ')}
            </div>
          )}
          {(sub.concepts_missed?.length || 0) > 0 && (
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>
              <strong style={{ color: 'var(--danger)' }}>Missed:</strong> {sub.concepts_missed.join(', ')}
            </div>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="tf-btn"
                    style={{ padding: '6px 14px', fontSize: 12 }}
                    onClick={() => onOverride(true)}>Mark present</button>
            <button type="button" className="tf-btn-outline"
                    style={{ padding: '6px 14px', fontSize: 12, color: 'var(--danger)', borderColor: 'rgba(224,68,68,0.3)' }}
                    onClick={() => onOverride(false)}>Mark absent</button>
          </div>
        </div>
      )}
    </div>
  )
}


const card = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 14,
  padding: 20,
  marginBottom: 12,
  boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
}

const codeBadge = {
  fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
  color: 'var(--accent)', background: 'rgba(108,92,231,0.07)', padding: '3px 10px', borderRadius: 6,
}

const pillStyle = (active) => ({
  padding: '8px 16px', borderRadius: 20, fontSize: 13, fontWeight: 500, cursor: 'pointer',
  textTransform: 'capitalize',
  background: active ? 'rgba(108,92,231,0.08)' : 'var(--surface2)',
  color: active ? 'var(--accent)' : 'var(--muted)',
  border: `1.5px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
  transition: 'all 0.12s',
})

const errBox = {
  background: 'rgba(224,68,68,0.06)', border: '1px solid rgba(224,68,68,0.15)',
  color: 'var(--danger)', padding: '10px 14px', borderRadius: 10, fontSize: 13, margin: '12px 0',
}
