import { Suspense } from 'react'
import { getPrograms, getInstitutions } from '@/lib/api'
import ProgramCard from '@/components/ProgramCard'
import SearchBar from '@/components/SearchBar'
import { FIELD_CATEGORIES, DEGREE_LABELS } from '@/lib/consts'
import Link from 'next/link'

interface SearchParams {
  search?: string
  institution?: string
  degree_level?: string
  page?: string
}

export default async function HomePage({ searchParams }: { searchParams: SearchParams }) {
  const [programsData, institutions] = await Promise.all([
    getPrograms({
      search: searchParams.search,
      institution: searchParams.institution,
      degree_level: searchParams.degree_level,
      page: searchParams.page ? Number(searchParams.page) : 1,
    }).catch(() => ({ count: 0, next: null, previous: null, results: [] })),
    getInstitutions().catch(() => []),
  ])

  const isFiltered = !!(searchParams.search || searchParams.institution || searchParams.degree_level)

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-to-br from-brand-800 via-brand-700 to-brand-600 text-white py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
            מצא את התואר שמתאים לך
          </h1>
          <p className="text-lg md:text-xl text-blue-100 mb-8 max-w-xl mx-auto">
            השוואה אמיתית בין תארים ראשונים בישראל — לפי ביקורות סטודנטים, סף קבלה, ותוכן לימודים
          </p>
          <div className="max-w-xl mx-auto">
            <SearchBar />
          </div>
        </div>
      </section>

      {/* Field categories */}
      {!isFiltered && (
        <section className="max-w-6xl mx-auto px-4 py-8">
          <h2 className="text-lg font-semibold text-gray-700 mb-4">חפש לפי תחום</h2>
          <div className="flex flex-wrap gap-2">
            {FIELD_CATEGORIES.map(cat => (
              <Link
                key={cat.query}
                href={`/?search=${encodeURIComponent(cat.query)}`}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-brand-400 hover:text-brand-700 transition-colors shadow-sm"
              >
                <span>{cat.icon}</span>
                {cat.label}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Filters row */}
      <section className="max-w-6xl mx-auto px-4 pb-4">
        <form className="flex flex-wrap gap-3 items-center">
          {/* Institution filter */}
          <select
            name="institution"
            defaultValue={searchParams.institution ?? ''}
            className="input w-auto text-sm py-2"
          >
            <option value="">כל המוסדות</option>
            {institutions.map(i => (
              <option key={i.slug} value={i.slug}>{i.name_he}</option>
            ))}
          </select>

          {/* Degree level filter */}
          <select
            name="degree_level"
            defaultValue={searchParams.degree_level ?? ''}
            className="input w-auto text-sm py-2"
          >
            <option value="">כל הדרגות</option>
            {Object.entries(DEGREE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>

          <button type="submit" className="btn-primary text-sm py-2">
            סנן
          </button>

          {isFiltered && (
            <Link href="/" className="text-sm text-gray-500 hover:text-gray-700 underline">
              נקה סינון
            </Link>
          )}
        </form>
      </section>

      {/* Program grid */}
      <section className="max-w-6xl mx-auto px-4 pb-16">
        {isFiltered && searchParams.search && (
          <h2 className="text-xl font-bold text-gray-800 mb-4">
            תוצאות עבור &ldquo;{searchParams.search}&rdquo;
            <span className="text-base font-normal text-gray-500 me-2">
              ({programsData.count} תוצאות)
            </span>
          </h2>
        )}

        {!isFiltered && (
          <h2 className="text-xl font-bold text-gray-800 mb-4">תוכניות לימוד</h2>
        )}

        {programsData.results.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            <div className="text-4xl mb-4">🔍</div>
            <p className="text-lg font-medium">לא נמצאו תוכניות</p>
            <p className="text-sm mt-1">נסה לשנות את מונחי החיפוש</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {programsData.results.map(p => (
              <ProgramCard key={p.id} program={p} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {(programsData.next || programsData.previous) && (
          <div className="flex justify-center gap-3 mt-8">
            {programsData.previous && (
              <Link
                href={`?page=${Number(searchParams.page ?? 1) - 1}`}
                className="btn-outline text-sm"
              >
                הקודם
              </Link>
            )}
            {programsData.next && (
              <Link
                href={`?page=${Number(searchParams.page ?? 1) + 1}`}
                className="btn-primary text-sm"
              >
                הבא
              </Link>
            )}
          </div>
        )}
      </section>

      {/* CTA strip */}
      <section className="bg-brand-700 text-white py-12 px-4 text-center">
        <h2 className="text-2xl font-bold mb-3">לא בטוח מה לבחור?</h2>
        <p className="text-blue-100 mb-6 max-w-md mx-auto">
          ענה על כמה שאלות קצרות ונמצא לך את התוכניות שהכי מתאימות לך
        </p>
        <Link href="/quiz" className="bg-white text-brand-700 font-bold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors inline-block">
          התחל שאלון התאמה
        </Link>
      </section>
    </>
  )
}
