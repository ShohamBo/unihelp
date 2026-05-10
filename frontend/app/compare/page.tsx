'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getProgramDetailClient, searchPrograms } from '@/lib/api'
import { DEGREE_LABELS, THEME_LABELS } from '@/lib/consts'
import type { ProgramDetail, ProgramListItem } from '@/lib/types'
import LeadForm from '@/components/LeadForm'

const MAX_PROGRAMS = 4

function parseKeys(raw: string | null): Array<[string, string]> {
  if (!raw) return []
  return raw
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
    .map(s => {
      const idx = s.indexOf('__')
      if (idx === -1) return null
      return [s.slice(0, idx), s.slice(idx + 2)] as [string, string]
    })
    .filter((x): x is [string, string] => x !== null)
    .slice(0, MAX_PROGRAMS)
}

function toKey(institution: string, slug: string) {
  return `${institution}__${slug}`
}

// ── Theme bar ─────────────────────────────────────────────────────────────────

function MiniThemeBar({ score }: { score: number }) {
  const color = score >= 0.75 ? 'bg-green-500' : score >= 0.5 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden w-full">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${score * 100}%` }} />
    </div>
  )
}

// ── Add-program search widget ─────────────────────────────────────────────────

function AddProgramSearch({ onAdd, disabledKeys }: {
  onAdd: (p: ProgramListItem) => void
  disabledKeys: string[]
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProgramListItem[]>([])
  const [open, setOpen] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function handleChange(v: string) {
    setQuery(v)
    if (timerRef.current) clearTimeout(timerRef.current)
    if (!v.trim()) { setResults([]); setOpen(false); return }
    timerRef.current = setTimeout(async () => {
      const data = await searchPrograms(v)
      setResults(data)
      setOpen(true)
    }, 300)
  }

  function pick(p: ProgramListItem) {
    onAdd(p)
    setQuery('')
    setResults([])
    setOpen(false)
  }

  return (
    <div className="relative">
      <input
        className="input text-sm"
        placeholder="חפש תוכנית להוספה..."
        value={query}
        onChange={e => handleChange(e.target.value)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onFocus={() => results.length > 0 && setOpen(true)}
        dir="rtl"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {results.map(p => {
            const key = toKey(p.institution_slug, p.slug)
            const disabled = disabledKeys.includes(key)
            return (
              <li key={p.id}>
                <button
                  className="w-full text-right px-4 py-3 text-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed flex flex-col"
                  disabled={disabled}
                  onMouseDown={() => !disabled && pick(p)}
                >
                  <span className="font-medium text-gray-900">{p.name_he}</span>
                  <span className="text-xs text-gray-500">{p.institution_name_he} · {DEGREE_LABELS[p.degree_level]}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ComparePage() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const [keys, setKeys] = useState<Array<[string, string]>>(() =>
    parseKeys(searchParams.get('programs'))
  )
  const [programs, setPrograms] = useState<Record<string, ProgramDetail | null>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const fetchProgram = useCallback(async (institution: string, slug: string) => {
    const key = toKey(institution, slug)
    setLoading(prev => ({ ...prev, [key]: true }))
    const data = await getProgramDetailClient(institution, slug)
    setPrograms(prev => ({ ...prev, [key]: data }))
    setLoading(prev => ({ ...prev, [key]: false }))
  }, [])

  useEffect(() => {
    for (const [inst, slug] of keys) {
      const key = toKey(inst, slug)
      if (!(key in programs)) fetchProgram(inst, slug)
    }
  }, [keys, programs, fetchProgram])

  function syncUrl(newKeys: Array<[string, string]>) {
    const raw = newKeys.map(([i, s]) => toKey(i, s)).join(',')
    router.replace(`/compare?programs=${encodeURIComponent(raw)}`, { scroll: false })
  }

  function addProgram(p: ProgramListItem) {
    if (keys.length >= MAX_PROGRAMS) return
    const pair: [string, string] = [p.institution_slug, p.slug]
    const newKeys = [...keys, pair]
    setKeys(newKeys)
    syncUrl(newKeys)
  }

  function removeProgram(institution: string, slug: string) {
    const newKeys = keys.filter(([i, s]) => !(i === institution && s === slug))
    setKeys(newKeys)
    syncUrl(newKeys)
  }

  const loaded = keys.map(([i, s]) => programs[toKey(i, s)] ?? null).filter(Boolean) as ProgramDetail[]
  const disabledKeys = keys.map(([i, s]) => toKey(i, s))

  // Collect all theme keys across programs
  const allThemes = Array.from(
    new Set(loaded.flatMap(p => p.summary ? Object.keys(p.summary.themes_breakdown) : []))
  )

  function row(label: string, cells: React.ReactNode[]) {
    return (
      <tr className="border-b border-gray-100 last:border-0">
        <td className="py-3 pe-4 text-sm font-medium text-gray-600 whitespace-nowrap align-top min-w-[120px]">
          {label}
        </td>
        {cells.map((cell, i) => (
          <td key={i} className="py-3 px-3 text-sm text-gray-800 align-top">
            {cell}
          </td>
        ))}
        {/* Empty cells for missing columns */}
        {Array.from({ length: MAX_PROGRAMS - cells.length - 1 }).map((_, i) => (
          <td key={`empty-${i}`} className="py-3 px-3" />
        ))}
      </tr>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <nav className="text-sm text-gray-500 mb-6 flex gap-2">
        <Link href="/" className="hover:text-brand-700">בית</Link>
        <span>/</span>
        <span className="text-gray-800">השוואת תוכניות</span>
      </nav>

      <h1 className="text-3xl font-bold text-gray-900 mb-2">השוואת תוכניות לימוד</h1>
      <p className="text-gray-500 mb-8 text-sm">השווה עד {MAX_PROGRAMS} תוכניות זו לצד זו</p>

      {/* Add program */}
      {keys.length < MAX_PROGRAMS && (
        <div className="mb-8 max-w-sm">
          <AddProgramSearch onAdd={addProgram} disabledKeys={disabledKeys} />
        </div>
      )}

      {keys.length === 0 && (
        <div className="text-center py-24 text-gray-400">
          <div className="text-5xl mb-4">⚖️</div>
          <p className="text-lg font-medium text-gray-600">לא נבחרו תוכניות להשוואה</p>
          <p className="text-sm mt-2">חפש תוכניות בשדה למעלה או עבור לדף תוכנית ולחץ "הוסף להשוואה"</p>
          <Link href="/" className="mt-6 btn-primary inline-block">חזרה לחיפוש</Link>
        </div>
      )}

      {keys.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="py-3 pe-4 text-start text-sm text-gray-400 font-normal min-w-[120px]" />
                {keys.map(([inst, slug]) => {
                  const key = toKey(inst, slug)
                  const p = programs[key]
                  const isLoading = loading[key]
                  return (
                    <th key={key} className="py-3 px-3 text-start min-w-[180px] align-top">
                      {isLoading ? (
                        <div className="animate-pulse space-y-2">
                          <div className="h-4 bg-gray-200 rounded w-3/4" />
                          <div className="h-3 bg-gray-100 rounded w-1/2" />
                        </div>
                      ) : p ? (
                        <div>
                          <Link
                            href={`/programs/${inst}/${slug}`}
                            className="font-bold text-gray-900 hover:text-brand-700 text-base leading-tight block"
                          >
                            {p.name_he}
                          </Link>
                          <div className="text-xs text-gray-500 mt-1">{p.institution_name_he}</div>
                          <button
                            className="mt-2 text-xs text-red-400 hover:text-red-600"
                            onClick={() => removeProgram(inst, slug)}
                          >
                            הסר ✕
                          </button>
                        </div>
                      ) : (
                        <div className="text-sm text-red-400">לא נמצא</div>
                      )}
                    </th>
                  )
                })}
              </tr>
            </thead>

            <tbody>
              {row('מוסד', keys.map(([i, s]) => programs[toKey(i, s)]?.institution_name_he ?? '—'))}
              {row('פקולטה', keys.map(([i, s]) => programs[toKey(i, s)]?.faculty_name_he ?? '—'))}
              {row('דרגה', keys.map(([i, s]) => {
                const p = programs[toKey(i, s)]
                return p ? DEGREE_LABELS[p.degree_level] : '—'
              }))}
              {row('משך לימודים', keys.map(([i, s]) => {
                const p = programs[toKey(i, s)]
                return p?.duration_years ? `${p.duration_years} שנים` : '—'
              }))}
              {row('נ"ז', keys.map(([i, s]) => {
                const p = programs[toKey(i, s)]
                return p?.total_credits ? String(p.total_credits) : '—'
              }))}
              {row('פסיכומטרי מינימום', keys.map(([i, s]) => {
                const p = programs[toKey(i, s)]
                return p?.admission?.psychometric_min ? String(p.admission.psychometric_min) : '—'
              }))}
              {row('סף קבלה אחרון', keys.map(([i, s]) => {
                const p = programs[toKey(i, s)]
                return p?.admission?.last_year_threshold ? String(p.admission.last_year_threshold) : '—'
              }))}

              {/* Pros */}
              <tr className="border-b border-gray-100">
                <td className="py-3 pe-4 text-sm font-medium text-green-700 whitespace-nowrap align-top">
                  יתרונות
                </td>
                {keys.map(([i, s]) => {
                  const p = programs[toKey(i, s)]
                  const pros = p?.summary?.pros_he?.slice(0, 3) ?? []
                  return (
                    <td key={toKey(i, s)} className="py-3 px-3 align-top">
                      {pros.length > 0 ? (
                        <ul className="space-y-1">
                          {pros.map((pro, idx) => (
                            <li key={idx} className="text-xs text-gray-700 flex gap-1">
                              <span className="text-green-500 shrink-0">✓</span>{pro}
                            </li>
                          ))}
                        </ul>
                      ) : <span className="text-sm text-gray-400">—</span>}
                    </td>
                  )
                })}
              </tr>

              {/* Cons */}
              <tr className="border-b border-gray-100">
                <td className="py-3 pe-4 text-sm font-medium text-red-600 whitespace-nowrap align-top">
                  חסרונות
                </td>
                {keys.map(([i, s]) => {
                  const p = programs[toKey(i, s)]
                  const cons = p?.summary?.cons_he?.slice(0, 3) ?? []
                  return (
                    <td key={toKey(i, s)} className="py-3 px-3 align-top">
                      {cons.length > 0 ? (
                        <ul className="space-y-1">
                          {cons.map((con, idx) => (
                            <li key={idx} className="text-xs text-gray-700 flex gap-1">
                              <span className="text-red-400 shrink-0">✗</span>{con}
                            </li>
                          ))}
                        </ul>
                      ) : <span className="text-sm text-gray-400">—</span>}
                    </td>
                  )
                })}
              </tr>

              {/* Theme scores */}
              {allThemes.map(themeKey => (
                <tr key={themeKey} className="border-b border-gray-100 last:border-0">
                  <td className="py-3 pe-4 text-sm font-medium text-gray-600 whitespace-nowrap align-middle">
                    {THEME_LABELS[themeKey] ?? themeKey}
                  </td>
                  {keys.map(([i, s]) => {
                    const p = programs[toKey(i, s)]
                    const score = p?.summary?.themes_breakdown?.[themeKey]
                    return (
                      <td key={toKey(i, s)} className="py-3 px-3 align-middle">
                        {score != null ? (
                          <div className="space-y-1">
                            <MiniThemeBar score={score} />
                            <span className="text-xs text-gray-500">{Math.round(score * 100)}%</span>
                          </div>
                        ) : <span className="text-sm text-gray-400">—</span>}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lead form for all compared programs */}
      {loaded.length > 0 && (
        <section className="mt-12 card p-8 max-w-lg mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-1 text-center">
            מעוניין/ת בתוכניות אלה?
          </h2>
          <p className="text-sm text-gray-500 mb-6 text-center">
            קבל פרטים מ{loaded.length > 1 ? 'כל המוסדות' : loaded[0].institution_name_he} ישירות
          </p>
          <LeadForm
            programName={loaded.map(p => p.name_he).join(', ')}
          />
        </section>
      )}

      {/* Share link */}
      {keys.length > 0 && (
        <div className="mt-8 text-center">
          <button
            className="btn-outline text-sm"
            onClick={() => {
              navigator.clipboard.writeText(window.location.href)
                .then(() => alert('הקישור הועתק!'))
                .catch(() => {})
            }}
          >
            העתק קישור להשוואה
          </button>
        </div>
      )}
    </div>
  )
}
