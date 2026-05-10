import Link from 'next/link'
import clsx from 'clsx'
import { type ProgramListItem } from '@/lib/types'
import { DEGREE_LABELS } from '@/lib/consts'

interface Props {
  program: ProgramListItem
  className?: string
}

const DEGREE_COLORS: Record<string, string> = {
  ba: 'bg-blue-50 text-blue-700',
  ma: 'bg-purple-50 text-purple-700',
  phd: 'bg-green-50 text-green-700',
}

export default function ProgramCard({ program, className }: Props) {
  const href = `/programs/${program.institution_slug}/${program.slug}`

  return (
    <Link href={href} className={clsx('card block p-5 hover:shadow-md transition-shadow group', className)}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className={clsx('badge', DEGREE_COLORS[program.degree_level] ?? 'bg-gray-100 text-gray-600')}>
          {DEGREE_LABELS[program.degree_level] ?? program.degree_level}
        </span>
        {program.is_dual_major && (
          <span className="badge bg-amber-50 text-amber-700">דו-חוגי</span>
        )}
      </div>

      <h3 className="text-base font-bold text-gray-900 group-hover:text-brand-700 transition-colors leading-snug mb-1">
        {program.name_he}
      </h3>

      <p className="text-sm text-gray-500 mb-3">{program.institution_name_he}</p>

      <div className="flex gap-4 text-xs text-gray-400">
        {program.duration_years && (
          <span>{program.duration_years} שנים</span>
        )}
        {program.total_credits && (
          <span>{program.total_credits} נ"ז</span>
        )}
      </div>
    </Link>
  )
}
