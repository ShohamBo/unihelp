import Link from 'next/link'

const INSTITUTIONS = [
  ['tau', 'אוניברסיטת תל אביב'],
  ['huji', 'האוניברסיטה העברית'],
  ['technion', 'הטכניון'],
  ['bgu', 'אוניברסיטת בן גוריון'],
  ['biu', 'אוניברסיטת בר אילן'],
  ['haifa', 'אוניברסיטת חיפה'],
]

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300 pt-12 pb-6 mt-16">
      <div className="max-w-6xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Brand */}
        <div>
          <span className="text-white text-lg font-bold">מסלול</span>
          <p className="mt-2 text-sm text-gray-400 leading-relaxed">
            פלטפורמת השוואת תארים אקדמיים לסטודנטים ישראלים. מבוסס על ביקורות אמיתיות, נתוני קבלה, ותוכן לימודים עדכני.
          </p>
        </div>

        {/* Institutions */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-3">מוסדות</h3>
          <ul className="space-y-1.5 text-sm">
            {INSTITUTIONS.map(([slug, name]) => (
              <li key={slug}>
                <Link href={`/?institution=${slug}`} className="hover:text-white transition-colors">
                  {name}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Links */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-3">קישורים</h3>
          <ul className="space-y-1.5 text-sm">
            {[
              ['/about', 'אודות'],
              ['/compare', 'השוואת תארים'],
              ['/quiz', 'שאלון התאמה'],
              ['/privacy', 'מדיניות פרטיות'],
            ].map(([href, label]) => (
              <li key={href}>
                <Link href={href} className="hover:text-white transition-colors">{label}</Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 mt-10 pt-6 border-t border-gray-800 text-center text-xs text-gray-500">
        © {new Date().getFullYear()} מסלול. כל הזכויות שמורות.
      </div>
    </footer>
  )
}
