const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeader() {
  if (typeof window === 'undefined') return {}
  const tok = localStorage.getItem('tf_token')
  return tok ? { Authorization: `Bearer ${tok}` } : {}
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  }
  if (body) opts.body = JSON.stringify(body)

  let res
  try {
    res = await fetch(`${API}${path}`, opts)
  } catch (e) {
    throw new Error(`Cannot reach API at ${API}. Is the backend running?`)
  }

  if (!res.ok) {
    const text = await res.text()
    // FastAPI wraps errors in {"detail": "..."} — surface that cleanly.
    let msg = text || `${res.status} ${res.statusText}`
    try {
      const parsed = JSON.parse(text)
      if (typeof parsed.detail === 'string') msg = parsed.detail
    } catch { /* non-JSON body, keep raw */ }
    throw new Error(msg)
  }
  return res.json()
}

// ── Sessions ──────────────────────────────────────────────────────────────────
export const startSession = (body) =>
  request('POST', '/sessions/start', body)

export const getSession = (sessionId) =>
  request('GET', `/sessions/${sessionId}`)

export const deleteSession = (sessionId) =>
  request('DELETE', `/sessions/${sessionId}`)

// ── Prerequisite ──────────────────────────────────────────────────────────────
export const submitPrereqQuiz = (sessionId, answers) =>
  request('POST', `/prereq/${sessionId}/submit`, { answers })

export const getPrereqStatus = (sessionId) =>
  request('GET', `/prereq/${sessionId}/status`)

// ── Planning ──────────────────────────────────────────────────────────────────
export const submitApproach = (sessionId, approach) =>
  request('POST', `/planning/${sessionId}/approach`, { approach })

export const getRoadmap = (sessionId) =>
  request('GET', `/planning/${sessionId}/roadmap`)

export const getAnalysis = (sessionId) =>
  request('GET', `/planning/${sessionId}/analysis`)

// ── Weekly ────────────────────────────────────────────────────────────────────
export const startWeek = (sessionId) =>
  request('POST', `/weekly/${sessionId}/start`)

export const checkCompletion = (sessionId) =>
  request('POST', `/weekly/${sessionId}/check`)

export const overrideCompletion = (sessionId) =>
  request('POST', `/weekly/${sessionId}/override-complete`)

export const getTaskQuiz = (sessionId) =>
  request('GET', `/weekly/${sessionId}/quiz`)

export const submitTaskQuiz = (sessionId, answers) =>
  request('POST', `/weekly/${sessionId}/quiz/submit`, { answers })

export const getWeeklyTasks = (sessionId) =>
  request('GET', `/weekly/${sessionId}/tasks`)

export const getWeeklyScore = (sessionId) =>
  request('GET', `/weekly/${sessionId}/score`)

// ── Teacher ───────────────────────────────────────────────────────────────────
export const getProjects = () =>
  request('GET', '/projects')

export const createProject = (body) =>
  request('POST', '/projects', body)

export const getDashboard = () =>
  request('GET', '/dashboard')

// ── Classrooms (demo) ─────────────────────────────────────────────────────────
export const listClasses = () =>
  request('GET', '/classes')

export const createClass = (body) =>
  request('POST', '/classes', body)

export const getClass = (cid) =>
  request('GET', `/classes/${cid}`)

export const generateClassQuiz = (cid, body) =>
  request('POST', `/classes/${cid}/quiz`, body)

export const generatePracticeQuiz = (cid, body) =>
  request('POST', `/classes/${cid}/practice`, body)

export const listClassSubmissions = (cid) =>
  request('GET', `/classes/${cid}/submissions`)

export const uploadClassMaterial = (cid, body) =>
  request('POST', `/classes/${cid}/materials`, body)

