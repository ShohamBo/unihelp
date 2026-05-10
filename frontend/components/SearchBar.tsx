'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { searchPrograms } from '@/lib/api'
import { type ProgramListItem } from '@/lib/types'
import { DEGREE_LABELS } from '@/lib/consts'
import clsx from 'clsx'

interface Props {
  compact?: boolean
}

export default function SearchBar({ compact }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProgramListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const containerRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  const search = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return }
    setLoading(true)
    try {
      const data = await searchPrograms(q)
      setResults(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => search(query), 300)
    return () => clearTimeout(debounceRef.current)
  }, [query, search])

  // Close on outside click
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) {
      router.push(`/?search=${encodeURIComponent(query.trim())}`)
      setOpen(false)
    }
    if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <input
          type="search"
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={compact ? 'חיפוש תוארים...' : 'חפש תואר, מוסד או תחום לימוד...'}
          className={clsx(
            'input ps-10',
            compact ? 'h-9 text-sm' : 'h-12 text-base shadow-sm',
          )}
          aria-label="חיפוש תארים"
        />
        <span className="absolute start-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
          🔍
        </span>
        {loading && (
          <span className="absolute end-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs">
            טוען...
          </span>
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden max-h-80 overflow-y-auto">
          {results.map(p => (
            <li key={p.id}>
              <Link
                href={`/programs/${p.institution_slug}/${p.slug}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                onClick={() => { setOpen(false); setQuery('') }}
              >
                <div>
                  <div className="text-sm font-semibold text-gray-900">{p.name_he}</div>
                  <div className="text-xs text-gray-500">{p.institution_name_he}</div>
                </div>
                <span className="text-xs text-gray-400 shrink-0 ms-4">
                  {DEGREE_LABELS[p.degree_level]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
