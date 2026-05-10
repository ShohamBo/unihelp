interface Props {
  pros: string[]
  cons: string[]
}

export default function ProsConsCard({ pros, cons }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="card p-5 border-green-100">
        <h3 className="font-bold text-green-700 mb-3 flex items-center gap-2">
          <span>✅</span> יתרונות
        </h3>
        <ul className="space-y-2">
          {pros.map((pro, i) => (
            <li key={i} className="text-sm text-gray-700 flex gap-2">
              <span className="text-green-500 mt-0.5 shrink-0">•</span>
              {pro}
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-5 border-red-100">
        <h3 className="font-bold text-red-700 mb-3 flex items-center gap-2">
          <span>⚠️</span> חסרונות
        </h3>
        <ul className="space-y-2">
          {cons.map((con, i) => (
            <li key={i} className="text-sm text-gray-700 flex gap-2">
              <span className="text-red-400 mt-0.5 shrink-0">•</span>
              {con}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