export async function uploadClassMaterialFile(cid, title, file) {
  const form = new FormData()
  form.append('title', title)
  form.append('file', file)
  const tok = typeof window !== 'undefined' ? localStorage.getItem('tf_token') : null
  const headers = tok ? { Authorization: `Bearer ${tok}` } : {}
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const res = await fetch(`${API}/classes/${cid}/materials/upload`, { method: 'POST', headers, body: form })
  if (!res.ok) {
    const text = await res.text()
    let msg = text
    try { const p = JSON.parse(text); if (typeof p.detail === 'string') msg = p.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const deleteClassMaterial = (cid, mid) =>
  request('DELETE', `/classes/${cid}/materials/${mid}`)

export const evaluateSubmission = (sid, body) =>
  request('POST', `/classes/submissions/${sid}/evaluate`, body)

export const joinClass = (body) =>
  request('POST', '/classes/join', body)

export const listAssignments = (cid) =>
  request('GET', `/classes/${cid}/assignments`)

export const submitQuizAnswers = (quizId, answers) =>
  request('POST', `/classes/assignments/${quizId}/submit`, { answers })

export const mySubmissions = (cid) =>
  request('GET', `/classes/${cid}/my-submissions`)

export const getStream = (cid) =>
  request('GET', `/classes/${cid}/stream`)

export const postMessage = (cid, body) =>
  request('POST', `/classes/${cid}/messages`, body)

export const createPoll = (cid, body) =>
  request('POST', `/classes/${cid}/polls`, body)

export const votePoll = (pid, optionIndex) =>
  request('POST', `/classes/polls/${pid}/vote`, { option_index: optionIndex })

export const getChatHistory = (cid) =>
  request('GET', `/classes/${cid}/chat`)

export const sendChatMessage = (cid, message) =>
  request('POST', `/classes/${cid}/chat`, { message })

export const getAnalytics = (cid) =>
  request('GET', `/classes/${cid}/analytics`)

export const getNotifications = () =>
  request('GET', '/notifications')

export const getUnreadCount = () =>
  request('GET', '/notifications/unread-count')

export const markNotificationsRead = () =>
  request('POST', '/notifications/mark-read')

export const getVoiceLanguages = (cid) =>
  request('GET', `/classes/${cid}/voice/languages`)

export const sendVoiceChat = (cid, audioB64, languageCode) =>
  request('POST', `/classes/${cid}/voice`, { audio_b64: audioB64, language_code: languageCode })

// ── Projects ─────────────────────────────────────────────────────────────────
export const listProjects = (cid) =>
  request('GET', `/classes/${cid}/projects`)

export const createProjectJSON = (cid, body) =>
  request('POST', `/classes/${cid}/projects`, body)

export async function createProjectFile(cid, title, dueDate, file) {
  const form = new FormData()
  form.append('title', title)
  form.append('due_date', dueDate || '')
  form.append('file', file)
  const tok = typeof window !== 'undefined' ? localStorage.getItem('tf_token') : null
  const headers = tok ? { Authorization: `Bearer ${tok}` } : {}
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const res = await fetch(`${API_URL}/classes/${cid}/projects/upload`, { method: 'POST', headers, body: form })
  if (!res.ok) {
    const text = await res.text()
    let msg = text
    try { const p = JSON.parse(text); if (typeof p.detail === 'string') msg = p.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const submitProject = (projectId, githubUrl) =>
  request('POST', `/classes/projects/${projectId}/submit`, { github_url: githubUrl })

export const listProjectSubmissions = (projectId) =>
  request('GET', `/classes/projects/${projectId}/submissions`)

export const checkProjectProgress = (psid) =>
  request('POST', `/classes/project-submissions/${psid}/check-progress`)

export const evaluateProjectAI = (psid) =>
  request('POST', `/classes/project-submissions/${psid}/evaluate-ai`)

export const evaluateProjectTeacher = (psid, body) =>
  request('POST', `/classes/project-submissions/${psid}/evaluate`, body)

export const recordWeeklySnapshot = (psid) =>
  request('POST', `/classes/project-submissions/${psid}/weekly-snapshot`)

export const getProjectChat = (pid) =>
  request('GET', `/classes/projects/${pid}/chat`)

export const sendProjectChat = (pid, message) =>
  request('POST', `/classes/projects/${pid}/chat`, { message })

export const getLeaderboard = (cid) =>
  request('GET', `/classes/${cid}/leaderboard`)

// ── Lectures + attendance summaries ──────────────────────────────────────────
export const listLectures = (cid) =>
  request('GET', `/classes/${cid}/lectures`)

export async function createLecture(cid, { title, threshold, heldAt, transcriptText, file }) {
  const form = new FormData()
  form.append('title', title)
  form.append('threshold', String(threshold ?? 60))
  if (heldAt) form.append('held_at', heldAt)
  if (transcriptText) form.append('transcript_text', transcriptText)
  if (file) form.append('file', file)
  const tok = typeof window !== 'undefined' ? localStorage.getItem('tf_token') : null
  const headers = tok ? { Authorization: `Bearer ${tok}` } : {}
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const res = await fetch(`${API_URL}/classes/${cid}/lectures`, { method: 'POST', headers, body: form })
  if (!res.ok) {
    const text = await res.text()
    let msg = text
    try { const p = JSON.parse(text); if (typeof p.detail === 'string') msg = p.detail } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const deleteLecture = (cid, lid) =>
  request('DELETE', `/classes/${cid}/lectures/${lid}`)

export const submitLectureSummary = (cid, lid, summary) =>
  request('POST', `/classes/${cid}/lectures/${lid}/summary`, { summary })

export const listLectureSummaries = (cid, lid) =>
  request('GET', `/classes/${cid}/lectures/${lid}/summaries`)

export const overrideAttendance = (cid, ssid, granted) =>
  request('POST', `/classes/${cid}/summary-submissions/${ssid}/override`, { granted })

export const getAttendanceReport = (cid) =>
  request('GET', `/classes/${cid}/attendance`)

export async function downloadAttendanceExcel(cid, lid, lectureTitle) {
  const res = await fetch(`${API}/classes/${cid}/lectures/${lid}/attendance-excel`, {
    method: 'GET',
    headers: authHeader(),
  })
  if (!res.ok) throw new Error('Failed to download attendance sheet')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `attendance_${(lectureTitle || 'lecture').replace(/\s+/g, '_')}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const registerUser = (body) =>
  request('POST', '/auth/register', body)

export const loginUser = (body) =>
  request('POST', '/auth/login', body)

export const getMe = () =>
  request('GET', '/auth/me')

export const logoutUser = () =>
  request('POST', '/auth/logout')
