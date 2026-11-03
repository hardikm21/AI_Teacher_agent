'use client'
import { useState } from 'react'

export default function QuizRunner({ quiz, mode = 'practice', onFinish, onSubmit }) {
  const [answers, setAnswers] = useState(Array(quiz.questions.length).fill(''))
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const score = submitted && mode === 'practice'
    ? quiz.questions.reduce((acc, q, i) =>
        (answers[i] || '').toUpperCase().startsWith(q.correct_answer.toUpperCase())
          ? acc + 1 : acc, 0)
    : 0

  function pick(qi, letter) {
    if (submitted) return
    const next = [...answers]; next[qi] = letter; setAnswers(next)
  }

  async function handleSubmit() {
    if (mode === 'assignment' && onSubmit) {
      setSubmitting(true)
      try {
        await onSubmit(answers)
        setSubmitted(true)
      } finally {
        setSubmitting(false)
      }
    } else {
      setSubmitted(true)
    }
  }

  const allAnswered = answers.every((a) => a)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: 'var(--muted)' }}>
        <span style={{ fontWeight: 600, color: 'var(--text)' }}>{quiz.title}</span>
        <span style={{
          fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
          background: 'rgba(108,92,231,0.07)', color: 'var(--accent)',
        }}>{quiz.difficulty}</span>
        <span>{quiz.questions.length} questions</span>
      </div>

      {quiz.questions.map((q, qi) => {
        const chosen = answers[qi]
        return (
          <div key={qi} style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 18,
          }}>
            <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 15, lineHeight: 1.4 }}>
              {qi + 1}. {q.question}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {q.options.map((opt, oi) => {
                const letter = opt.trim()[0]
                const picked = chosen === letter
                const right  = q.correct_answer === letter
                let bg = 'var(--surface2)'
                let border = 'var(--border)'
                let color = 'var(--text)'
                if (submitted && mode === 'practice' && right) {
                  bg = 'rgba(0,184,148,0.1)'; border = 'var(--accent3)'; color = '#047857'
                } else if (submitted && mode === 'practice' && picked && !right) {
                  bg = 'rgba(224,68,68,0.08)'; border = 'var(--danger)'; color = 'var(--danger)'
                } else if (picked) {
                  bg = 'rgba(108,92,231,0.08)'; border = 'var(--accent)'; color = 'var(--accent)'
                }
                return (
                  <button
                    key={oi}
                    onClick={() => pick(qi, letter)}
                    disabled={submitted}
                    style={{
                      textAlign: 'left',
                      padding: '10px 14px',
                      borderRadius: 8,
                      fontSize: 14,
                      color,
                      background: bg,
                      border: `1.5px solid ${border}`,
                      cursor: submitted ? 'default' : 'pointer',
                      transition: 'all 0.12s',
                      fontWeight: picked ? 500 : 400,
                    }}
                  >
                    {opt}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}

      {!submitted ? (
        <button
          className="tf-btn"
          disabled={!allAnswered || submitting}
          onClick={handleSubmit}
          style={{ alignSelf: 'flex-start' }}
        >
          {submitting ? 'Submitting...' : (mode === 'assignment' ? 'Submit answers' : 'Check answers')}
        </button>
      ) : mode === 'practice' ? (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 18,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
        }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', marginBottom: 4 }}>
              Your score
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: score >= quiz.questions.length * 0.7 ? 'var(--accent3)' : 'var(--accent2)' }}>
              {score} / {quiz.questions.length}
            </div>
          </div>
          <button
            className="tf-btn-outline"
            onClick={() => onFinish && onFinish({ score, total: quiz.questions.length })}
          >
            Done
          </button>
        </div>
      ) : (
        <div style={{
          background: 'rgba(0,184,148,0.06)',
          border: '1px solid rgba(0,184,148,0.15)',
          borderRadius: 12,
          padding: 18,
          color: '#047857',
          fontSize: 14,
          fontWeight: 500,
        }}>
          Your answers have been submitted and evaluated by AI. Check your results below.
        </div>
      )}
    </div>
  )
}
