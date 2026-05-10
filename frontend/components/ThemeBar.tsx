import { THEME_LABELS } from '@/lib/consts'
import clsx from 'clsx'

interface Props {
  themes: Record<string, number>
}

function scoreColor(score: number): string {
  if (score >= 0.75) return 'bg-green-500'
  if (score >= 0.5)  return 'bg-amber-400'
  return 'bg-red-400'
}

export default function ThemeBar({ themes }: Props) {
  const sorted = Object.entries(themes)
    .filter(([, v]) => typeof v === 'number')
    .sort(([, a], [, b]) => b - a)

  if (sorted.length === 0) return null

  return (
    <div className="space-y-3">
      {sorted.map(([key, score]) => (
        <div key={key}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-700 font-medium">{THEME_LABELS[key] ?? key}</span>
            <span className="text-gray-500">{Math.round(score * 100)}%</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full transition-all duration-500', scoreColor(score))}
              style={{ width: `${score * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
