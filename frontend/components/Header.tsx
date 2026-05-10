'use client'

import Link from 'next/link'
import { useState } from 'react'
import SearchBar from './SearchBar'

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center gap-4">
        {/* Logo */}
        <Link href="/" className="text-xl font-bold text-brand-700 shrink-0 me-4">
          מסלול
        </Link>

        {/* Search — hidden on mobile, shown on md+ */}
        <div className="hidden md:flex flex-1 max-w-lg">
          <SearchBar compact />
        </div>

        <nav className="hidden md:flex items-center gap-6 ms-auto text-sm font-medium text-gray-600">
          <Link href="/" className="hover:text-brand-700 transition-colors">בית</Link>
          <Link href="/compare" className="hover:text-brand-700 transition-colors">השוואה</Link>
          <Link href="/quiz" className="hover:text-brand-700 transition-colors">שאלון התאמה</Link>
          <Link href="/about" className="hover:text-brand-700 transition-colors">אודות</Link>
        </nav>

        {/* Mobile menu toggle */}
        <button
          className="md:hidden ms-auto p-2 rounded-lg hover:bg-gray-100 transition-colors"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="תפריט"
        >
          <div className="w-5 h-0.5 bg-gray-700 mb-1" />
          <div className="w-5 h-0.5 bg-gray-700 mb-1" />
          <div className="w-5 h-0.5 bg-gray-700" />
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 pb-4">
          <div className="pt-3 pb-2">
            <SearchBar compact />
          </div>
          <nav className="flex flex-col gap-1 text-sm font-medium text-gray-700">
            {[
              ['/', 'בית'],
              ['/compare', 'השוואה'],
              ['/quiz', 'שאלון התאמה'],
              ['/about', 'אודות'],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  )
}
