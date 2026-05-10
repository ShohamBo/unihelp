import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import Link from 'next/link'
import { getProgramDetail, getPrograms } from '@/lib/api'
import { DEGREE_LABELS } from '@/lib/consts'
import ThemeBar from '@/components/ThemeBar'
import ProsConsCard from '@/components/ProsConsCard'
import LeadForm from '@/components/LeadForm'

interface Params {
  institution: string
  program: string
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  try {
    const p = await getProgramDetail(params.institution, params.program)
    return {
      title: `${p.name_he} — ${p.institution_name_he}`,
      description: p.summary?.summary_he
        ? p.summary.summary_he.slice(0, 160)
        : `${DEGREE_LABELS[p.degree_level]} ב${p.institution_name_he}. ${p.description_he.slice(0, 120)}`,
    }
  } catch {
    return { title: 'תוכנית לימוד | מסלול' }
  }
}

export async function generateStaticParams() {
  try {
    const data = await getPrograms({ page: 1 })
    return data.results.map(p => ({
      institution: p.institution_slug,
      program: p.slug,
    }))
  } catch {
    return []
  }
}

export const revalidate = 3600

export default async function ProgramDetailPage({ params }: { params: Params }) {
  let program
  try {
    program = await getProgramDetail(params.institution, params.program)
  } catch {
    notFound()
  }

  const { summary, admission, top_snippets } = program

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6 flex gap-2 flex-wrap">
        <Link href="/" className="hover:text-brand-700">בית</Link>
        <span>/</span>
        <Link href={`/?institution=${program.institution_slug}`} className="hover:text-brand-700">
          {program.institution_name_he}
        </Link>
        <span>/</span>
        <span className="text-gray-800">{program.name_he}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-8">

          {/* Hero */}
          <div>
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="badge bg-brand-100 text-brand-700">
                {DEGREE_LABELS[program.degree_level]}
              </span>
              {program.is_dual_major && (
                <span className="badge bg-amber-50 text-amber-700">דו-חוגי</span>
              )}
              {program.is_extended && (
                <span className="badge bg-purple-50 text-purple-700">מורחב</span>
              )}
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2 leading-tight">
              {program.name_he}
            </h1>
            <p className="text-xl text-gray-600">
              {program.institution_name_he}
              {program.faculty_name_he && ` · ${program.faculty_name_he}`}
              {program.institution_city && ` · ${program.institution_city}`}
            </p>
          </div>

          {/* Key stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {program.duration_years && (
              <StatBox label="משך לימודים" value={`${program.duration_years} שנים`} />
            )}
            {program.total_credits && (
              <StatBox label='נ"ז' value={String(program.total_credits)} />
            )}
            {admission?.psychometric_min && (
              <StatBox label="פסיכומטרי מינימום" value={String(admission.psychometric_min)} />
            )}
            {admission?.last_year_threshold && (
              <StatBox label="סף קבלה אחרון" value={String(admission.last_year_threshold)} />
            )}
          </div>

          {/* AI Summary */}
          {summary && (
            <section>
              <SectionTitle>מה אומרים הסטודנטים</SectionTitle>
              <div className="card p-6">
                <p className="text-gray-700 leading-relaxed text-base">{summary.summary_he}</p>
                <p className="text-xs text-gray-400 mt-4">
                  מבוסס על {summary.snippet_count} ביקורות · עודכן {new Date(summary.last_generated_at).toLocaleDateString('he-IL')}
                </p>
              </div>
            </section>
          )}

          {/* Pros / Cons */}
          {summary && (summary.pros_he.length > 0 || summary.cons_he.length > 0) && (
            <section>
              <SectionTitle>יתרונות וחסרונות</SectionTitle>
              <ProsConsCard pros={summary.pros_he} cons={summary.cons_he} />
            </section>
          )}

          {/* Theme breakdown */}
          {summary?.themes_breakdown && Object.keys(summary.themes_breakdown).length > 0 && (
            <section>
              <SectionTitle>פירוט נושאים</SectionTitle>
              <div className="card p-6">
                <ThemeBar themes={summary.themes_breakdown} />
              </div>
            </section>
          )}

          {/* Sample snippets */}
          {top_snippets.length > 0 && (
            <section>
              <SectionTitle>ביקורות נבחרות</SectionTitle>
              <div className="space-y-4">
                {top_snippets.map(s => (
                  <blockquote key={s.id} className="card p-5 border-s-4 border-brand-200">
                    <p className="text-gray-700 text-sm leading-relaxed italic">
                      &ldquo;{s.raw_text.slice(0, 280)}{s.raw_text.length > 280 ? '...' : ''}&rdquo;
                    </p>
                    <footer className="mt-3 text-xs text-gray-400 flex gap-3">
                      <span>{s.source_name}</span>
                      {s.posted_at && (
                        <span>{new Date(s.posted_at).toLocaleDateString('he-IL')}</span>
                      )}
                    </footer>
                  </blockquote>
                ))}
              </div>
            </section>
          )}

          {/* Admission requirements */}
          {admission && (admission.bagrut_requirements_he || admission.additional_requirements_he) && (
            <section>
              <SectionTitle>דרישות קבלה</SectionTitle>
              <div className="card p-6 space-y-3 text-sm text-gray-700">
                {admission.bagrut_requirements_he && (
                  <p>{admission.bagrut_requirements_he}</p>
                )}
                {admission.additional_requirements_he && (
                  <p>{admission.additional_requirements_he}</p>
                )}
              </div>
            </section>
          )}

          {program.canonical_url && (
            <a
              href={program.canonical_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-brand-600 hover:underline"
            >
              לדף הרשמי של התוכנית ↗
            </a>
          )}
        </div>

        {/* Sidebar — lead form */}
        <aside className="lg:col-span-1">
          <div className="card p-6 sticky top-20">
            <h2 className="text-lg font-bold text-gray-900 mb-1">מעוניין/ת בתוכנית?</h2>
            <p className="text-sm text-gray-500 mb-4">קבל פרטים ישירות מ{program.institution_name_he}</p>
            <LeadForm
              programSlug={program.slug}
              institutionSlug={program.institution_slug}
              programName={program.name_he}
            />
          </div>

          {/* Compare CTA */}
          <div className="mt-4 card p-4 text-center">
            <p className="text-sm text-gray-600 mb-2">רוצה להשוות עם תוכניות אחרות?</p>
            <Link
              href={`/compare?programs=${program.institution_slug}__${program.slug}`}
              className="btn-outline text-sm w-full block text-center"
            >
              הוסף להשוואה
            </Link>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-xl font-bold text-gray-800 mb-4">{children}</h2>
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4 text-center">
      <div className="text-2xl font-bold text-brand-700">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}
