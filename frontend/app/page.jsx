'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthed } from '@/lib/auth'

export default function HomePage() {
  const router = useRouter()
  useEffect(() => {
    router.replace(isAuthed() ? '/classes' : '/signin')
  }, [router])
  return null
}
